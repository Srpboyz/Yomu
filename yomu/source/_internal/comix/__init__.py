import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Response, Request, Url
from yomu.source import Chapter, Manga, MangaList, Page, RateLimit, Source, FilterType

from .dto import *
from .hash import generate_hash

DATE_REGEX = re.compile(
    r"^(\d+)\s*(s|m|h|d|w|mo|mos|y|yr|yrs|min|mins|sec|secs|hr|hrs|day|days|week|weeks|month|months|year|years)$"
)


def parse_date(date_str: str) -> datetime | None:
    trimmed = date_str.strip().lower().removesuffix(" ago")
    match = DATE_REGEX.search(trimmed)
    if not match:
        return None

    try:
        amount = int(match.group(1))
    except (ValueError, TypeError):
        return None
    unit = match.group(2)

    now = datetime.now()
    if unit in ("s", "sec", "secs"):
        return now - timedelta(seconds=amount)
    if unit in ("m", "min", "mins"):
        return now - timedelta(minutes=amount)
    if unit in ("h", "hr", "hrs"):
        return now - timedelta(hours=amount)
    if unit in ("d", "day", "days"):
        return now - timedelta(days=amount)
    if unit in ("w", "week", "weeks"):
        return now - timedelta(weeks=amount)
    if unit in ("mo", "mos", "month", "months"):
        return now - relativedelta(months=amount)
    if unit in ("y", "yr", "yrs", "year", "years"):
        return now - relativedelta(years=amount)
    return None


class Comix(Source):
    BASE_URL = "https://comix.to"
    API_URL = "https://comix.to/api/v1"
    rate_limit = RateLimit(5)

    NSFW_IDS = ["87264", "8", "87265", "13", "87266", "87268"]

    has_filters = True
    filters = {
        "nsfw": {
            "display_name": "NSFW",
            "value": False,
            "type": FilterType.CHECKBOX,
        }
    }

    @property
    def is_nsfw(self) -> bool:
        return self.filters["nsfw"]["value"]

    @is_nsfw.setter
    def is_nsfw(self, is_nsfw: bool) -> None:
        self.filters["nsfw"]["value"] = is_nsfw

    def get_latest(self, page: int) -> Request:
        return Request(
            Url(
                f"{Comix.API_URL}/manga",
                params={
                    "order[chapter_updated_at]": "desc",
                    "genres_ex[]": Comix.NSFW_IDS if not self.is_nsfw else [],
                    "limit": 100,
                    "page": page,
                },
            )
        )

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        return Request(
            Url(
                f"{Comix.API_URL}/manga",
                params={
                    "order[relevance]": "desc",
                    "genres_ex[]": Comix.NSFW_IDS if not self.is_nsfw else [],
                    "limit": 100,
                    "keyword": query,
                },
            )
        )

    def _parse_search_data(self, data: MangaDto) -> Manga:
        return Manga(
            title=data["title"],
            thumbnail=(data.get("poster") or {}).get("large"),
            url=f"/manga/{data['hid']}",
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: ItemsDto = response.json()["result"]
        has_next_page = (
            data["meta"]["page"] < data["meta"]["lastPage"]
            if "meta" in data
            else data["pagination"]["current_page"] < data["pagination"]["last_page"]
            if "pagination" in data
            else False
        )
        return MangaList(
            mangas=list(map(self._parse_search_data, data["items"])),
            has_next_page=has_next_page,
        )

    def get_manga_info(self, manga: Manga) -> Manga:
        return Request(
            Url(Comix.API_URL + manga.url, params={"includes[]": ["author", "artist"]})
        )

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = response.json()["result"]

        manga = self._parse_search_data(data)
        manga.description = data["synopsis"]
        manga.author = (
            ", ".join((author["title"] for author in data["authors"])) or None
        )
        manga.artist = (
            ", ".join((artist["title"] for artist in data["artists"])) or None
        )

        return manga

    def get_chapters(self, manga: Manga, page: int = 1) -> Request:
        path = manga.url + "/chapters"
        return Request(
            Url(
                Comix.API_URL + path,
                params={
                    "limit": 100,
                    "order[number]": "desc",
                    "page": page,
                    "_": generate_hash(path),
                },
            )
        )

    def _parse_chapter(self, data: ChapterDto, number: int) -> Chapter:
        title_parts = []
        if (volume := data.get("volume")) is not None:
            title_parts.append(f"Vol. {volume}")
        if (number := data.get("number")) is not None:
            title_parts.append(f"Chapter {number}")
        if (name := data.get("name")) is not None and (name := name.strip()):
            title_parts.append(str(name))

        title = " - ".join(title_parts)
        uploaded = (
            parse_date(created_at)
            if (created_at := data.get("createdAtFormatted")) is not None
            else None
        )
        url = f"/chapters/{data['id']}"

        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        result = response.json()["result"]
        chapters = result["items"]

        if "meta" in result:
            current_page = result["meta"]["page"]
            last_page = result["meta"]["lastPage"]
        elif "pagination" in result:
            current_page = result["pagination"]["current_page"]
            last_page = result["pagination"]["last_page"]
        else:
            current_page, last_page = 1, 0

        while current_page < last_page:
            current_page += 1
            response = self.network.handle_request(
                self.get_chapters(manga, current_page)
            )
            response.wait()
            result = response.json()["result"]
            chapters.extend(result["items"])
            response.deleteLater()

        return [self._parse_chapter(data, i) for i, data in enumerate(chapters)]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(
            Url(Comix.API_URL + chapter.url, params={"_": generate_hash(chapter.url)})
        )

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=i, url=image["url"])
            for i, image in enumerate(response.json()["result"]["pages"])
        ]

    def get_page(self, page: Page) -> Request:
        url = Url(page.url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/"
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        new_value = filters.get("nsfw", False)
        if new_value == self.is_nsfw:
            return False

        self.is_nsfw = new_value
        return True
