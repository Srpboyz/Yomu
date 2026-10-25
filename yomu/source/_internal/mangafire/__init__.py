from datetime import datetime
from typing import Sequence

from yomu.core.network import Request, Response, Url
from yomu.source import Chapter, MangaList, Manga, Page, RateLimit, Source

from .vrf import get_vrf_token
from .dto import *


class MangaFire(Source):
    BASE_URL = "https://mangafire.to"
    API_URL = BASE_URL + "/api"
    rate_limit = RateLimit(2)

    def get_latest(self, page: int) -> Request:
        path = "/titles"
        params = {"order[chapter_updated_at]": "desc", "page": page, "limit": 50}
        params["vrf"] = get_vrf_token(path, params)
        return Request(Url(MangaFire.API_URL + path, params=params))

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        path = "/titles"
        params = {
            "keyword": query,
            "content_rating[]": ["safe", "suggestive"],
            "order[relevance]": "desc",
            "page": 1,
            "limit": 30,
        }
        params["vrf"] = get_vrf_token(path, params)
        return Request(Url(MangaFire.API_URL + path, params=params))

    def parse_manga_dto(self, dto: MangaDto) -> Manga:
        poster = dto.get("poster")
        thumbnail = (
            poster.get("large") or poster.get("medium") or poster.get("small")
            if poster is not None
            else None
        )
        return Manga(
            title=dto["title"],
            thumbnail=thumbnail,
            url=f"/manga/{dto['slug']}.{dto['hid']}",
        )

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: APIResponse[MangaDto] = response.as_json()
        return MangaList(
            mangas=[self.parse_manga_dto(dto) for dto in data["items"]],
            has_next_page=data["meta"]["hasNext"],
        )

    def get_manga_info(self, manga: Manga) -> Request:
        *_, hid = manga.url.split(".")
        path = f"/titles/{hid}"
        return Request(
            Url(MangaFire.API_URL + path, params={"vrf": get_vrf_token(path, {})})
        )

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        dto: MangaDto = response.as_json()["data"]

        title = dto["title"]
        description = dto.get("synopsisHtml")
        authors = (
            ", ".join((author["title"] for author in dto.get("authors") or [])) or None
        )
        artists = (
            ", ".join((artist["title"] for artist in dto.get("artists") or [])) or None
        )
        poster = dto.get("poster")
        thumbnail = (
            poster.get("large") or poster.get("medium") or poster.get("small")
            if poster is not None
            else None
        )

        return Manga(
            title=title,
            description=description,
            author=authors,
            artist=artists,
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga, page: int = 1) -> Request:
        *_, hid = manga.url.split(".")
        path = f"/titles/{hid}/chapters"
        params = {
            "language": "en",
            "sort": "number",
            "order": "asc",
            "page": page,
            "limit": 200,
        }
        params["vrf"] = get_vrf_token(path, params)
        return Request(Url(MangaFire.API_URL + path, params=params))

    def parse_chapter_dto(
        self, dto: ChapterDto, number: int, manga_url: str
    ) -> ChapterDto:
        title = f"Chapter {dto['number']}"
        if dto["name"]:
            title += f" • {dto['name']}"
        created_at = dto.get("createdAt")
        uploaded = (
            datetime.fromtimestamp(created_at) if created_at is not None else None
        )
        return Chapter(
            title=title,
            number=number,
            uploaded=uploaded,
            url=f"{manga_url}/en/chapter-{dto['number']}#{dto['id']}",
        )

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        data: APIResponse[ChapterDto] = response.as_json()
        manga_url = manga.url.replace("manga", "read")

        items = data["items"]
        for page in range(2, data["meta"]["lastPage"] + 1):
            request = self.get_chapters(manga, page)
            request.source = self
            request.setPriority(Request.Priority.HighPriority)
            response = self.network.handle_request(request)
            response.wait()

            data: APIResponse[ChapterDto] = response.as_json()
            items.extend(data["items"])
            response.deleteLater()

        return [
            self.parse_chapter_dto(dto, i, manga_url) for i, dto in enumerate(items)
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        *_, chapter_id = chapter.url.split("#")
        path = f"/chapters/{chapter_id}"
        return Request(
            Url(MangaFire.API_URL + path, params={"vrf": get_vrf_token(path, {})})
        )

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        data: list[PageDto] = response.as_json()["data"]["pages"]
        return [Page(number=i, url=page["url"]) for i, page in enumerate(data)]

    def get_page(self, page: Page) -> Request:
        request = super().get_page(page)
        request.setRawHeader(b"Referer", f"{MangaFire.BASE_URL}/".encode())
        return request
