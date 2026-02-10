from typing import TypedDict


class MangaDto(TypedDict):
    id: int
    slug: str
    postTitle: str
    postContent: str  # Description
    author: str
    artist: str
    featuredImage: str
    isNovel: bool


class MangaListDto(TypedDict):
    posts: list[MangaDto]
    totalCount: int


class ChapterDto(TypedDict):
    id: int
    slug: str
    title: str
    number: int
    createdAt: str
    isAccessible: bool
