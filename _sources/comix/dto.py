from typing import TypedDict


class MangaDto(TypedDict):
    class Poster(TypedDict):
        small: str
        medium: str
        large: str

    hash_id: str
    title: str
    synopsis: str | None
    poster: Poster


class ChapterDto(TypedDict):
    chapter_id: int
    number: float
    name: str
    updated_at: int


class PaginationDto(TypedDict):
    current_page: int
    last_page: int


class ItemsDto(TypedDict):
    items: list[MangaDto]
    pagination: PaginationDto


class SearchResponse(TypedDict):
    result: ItemsDto
