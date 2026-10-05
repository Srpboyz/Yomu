from yomu.core.network import Response
from yomu.source.base import Madara
from yomu.source import *


class ToonGod(Madara):
    BASE_URL = "https://www.toongod.org"
    request_sub_string = "webtoons"

    def parse_manga_info(self, response: Response, manga: Manga) -> Manga:
        document = response.as_beautifulsoup()

        title = (
            document.select_one(self.manga_title_selector)
            .find(string=True, recursive=False)
            .strip()
        )

        description = (
            document.select_one(self.manga_details_selector)
            .select_one("p")
            .get_text(separator=" ", strip=True)
        )
        author = getattr(document.select_one(self.manga_author_selector), "text", None)
        artist = getattr(document.select_one(self.manga_artist_selector), "text", None)

        img = document.select_one(self.manga_thumbnail_selector)
        thumbnail = self.get_image_from_element(img) if img is not None else img
        url = self.url_to_slug(response.url().toString())

        info = Manga(
            title=title,
            description=description,
            author=author,
            artist=artist,
            thumbnail=thumbnail,
            url=url,
        )
        return info
