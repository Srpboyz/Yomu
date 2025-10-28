from datetime import datetime

from bs4 import Tag
from dateparser import parse
from PyQt6.QtNetwork import QSslConfiguration, QSslSocket

from yomu.core import Request
from yomu.source import *
from _sources.base.madara import Madara


class Manga18fx(Madara):
    BASE_URL = "https://manga18fx.com"

    manga_latest_selector = "div.listupd > div.page-item"
    manga_search_selector = manga_latest_selector
    next_page_selector = "li.next:not(.disabled)"

    manga_details_selector = "div.dsct"
    chapter_selector = "li.a-h"
    page_selector = "div.page-break"

    def url_to_slug(self, url: str) -> str:
        return url

    def get_latest(self, page: int) -> Request:
        return self._build_request(f"{Manga18fx.BASE_URL}/page/{page}")

    def latest_manga_from_element(self, element: Tag) -> Manga:
        a = element.select_one("div.thumb-manga a")
        title, url = a.get("title", ""), self.url_to_slug(a.attrs["href"])
        thumbnail = element.select_one("img").attrs["data-src"]

        return Manga(title=title, thumbnail=thumbnail, url=url)

    def search_for_manga(self, query: str) -> Request:
        query = query.replace(" ", "+")
        return self._build_request(f"{Manga18fx.BASE_URL}/search?q={query}")

    search_manga_from_element = latest_manga_from_element

    def chapter_from_element(self, element: Tag, number: int) -> Chapter:
        a = element.find("a")
        title, url = a.text.strip(), self.url_to_slug(a.attrs["href"])
        uploaded = (
            parse(upload_span.text)
            if (upload_span := element.select_one("span")) is not None
            else datetime.now()
        )

        return Chapter(number=number, title=title, url=url, uploaded=uploaded)

    def get_page(self, page: Page) -> Request:
        request = super().get_page(page)
        ssl = QSslConfiguration()
        ssl.setPeerVerifyMode(QSslSocket.PeerVerifyMode.VerifyNone)
        request.setSslConfiguration(ssl)
        return request
