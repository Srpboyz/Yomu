from typing import NotRequired, TypedDict


class ItemDto(TypedDict):
    title: str
    slug: str
    coverImageUrl: NotRequired[str]


class SeriesDto(TypedDict):
    items: list[ItemDto]
    page: int
    totalPages: int


class MangaDetailsDto(TypedDict):
    title: str
    synopsis: NotRequired[str]
    coverImageUrl: NotRequired[str]
    authors: NotRequired[list[MangaInfoDto]]
    artists: NotRequired[list[MangaInfoDto]]


class MangaInfoDto(TypedDict):
    name: str


class ChapterDto(TypedDict):
    number: str
    title: str | None
    slug: str
    publishedAt: str
    coinPrice: int

    # Used for getting pages
    id: int
    pages: list[PageDto]
    scrambled: bool


class PageDto(TypedDict):
    position: int
    url: str
    mime: str


class PageKeysDto(TypedDict):
    chapterKeyB64: str
    gridSize: int
    sessionDefault: bool


class OpenResponseDto(TypedDict):
    sessionId: str
    payloadA: int


class DrmResponse(TypedDict):
    payloadB: str
