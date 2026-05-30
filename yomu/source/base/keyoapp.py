import re

from bs4 import BeautifulSoup, Tag
from dateparser import parse as parse_date

from yomu.core.network import Response, Request
from yomu.source import *


class Keyoapp(Source):
    latest_updates_selector: str = "div.grid > div.group"
    search_selector: str = "#searched_series_page > button"
    manga_description_selector: str = "div:containsOwn(Synopsis) ~ div"
    manga_author_selector: str = "div:has(span:-soup-contains(Author)) ~ div"
    manga_artist_selector: str = "div:has(span:-soup-contains(Artist)) ~ div"
    chapter_date_selector: str = ".text-xs"

    IMAGE_REGEX = re.compile(r'url\(\s*["\']?([^"\'\s\)]+)["\']?\s*\)')
    CDN_REGEX = re.compile(r"^(https?:)?//cdn\d*\.keyoapp\.com")

    def get_latest(self, page: int) -> Request:
        request = Request(f"{self.BASE_URL}/latest/")
        return request

    def parse_latest_element(self, element: Tag) -> Manga:
        data = element.select_one("a[href]")
        title = data.attrs["title"]
        thumbnail = Keyoapp.IMAGE_REGEX.search(
            element.select_one("*[style*=background-image]").attrs["style"]
        ).group(1)
        url = data.attrs["href"].replace(self.BASE_URL, "")

        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        document = BeautifulSoup(bytes(response.read_all()), features="lxml")
        return MangaList(
            mangas=list(
                map(
                    self.parse_latest_element,
                    document.select(self.latest_updates_selector),
                )
            )
        )

    def search_for_manga(self, query: str) -> Request:
        return Request(f"{self.BASE_URL}/series?q={query}")

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        document, query = (
            BeautifulSoup(bytes(response.read_all()), features="lxml"),
            query.lower(),
        )
        return MangaList(
            mangas=list(
                map(
                    self.parse_latest_element,
                    filter(
                        lambda element: query in element.attrs["title"].lower(),
                        document.select(self.search_selector),
                    ),
                )
            )
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(self.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = BeautifulSoup(bytes(response.read_all()), features="lxml")

        title_tag = document.select_one("div.grid > h1")
        title = title_tag.get_text(" ", strip=True) if title_tag is not None else None

        description_tag = document.select_one(self.manga_description_selector)
        description = (
            description_tag.get_text(" ", strip=True)
            if description_tag is not None
            else None
        )

        author_tag = document.select_one(self.manga_author_selector)
        author = (
            author_tag.get_text(" ", strip=True) if author_tag is not None else None
        )

        artist_tag = document.select_one(self.manga_artist_selector)
        artist = (
            artist_tag.get_text(" ", strip=True) if artist_tag is not None else None
        )

        thumbnail_tag = document.select_one("div[class*=photoURL]")
        thumbnail = (
            Keyoapp.IMAGE_REGEX.search(thumbnail_tag.attrs["style"]).group(1)
            if thumbnail_tag is not None
            else None
        )

        return Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(self.BASE_URL + manga.url)

    def chapter_from_element(self, element: Tag, number: int) -> Chapter:
        title = element.select_one(".text-sm").get_text(" ", strip=True)
        uploaded = parse_date(
            element.select_one(self.chapter_date_selector).get_text(" ", strip=True)
        )
        url = element.attrs["href"].replace(self.BASE_URL, "")
        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        document = BeautifulSoup(bytes(response.read_all()), features="lxml")
        return [
            self.chapter_from_element(element, i)
            for i, element in enumerate(
                document.select(
                    "#chapters > a:not(:has(.text-sm span:matches(Upcoming))):not(:has(img[alt~=Coin]))"
                )[::-1]
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(self.BASE_URL + chapter.url)

    def get_page_image_attr(self, element: Tag) -> str:
        attrs = element.attrs
        if "data-lazy-src" in attrs:
            return attrs["data-lazy-src"]
        if "data-src" in attrs:
            return attrs["data-src"]
        return attrs["src"]

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        document = BeautifulSoup(bytes(response.read_all()), features="lxml")
        return [
            Page(number=i, url=url)
            for i, url in enumerate(
                filter(
                    lambda element: bool(Keyoapp.CDN_REGEX.search(str(element))),
                    map(
                        lambda element: self.get_page_image_attr(element),
                        document.select("#pages > img"),
                    ),
                )
            )
        ]
