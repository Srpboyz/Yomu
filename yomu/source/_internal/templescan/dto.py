from typing import TypedDict


class MangaDataDto(TypedDict):
    id: int
    title: str
    description: str
    author: str
    thumbnail: str
    sref: str


class ChapterDataDto(TypedDict):
    index: int
    chapter_name: str
    chapter_title: str
    chapter_slug: str
    created_at: str
    lk: int
