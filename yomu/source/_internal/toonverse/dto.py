from typing import NotRequired, TypedDict


class MangaDto(TypedDict):
    id: str
    title: str
    description: NotRequired[str]
    author: NotRequired[str]
    artist: NotRequired[str]
    chapterCount: int
    coverUrl: str
    slug: str


class ChapterDto(TypedDict):
    title: str
    number: float
    publishedAt: str


class PagesDto(TypedDict):
    number: int
    imageUrl: str
