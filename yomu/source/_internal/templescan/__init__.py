import json
import re

from dateparser import parse as parse_date
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Response, Request
from yomu.source import *

from .dto import *

MANGA_REGEX = re.compile(r'list\\":(.*),')
DETAILS_REGEX = re.compile(r'seriesData\\":(\{.*\}).*hasFollowed')
IMAGES_REGEX = re.compile(r'images\\":(\[.*?]).*')
UNESCAPE_REGEX = re.compile(r"\\(.)")


class TempleScan(Source):
    name = "Temple Scan"
    BASE_URL = "https://templetoons.com"
    rate_limit = RateLimit(1)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cache: list[Manga] = []

    def _create_request(self, url: str) -> Request:
        headers = QHttpHeaders()
        headers.replaceOrAppend("Sec-Fetch-Dest", "document")
        headers.replaceOrAppend("Sec-Fetch-Mode", "navigate")
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, f"{TempleScan.BASE_URL}/"
        )
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Origin, TempleScan.BASE_URL
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

    def _parse_manga(self, data: MangaDataDto) -> Manga:
        return Manga(
            title=data["title"],
            thumbnail=data["thumbnail"],
            url=f"/comic/{data['sref']}",
        )

    def _parse_manga_cache(self, response: Response) -> None:
        document = response.as_beautifulsoup()
        script = document.select_one("script:-soup-contains(list)")
        if script is None:
            raise TypeError

        manga_data = json.loads(
            UNESCAPE_REGEX.sub(
                r"\1", MANGA_REGEX.search(script.get_text(strip=True)).group(1)
            )
        )

        self.cache = list(
            map(
                self._parse_manga,
                sorted(
                    manga_data,
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
        document = response.as_beautifulsoup()
        script = document.select_one("script:-soup-contains(seriesData)")
        if script is None:
            raise TypeError

        data: MangaDataDto = json.loads(
            UNESCAPE_REGEX.sub(
                r"\1", DETAILS_REGEX.search(script.get_text(strip=True)).group(1)
            )
        )

        return Manga(
            title=data["title"],
            description=data["description"],
            author=data["author"],
            thumbnail=data["thumbnail"],
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return self._create_request(TempleScan.BASE_URL + manga.url)

    def _parse_chapter_data(
        self, data: ChapterDataDto, index: int, manga_slug: str
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
        document = response.as_beautifulsoup()
        script = document.select_one("script:-soup-contains(seriesData)")
        if script is None:
            raise TypeError

        data: MangaDataDto = json.loads(
            UNESCAPE_REGEX.sub(
                r"\1", DETAILS_REGEX.search(script.get_text(strip=True)).group(1)
            )
        )

        chapters: list[ChapterDataDto] = next(
            filter(lambda group: group["season_name"] == "All chapters", data["groups"])
        )["items"][::-1]

        return list(
            map(
                lambda pair: self._parse_chapter_data(pair[1], pair[0] + 1, manga.url),
                enumerate(filter(lambda chapter: chapter["lk"] == 0, chapters)),
            )
        )

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return self._create_request(TempleScan.BASE_URL + chapter.url)

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[str]:
        document = response.as_beautifulsoup()
        script = document.select_one("script:-soup-contains(images)")
        if script is None:
            raise TypeError

        pages = json.loads(
            UNESCAPE_REGEX.sub(
                r"\1", IMAGES_REGEX.search(script.get_text(strip=True)).group(1)
            )
        )

        return list(
            map(
                lambda data: Page(number=data[0], url=data[1].rstrip("\n")),
                enumerate(pages),
            )
        )
