from datetime import datetime
from typing import Sequence

from bs4 import BeautifulSoup, Tag
from dateparser import parse
from PyQt6.QtCore import QUrl, QUrlQuery

from yomu.core.network import Request, Response
from yomu.source import *
from yomu.source.models import Chapter, Manga, MangaList, Page


class Madara(Source):
    request_sub_string: str

    manga_latest_selector: str = "div.page-item-detail.manga"
    manga_search_selector: str = "div.c-tabs-item__content"
    next_page_selector: str = "div.nav-previous, nav.navigation-ajax, a.nextpostslink"

    manga_title_selector: str = (
        "div.post-title h3, div.post-title h1, #manga-title > h1"
    )
    manga_details_selector: str = (
        "div.description-summary div.summary__content, "
        "div.summary_content div.post-content_item > h5 + div, "
        "div.summary_content div.manga-excerpt"
    )
    manga_author_selector: str = "div.author-content > a"
    manga_artist_selector: str = "div.artist-content > a"
    manga_thumbnail_selector: str = "div.summary_image img"

    chapter_selector: str = "li.wp-manga-chapter"
    page_selector: str = "div.page-break.no-gaps"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _build_request(
        self,
        url: str | QUrl,
        route: Request.Route = Request.Route.GET,
        data: dict | None = None,
    ) -> Request:
        request = Request(url=url, route=route, data=data)
        request.setRawHeader(b"Referer", f"{self.BASE_URL}/".encode())
        return request

    def url_to_slug(self, url: str) -> str:
        return url.replace(self.BASE_URL, "")

    def get_image_from_element(self, element: Tag) -> str:
        attrs = element.attrs
        if "data-src" in attrs:
            return attrs["data-src"]
        if "data-lazy-src" in attrs:
            return attrs["data-lazy-src"]
        if "srcset" in attrs:
            return attrs["srcset"].split(" ")[0]
        if "data-cfsrc" in attrs:
            return attrs["data-cfsrc"]
        return attrs["src"]

    def get_latest(self, page: int) -> Request:
        url = f"{self.BASE_URL}/{self.request_sub_string}/"
        if page >= 2:
            url += f"page/{page}"
        url += "?m_orderby=latest"

        return self._build_request(url)

    def latest_manga_from_element(self, element: Tag) -> Manga:
        a = element.select_one("div.post-title.font-title a")
        title, url = a.text, self.url_to_slug(a.attrs["href"])

        img = element.select_one("img")
        thumbnail = self.get_image_from_element(img) if img is not None else None

        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_latest(self, response: Response, page: int) -> MangaList:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")

        mangas = list(
            map(self.latest_manga_from_element, html.select(self.manga_latest_selector))
        )
        can_load_more = bool(html.select(self.next_page_selector))

        return MangaList(mangas=mangas, has_next_page=can_load_more)

    def search_for_manga(self, query: str) -> None:
        query = query.replace(" ", "+")
        return self._build_request(self._build_search_query(query))

    def search_manga_from_element(self, element: Tag) -> Manga:
        a = element.select_one("div.post-title a")
        thumbnail = self.get_image_from_element(element.select_one("img"))

        title, url = a.text, self.url_to_slug(a.attrs["href"])
        return Manga(title=title, thumbnail=thumbnail, url=url)

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        mangas = list(
            map(self.search_manga_from_element, html.select(self.manga_search_selector))
        )
        return MangaList(mangas=mangas)

    def get_manga_info(self, manga: Manga) -> Request:
        return self._build_request(self.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")

        title = (
            html.select_one(self.manga_title_selector)
            .find(string=True, recursive=False)
            .strip()
        )

        description = html.select_one(self.manga_details_selector).get_text(separator=" ", strip=True)  # fmt:skip
        author = getattr(html.select_one(self.manga_author_selector), "text", None)
        artist = getattr(html.select_one(self.manga_artist_selector), "text", None)

        img = html.select_one(self.manga_thumbnail_selector)
        thumbnail = self.get_image_from_element(img) if img is not None else img
        url = self.url_to_slug(response.url().toString())

        info = Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=url,
        )
        return info

    def get_chapters(self, manga: Manga) -> Request:
        return self._build_request(self.BASE_URL + manga.url)

    def chapter_from_element(self, element: Tag, number: int) -> Chapter:
        a = element.find("a")
        title, url = a.text.strip(), self.url_to_slug(a.attrs["href"])

        if (upload_span := element.select_one("span a")) is not None:
            relative_upload = upload_span.attrs.get("title")
            uploaded = (
                parse(relative_upload)
                if relative_upload is not None
                else datetime.now()
            )
        else:
            uploaded = (
                parse(upload_span.text)
                if (upload_span := element.find("i")) is not None
                else datetime.now()
            )

        uploaded = uploaded or datetime.now()
        return Chapter(number=number, title=title, url=url, uploaded=uploaded)

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        chapters = [
            self.chapter_from_element(element, number)
            for number, element in enumerate(html.select(self.chapter_selector)[::-1])
        ]
        return chapters

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return self._build_request(self.BASE_URL + chapter.url)

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        pages = [
            Page(
                number=number,
                url=self.get_image_from_element(div.select_one("img")).strip(),
            )
            for number, div in enumerate(html.select(self.page_selector))
        ]
        return pages

    def get_thumbnail(self, manga: Manga) -> Request:
        return self._build_request(manga.thumbnail)

    def get_page(self, page: Page) -> Request:
        return self._build_request(page.url)

    def _build_search_query(self, query: str) -> QUrl:
        params = {"s": query, "post_type": "wp-manga"}

        url = QUrl(f"{self.BASE_URL}/")
        url_query = QUrlQuery()
        for param, value in params.items():
            if isinstance(value, list):
                for val in value:
                    url_query.addQueryItem(param, str(val))
            else:
                url_query.addQueryItem(param, str(value))
        url.setQuery(url_query)
        return url
