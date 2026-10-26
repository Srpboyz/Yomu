from typing import NotRequired, TypedDict


class MangaDto(TypedDict):
    id: int
    title: str
    photo: NotRequired[str]
    description: NotRequired[str]
    authors: NotRequired[str]
    artists: NotRequired[str]


class ChapterDto(TypedDict):
    id: int
    chapter_number: NotRequired[float]
    chapter_title: NotRequired[str]
    volume_number: NotRequired[str]
    date_added: NotRequired[str]


class PaginationDto(TypedDict):
    total: NotRequired[int]
    current: NotRequired[int]
    nextCursor: NotRequired[str]


class ViewAllDataDto(TypedDict):
    manga_list: list[MangaDto]
    pagination: PaginationDto
