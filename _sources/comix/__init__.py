from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from dateparser import parse
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Response, Request, Url
from yomu.source import Chapter, Manga, MangaList, Page, RateLimit, Source, FilterType

if TYPE_CHECKING:
    from .dto import *


class Comix(Source):
    BASE_URL = "https://comix.to"
    API_URL = "https://comix.to/api/v2"
    rate_limit = RateLimit(5, 1)

    NSFW_IDS = ["-87264", "-8", "-87265", "-13", "-87266", "-87268"]

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
        url = Url(f"{Comix.API_URL}/manga")
        url.add_params(
            {
                "order[chapter_updated_at]": "desc",
                "genres[]": Comix.NSFW_IDS if not self.is_nsfw else [],
                "limit": 100,
                "page": page,
            }
        )

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/"
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        url = Url(f"{Comix.API_URL}/manga")
        url.add_params(
            {
                "order[relevance]": "desc",
                "genres[]": Comix.NSFW_IDS if not self.is_nsfw else [],
                "limit": 100,
                "keyword": query,
            }
        )

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/"
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

    def _parse_search_data(self, data: MangaDto) -> Manga:
        return Manga(
            title=data["title"],
            thumbnail=data["poster"]["large"],
            url=f"/manga/{data['hash_id']}",
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: ItemsDto = response.json()["result"]
        return MangaList(
            mangas=list(map(self._parse_search_data, data["items"])),
            has_next_page=(
                data["pagination"]["current_page"] < data["pagination"]["last_page"]
            ),
        )

    def get_manga_info(self, manga: Manga) -> Manga:
        url = Url(Comix.API_URL + manga.url)
        url.add_params({"includes[]": ["author", "artist"]})

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/"
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = response.json()["result"]

        manga = self._parse_search_data(data)
        manga.description = data["synopsis"]
        manga.author = next((author["title"] for author in data["author"]), None)
        manga.artist = next((artist["title"] for artist in data["artist"]), None)

        return manga

    def get_chapters(self, manga: Manga, page: int = 1) -> Request:
        url = Url(Comix.API_URL + manga.url + "/chapters")
        url.set_params({"limit": 100, "order[number]": "desc", "page": page})

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/"
        )

        request = Request(url)
        request.setHeaders(headers)
        return request

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
            datetime.fromtimestamp(updated_at)
            if (updated_at := data.get("updated_at")) is not None
            else datetime.now()
        )
        url = f"/chapters/{data['chapter_id']}"

        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        result = response.json()["result"]
        chapters = result["items"]

        current_page, last_page = (
            result["pagination"]["current_page"],
            result["pagination"]["last_page"],
        )
        while current_page < last_page:
            current_page += 1
            request = self.get_chapters(manga, current_page)
            response = self.network.handle_request(request)
            self.network.wait_for_request(response)
            result = response.json()["result"]
            chapters.extend(result["items"])
            response.deleteLater()

        return [self._parse_chapter(data, i) for i, data in enumerate(chapters)]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comix.BASE_URL + "/")

        request = Request(Comix.API_URL + chapter.url)
        request.setHeaders(headers)
        return request

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=i, url=image)
            for i, image in enumerate(response.json()["result"]["images"])
        ]

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        new_value = filters.get("nsfw", False)
        if new_value == self.is_nsfw:
            return False

        self.is_nsfw = new_value
        return True
