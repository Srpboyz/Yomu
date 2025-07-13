from yomu.core.network import Request
from yomu.source import Manga, RateLimit
from _sources.base.madara import Madara


class FireScans(Madara):
    name = "Fire Scans"
    BASE_URL = "https://firescans.xyz"
    rate_limit = RateLimit(20, 5)

    request_sub_string = "manga"

    def get_chapters(self, manga: Manga) -> Request:
        request = Request(
            f"{self.BASE_URL + manga.url}ajax/chapters", route=Request.Route.POST
        )
        request.setRawHeader(b"X-Requested-With", b"XMLHttpRequest")
        return request
