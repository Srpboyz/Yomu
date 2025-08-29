from yomu.core.network import Request
from yomu.source import Source, RateLimit, Manga


class MangaCache:
    def __init__(self):
        self.cache = []
        self.page = 0


class TempleScan(Source):
    name = "Temple Scan"
    BASE_URL = "https://www.templescans.com"
    rate_limit = RateLimit(1, 1)

    def get_latest(self, page: int) -> Request:
        if page == 1:
            response = self.network.handle_request()
            self.network.wait_for_request(response)
            self._cache = response.json()
            response.deleteLater()

        return super().get_latest(page)
