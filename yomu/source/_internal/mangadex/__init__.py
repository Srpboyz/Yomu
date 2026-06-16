import re

from dateparser import parse

from yomu.core import Request
from yomu.core.network import Response, Url
from yomu.source import *

from .utils import *


class MangaDex(Source):
    BASE_URL = BASE_URL
    API_URL = API_URL
    UPLOAD_URL = UPLOAD_URL
    has_filters = True
    rate_limit = RateLimit(3)
    filters = {
        "content-rating": {
            "display_name": "Content Rating",
            "value": ["safe", "suggestive"],
            "options": ["safe", "suggestive", "erotica", "pornographic"],
            "type": FilterType.LIST,
        }
    }

    def get_latest(self, page: int) -> Request:
        offset = 100 * (page - 1)

        params = {
            "limit": 100,
            "offset": offset,
            "translatedLanguage[]": ["en"],
            "order[readableAt]": "desc",
            "includeFutureUpdates": 0,
            "includeFuturePublishAt": 0,
            "includeEmptyPages": 0,
            "contentRating[]": self.filters["content-rating"]["value"],
        }

        return Request(Url(f"{API_URL}/chapter", params=params), user_agent=USER_AGENT)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        json = response.json()

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
        response.wait()

        json = response.json()
        response.deleteLater()

        mangas = [
            Manga(title=title, url=url, thumbnail=thumbnail)
            for title, thumbnail, url in parse_manga_data(json)
        ]

        return MangaList(mangas=mangas, has_next_page=can_load_more)

    def search_for_manga(self, query: str) -> None:
        params = {
            "title": query,
            "limit": 100,
            "includes[]": ["cover_art"],
            "hasAvailableChapters": "true",
            "contentRating[]": self.filters["content-rating"]["value"],
        }

        return Request(Url(f"{API_URL}/manga", params=params), user_agent=USER_AGENT)

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        json = response.json()
        mangas = list(
            dict.fromkeys(
                Manga(title=title, url=url, thumbnail=thumbnail)
                for title, thumbnail, url in parse_manga_data(json)
            )
        )
        return MangaList(mangas=mangas, has_next_page=False)

    def get_manga_info(self, manga: Manga) -> Request:
        manga_id = re.match(Regex.MANGA, manga.url).group(1)
        return create_manga_request([manga_id])

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        json = response.json()

        manga_url = BASE_URL + "/title/{0}"
        cover_url = UPLOAD_URL + "/covers/{}/{}"

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

        title = utils.get_en_or_first_title(
            manga_data["attributes"]["title"], manga_data["attributes"]["altTitles"]
        )
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

        return Request(
            Url(f"{API_URL}/manga/{manga_id}/feed", params=params),
            user_agent=USER_AGENT,
        )

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        json = response.json()
        total = json["total"]

        manga_id = re.match(Regex.CHAPTER, response.url().toString()).group(1)

        chapter_url = BASE_URL + "/chapter/{0}"
        manga_feed_url = f"{API_URL}/manga/{manga_id}/feed"
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

            request = Request(
                Url(manga_feed_url, params=params), user_agent=USER_AGENT, source=self
            )
            request.setPriority(Request.Priority.HighPriority)

            response = self.network.handle_request(request)
            response.wait()
            if response.error() != Response.Error.NoError:
                break

            json = response.json()
            response.deleteLater()

        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        id = re.match(r"https://mangadex\.org/chapter/((\S+))", chapter.url).group(1)  # fmt: skip
        return Request(
            f"{API_URL}/at-home/server/{id}?forcePort443=true", user_agent=USER_AGENT
        )

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        json = response.json()

        url: str = UPLOAD_URL + "/data/" + json["chapter"]["hash"] + "/{0}"
        pages = [
            Page(number=number, url=url.format(page))
            for number, page in enumerate(json["chapter"]["data"])
        ]
        return pages

    def get_thumbnail(self, manga: Manga) -> Request:
        return Request(manga.thumbnail, user_agent=USER_AGENT)

    def get_page(self, page: Page) -> Request:
        return Request(page.url, user_agent=USER_AGENT)

    def update_filters(self, filters) -> None:
        new_filters = filters["content-rating"]
        if new_filters == self.filters["content-rating"]["value"]:
            return False

        self.filters["content-rating"]["value"] = new_filters
        return True
