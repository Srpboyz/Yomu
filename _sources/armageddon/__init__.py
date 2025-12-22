import base64
import re
import json

from bs4 import BeautifulSoup
from yomu.core.network import Response
from yomu.source import Chapter, Page
from _sources.base.mangathemesia import MangaThemesia


class Armageddon(MangaThemesia):
    BASE_URL = "https://www.silentquill.net"
    request_sub_string = "manga"

    def parse_chapter_pages(self, response: Response, chapter: Chapter) -> list[Page]:
        document = BeautifulSoup(response.read_all().data(), features="html.parser")

        script = document.select_one("script:-soup-contains(WyJodHRw)")
        if script is None:
            return []

        match = re.search(
            rb"""['"](WyJodHRw[\w+/=]+)['"]""", response.read_all().data()
        )
        if match is None:
            return []

        base64_string = match.group(1)
        urls = json.loads(base64.b64decode(base64_string).decode("utf-8"))
        return [Page(number=number, url=url) for number, url in enumerate(urls)]
