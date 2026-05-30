from bs4 import BeautifulSoup, BeautifulStoneSoup
from yomu.core.network import Response
from yomu.source.base import Keyoapp
from yomu.source import Page


class ErisScans(Keyoapp):
    name = "Eris Scans"
    BASE_URL = "https://erisscans.com"

    manga_description_selector = "div.grid > div.overflow-hidden > p"
    manga_author_selector = "div[alt=Author]"
    manga_artist_selector = "div[alt=Artist]"

    def parse_chapter_pages(self, response: Response, _) -> list[Page]:
        document = BeautifulSoup(bytes(response.read_all()), features="lxml")
        return [
            Page(number=i, url=f"https://cdn.meowing.org/uploads/{uid}")
            for i, uid in enumerate(
                filter(
                    None,
                    map(
                        lambda element: element.attrs["uid"],
                        document.select("#pages > img"),
                    ),
                )
            )
        ]
