from __future__ import annotations
from bs4 import BeautifulSoup

from PyQt6.QtNetwork import QNetworkCookie

from yomu.core import Request
from yomu.core.network import Network, Response
from yomu.source import FilterType
from yomu.source.models import *

from _sources.base.madara import Madara


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

    def __init__(self, network: Network) -> None:
        super().__init__(network)
        self._is_nsfw = False
        network.cookieJar().setCookiesFromUrl(
            [QNetworkCookie(b"toonily-mature", b"0")], Toonily.BASE_URL
        )

    @property
    def is_nsfw(self) -> bool:
        return self._is_nsfw

    @is_nsfw.setter
    def is_nsfw(self, nsfw: bool) -> None:
        self._is_nsfw = nsfw
        self.network.cookieJar().setCookiesFromUrl(
            [QNetworkCookie(b"toonily-mature", f"{int(nsfw)}".encode())],
            Toonily.BASE_URL,
        )

    def parse_chapter_pages(self, response: Response) -> list[Page]:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        pages = [
            Page(
                number=number,
                url=self.get_image_from_element(div.select_one("img")).strip(),
            )
            for number, div in enumerate(html.select(self.page_selector)[:-1])
        ]
        return pages

    def search_for_manga(self, query: str) -> Request:
        query = query.replace(" ", "-")
        return self._build_request(f"{Toonily.BASE_URL}/search/{query}")

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        new_value = filters.get("nsfw", False)
        if new_value == self.filters["nsfw"]["value"]:
            return False

        self.filters["nsfw"]["value"] = is_nsfw = new_value
        self.network.cookieJar().setCookiesFromUrl(
            [QNetworkCookie(b"toonily-mature", f"{int(is_nsfw)}".encode())],
            Toonily.BASE_URL,
        )
        return True
