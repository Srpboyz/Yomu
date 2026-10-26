from datetime import datetime
from math import ceil

from yomu.core.network import Response, Request, Url
from yomu.source import *
from .dto import *

LATEST_LIMIT = 24
CHAPTER_LIMIT = 100


class ToonVerse(Source):
    BASE_URL = "https://toonverse.net"
    API_URL = "https://api.toonverse.net/api"

    def get_latest(self, page: int) -> Request:
        return Request(
            Url(
                f"{ToonVerse.API_URL}/series",
                params={
                    "sortBy": "updated",
                    "limit": LATEST_LIMIT,
                    "offset": LATEST_LIMIT * (page - 1),
                },
            )
        )

    def parse_latest(self, response: Response, page: int) -> MangaList:
        data = response.as_json()["data"]
        return MangaList(
            mangas=[
                Manga(
                    title=dto["title"],
                    thumbnail=dto["coverUrl"],
                    url=dto["slug"],
                )
                for dto in data["items"]
            ],
            has_next_page=data["hasMore"],
        )

    def search_for_manga(self, query: str) -> None:
        return Request(
            Url(
                f"{ToonVerse.API_URL}/series",
                params={"search": query.strip(), "limit": 24},
            )
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data = response.as_json()["data"]
        return MangaList(
            mangas=[
                Manga(
                    title=dto["title"],
                    thumbnail=dto["coverUrl"],
                    url=dto["slug"],
                )
                for dto in data["items"]
            ]
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(f"{ToonVerse.API_URL}/series/slug/{manga.url}")

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = response.as_json()["data"]
        return Manga(
            title=data["title"],
            description=data.get("description"),
            author=data.get("author"),
            artist=data.get("artist"),
            thumbnail=data["coverUrl"],
            url=data["slug"],
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(f"{ToonVerse.API_URL}/series/slug/{manga.url}")

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        data: MangaDto = response.as_json()["data"]
        manga_id = data["id"]

        chapters: list[ChapterDto] = []
        for i in range(ceil(data["chapterCount"] / CHAPTER_LIMIT)):
            request = Request(
                Url(
                    f"{ToonVerse.API_URL}/series/{manga_id}/chapters",
                    params={
                        "limit": CHAPTER_LIMIT,
                        "offset": CHAPTER_LIMIT * i,
                        "order": "asc",
                    },
                )
            )

            response = self.network.handle_request(request)
            response.wait()
            chapters.extend(response.as_json()["data"]["chapters"])

        return [
            Chapter(
                title=dto["title"],
                number=i,
                uploaded=datetime.fromisoformat(dto["publishedAt"]),
                url=f"{manga.url}/{dto['number']}",
            )
            for i, dto in enumerate(chapters)
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(f"{ToonVerse.API_URL}/reading/chapter/{chapter.url}")

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        pages: list[PagesDto] = response.as_json()["data"]["chapter"]["pages"]
        return [Page(number=dto["number"], url=dto["imageUrl"]) for dto in pages]
