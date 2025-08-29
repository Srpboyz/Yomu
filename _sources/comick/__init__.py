from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Sequence

from dateparser import parse
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Response, Request, Url
from yomu.source import Chapter, Manga, MangaList, Page, RateLimit, Source

if TYPE_CHECKING:
    from .dto import *


class Comick(Source):
    BASE_URL = "https://comick.io"
    API_URL = "https://api.comick.fun"
    COVER_URL = "https://meo.comick.pictures/"
    rate_limit = RateLimit(3, 1)

    def get_latest(self, page: int) -> Request:
        url = Url(f"{Comick.API_URL}/v1.0/search")
        url.add_params(
            {"sort": "uploaded", "limit": 50, "page": page, "tachiyomi": "true"}
        )

        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comick.BASE_URL + "/")

        request = Request(url, user_agent=f"Tachiyomi {Request.DEFAULT_USER_AGENT}")
        request.setHeaders(headers)
        return request

    def parse_latest(self, response: Response, page: int) -> MangaList:
        page = int(response.url().query().queryItemValue("page"))
        return MangaList(
            mangas=list(map(self._parse_search_data, response.json())),
            has_next_page=page < 50,
        )

    def _parse_search_data(self, data: SearchManga) -> Manga:
        key = next(iter(data["md_covers"]), dict()).get("b2key")

        return Manga(
            title=data["title"],
            thumbnail=Comick.COVER_URL + key,
            url=f"/comic/{data['hid']}",
        )

    def search_for_manga(self, query: str) -> Request:
        url = Url(f"{Comick.API_URL}/v1.0/search")
        url.add_params({"q": query, "limit": 300, "tachiyomi": "true"})

        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comick.BASE_URL + "/")

        request = Request(url, user_agent=f"Tachiyomi {Request.DEFAULT_USER_AGENT}")
        request.setHeaders(headers)
        return request

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        return MangaList(
            mangas=list(map(self._parse_search_data, response.json())),
            has_next_page=False,
        )

    def get_manga_info(self, manga: Manga) -> Manga:
        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comick.BASE_URL + "/")

        request = Request(
            Comick.API_URL + manga.url,
            user_agent=f"Tachiyomi {Request.DEFAULT_USER_AGENT}",
        )
        request.setHeaders(headers)
        return request

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: ComicInfo = response.json()

        manga = self._parse_search_data(data["comic"])
        manga.description = data["comic"]["desc"]
        manga.author = next((author["name"] for author in data["authors"]), None)
        manga.artist = next((artist["name"] for artist in data["artists"]), None)

        return manga

    def get_chapters(self, manga: Manga) -> Request:
        url = Url(Comick.API_URL + manga.url + "/chapters")
        url.set_params({"lang": "en", "limit": 99999, "tachiyomi": "true"})

        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comick.BASE_URL + "/")

        request = Request(url, user_agent=f"Tachiyomi {Request.DEFAULT_USER_AGENT}")
        request.setHeaders(headers)
        return request

    def _parse_chapter(self, data: ChapterInfo, number: int) -> Chapter:
        title_parts = []
        if data["vol"] is not None and (vol := data["vol"].strip()):
            title_parts.append(f"Vol. {vol}")
        if data["chap"] is not None and (chap := data["chap"].strip()):
            title_parts.append(f"Chapter {chap}")
        if data["title"] is not None and (title := data["title"].strip()):
            title_parts.append(str(title))

        title = " - ".join(title_parts)
        uploaded = parse(data["created_at"]) or datetime.now()
        url = f"/chapter/{data['hid']}"

        return Chapter(
            title=title,
            number=number,
            uploaded=uploaded,
            url=url,
        )

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        chapters: list[ChapterInfo] = sorted(
            response.json()["chapters"], key=lambda data: float(data["chap"])
        )
        return [self._parse_chapter(data, i) for i, data in enumerate(chapters)]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        url = Url(Comick.API_URL + chapter.url)
        url.set_params({"tachiyomi": "true"})

        headers = QHttpHeaders()
        headers.append(QHttpHeaders.WellKnownHeader.Referer, Comick.BASE_URL + "/")

        request = Request(url, user_agent=f"Tachiyomi {Request.DEFAULT_USER_AGENT}")
        request.setHeaders(headers)
        return request

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        return [
            Page(number=i, url=image["url"])
            for i, image in enumerate(response.json()["chapter"]["images"])
        ]
