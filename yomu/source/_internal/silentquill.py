from typing import Sequence
import re

from bs4 import Tag
from dateparser import parse as parse_date

from yomu.core.network import Request, Response, Url
from yomu.source import Chapter, Page
from yomu.source import *

CARD_REGEX = re.compile(
    r'"href":"/series/(?P<slug>[^"/]+)/","className":"block".*?"src":"(?P<img>[^"?]+)(?:\?[^"]*)?","alt":"(?P<title>(?:[^"\\]|\\.)*)"',
    re.DOTALL,
)

PAGE_REGEX = re.compile(r'\{"url":"(/img/p/[^"]+)","width":[^,]*,"height":[^}]*\}')


class SilentQuill(Source):
    BASE_URL = "https://www.silentquill.net"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Override id as the source was previously know as armaggedon
        self.id = 315898738210

    def get_latest(self, page: int) -> Request:
        return self.search_for_manga(page=page)

    def parse_latest_manga(self, m: re.Match) -> Manga:
        return Manga(
            title=m["title"],
            thumbnail=SilentQuill.BASE_URL + m["img"],
            url=f"/{m['slug']}/",
        )

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, page=page)

    def search_for_manga(self, query: str = "", *, page: int = 1) -> Request:
        request = Request(
            Url(f"{SilentQuill.BASE_URL}/search", params={"page": page, "q": query})
        )
        request.setRawHeader(b"rsc", b"1")
        return request

    def parse_search_results(
        self, response: Response, query: str = "", page: int = ""
    ) -> MangaList:
        next_js = bytes(response.read_all()).decode()
        mangas = list(map(self.parse_latest_manga, CARD_REGEX.finditer(next_js)))
        return MangaList(mangas=mangas, has_next_page="Next →" in next_js)

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(Url(f"{SilentQuill.BASE_URL}/series" + manga.url))

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = response.as_beautifulsoup()

        element = document.select_one("h1")
        title = element.get_text() if element is not None else manga.title

        element = document.select_one("div.reader-content")
        description = element.get_text() if element is not None else None

        element = document.select_one('main img[src^="/img/"]')
        thumbnail = (
            SilentQuill.BASE_URL + element.attrs["src"] if element is not None else None
        )

        element = document.select_one("p.mt-2.text-sm.text-ink-dim")
        author, artist = (
            element.get_text().split(" · art by ")
            if element is not None
            else [None, None]
        )

        return Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(Url(f"{SilentQuill.BASE_URL}/series" + manga.url))

    def parse_chapter_from_element(self, element: Tag, number: int) -> Chapter:
        title = element.select_one("span.text-base").get_text()
        uploaded = parse_date(element.select_one("span.text-right").get_text())
        url = element.attrs["href"]
        return Chapter(title=title, number=0, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        document = response.as_beautifulsoup()
        return [
            self.parse_chapter_from_element(element, i)
            for i, element in enumerate(document.select("a.grid.h-11")[::-1])
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        request = Request(SilentQuill.BASE_URL + chapter.url)
        request.setRawHeader(b"rsc", b"1")
        return request

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=i, url=SilentQuill.BASE_URL + url)
            for i, url in enumerate(
                PAGE_REGEX.findall(bytes(response.read_all()).decode())
            )
        ]
