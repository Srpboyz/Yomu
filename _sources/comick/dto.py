from typing import TypedDict


class Cover(TypedDict):
    w: int
    h: int
    b2key: str


class SearchManga(TypedDict):
    hid: str
    title: str
    desc: str
    md_covers: list[Cover]


class Author(TypedDict):
    name: str
    slug: str


class ComicInfo(TypedDict):
    comic: SearchManga
    authors: list[Author]
    artists: list[Author]


class ChapterInfo(TypedDict):
    hid: str
    vol: str | None
    chap: str
    title: str | None
    updated_at: str
    created_at: str
    lang: str
