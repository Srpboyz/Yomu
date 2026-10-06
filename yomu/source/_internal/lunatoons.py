from yomu.core.network.response import Response
from yomu.source import Chapter, Page
from yomu.source.base import Keyoapp


class LunaToons(Keyoapp):
    name = "Luna Toons"
    BASE_URL = "https://lunatoons.org"
    CDN_URL = "https://cdn.meowing.org/uploads"

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=i, url=f"{LunaToons.CDN_URL}/{image.attrs['uid']}")
            for i, image in enumerate(
                response.as_beautifulsoup().select("#pages > img")
            )
        ]
