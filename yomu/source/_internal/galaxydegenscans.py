from yomu.core import Request
from yomu.source.models import *

from yomu.source.base import Madara


class GalaxyDegenScans(Madara):
    name = "Galaxy Degen Scans"
    BASE_URL = "https://gdscans.com"

    request_sub_string = "manga"
    page_selector = "div.page-break"

    def get_chapters(self, manga: Manga) -> Request:
        request = Request(
            f"{self.BASE_URL + manga.url}ajax/chapters/", route=Request.Route.POST
        )
        request.setRawHeader(b"Referer", manga.url.encode())
        request.setRawHeader(b"X-Requested-With", b"XMLHttpRequest")
        return request
