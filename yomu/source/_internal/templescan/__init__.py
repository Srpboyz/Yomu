import json
import re
from typing import TypedDict

from bs4 import BeautifulSoup
from dateparser import parse as parse_date
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Response, Request
from yomu.source import *


class MangaData(TypedDict):
    id: int
    title: str
    description: str
    author: str
    thumbnail: str
    series_slug: str


class ChapterData(TypedDict):
    index: int
    chapter_name: str
    chapter_title: str
    chapter_slug: str
    created_at: str
    price: int


class TempleScan(Source):
    name = "Temple Scan"
    BASE_URL = "https://templetoons.com"
    rate_limit = RateLimit(1)

    DETAILS_REGEX = re.compile(r'info\\":(\{.*\}).*userIsFollowed')
    IMAGES_REGEX = re.compile(r'images\\":(\[.*?]).*')
    UNESCAPE_REGEX = re.compile(r"\\(.)")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cache: list[Manga] = []

    def _create_request(self, url: str) -> Request:
        request = Request(url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, f"{TempleScan.BASE_URL}/"
        )
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Origin, TempleScan.BASE_URL
        )

        request.setHeaders(headers)
        return request

    def _parse_manga(self, data: MangaData) -> Manga:
        return Manga(
            title=data["title"],
            thumbnail=data["thumbnail"],
            url=f"/comic/{data['series_slug']}",
        )

    def _parse_manga_cache(self, response: Response) -> None:
        document = BeautifulSoup(response.read_all().data(), features="lxml")

        script = document.select_one("script:-soup-contains(allComics)")
        if script is None:
            raise TypeError

        script_text = TempleScan.UNESCAPE_REGEX.sub(r"\1", script.get_text(strip=True))
        start = script_text.index("[", script_text.index("allComics"))
        end = script_text.rfind("}]", start)

        self.cache = list(
            map(
                self._parse_manga,
                sorted(
                    json.loads(script_text[start:end]),
                    key=lambda data: parse_date(
                        data["update_chapter"]
                        if data["update_chapter"]
                        else data["created_at"]
                    ),
                    reverse=True,
                ),
            )
        )

    def get_latest(self, page: int) -> Request:
        return self._create_request(TempleScan.BASE_URL + "/comics")

    def parse_latest(self, response: Response, page: int) -> MangaList:
        if page == 1:
            self._parse_manga_cache(response)

        max_length = len(self.cache)
        start = (page - 1) * 20
        end = min(start + 20, max_length)
        mangas = self.cache[start:end]

        return MangaList(mangas=mangas, has_next_page=end < max_length)

    def search_for_manga(self, query: str) -> Request:
        return self._create_request(TempleScan.BASE_URL + "/comics")

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        if not self.cache:
            self._parse_manga_cache(response)

        query = query.lower()
        return MangaList(
            mangas=list(filter(lambda comic: query in comic.title.lower(), self.cache))
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return self._create_request(TempleScan.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaData = json.loads(
            TempleScan.UNESCAPE_REGEX.sub(
                r"\1",
                next(
                    TempleScan.DETAILS_REGEX.finditer(
                        response.read_all().data().decode()
                    )
                ).group(1),
            )
        )

        return Manga(
            title=manga.title,
            description=data["description"],
            author=data["author"],
            thumbnail=manga.thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return self._create_request(TempleScan.BASE_URL + manga.url)

    def _parse_chapter_data(
        self, data: ChapterData, index: int, manga_slug: str
    ) -> Chapter:
        title = data["chapter_name"]
        if data["chapter_title"]:
            title += f" • {data['chapter_title']}"

        return Chapter(
            title=title,
            number=index,
            uploaded=parse_date(data["created_at"]),
            url=f"{manga_slug}/{data['chapter_slug']}",
        )

    def parse_chapters(self, response: Response, manga: Manga) -> list[Page]:
        data: MangaData = json.loads(
            TempleScan.UNESCAPE_REGEX.sub(
                r"\1",
                next(
                    TempleScan.DETAILS_REGEX.finditer(
                        response.read_all().data().decode()
                    )
                ).group(1),
            )
        )

        chapters: list[ChapterData] = next(
            filter(
                lambda season: season["season_name"] == "All chapters", data["Season"]
            )
        )["Chapter"][::-1]

        return list(
            map(
                lambda pair: self._parse_chapter_data(pair[1], pair[0] + 1, manga.url),
                enumerate(filter(lambda chapter: chapter["price"] == 0, chapters)),
            )
        )

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return self._create_request(TempleScan.BASE_URL + chapter.url)

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[str]:
        pages = json.loads(
            TempleScan.UNESCAPE_REGEX.sub(
                r"\1",
                next(
                    TempleScan.IMAGES_REGEX.finditer(
                        response.read_all().data().decode()
                    )
                ).group(1),
            )
        )

        return list(
            map(
                lambda data: Page(number=data[0], url=data[1].rstrip("\n")),
                enumerate(pages),
            )
        )
