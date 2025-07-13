from bs4 import BeautifulSoup
from dateparser import parse
from datetime import datetime

from yomu.core import Request
from yomu.core.network import Response
from yomu.source import *


class Mangakakalot(Source):
    BASE_URL = "https://mangakakalot.com"

    def _build_request(
        self,
        url: str,
        route: Request.Route = Request.Route.GET,
        data: dict | None = None,
    ) -> Request:
        request = Request(url=url, route=route, data=data)
        request.setRawHeader(b"Referer", f"{Mangakakalot.BASE_URL}/".encode())
        return request

    def get_latest(self, page: int) -> Request:
        url = f"{Mangakakalot.BASE_URL}/manga_list?type=latest&category=all&state=all&page={page}"
        return self._build_request(url)

    def parse_latest(self, response: Response) -> MangaList:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        mangas: list[Manga] = []
        for div in html.find_all("div", {"class": "list-truyen-item-wrap"}):
            a = div.find("a")
            title, thumbnail, url = (
                a.attrs["title"],
                div.find("img").attrs["src"],
                a.attrs["href"],
            )
            mangas.append(Manga(title=title, thumbnail=thumbnail, url=url))

        can_load_more = bool(
            html.select_one(
                "a.page_select + a:not(.page_last), a.page-select + a:not(.page-last)"
            )
        )

        manga_list = MangaList(mangas=mangas, has_next_page=can_load_more)
        return manga_list

    def get_manga_info(self, manga: Manga) -> Request:
        return self._build_request(manga.url)

    def parse_manga_info(self, response: Response) -> Manga:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        info_tag = html.select_one("div.manga-info-top, div.panel-story-info")

        # fmt: off
        title = info_tag.select_one("h1, h2").text
        description = html.select_one("div#noidungm, div#panel-story-info-description").text.replace("\n", " ")
        authors = info_tag.select("li:-soup-contains(author) a, td:has(i.info-author) + td a")
        author = " - ".join(a.text.strip() for a in authors) if authors is not None else None

        thumbnail = html.select_one("div.manga-info-pic img, span.info-image img").attrs["src"]
        url = response.url().toString()
        # fmt:on

        return Manga(
            title=title,
            description=description,
            author=author,
            thumbnail=thumbnail,
            url=url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return self._build_request(manga.url)

    def parse_chapters(self, response: Response) -> list[Chapter]:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        chapter_list = html.select(
            "div.chapter-list div.row, ul.row-content-chapter li"
        )

        chapters = []
        for i, chapter_data in enumerate(chapter_list[::-1]):
            a_tag = chapter_data.find("a")
            title = a_tag.text.strip()
            url = a_tag.attrs["href"]

            spans = chapter_data.find_all("span", {"class": "chapter-time text-nowrap"})
            uploaded = parse(spans[-1].text) if spans else datetime.now()

            chapters.append(Chapter(number=i, title=title, url=url, uploaded=uploaded))
        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return self._build_request(chapter.url)

    def parse_chapter_pages(self, response: Response) -> list[Page]:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        pages = html.select("div.container-chapter-reader > img")
        return [
            Page(number=number, url=page.attrs["src"])
            for number, page in enumerate(pages)
        ]

    def get_thumbnail(self, manga: Manga) -> Request:
        return self._build_request(manga.thumbnail)

    def get_page(self, page: Page) -> Request:
        return self._build_request(page.url)

    def search_for_manga(self, query: str) -> None:
        query = query.replace(" ", "_")
        return self._build_request(f"{Mangakakalot.BASE_URL}/search/story/{query}")

    def parse_search_results(self, response: Response) -> MangaList:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")

        mangas = []
        for div in html.find_all("div", {"class": "story_item"}):
            title = div.find("h3", {"class": "story_name"}).text.strip()

            a = div.find("a")
            thumbnail, url = (
                a.find("img").attrs["src"],
                a.attrs["href"],
            )

            mangas.append(Manga(title=title, thumbnail=thumbnail, url=url))

        can_load_more = bool(
            html.select_one(
                "a.page_select + a:not(.page_last), a.page-select + a:not(.page-last)"
            )
        )

        return MangaList(mangas=mangas, has_next_page=can_load_more)
