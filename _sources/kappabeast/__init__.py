import json
import re


from yomu.core import Request
from yomu.core.network import Response
from yomu.source import *

from _sources.base.mangathemesia import MangaThemesia
from yomu.source import MangaList, Page


class KappaBeast(MangaThemesia):
    name = "Kappa Beast"
    BASE_URL = "https://kappabeast.com"
    rate_limit = RateLimit(3, 1)

    request_sub_string = "manga"
    page_selector = ".epcontent.entry-content img"

    def get_latest(self, page: int) -> Request:
        return self._build_request("https://kappabeast.com/manga/?order=update")

    def parse_latest(self, response: Response) -> MangaList:
        return self.parse_search_results(response)

    def search_for_manga(self, query: str) -> Request:
        return self._build_request(f"https://kappabeast.com/?s={query}")

    def parse_chapter_pages(self, response: Response) -> list[Page]:
        urls: list[str] = json.loads(
            re.search(rb'"images"\s*:\s*(\[.*?])', response.read_all().data()).group(1)
        )
        return [Page(number=number, url=url) for number, url in enumerate(urls)]
