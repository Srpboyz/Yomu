from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from hashlib import md5
from typing import NotRequired, Sequence, TypedDict

from yomu.core.network import Network, Request, Response
from .ratelimit import RateLimit
from .models import *


__all__ = ("FilterOption", "FilterType", "Source")


class FilterType(StrEnum):
    CHECKBOX = "CHECKBOX"
    LIST = "LIST"


class FilterOption(TypedDict):
    display_name: NotRequired[str]
    value: int | str | bool | list
    options: NotRequired[list[str]]
    type: FilterType


class Source(ABC):
    BASE_URL: str
    ICON_URL: str = None

    name: str
    rate_limit: RateLimit | None = None
    has_filters: bool = False
    filters: dict[str, FilterOption] = {}
    supports_latest: bool = True
    supports_search: bool = True

    def __init__(self, network: Network) -> None:
        self._network = network

        cls = self.__class__
        if not hasattr(cls, "name") or not isinstance(cls.name, str):
            cls.name = cls.__name__

        self.name = (
            cls.__name__
            if not hasattr(cls, "name") or not isinstance(cls.name, str)
            else cls.name
        )

        self.id = int(str(int(md5(self.name.lower().encode()).hexdigest(), 16))[:12])

    def __init_subclass__(cls) -> None:
        if hasattr(cls, "name") and not isinstance(cls.name, str):
            raise TypeError("Name must be of type str")

        if not isinstance(cls.rate_limit, RateLimit) and cls.rate_limit is not None:
            raise TypeError(
                f"The rate limit must be of type RateLimit or None, not {type(cls.rate_limit).__name__}"
            )

    @property
    def network(self) -> Network:
        return self._network

    def __hash__(self) -> int:
        return hash(self.id)

    @abstractmethod
    def get_latest(self, page: int) -> Request: ...

    @abstractmethod
    def parse_latest(self, response: Response) -> MangaList: ...

    def latest_request_error(self, response: Response) -> None: ...

    @abstractmethod
    def search_for_manga(self, query: str) -> Request: ...

    @abstractmethod
    def parse_search_results(self, response: Response) -> MangaList: ...

    def search_request_error(self, response: Response) -> None: ...

    @abstractmethod
    def get_manga_info(self, manga: Manga) -> Request: ...

    @abstractmethod
    def parse_manga_info(self, response: Response) -> Manga: ...

    def manga_info_request_error(self, response: Response) -> None: ...

    @abstractmethod
    def get_chapters(self, manga: Manga) -> Request: ...

    @abstractmethod
    def parse_chapters(self, response: Response) -> Sequence[Chapter]: ...

    def chapter_request_error(self, response: Response) -> None: ...

    @abstractmethod
    def get_chapter_pages(self, chapter: Chapter) -> Request: ...

    @abstractmethod
    def parse_chapter_pages(self, response: Response) -> Sequence[Page]: ...

    def chapter_pages_request_error(self, response: Response) -> None: ...

    def get_thumbnail(self, manga: Manga) -> Request:
        return Request(manga.thumbnail)

    def parse_thumbnail(self, response: Response) -> bytes:
        return response.read_all().data()

    def thumbnail_request_error(self, response: Response) -> None: ...

    def get_page(self, page: Page) -> Request:
        return Request(page.url)

    def parse_page(self, response: Response) -> bytes:
        return response.read_all().data()

    def page_request_error(self, response: Response) -> None: ...

    def update_filters(self, filters: dict[str, int | str | bool]) -> bool:
        return False
