from dataclasses import replace
from typing import Sequence

from yomu.core.network import Response
from yomu.source.base import MangaThemesia
from yomu.source.models import Chapter, Page


class Armageddon(MangaThemesia):
    BASE_URL = "https://www.silentquill.net"
    request_sub_string = "manga"
    image_attr = "data-src"

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        pages = super().parse_chapter_pages(response, chapter)
        return [
            replace(page, url=page.url.replace("https:///", "https://"))
            for page in pages
        ]
