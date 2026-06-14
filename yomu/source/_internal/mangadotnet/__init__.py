import json
from datetime import datetime

from yomu.core.network import Request, Response, Url
from yomu.source import *
from yomu.source.models import Manga, Page

from .dto import *
from .helpers import has_next_page, decode_rsc


class Mangadotnet(Source):
    BASE_URL = "https://mangadot.net"

    def get_latest(self, page: int) -> Request:
        params = {"adult": "both", "_routes": "pages/ViewAllPage"}
        if page > 1:
            params["page"] = page
        return Request(
            Url(f"{Mangadotnet.BASE_URL}/view-all/latest-updates.data", params=params)
        )

    def parse_manga_data(self, manga: MangaDto) -> Manga:
        thumbnail = manga.get("photo")
        if thumbnail is not None and thumbnail.startswith("/"):
            thumbnail = Mangadotnet.BASE_URL + thumbnail
        return Manga(title=manga["title"], thumbnail=thumbnail, url=str(manga["id"]))

    def parse_latest(self, response: Response, page: int) -> MangaList:
        data: ViewAllDataDto = (
            decode_rsc(response.json())
                ["pages/ViewAllPage"]["data"]["data"]
        )  # fmt:skip

        return MangaList(
            mangas=list(map(self.parse_manga_data, data["manga_list"])),
            has_next_page=has_next_page(data["pagination"]),
        )

    def search_for_manga(self, query: str) -> Request:
        return Request(
            Url(
                f"{Mangadotnet.BASE_URL}/search.data",
                params={
                    "adult": "both",
                    "_routes": "pages/SearchPage",
                    "search": query,
                },
            )
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        return MangaList(
            mangas=list(
                map(
                    self.parse_manga_data,
                    decode_rsc(response.json())["pages/SearchPage"]["data"]["results"],
                )
            ),
            has_next_page=False,
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(
            f"{Mangadotnet.BASE_URL}/manga/{manga.url}.data?_routes=pages/MangaDetailPage"
        )

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = (
            decode_rsc(response.json())
                ["pages/MangaDetailPage"]["data"]["mangaData"]["manga"]
        )  # fmt:skip

        description = data.get("description")
        try:
            authors = ", ".join(json.loads(data.get("authors", "[]")))
        except json.decoder.JSONDecodeError:
            authors = data.get("authors")
        try:
            artists = ", ".join(json.loads(data.get("artists", "[]")))
        except json.decoder.JSONDecodeError:
            artists = data.get("artists")

        thumbnail = data.get("photo")
        if thumbnail is not None and thumbnail.startswith("/"):
            thumbnail = Mangadotnet.BASE_URL + thumbnail

        return Manga(
            title=data["title"],
            description=description,
            author=authors,
            artist=artists,
            thumbnail=thumbnail,
            url=str(data["id"]),
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(
            f"{Mangadotnet.BASE_URL}/api/manga/{manga.url}/chapters/list?lang=en"
        )

    def parse_chapter_data(self, data: ChapterDto, number: int) -> Chapter:
        title = data.get("chapter_title", "")
        if (
            "chapter" not in title.lower()
            and (chapter_num := data.get("chapter_number")) is not None
        ):
            title = f"Chapter {chapter_num} • {title}"
        if (
            "vol" not in title.lower()
            and (vol_num := data.get("volume_number")) is not None
        ):
            title = f"Vol {vol_num} • {title}"

        date_added = data.get("date_added")
        if date_added is not None:
            uploaded = datetime.fromisoformat(date_added)

        return Chapter(
            title=title, number=number, uploaded=uploaded, url=str(data["id"])
        )

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        return [
            self.parse_chapter_data(chapter_data, i)
            for i, chapter_data in enumerate(
                sorted(response.json(), key=lambda data: data["chapter_number"])
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(f"{Mangadotnet.BASE_URL}/api/chapters/{chapter.url}/images")

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(
                number=i,
                url=(
                    image["url"]
                    if image["url"].startswith("http")
                    else Mangadotnet.BASE_URL + image["url"]
                ),
            )
            for i, image in enumerate(response.json()["images"])
        ]
