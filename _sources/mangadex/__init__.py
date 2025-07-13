import re

from dateparser import parse
from PyQt6.QtCore import QJsonDocument
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core import Request
from yomu.core.network import Response, Url
from yomu.source import *

from .utils import *


class MangaDex(Source):
    BASE_URL = BASE_URL
    API_URL = API_URL
    UPLOAD_URL = UPLOAD_URL
    has_filters = True
    rate_limit = RateLimit(3, 1)
    filters = {
        "content-rating": {
            "display_name": "Content Rating",
            "value": ["safe", "suggestive"],
            "options": ["safe", "suggestive", "erotica", "pornographic"],
            "type": FilterType.LIST,
        }
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def get_latest(self, page: int) -> Request:
        limit = 100
        offset = limit * (page - 1)

        params = {
            "limit": limit,
            "offset": offset,
            "translatedLanguage[]": ["en"],
            "order[readableAt]": "desc",
            "includeFutureUpdates": 0,
            "includeFuturePublishAt": 0,
            "includeEmptyPages": 0,
            "contentRating[]": self.filters["content-rating"]["value"],
        }

        url = Url(f"{MangaDex.API_URL}/chapter")
        url.set_params(params)
        return Request(url)

    def parse_latest(self, response: Response) -> MangaList:
        json = QJsonDocument.fromJson(response.read_all()).toVariant()

        can_load_more = json["offset"] + 7 < min(json["total"], 10000)

        manga_ids = []
        for chapter in json.get("data", []):
            for relationship in chapter.get("relationships", []):
                if relationship["type"] == "manga":
                    manga_ids.append(relationship["id"])

        request = create_manga_request(manga_ids)
        request.setPriority(Request.Priority.HighPriority)
        request.source = self

        response = self.network.handle_request(request)  # fmt: skip
        self.network.wait_for_request(response)

        json = QJsonDocument.fromJson(response.read_all()).toVariant()
        response.deleteLater()

        mangas = [
            Manga(title=title, url=url, thumbnail=thumbnail)
            for title, thumbnail, url in parse_manga_data(json)
        ]

        return MangaList(mangas=mangas, has_next_page=can_load_more)

    def get_manga_info(self, manga: Manga) -> Request:
        manga_id = re.match(Regex.MANGA, manga.url).group(1)
        return create_manga_request([manga_id])

    def parse_manga_info(self, response: Response) -> Manga | None:
        json = QJsonDocument.fromJson(response.read_all()).toVariant()

        manga_url = MangaDex.BASE_URL + "/title/{0}"
        cover_url = MangaDex.UPLOAD_URL + "/covers/{}/{}"

        manga_data = json["data"][0]
        thumbnail, author, artist = None, None, None
        for relationship in manga_data["relationships"]:
            type = relationship["type"]
            if type == "cover_art":
                thumbnail = cover_url.format(
                    manga_data["id"], relationship["attributes"]["fileName"]
                )
            elif type == "author":
                author = relationship["attributes"]["name"]
            elif type == "artist":
                artist = relationship["attributes"]["name"]

        title = manga_data["attributes"]["title"].get("en")
        if title is None:
            for title_data in manga_data["attributes"]["altTitles"]:
                title = title_data.get("en")
                if title is not None:
                    break

        description = manga_data["attributes"]["description"].get("en", "")
        url = manga_url.format(manga_data["id"])

        return Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        manga_id = re.match(Regex.MANGA, manga.url).group(1)

        params = {
            "limit": 500,
            "offset": 0,
            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
            "translatedLanguage[]": ["en"],
            "order[volume]": "desc",
            "order[chapter]": "desc",
            "includeFuturePublishAt": 0,
            "includeEmptyPages": 0,
        }

        url = Url(f"{MangaDex.API_URL}/manga/{manga_id}/feed")
        url.set_params(params)
        return Request(url)

    def parse_chapters(self, response: Response) -> list[Chapter]:
        json = QJsonDocument.fromJson(response.read_all()).toVariant()
        total = json["total"]

        manga_id = re.match(Regex.CHAPTER, response.url().toString()).group(1)

        chapter_url = MangaDex.BASE_URL + "/chapter/{0}"
        manga_feed_url = f"{MangaDex.API_URL}/manga/{manga_id}/feed"
        params = {
            "limit": 500,
            "offset": 0,
            "translatedLanguage[]": ["en"],
            "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
            "order[volume]": "desc",
            "order[chapter]": "desc",
            "includeFuturePublishAt": 0,
            "includeEmptyPages": 0,
        }

        chapters = []
        while True:
            for i, chapter_data in enumerate(json.get("data", [])[::-1]):
                url = chapter_url.format(chapter_data["id"])
                if chapter_num := chapter_data["attributes"]["chapter"]:
                    title = f"Chapter {chapter_num}"
                    title_append = chapter_data["attributes"]["title"]
                    if title_append:
                        title += f" • {title_append}"
                else:
                    title = "Oneshot"

                uploaded = parse(chapter_data["attributes"]["createdAt"])
                chapters.append(
                    Chapter(number=i, title=title, url=url, uploaded=uploaded)
                )

            params["offset"] += 500
            if params["offset"] >= total:
                break

            url = Url(manga_feed_url)
            url.set_params(params)

            request = Request(url)
            request.source = self
            request.setPriority(Request.Priority.HighPriority)

            r = self.network.handle_request(request)
            self.network.wait_for_request(r)
            if r.error() != Response.Error.NoError:
                break

            json = QJsonDocument.fromJson(r.read_all()).toVariant()
            r.deleteLater()

        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        id = re.match(r"https://mangadex\.org/chapter/((\S+))", chapter.url).group(1)  # fmt: skip
        url = f"{MangaDex.API_URL}/at-home/server/{id}?forcePort443=true"
        return Request(url)

    def parse_chapter_pages(self, response: Response) -> list[Page]:
        json = QJsonDocument.fromJson(response.read_all()).toVariant()

        url: str = MangaDex.UPLOAD_URL + "/data/" + json["chapter"]["hash"] + "/{0}"
        pages = [
            Page(number=number, url=url.format(page))
            for number, page in enumerate(json["chapter"]["data"])
        ]
        return pages

    def search_for_manga(self, query: str) -> None:
        params = {
            "title": query,
            "limit": 100,
            "includes[]": ["cover_art"],
            "hasAvailableChapters": "true",
            "contentRating[]": self.filters["content-rating"]["value"],
        }

        url = Url(f"{MangaDex.API_URL}/manga")
        url.set_params(params)
        return Request(url)

    def parse_search_results(self, response: Response) -> MangaList:
        json = QJsonDocument.fromJson(response.read_all()).toVariant()
        mangas = list(
            dict.fromkeys(
                Manga(title=title, url=url, thumbnail=thumbnail)
                for title, thumbnail, url in parse_manga_data(json)
            )
        )
        return MangaList(mangas=mangas, has_next_page=False)

    def get_thumbnail(self, manga: Manga) -> Request:
        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Origin, BASE_URL)
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Referer, f"{BASE_URL}/")

        request = super().get_thumbnail(manga)
        request.setHeaders(headers)
        return request

    def update_filters(self, filters) -> None:
        new_filters = filters["content-rating"]
        if new_filters == self.filters["content-rating"]["value"]:
            return False

        self.filters["content-rating"]["value"] = new_filters
        return True
