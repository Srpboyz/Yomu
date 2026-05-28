import json
import re
from typing import TypedDict
from urllib.parse import urljoin

from typing import Sequence
from bs4 import BeautifulSoup, Tag
from dateparser import parse as parse_date

from yomu.core.network import Response, Request
from yomu.source import *


class ChapterDto(TypedDict):
    number: str
    title: str | None
    slug: str
    publishedAt: str
    coinPrice: int


class PhiliaScans(Source):
    name = "Philia Scans"
    BASE_URL = "https://philiascans.org"

    UNESCAPE_REGEX = re.compile(r"\\(.)")
    CHAPTERS_REGEX = re.compile(r"langChapters\\\":(\[.*?\])\s*,\s*\\\"hasVolumes")

    def image_from_tag(self, tag: Tag | None) -> str | None:
        if tag is None:
            return None
        attrs = tag.attrs
        if "data-lazy-src" in attrs:
            return attrs["data-lazy-src"]
        if "data-src" in attrs:
            return attrs["data-src"]
        return attrs["src"]

    def get_latest(self, page: int) -> Request:
        return Request(
            f"{PhiliaScans.BASE_URL}/all-mangas?m_orderby=recently-updated&m_order=desc&page={page}"
        )

    def parse_latest(self, response: Response, page: int) -> MangaList:
        return self.parse_search_results(response, "")

    def search_for_manga(self, query: str) -> Request:
        return Request(f"{PhiliaScans.BASE_URL}/all-mangas?s={query.replace(' ', '+')}")

    def parse_manga_from_tag(self, tag: Tag) -> Manga:
        img = tag.select_one("div.image-with-skeleton > img")
        title_tag = tag.select_one(".card-title, h3, h2")
        title = None

        if title_tag and (text := title_tag.get_text(" ", strip=True)):
            title = text

        if not title and img and (alt := img.get("alt", "").strip()):
            title = alt

        if not title:
            title = tag.get_text(" ", strip=True)

        if not title:
            return None

        lower_title = title.lower()
        if lower_title in ("read", "read now") or lower_title.startswith("chapter"):
            return None

        url = tag.attrs["href"].replace(PhiliaScans.BASE_URL, "")
        if not url.endswith("/"):
            url += "/"
        thumbnail = urljoin(PhiliaScans.BASE_URL, self.image_from_tag(img))
        return Manga(title=title, url=url, thumbnail=thumbnail)

    def parse_search_results(self, response: Response, query: str) -> MangaList:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        has_next_page = document.select_one("a.page-link[rel=next]") is not None
        return MangaList(
            mangas=list(
                filter(
                    None,
                    map(
                        self.parse_manga_from_tag,
                        document.select('a.manga-card, a[href^="/series/"]'),
                    ),
                )
            ),
            has_next_page=has_next_page,
        )

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(PhiliaScans.BASE_URL + manga.url)

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = BeautifulSoup(response.read_all().data(), features="lxml")

        title_tag = document.select_one("h1, .detail-title")
        title = title_tag.get_text(" ", True) if title_tag is not None else None

        description_tag = document.select_one(
            "#synopsis-wrap, .synopsis, .description, [class*=synopsis], [class*=description]"
        )
        description = (
            description_tag.get_text(" ", True) if description_tag is not None else None
        )

        author_tag = document.select_one(
            "ul.info-list li.info-key:has(span.info-key:-soup-contains(Author)) + span.info-val"
        )
        author = author_tag.get_text(strip=True) if author_tag is not None else None

        artist_tag = document.select_one(
            "ul.info-list li.info-key:has(span.info-key:-soup-contains(Author)) + span.info-val"
        )
        artist = artist_tag.get_text(strip=True) if artist_tag is not None else None

        thumbnail_tag = document.select_one(".detail-cover img, .manga-card-cover img")
        thumbnail = (
            urljoin(PhiliaScans.BASE_URL, self.image_from_tag(thumbnail_tag))
            if thumbnail_tag is not None
            else None
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
        return Request(PhiliaScans.BASE_URL + manga.url)

    def parse_chapter_data(self, data: ChapterDto, number: int, manga_url: str) -> None:
        title = f"Chapter {data['number']}"
        if data["title"]:
            title += f" • {data['title']}"
        uploaded = parse_date(data["publishedAt"])
        url = manga_url + data["slug"] + "/"
        return Chapter(title=title, number=number, uploaded=uploaded, url=url)

    def parse_chapters(self, response: Response, manga: Manga) -> Sequence[Chapter]:
        return [
            self.parse_chapter_data(data, i, manga.url)
            for i, data in enumerate(
                filter(
                    lambda data: not data["coinPrice"],
                    json.loads(
                        PhiliaScans.UNESCAPE_REGEX.sub(
                            r"\1",
                            next(
                                PhiliaScans.CHAPTERS_REGEX.finditer(
                                    response.read_all().data().decode()
                                )
                            ).group(1),
                        )
                    )[::-1],
                )
            )
        ]

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(PhiliaScans.BASE_URL + chapter.url)

    def parse_chapter_pages(
        self, response: Response, chapter: Chapter
    ) -> Sequence[Page]:
        document = BeautifulSoup(response.read_all().data(), features="lxml")
        return [
            Page(number=i, url=PhiliaScans.BASE_URL + self.image_from_tag(tag))
            for i, tag in enumerate(document.select("div.page-wrap img"))
        ]
