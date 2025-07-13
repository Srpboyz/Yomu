from datetime import datetime
import json

from bs4 import BeautifulSoup
from dateparser import parse

from yomu.core.network import Response, Request, Url
from yomu.source import *

from .types import *


class NyxScans(Source):
    BASE_URL = "https://nyxscans.com"
    API_URL = "https://api.nyxscans.com/api"

    per_page = 18

    def get_latest(self, page: int) -> Request:
        return Request(
            f"{NyxScans.API_URL}/query?page={page}&perPage={NyxScans.per_page}"
        )

    def parse_latest(self, response: Response) -> MangaList:
        return self.parse_search_results(response)

    def get_manga_info(self, manga: Manga) -> Request:
        return Request(f"{NyxScans.BASE_URL}/series/{manga.url}")

    def parse_manga_info(self, response: Response) -> Manga:
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        script = html.find_all("script", type="application/ld+json")[-1]

        data = json.loads(script.get_text(strip=True))
        for manga_data in data["@graph"][::-1]:
            if manga_data["@type"] == "Article":
                break
        else:
            raise TypeError("Couldn't get manga data")

        title = manga_data["name"]
        description = manga_data["description"]
        author = manga_data["author"]["name"]
        thumbnail = manga_data["image"]["@id"]
        url = response.url().toString().replace(f"{NyxScans.BASE_URL}/series/", "")

        return Manga(
            title=title,
            description=description,
            author=author,
            thumbnail=thumbnail,
            url=url,
        )

    def get_chapters(self, manga: Manga) -> Request:
        manga_id = Url(manga.url).fragment()
        return Request(
            f"{NyxScans.API_URL}/chapters?postId={manga_id}&skip=0&take=999&order=desc&userId=undefined"
        )

    def _parse_chapter(self, chapter: ChapterDto) -> Chapter:
        number = chapter["number"]
        slug = f"{chapter['mangaPost']['slug']}/{chapter['slug']}"
        uploaded = parse(chapter["createdAt"]) or datetime.now()

        title = f"Chapter {number}"
        if chapter["title"]:
            title += f" • {chapter['title']}"

        return Chapter(title=title, number=number, url=slug, uploaded=uploaded)

    def parse_chapters(self, response: Response) -> list[Chapter]:
        return list(
            map(
                self._parse_chapter,
                filter(
                    lambda chapter: chapter["isAccessible"],
                    response.json()["post"]["chapters"],
                ),
            )
        )

    def get_chapter_pages(self, chapter: Chapter) -> Request:
        return Request(f"{NyxScans.BASE_URL}/series/{chapter.url}")

    def parse_chapter_pages(self, response):
        html = BeautifulSoup(response.read_all().data(), features="html.parser")
        script = html.select_one("script:-soup-contains(images)")
        if script is None:
            raise TypeError()

        data = script.get_text(strip=True)
        index = data.index("images")
        start = data.index("[", index)

        depth = 1
        end = start + 1

        while end < len(data) and depth > 0:
            char = data[end]
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            end += 1

        images = json.loads(data[start:end].replace("\\", ""))
        return list(
            map(lambda image: Page(number=image["order"], url=image["url"]), images)
        )

    def search_for_manga(self, query: str) -> Request:
        return Request(f"{NyxScans.API_URL}/query?page=1&perPage=18&searchTerm={query}")

    def parse_search_results(self, response: Response) -> MangaList:
        data: MangaListDto = response.json()

        mangas = [
            Manga(
                title=manga["postTitle"],
                thumbnail=manga["featuredImage"],
                url=f"{manga['slug']}#{manga['id']}",
            )
            for manga in filter(lambda manga: not manga["isNovel"], data["posts"])
        ]

        page = int(response.url().query().queryItemValue("page"))
        has_next_page = (page * NyxScans.per_page) > data["totalCount"]

        return MangaList(mangas=mangas, has_next_page=has_next_page)
