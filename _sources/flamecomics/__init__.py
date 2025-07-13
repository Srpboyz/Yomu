from _sources.base.mangathemesia import MangaThemesia


class FlameComics(MangaThemesia):
    name = "Flame Comics"
    BASE_URL = "https://flamecomics.xyz"
    request_sub_string = "series"

    page_selector = "div#readerarea img:not(noscript img)[class*=wp-image]"
