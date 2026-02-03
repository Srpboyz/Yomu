from datetime import datetime

from typing import Sequence
from bs4 import BeautifulSoup, Tag

from yomu.core.network import Response, Request, Url
from yomu.source import *


class PhiliaScans(Source):
    name = "Philia Scans"
    BASE_URL = "https://philiascans.org"

    def image_from_tag(self, tag: Tag | None) -> str | None:
        if tag is None:
            return None
        attrs = tag.attrs
        if "data-lazy-src" in attrs:
            return attrs["data-lazy-src"]
        if "data-src" in attrs:
            return attrs["data-src"]
        return attrs["src"]

    def get_latest(self, page: int) -> Request:
        return Request(f"{PhiliaScans.BASE_URL}/recently-updated/?page={page}")

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        url = Url(PhiliaScans.BASE_URL)
        url.add_params({"post_type": "wp-manga", "s": query, "paged": 1})
        return Request(url)

    def parse_manga_from_tag(self, tag: Tag) -> Manga:
        title_tag = tag.select_one("a.c-title")

        title = title_tag.get_text(" ", strip=True)
        url = title_tag.attrs["href"].replace(PhiliaScans.BASE_URL, "")
        thumbnail = self.image_from_tag(
            tag.select_one("a.poster div.poster-image-wrapper > img")
        )

        return Manga(title=title, url=url, thumbnail=thumbnail)

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        has_next_page = (
            document.select_one("li.page-item:not(.disabled) a.page-link[rel=next]")
            is not None
        )
        return MangaList(
            mangas=list(map(self.parse_manga_from_tag, document.select("div.unit"))),
            has_next_page=has_next_page,
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(PhiliaScans.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = BeautifulSoup(response.read_all().data(), features="lxml")

        title = document.select_one("h1.serie-title").get_text(" ", True)
        description = document.select_one("div.description-content").get_text(" ", True)
        author = document.select_one(
            ".stat-item:has(.stat-label:-soup-contains(Author)) .stat-value"
        ).get_text(" ", True)
        artist = document.select_one(
            ".stat-item:has(.stat-label:-soup-contains(Artist)) .stat-value"
        ).get_text(" ", True)

        thumbnail = self.image_from_tag(document.select_one("div.main-cover img.cover"))

        return Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(PhiliaScans.BASE_URL + manga.url)

    def chapter_from_tag(self, tag: Tag, number: int) -> Manga | None:
        url_tag = tag.select_one("a")
        if url_tag is None:
            return None
        url = url_tag.attrs["href"].replace(self.BASE_URL, "")
        if "#" in url:
            return None

        title = tag.select_one("zebi").get_text(" ", True)
        return Chapter(title=title, number=number, uploaded=datetime.now(), url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        return list(
            filter(
                None,
                [
                    self.chapter_from_tag(tag, i)
                    for i, tag in enumerate(document.select("li.item")[::-1])
                ],
            )
        )

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(PhiliaScans.BASE_URL + chapter.url)

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        return [
            Page(number=i, url=self.image_from_tag(tag))
            for i, tag in enumerate(document.select("div#ch-images img"))
        ]
