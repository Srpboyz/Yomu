from yomu.core.network import Request
from yomu.source import Manga, RateLimit
from yomu.source.base import Madara


class TheBlank(Madara):
    name = "The Blank Scanlations"
    BASE_URL = "https://theblank.net"
    rate_limit = RateLimit(10)

    request_sub_string = "manga"
    chapter_selector: str = "li.wp-manga-chapter:not(.vip-permission)"

    def get_chapters(self, manga: Manga) -> Request:
        request = Request(
            f"{self.BASE_URL + manga.url}/ajax/chapters", route=Request.Route.POST
        )
        request.setRawHeader(b"X-Requested-With", b"XMLHttpRequest")
        return request
