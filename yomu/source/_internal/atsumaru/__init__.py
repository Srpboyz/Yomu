from __future__ import annotations
from typing import TYPE_CHECKING, Sequence

from dateparser import parse as parse_date
from PyQt6.QtNetwork import QHttpHeaders
from yomu.core.network import Request, Response, Url
from yomu.source import *

if TYPE_CHECKING:
    from .dto import *


class Atsumaru(Source):
    BASE_URL = "https://atsu.moe"
    rate_limit = RateLimit(2)

    def get_latest(self, page: int) -> Request:
        request = Request(
            f"{Atsumaru.BASE_URL}/api/infinite/recentlyUpdated?page={page - 1}&types=Manga,Manwha,Manhua,OEL"
        )

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_latest_manga(self, data: MangaDto) -> None:
        thumbnail = (
            f"{Atsumaru.BASE_URL}/static/{data['image']}"
            if "image" in data
            else f"{Atsumaru.BASE_URL}{data['poster']}"
        )

        return Manga(title=data["title"], thumbnail=thumbnail, url=data["id"])

    def parse_latest(self, response: Response, page: int) -> MangaList:
        data: BrowseMangaDto = response.json()
        return MangaList(
            mangas=list(map(self.parse_latest_manga, data["items"])), has_next_page=True
        )

    def search_for_manga(self, query: str) -> Request:
        url = Url(f"{Atsumaru.BASE_URL}/collections/manga/documents/search")
        url.set_params(
            {
                "q": query,
                "query_by": "title,englishTitle,otherNames",
                "limit": "24",
                "query_by_weights": "3,2,1",
                "include_fields": "id,title,englishTitle,poster",
                "num_typos": "4,3,2",
            }
        )

        request = Request(url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: SearchResultDto = response.json()
        return MangaList(
            mangas=list(
                map(lambda hit: self.parse_latest_manga(hit["document"]), data["hits"])
            ),
            has_next_page=False,
        )

    def get_manga_info(self, manga: Manga) -> Request:
        request = Request(f"{Atsumaru.BASE_URL}/api/manga/page?id={manga.url}")

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDto = response.json()["mangaPage"]

        return Manga(
            title=data["title"],
            description=data["synopsis"],
            author=", ".join(map(lambda author: author["name"], data["authors"])),
            thumbnail=f"{Atsumaru.BASE_URL}/static/{data['poster']['image']}",
            url=data["id"],
        )

    def get_chapters(self, manga: Manga, page: int = 0) -> Request:
        request = Request(
            f"{Atsumaru.BASE_URL}/api/manga/chapters?id={manga.url}&filter=all&sort=desc&page={page}"
        )

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_chapter(self, data: ChapterDto, manga_id: str, number: int) -> Chapter:
        return Chapter(
            title=data["title"],
            number=number,
            uploaded=parse_date(data["createdAt"]),
            url=f"{manga_id}/{data['id']}",
        )

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        result: ChapterListDto = response.json()

        chapters = [*result["chapters"]]
        while result["page"] + 1 < result["pages"]:
            response = self.network.handle_request(
                self.get_chapters(manga, result["page"] + 1)
            )
            response.wait()
            result: ChapterListDto = response.json()
            chapters.extend(result["chapters"])
            response.deleteLater()

        return [
            self.parse_chapter(chapter, manga.url, i)
            for i, chapter in enumerate(chapters[::-1])
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        manga_id, chapter_id = chapter.url.split("/")
        url = Url(f"{Atsumaru.BASE_URL}/api/read/chapter")
        url.set_params({"mangaId": manga_id, "chapterId": chapter_id})

        request = Request(url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "*/*")
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, "atsu.moe")
        request.setHeaders(headers)

        return request

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        pages: PageDto = response.json()["readChapter"]

        return [
            Page(number=i, url=page["image"]) for i, page in enumerate(pages["pages"])
        ]

    def get_page(self, page: Page) -> Request:
        url = Url(page.url)
        request = Request(page.url)

        headers = QHttpHeaders()
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.Accept, "image/avif,image/webp,*/*"
        )
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Host, url.host())
        request.setHeaders(headers)

        return request
