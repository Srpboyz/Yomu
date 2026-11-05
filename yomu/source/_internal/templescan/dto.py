from typing import TypedDict


class MangaDataDto(TypedDict):
    id: int
    zbs04ch: str  # title
    description: str
    author: str
    thumbnail: str
    dsj6345: str  # slug


class ChapterDataDto(TypedDict):
    bhatw56: int
    syzj8a3: str  # chapter_name
    chapter_title: str
    gwgbquh: str  # chapter_slug
    created_at: str
    ig522pf: int  # price
