from typing import Sequence
from bs4 import BeautifulSoup, Tag
from dateparser import parse
from PyQt6.QtCore import QUrl

from yomu.core.network import Request, Response
from yomu.source import *


class MangaThemesia(Source):
    request_sub_string: str

    title_selector: str = "h1.entry-title, .ts-breadcrumb li:last-child span"
    details_selector: str = ".desc, .entry-content[itemprop=description]"
    author_selector: str = (
        ".infotable tr:-soup-contains(Author) td:last-child, "
        ".tsinfo .imptdt:-soup-contains(Author) i, "
        ".fmed b:-soup-contains(Author) + span, "
        "span:-soup-contains(Author)"
    )
    artist_selector: str = (
        ".infotable tr:-soup-contains(Artist) td:last-child, "
        ".tsinfo .imptdt:-soup-contains(Artist) i, "
        ".fmed b:-soup-contains(Artist) + span, "
        "span:-soup-contains(Artist)"
    )
    thumbnail_selector: str = ".infomanga > div[itemprop=image] img, .thumb img"
    search_selector: str = ".utao .uta .imgu, .listupd .bs .bsx, .listo .bs .bsx"

    chapter_selector: str = (
        "div.bxcl li, div.cl li, #chapterlist li, ul li:has(div.chbox):has(div.eph-num)"
    )
    page_selector: str = "div#readerarea img"

    def _build_request(
        self,
        url: str | QUrl,
        route: Request.Route = Request.Route.GET,
        data: dict | None = None,
    ) -> Request:
        request = Request(url=url, route=route, data=data)
        request.setRawHeader(b"Referer", f"{self.BASE_URL}/".encode())
        return request

    def get_image_url(self, element: Tag | None) -> str | None:
        if element is None:
            return None

        attrs = element.attrs
        if "data-lazy-src" in attrs:
            return attrs["data-lazy-src"]
        if "data-src" in attrs:
            return attrs["data-src"]
        if "data-cfsrc" in attrs:
            return attrs["data-cfsrc"]
        return attrs["src"]

    def url_to_slug(self, url: str) -> str:
        return url.replace(self.BASE_URL, "")

    def get_latest(self, page: int) -> Request:
        return self.search_for_manga("", page=page)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "", check_for_next=True)

    def search_for_manga(self, query: str, *, page: int = 1) -> Request:
        query = query.replace(" ", "+")
        url = f"{self.BASE_URL}/{self.request_sub_string}?page={page}&order=update&title={query}"
        return self._build_request(url)

    def manga_from_element(self, element: Tag) -> Manga:
        a = element.select_one("a")

        title = a.attrs["title"]
        thumbnail = self.get_image_url(element.select_one("img"))
        url = self.url_to_slug(a.attrs["href"])

        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_search_results(
        self, response: Response, query: str, *, check_for_next: bool = False
    ) -> MangaList:
        document = response.as_beautifulsoup()
        mangas = list(
            map(self.manga_from_element, document.select(self.search_selector))
        )
        has_next_page = (
            bool(document.select_one("div.pagination .next, div.hpage .r"))
            if check_for_next
            else False
        )
        return MangaList(mangas=mangas, has_next_page=has_next_page)

    def get_manga_info(self, manga: Manga) -> Request:
        return self._build_request(self.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = response.as_beautifulsoup()

        title = document.select_one(self.title_selector).text
        description = document.select_one(self.details_selector).get_text(separator=" ", strip=True)  # fmt:skip
        author = getattr(document.select_one(self.author_selector), "text", None)
        artist = getattr(document.select_one(self.artist_selector), "text", None)

        thumbnail = self.get_image_url(document.select_one(self.thumbnail_selector))
        url = self.url_to_slug(response.url().toString())

        info = Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=url,
        )
        return info

    def get_chapters(self, manga: Manga) -> Request:
        return self._build_request(self.BASE_URL + manga.url)

    def chapter_from_element(self, element: Tag, number: int) -> Chapter:
        title = (
            element.select_one(".lch a, .chapternum").text.strip().replace("\n", " ")
        )
        uploaded = parse(element.select_one(".chapterdate").text.strip())
        url = self.url_to_slug(element.select_one("a").attrs["href"])
        return Chapter(number=number, title=title, url=url, uploaded=uploaded)

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        return [
            self.chapter_from_element(element, number)
            for number, element in enumerate(
                response.as_beautifulsoup().select(self.chapter_selector)[::-1]
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return self._build_request(self.BASE_URL + chapter.url)

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=number, url=self.get_image_url(page))
            for number, page in enumerate(
                response.as_beautifulsoup().select(self.page_selector)
            )
        ]

    def get_page(self, page: Page) -> Request:
        return self._build_request(page.url)
