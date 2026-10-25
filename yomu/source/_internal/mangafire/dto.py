from typing import NotRequired, TypedDict


class APIMeta(TypedDict):
    lastPage: int
    hasNext: bool


class APIResponse[T](TypedDict):
    items: list[T]
    meta: APIMeta


class PosterDto(TypedDict):
    small: NotRequired[str]
    medium: NotRequired[str]
    large: NotRequired[str]


class EntityDto(TypedDict):
    title: str


class MangaDto(TypedDict):
    hid: str
    slug: str
    title: str
    poster: NotRequired[PosterDto]
    synopsisHtml: NotRequired[str]
    authors: NotRequired[list[EntityDto]]
    artists: NotRequired[list[EntityDto]]


class ChapterDto(TypedDict):
    id: int
    number: float
    name: NotRequired[str]
    createdAt: NotRequired[int]
    language: str


class PageDto(TypedDict):
    url: str
