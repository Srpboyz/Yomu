import re
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtNetwork import QHttpHeaders
from yomu.core.network import Request, Response, Url
from yomu.source import *

if TYPE_CHECKING:
    from .dto import *

LIMIT = 40


class Atsumaru(Source):
    BASE_URL = "https://atsu.moe"
    API_URL = f"{BASE_URL}/api"
    rate_limit = RateLimit(2)

    has_filters = True
    filters = {
        "nsfw": {
            "display_name": "NSFW",
            "value": False,
            "type": FilterType.CHECKBOX,
        }
    }

    def get_latest(self, page: int) -> Request:
        content_ratings = ["Safe", "Suggestive"]
        if self.filters["nsfw"]["value"]:
            content_ratings.extend(["Erotica", "Pornographic"])

        return Request(
            Url(
                f"{Atsumaru.API_URL}/home2/recentlyUpdated",
                params={
                    "offset": (page - 1) * LIMIT,
                    "limit": LIMIT,
                    "types": "Manga,Manwha,Manhua,OEL",
                    "mediums": "Comic",
                    "contentRatings": ",".join(content_ratings),
                },
            )
        )

    def parse_latest_manga(self, data: MangaDto) -> None:
        thumbnail = (
            f"{Atsumaru.BASE_URL}/static/{data['image']}"
            if "image" in data
            else f"{Atsumaru.BASE_URL}{data['poster']}"
        )

        return Manga(title=data["title"], thumbnail=thumbnail, url=data["id"])

    def parse_latest(self, response: Response, page: int) -> MangaList:
        data: BrowseMangaDto = response.as_json()
        return MangaList(
            mangas=list(
                map(
                    self.parse_latest_manga,
                    filter(
                        lambda d: d["medium"] == "Comic",
                        data["items"],
                    ),
                )
            ),
            has_next_page=True,
        )

    def search_for_manga(self, query: str) -> Request:
        filters = ["hidden:!=true"]
        if not self.filters["nsfw"]["value"]:
            filters.append("isAdult:=false")

        request = Request(
            Url(
                f"{Atsumaru.BASE_URL}/collections/manga/documents/search",
                params={
                    "q": query,
                    "query_by": "title,englishTitle,otherNames",
                    "limit": LIMIT,
                    "query_by_weights": "3,2,1",
                    "include_fields": "id,title,englishTitle,poster",
                    "num_typos": "4,3,2",
                    "filter_by": " && ".join(filters),
                },
            )
        )

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: SearchResultDto = response.as_json()
        return MangaList(
            mangas=list(
                map(lambda hit: self.parse_latest_manga(hit["document"]), data["hits"])
            ),
            has_next_page=False,
        )

    def get_manga_info(self, manga: Manga) -> Request:
        request = Request(f"{Atsumaru.API_URL}/manga/page?id={manga.url}")

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = response.as_json()["mangaPage"]

        return Manga(
            title=data["title"],
            description=data["synopsis"],
            author=", ".join(
                map(
                    lambda author: author["name"],
                    filter(lambda author: author["type"] == "Author", data["authors"]),
                )
            ),
            artist=", ".join(
                map(
                    lambda author: author["name"],
                    filter(lambda author: author["type"] == "Artist", data["authors"]),
                )
            ),
            thumbnail=f"{Atsumaru.BASE_URL}/static/{data['poster']['image']}",
            url=data["id"],
        )

    def get_chapters(self, manga: Manga) -> Request:
        request = Request(f"{Atsumaru.API_URL}/manga/allChapters?mangaId={manga.url}")

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_chapter(self, data: ChapterDto, manga_id: str, number: int) -> Chapter:
        return Chapter(
            title=data["title"],
            number=number,
            uploaded=datetime.fromtimestamp(data["createdAt"] / 1000),
            url=f"{manga_id}/{data['id']}",
        )

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        result: ChapterListDto = response.as_json()
        return [
            self.parse_chapter(chapter, manga.url, i)
            for i, chapter in enumerate(
                sorted(result["chapters"], key=lambda data: data["number"])
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        manga_id, chapter_id = chapter.url.split("/")

        request = Request(
            Url(
                f"{Atsumaru.API_URL}/read/chapter",
                params={"mangaId": manga_id, "chapterId": chapter_id},
            )
        )
        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_chatper_page(self, i: int, url: str) -> Page:
        if url.startswith("//"):
            url = f"https:{url}"
        elif not url.startswith("http"):
            url = (
                f"{Atsumaru.BASE_URL}/static/" 
                + url.removeprefix("/").removeprefix("static/")
            )  # fmt: skip
        url = re.sub(r"^https?:?//", "https://cdn.", url, count=1)
        return Page(number=i, url=url)

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        pages: PageDto = response.as_json()["readChapter"]

        return [
            self.parse_chatper_page(i, page["image"])
            for i, page in enumerate(pages["pages"])
        ]

    def get_page(self, page: Page) -> Request:
        url = Url(page.url)
        request = Request(url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Accept, "image/avif,image/webp,*/*"
        )
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, url.host())
        request.setHeaders(headers)

        return request

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        new_value = filters.get("nsfw", False)
        if new_value == self.filters["nsfw"]["value"]:
            return False

        self.filters["nsfw"]["value"] = new_value
        return True
