from PyQt6.QtNetwork import QHttpHeaders

from yomu.core.network import Request
from yomu.source import Manga

from _sources.base.madara import Madara


class KDTScans(Madara):
    name = "KDT Scans"
    BASE_URL = "https://kdtscans.com"

    request_sub_string = "manga"

    page_selector = "div.page-break"

    def get_chapters(self, manga: Manga) -> Request:
        headers = QHttpHeaders()
        headers.replaceOrAppend(QHttpHeaders.WellKnownHeader.Referer, manga.url)
        headers.replaceOrAppend("X-Requested-With", manga.url)

        request = Request(
            f"{KDTScans.BASE_URL + manga.url}ajax/chapters/", route=Request.Route.POST
        )
        request.setHeaders(headers)
        return request

    def get_chapter_pages(self, chapter):
        return self._build_request(f"{KDTScans.BASE_URL + chapter.url}?style=list")
