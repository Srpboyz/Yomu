from typing import Sequence

from bs4 import BeautifulSoup
from PyQt6.QtNetwork import QNetworkCookie

from yomu.core import Request
from yomu.core.network import Response
from yomu.source import *
from yomu.source.base import Madara


class Toonily(Madara):
    BASE_URL = "https://toonily.com"
    has_filters = True
    filters = {
        "nsfw": {
            "display_name": "NSFW",
            "value": False,
            "type": FilterType.CHECKBOX,
        }
    }

    request_sub_string = "serie"
    manga_search_selector = "div.page-item-detail.manga"
    manga_details_selector = "div.summary__content p"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.network.cookieJar().setCookiesFromUrl(
            [QNetworkCookie(b"toonily-mature", b"0")], Toonily.BASE_URL
        )

    @property
    def is_nsfw(self) -> bool:
        return self.filters["nsfw"]["value"]

    @is_nsfw.setter
    def is_nsfw(self, is_nsfw: bool) -> None:
        self.filters["nsfw"]["value"] = is_nsfw
        self.network.cookieJar().setCookiesFromUrl(
            [QNetworkCookie(b"toonily-mature", f"{int(is_nsfw)}".encode())],
            Toonily.BASE_URL,
        )

    def search_for_manga(self, query: str) -> Request:
        query = query.replace(" ", "-")
        return self._build_request(f"{Toonily.BASE_URL}/search/{query}")

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        html = BeautifulSoup(response.read_all().data(), features="lxml")
        pages = [
            Page(
                number=number,
                url=self.get_image_from_element(div.select_one("img")).strip(),
            )
            for number, div in enumerate(html.select(self.page_selector)[:-1])
        ]
        return pages

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        new_value = filters.get("nsfw", False)
        if new_value == self.filters["nsfw"]["value"]:
            return False

        self.is_nsfw = new_value
        return True
