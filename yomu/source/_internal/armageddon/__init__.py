from yomu.source.base import MangaThemesia


class Armageddon(MangaThemesia):
    BASE_URL = "https://www.silentquill.net"
    request_sub_string = "manga"
    title_selector = "h1.kdt8-left-title"
    details_selector = ".kdt8-synopsis"
    thumbnail_selector = ".kdt8-cover img"
