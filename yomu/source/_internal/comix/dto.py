from typing import NotRequired, TypedDict


class MangaDto(TypedDict):
    class Poster(TypedDict):
        small: str
        medium: str
        large: str

    hid: str
    title: str
    synopsis: str | None
    poster: Poster


class ChapterDto(TypedDict):
    id: int
    number: float
    name: str
    createdAtFormatted: str


class MetaDto(TypedDict):
    page: int
    lastPage: int
    hasNext: int


class PaginationDto(TypedDict):
    current_page: int
    last_page: int


class ItemsDto(TypedDict):
    items: list[MangaDto]
    meta: NotRequired[MetaDto]
    pagination: NotRequired[PaginationDto]


class SearchResponse(TypedDict):
    result: ItemsDto
