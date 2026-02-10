from typing import TypedDict, NotRequired


class PosterDto(TypedDict):
    image: str


class AuthorDto(TypedDict):
    name: str


class MangaDto(TypedDict):
    id: str
    title: str
    authors: list[AuthorDto]
    synopsis: str
    image: NotRequired[str]  # either image or poster is given
    poster: NotRequired[PosterDto]


class BrowseMangaDto(TypedDict):
    items: list[MangaDto]


class SearchResultDto(TypedDict):
    class SearchMangaDto(TypedDict):
        document: MangaDto

    hits: list[SearchMangaDto]


class ChapterDto(TypedDict):
    id: str
    title: str
    createdAt: str


class ChapterListDto(TypedDict):
    chapters: list[ChapterDto]
    pages: int
    page: int


class PageDataDto(TypedDict):
    image: str


class PageDto(TypedDict):
    pages: list[PageDataDto]
