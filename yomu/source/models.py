from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime


__all__ = ("Manga", "MangaList", "Chapter", "Page")


@dataclass(slots=True, kw_only=True)
class Base:
    title: str
    url: str

    def __post_init__(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError(f"Title must be of type str, not {type(self.title)}")

        if not isinstance(self.url, str):
            raise TypeError(f"Url must be of type str, not {type(self.url)}")

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Base):
            return False
        return self.url == value.url

    def __ne__(self, value: object) -> bool:
        if not isinstance(value, Base):
            return True
        return self.url != value.url

    def __hash__(self) -> int:
        return hash(self.url)


@dataclass(repr=True, eq=False, kw_only=True, slots=True)
class Manga(Base):
    description: str | None = field(default=None)
    author: str | None = field(default=None)
    artist: str | None = field(default=None)
    thumbnail: str | None

    def __post_init__(self) -> None:
        if self.description is not None and not isinstance(self.description, str):
            raise TypeError(
                f"Description must be of type str or None, not {type(self.description)}"
            )

        if self.author is not None and not isinstance(self.author, str):
            raise TypeError(
                f"Author must be of type str or None, not {type(self.author)}"
            )

        if self.artist is not None and not isinstance(self.artist, str):
            raise TypeError(
                f"Artist must be of type str or None, not {type(self.artist)}"
            )

        if self.thumbnail is not None and not isinstance(self.thumbnail, str):
            raise TypeError(
                f"Thumbnail must be of type str, not {type(self.thumbnail)}"
            )

        return Base.__post_init__(self)


@dataclass(repr=True, eq=False, kw_only=True, slots=True)
class Chapter(Base):
    number: int
    uploaded: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.uploaded, datetime):
            raise TypeError(
                f"Variable uploaded must be of type datetime, not {type(self.uploaded)}"
            )

        return Base.__post_init__(self)


@dataclass(kw_only=True, slots=True)
class Page:
    number: int
    url: str

    def __post_init__(self) -> None:
        if not isinstance(self.number, int):
            raise TypeError(f"Number must be of type int, not {type(self.number)}")
        if not isinstance(self.url, str):
            raise TypeError(f"Url must be of type str, not {type(self.url)}")


@dataclass(repr=True, kw_only=True, slots=True)
class MangaList:
    mangas: Sequence[Manga]
    has_next_page: bool = field(default=False)

    def __post_init__(self) -> None:
        if not isinstance(self.mangas, Sequence) or not all(
            isinstance(manga, Manga) for manga in self.mangas
        ):
            raise TypeError(f"Mangas must be a Sequence[Manga]")

        if not isinstance(self.has_next_page, bool):
            raise TypeError(
                f"has_next_page must be of type bool, not {type(self.has_next_page)}"
            )
