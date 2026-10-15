import re

from bs4 import BeautifulSoup, NavigableString, Tag
from dateparser import parse as parse_date

from yomu.core.network import Request, Response, Url
from yomu.source import Chapter, Manga, MangaList, Page, Source


class LunaToons(Source):
    name = "Luna Toons"
    BASE_URL = "https://lunatoons.net"
    CDN_URL = "https://cdn.meowing.org/uploads"

    def get_latest(self, page: int) -> Request:
        return Request(
            Url(LunaToons.BASE_URL, params={"_ajax": "recent-chapters", "page": page})
        )

    def parse_latest_element(self, element: Tag) -> Manga:
        tag = element.select_one("h2.ru-title > a")
        title, url = tag.text.strip(), tag.attrs["href"]

        tag = element.select_one("img.ru-cover-img")
        thumbnail = tag.attrs.get("data-src") if tag is not None else None

        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        document = response.as_beautifulsoup()
        mangas = list(
            map(self.parse_latest_element, document.select("article.ru-card"))
        )
        has_next_page = bool(
            document.select_one(
                'button[aria-label="Next recently updated page"]:not([disabled])'
            )
        )
        return MangaList(mangas=mangas, has_next_page=has_next_page)

    def search_for_manga(self, query: str) -> Request:
        return Request(Url(LunaToons.BASE_URL, params={"_ajax": "search", "q": query}))

    def parse_search_element(self, element: Tag) -> Manga:
        tag = element.select_one("h2")
        title = tag.text.strip() if element is not None else ""

        tag = element.select_one("img")
        thumbnail = tag.attrs.get("data-src") if tag is not None else None

        url = element.attrs["href"]
        return Manga(title=title, thumbnail=thumbnail, url=url)

    def is_novel(self, element: Tag) -> bool:
        if element.select('[data-type="novel" i]'):
            return True

        for span in element.find_all("span"):
            own_text = "".join(
                t for t in span.contents if isinstance(t, NavigableString)
            ).strip()
            if re.match(r"^novel$", own_text, re.IGNORECASE):
                return True

        return False

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        document = BeautifulSoup(response.as_json()["html"], features="lxml")
        mangas = list(
            map(
                self.parse_search_element,
                filter(
                    lambda e: not self.is_novel(e), document.select("a.group[href]")
                ),
            )
        )
        return MangaList(mangas=mangas)

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(LunaToons.BASE_URL + manga.url)

    def meta_value(self, document: BeautifulSoup, text: str) -> None:
        element = document.select_one(f"span.text-xs:-soup-contains({text})")
        if element is None:
            return None

        parent = element.parent
        if parent is None:
            return None

        sibling = parent.next_element_sibling
        if sibling is None:
            return None

        return sibling.text.strip() or None

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = response.as_beautifulsoup()

        element = document.select_one("h1")
        title = element.text.strip() if element is not None else manga.title

        element = document.select_one("#series-desc")
        description = element.get_text().strip() if element is not None else None

        element = document.select_one('meta[property="og:image"]')
        thumbnail = element.attrs["content"] if element is not None else None

        author = self.meta_value(document, "Author")
        artist = self.meta_value(document, "Artist")

        return Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=manga.url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        return Request(
            Url(
                LunaToons.BASE_URL,
                params={
                    "_chapters_html": "1",
                    "series_slug": manga.url.replace("/", ""),
                },
            )
        )

    def parse_chapter_from_element(self, element: Tag, number: int) -> Chapter:
        title = element.attrs["data-ch-label"]
        url = element.attrs["href"]
        element = element.select_one(".ch-date-row span:last-child")
        uploaded = parse_date(element.text) if element is not None else None
        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> list[Chapter]:
        document = BeautifulSoup(response.as_json()["rows_html"], features="lxml")
        return [
            self.parse_chapter_from_element(element, i)
            for i, element in enumerate(
                filter(
                    lambda e: e.attrs.get("data-ch-locked") != "1",
                    reversed(document.select("a.chapter-row[href]")),
                )
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(LunaToons.BASE_URL + chapter.url)

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        return [
            Page(number=i, url=element.attrs["src"])
            for i, element in enumerate(
                response.as_beautifulsoup().select("#strip-reader img.reader-page")
            )
        ]
