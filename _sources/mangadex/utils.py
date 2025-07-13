from enum import StrEnum

from yomu.core import Request
from yomu.core.network import Url

__all__ = (
    "BASE_URL",
    "API_URL",
    "UPLOAD_URL",
    "Regex",
    "create_manga_request",
    "parse_manga_data",
)

BASE_URL = "https://mangadex.org"
API_URL = "https://api.mangadex.org"
UPLOAD_URL = "https://uploads.mangadex.org"


class Regex(StrEnum):
    CHAPTER = r"https://api\.mangadex\.org/manga/(\S+)/feed\S+"
    MANGA = r"https://mangadex\.org/title/(\S+)"


def create_manga_request(manga_ids: list) -> Request:
    params = {
        "limit": len(manga_ids),
        "ids[]": manga_ids,
        "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
        "includes[]": ["cover_art", "author", "artist"],
    }

    url = Url(f"{API_URL}/manga")
    url.set_params(params)
    return Request(url)


def parse_manga_data(json: dict):
    manga_url = BASE_URL + "/title/{0}"
    cover_url = UPLOAD_URL + "/covers/{}/{}"
    for manga_data in json.get("data", []):
        dex_id = manga_data["id"]
        thumbnail = None
        for relationship in manga_data["relationships"]:
            if relationship["type"] == "cover_art":
                thumbnail = cover_url.format(
                    dex_id, relationship["attributes"]["fileName"]
                )
                break

        title = manga_data["attributes"]["title"].get("en")
        if title is None:
            for title_data in manga_data["attributes"]["altTitles"]:
                title = title_data.get("en")
                if title is not None:
                    break

        if title is None:
            title = tuple(manga_data["attributes"]["title"].values())[0]
        url = manga_url.format(dex_id)

        yield title, thumbnail, url
