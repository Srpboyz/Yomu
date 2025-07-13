from datetime import datetime

from bs4 import BeautifulSoup, Tag
from dateparser import parse
from PyQt6.QtNetwork import QSslConfiguration, QSslSocket
from yomu.core.network import Request, Response, Url
from yomu.source import Chapter, MangaList, Manga, Page, Source


class MangaFire(Source):
    BASE_URL = "https://mangafire.to"
    supports_latest = True
    supports_search = True

    def url_to_slug(self, url: str) -> str:
        return url.replace(self.BASE_URL, "")

    def get_latest(self, page: int) -> Request:
        url = Url(f"{MangaFire.BASE_URL}/filter")
        url.add_params({"language[]": "en", "sort": "recently_updated", "page": page})
        return Request(url)

    def parse_latest(self, response: Response) -> MangaList:
        return self.parse_search_results(response)

    def search_for_manga(self, query: str) -> Request:
        query = query.replace(" ", "+")

        url = Url(f"{MangaFire.BASE_URL}/filter")
        url.add_params({"keyword": query, "language[]": "en"})
        return Request(url)

    def manga_from_element(self, element: Tag) -> Manga:
        a = element.select_one(".info > a")

        title = a.text
        thumbnail = element.select_one("img").attrs["src"]
        url = Url(self.url_to_slug(a.attrs["href"]))
        url.setFragment(None)

        return Manga(title=title, thumbnail=thumbnail, url=url.toString())

    def parse_search_results(self, response: Response) -> MangaList:
        document = BeautifulSoup(response.read_all().data(), features="html.parser")
        mangas = list(
            map(
                self.manga_from_element,
                document.select(".original.card-lg .unit .inner"),
            )
        )
        has_next_page = bool(
            document.select_one(".page-item.active + .page-item .page-link")
        )
        return MangaList(mangas=mangas, has_next_page=has_next_page)

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(MangaFire.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response) -> Manga:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        document = html.select_one(".main-inner:not(.manga-bottom)")

        title = document.select_one("h1").get_text(" ", True)
        description = html.select_one("#synopsis .modal-content").get_text(" ", True)
        author = document.select_one(
            '.meta span:-soup-contains("Author:") + span'
        ).get_text(" ", True)
        thumbnail_url = document.select_one(".poster img").attrs["src"]
        url = Url(self.url_to_slug(response.url().toString()))
        url.setFragment(None)

        return Manga(
            title=title,
            description=description,
            author=author,
            thumbnail=thumbnail_url,
            url=url.toString(),
        )

    def _parse_chapter_from_elements(
        self, manga: Tag, read: Tag, number: int
    ) -> Chapter:
        assert manga.attrs["data-number"] == read.attrs["data-number"]

        manga = manga.select_one("a")
        spans = manga.select("span")

        title = spans[0].text.strip()
        uploaded = parse(spans[-1].text) or datetime.now()
        url = Url(self.url_to_slug(read.attrs["href"]))
        url.setFragment(read.attrs["data-id"])
        url = url.toString()

        return Chapter(number=number, title=title, uploaded=uploaded, url=url)

    def get_chapters(self, manga: Manga) -> Request:
        if (index := manga.url.find(".")) == -1:
            raise Exception("Manga Id not found")
        manga_id = manga.url[index + 1 :]

        url = Url(f"{MangaFire.BASE_URL}/ajax/manga/{manga_id}/chapter/en")
        url.setFragment(str(manga_id))
        return Request(url)

    def parse_chapters(self, response: Response) -> list[Chapter]:
        document = BeautifulSoup(response.json()["result"], features="html.parser")
        manga_list = document.select("li")

        manga_id = response.url().fragment()
        response = self.network.handle_request(
            Request(
                f"{MangaFire.BASE_URL}/ajax/read/{manga_id}/chapter/en", source=self
            )
        )
        self.network.wait_for_request(response)

        document = BeautifulSoup(
            response.json()["result"]["html"], features="html.parser"
        )
        read_list = document.select("ul a")

        assert len(manga_list) == len(read_list)

        chapters = list(
            self._parse_chapter_from_elements(manga, read, i)
            for i, (manga, read) in enumerate(list(zip(manga_list, read_list))[::-1])
        )

        response.deleteLater()
        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        chapter_id = Url(chapter.url).fragment()
        return Request(MangaFire.BASE_URL + f"/ajax/read/chapter/{chapter_id}")

    def parse_chapter_pages(self, response: Response) -> list[Page]:
        return [
            Page(number=i, url=image[0])
            for i, image in enumerate(response.json()["result"]["images"])
        ]

    def get_page(self, page):
        request = super().get_page(page)
        request.setRawHeader(b"Referer", f"{MangaFire.BASE_URL}".encode())

        ssl = QSslConfiguration()
        ssl.setPeerVerifyMode(QSslSocket.PeerVerifyMode.VerifyNone)
        request.setSslConfiguration(ssl)
        return request
