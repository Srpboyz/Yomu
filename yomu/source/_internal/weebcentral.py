import re
from bs4 import BeautifulSoup, Tag
from dateparser import parse as parse_date

from yomu.core.network import Response, Request, Url
from yomu.source import *
from yomu.source import MangaList


class WeebCentral(Source):
    name = "Weeb Central"
    BASE_URL = "https://weebcentral.com"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.network.add_rate_limit(RateLimit(1, 2, url="weebcentral.com"))

    def get_latest(self, page: int) -> Request:
        return Request(
            Url(
                f"{WeebCentral.BASE_URL}/search/data",
                params={
                    "sort": "Latest Updates",
                    "order": "Descending",
                    "limit": 32,
                    "offset": (page - 1) * 32,
                    "display_mode": "Full Display",
                },
            )
        )

    def get_thumbnail_source(self, element: Tag) -> str | None:
        source = element.select_one("source")
        if source is None:
            return element.select_one("img").attrs["src"]

        srcset = source.attrs.get("srcset")
        if srcset is None:
            return element.select_one("img").attrs["src"]

        return srcset.replace("small", "normal")

    def parse_latest_manga(self, element: Tag) -> Manga:
        title = element.select_one("div:not([class]):last-child").get_text(
            " ", strip=True
        )
        thumbnail = self.get_thumbnail_source(element)
        url = element.attrs["href"].replace(WeebCentral.BASE_URL, "")
        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        mangas = list(
            map(self.parse_latest_manga, document.select("article > section > a"))
        )
        has_next_page = bool(document.select_one("button"))
        return MangaList(mangas=mangas, has_next_page=has_next_page)

    def search_for_manga(self, query: str) -> None:
        return Request(
            Url(
                f"{WeebCentral.BASE_URL}/search/data",
                params={
                    "text": re.sub(r"[!#:(),-]", "", query),
                    "limit": 32,
                    "offset": 0,
                    "display_mode": "Full Display",
                },
            )
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        return self.parse_latest(response, 1)

    def get_manga_info(self, manga: Manga) -> Manga:
        return Request(WeebCentral.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = BeautifulSoup(response.read_all().data(), features="lxml")

        content_elements = document.select("section[x-data] > section")
        if not content_elements:
            raise TypeError

        content_element = content_elements[0]
        thumbnail_url = self.get_thumbnail_source(content_element)
        author = ", ".join(
            (
                author.get_text(" ", strip=True)
                for author in document.select(
                    "ul > li:has(strong:-soup-contains(Author)) > span > a"
                )
            )
        )

        content_element = content_elements[1]
        title = content_element.select_one("h1").get_text("", strip=True)
        description = content_element.select_one(
            "li:has(strong:-soup-contains(Description)) > p"
        ).get_text(" ", strip=True)

        return Manga(
            title=title,
            description=description,
            author=author,
            thumbnail=thumbnail_url,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        manga_url = "/".join(manga.url.split("/")[:-1]) + "/full-chapter-list"
        return Request(WeebCentral.BASE_URL + manga_url)

    def parse_chapter_element(self, element: Tag, number: int) -> Chapter:
        title = element.select_one("span.flex > span").get_text(
            separator=" ", strip=True
        )
        uploaded = parse_date(element.select_one("time[datetime]").attrs["datetime"])
        url = element.attrs["href"].replace(WeebCentral.BASE_URL, "")
        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        return [
            self.parse_chapter_element(element, i)
            for i, element in enumerate(document.select("div[x-data] > a")[::-1])
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(
            Url(
                WeebCentral.BASE_URL + chapter.url + "/images",
                params={"is_prev": False, "reading_style": "long_strip"},
            )
        )

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        pages = [
            Page(number=i, url=element.attrs["src"])
            for i, element in enumerate(
                document.select("section[x-data*=scroll] > img")
            )
        ]
        return pages
