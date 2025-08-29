from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from yomu.source import (
    Source,
    Manga as SourceManga,
    Chapter as SourceChapter,
    Page as SourcePage,
)

if TYPE_CHECKING:
    from .network import Request

__all__ = ("Manga", "Chapter", "Page")


@dataclass(slots=True, kw_only=True)
class Base:
    id: int
    title: str
    url: str

    def __eq__(self, value: object) -> bool:
        if type(value) != type(self):
            return False
        if hasattr(self, "id") and hasattr(value, "id"):
            return self.id == value.id
        return self.url == value.url

    def __ne__(self, value: object) -> bool:
        if type(value) != type(self):
            return True
        if hasattr(self, "id") and hasattr(value, "id"):
            return self.id != value.id
        return self.url != value.url

    def __hash__(self) -> int:
        return hash(self.id) if hasattr(self, "id") else hash(self.url)


@dataclass(repr=True, eq=False, kw_only=True)
class Manga(Base):
    source: Source | None
    description: str | None
    author: str | None
    artist: str | None
    thumbnail: str
    library: bool
    initialized: bool

    def to_source_manga(self) -> SourceManga:
        return SourceManga(
            title=self.title,
            description=self.description,
            author=self.author,
            artist=self.artist,
            thumbnail=self.thumbnail,
            url=self.url,
        )

    def get_manga_info(self) -> Request:
        request = self.source.get_manga_info(self.to_source_manga())
        request.source = self.source
        return request

    def get_chapters(self) -> Request:
        request = self.source.get_chapters(self.to_source_manga())
        request.source = self.source
        return request

    def get_thumbnail(self) -> Request:
        request = self.source.get_thumbnail(self.to_source_manga())
        request.source = self.source
        return request


@dataclass(repr=True, eq=False, kw_only=True)
class Chapter(Base):
    number: int
    manga: Manga
    uploaded: datetime
    downloaded: bool
    read: bool

    @property
    def source(self) -> Source:
        return self.manga.source

    def to_source_chapter(self) -> SourceChapter:
        return SourceChapter(
            number=self.number, title=self.title, url=self.url, uploaded=self.uploaded
        )

    def get_pages(self) -> Request:
        request = self.source.get_chapter_pages(self.to_source_chapter())
        request.source = self.source
        return request


@dataclass
class Page:
    number: int
    chapter: Chapter
    url: str
    downloaded: bool

    @property
    def source(self) -> Source:
        return self.chapter.source

    @classmethod
    def from_source_page(cls, chapter: Chapter, source_page: SourcePage) -> Page:
        return cls(
            number=source_page.number,
            chapter=chapter,
            url=source_page.url,
            downloaded=chapter.downloaded,
        )

    def to_source_page(self) -> SourcePage:
        return SourcePage(number=self.number, url=self.url)

    def get(self) -> Request:
        request = self.source.get_page(self.to_source_page())
        request.source = self.source
        return request


@dataclass
class Category:
    id: int
    name: str
