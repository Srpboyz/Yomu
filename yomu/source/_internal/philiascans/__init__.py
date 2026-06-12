from dateparser import parse as parse_date
from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Request, Response, Url
from yomu.core.exceptions import YomuException
from yomu.source import *
from .dto import *

from .descrambler import process_image


class PhiliaScansImageException(YomuException):
    def __init__(self) -> None:
        super().__init__("Philia Scans: Failed to decrypt image")


class PhiliaScans(Source):
    name = "Philia Scans"
    BASE_URL = "https://philiascans.org"
    API_URL = f"{BASE_URL}/api"

    def get_latest(self, page: int) -> Request:
        return Request(
            Url(f"{PhiliaScans.API_URL}/manga", params={"page": page, "perPage": 20})
        )

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        return Request(
            Url(
                f"{PhiliaScans.API_URL}/manga",
                params={"page": 1, "perPage": 20, "q": query},
            )
        )

    def parse_manga_data(self, item: ItemDto) -> Manga:
        title = item["title"]

        thumbnail = item.get("coverImageUrl")
        if thumbnail is not None and not thumbnail.startswith("http"):
            thumbnail = PhiliaScans.BASE_URL + thumbnail

        url = f"/series/{item['slug']}"
        if not url.endswith("/"):
            url += "/"
        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        data: SeriesDto = response.json()
        return MangaList(
            mangas=list(map(self.parse_manga_data, data["items"])),
            has_next_page=data["page"] < data["totalPages"],
        )

    def get_manga_info(self, manga: Manga) -> Request:
        url = tuple(filter(None, manga.url.split("/")))[1]
        return Request(f"{PhiliaScans.API_URL}/manga/{url}")

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        data: MangaDetailsDto = response.json()

        thumbnail = data.get("coverImageUrl")
        if thumbnail is not None and not thumbnail.startswith("http"):
            thumbnail = PhiliaScans.BASE_URL + thumbnail

        return Manga(
            title=data["title"],
            description=data.get("synopsis"),
            author=", ".join((author["name"] for author in data.get("authors") or [])),
            artist=", ".join((artist["name"] for artist in data.get("artists") or [])),
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        url = tuple(filter(None, manga.url.split("/")))[1]
        return Request(f"{PhiliaScans.API_URL}/manga/{url}/chapters")

    def parse_chapter_data(self, data: ChapterDto, number: int, manga_url: str) -> None:
        title = f"Chapter {data['number']}"
        if data["title"]:
            title += f" • {data['title']}"
        uploaded = parse_date(data["publishedAt"])
        url = manga_url + data["slug"] + "/"
        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        return [
            self.parse_chapter_data(data, i, manga.url)
            for i, data in enumerate(
                sorted(
                    filter(
                        lambda data: not data["coinPrice"],
                        response.json()["items"],
                    ),
                    key=lambda data: float(data["number"]),
                )
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        segments = tuple(filter(None, chapter.url.split("/")))
        manga_url, chapter_url = segments[1:3]
        return Request(
            f"{PhiliaScans.API_URL}/manga/{manga_url}/chapters/{chapter_url}"
        )

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        data: ChapterDto = response.json()["chapter"]
        chapter_id, is_scrambled = data["id"], data["scrambled"]

        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Accept, "application/json")
        headers.replaceOrAppend(
            QHttpHeaders.WellKnownHeader.AcceptLanguage,
            "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6",
        )
        headers.replaceOrAppend("Sec-Fetch-Mode", "cors")
        headers.replaceOrAppend("X-Requested-With", "cors")

        request = Request(
            f"{PhiliaScans.API_URL}/reader/access-token", route=Request.Route.POST
        )
        request.setHeaders(headers)
        response = self.network.handle_request(request)
        response.wait()
        headers.replaceOrAppend("X-Reader-Access-Token", response.json()["token"])
        response.deleteLater()

        request = Request(f"{PhiliaScans.API_URL}/chapters/{chapter_id}/page-keys")
        request.setHeaders(headers)
        response = self.network.handle_request(request)
        response.wait()
        page_keys: PageKeysDto = response.json()
        response.deleteLater()

        request = Request(
            f"{PhiliaScans.API_URL}/chapters/{chapter_id}/open",
            route=Request.Route.POST,
        )
        request.setHeaders(headers)
        response = self.network.handle_request(request)
        response.wait()
        open_response: OpenResponseDto = response.json()
        response.deleteLater()

        request = Request(
            f"{PhiliaScans.API_URL}/chapters/{chapter_id}/get-drm?session={open_response['sessionId']}"
        )
        request.setHeaders(headers)
        response = self.network.handle_request(request)
        response.wait()
        drm_response: DrmResponse = response.json()
        response.deleteLater()

        def parse_chapter_page_data(page: PageDto) -> Page:
            url = page["url"]
            if not url.startswith("http"):
                url = PhiliaScans.BASE_URL + url
            url = f"{url}#{int(is_scrambled)};{page['mime']};{page_keys['chapterKeyB64']};{page_keys['gridSize']};{open_response['payloadA']};{drm_response['payloadB']}"
            return Page(number=page["position"], url=url)

        return list(map(parse_chapter_page_data, data["pages"]))

    def parse_page(self, response: Response, page: Page) -> bytes:
        if (image := process_image(response, page.number)) is None:
            raise PhiliaScansImageException
        return image
