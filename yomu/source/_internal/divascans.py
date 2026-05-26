from typing import Sequence

from bs4 import BeautifulSoup

from yomu.core.network.response import Response
from yomu.source import Page
from yomu.source.base import Iken
from yomu.source.models import Chapter


class DivaScans(Iken):
    name = "Diva Scans"
    BASE_URL = "https://divatoon.com"
    API_URL = "https://api.divatoon.com/api"

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        return [
            Page(number=i, url=img.attrs["src"])
            for i, img in enumerate(document.select("img[data-reader-page-image]"))
        ]
