from typing import TypedDict


class MangaDataDto(TypedDict):
    id: int
    iw7kl7l: str  # title
    description: str
    author: str
    thumbnail: str
    ke8ivdg: str  # slug


class ChapterDataDto(TypedDict):
    index: int
    q8m6vtm: str  # chapter_name
    chapter_title: str
    yy1u07t: str  # chapter_slug
    created_at: str
    q56zcrk: int  # price
