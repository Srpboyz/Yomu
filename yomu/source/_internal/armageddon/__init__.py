from yomu.source.base import MangaThemesia


class Armageddon(MangaThemesia):
    BASE_URL = "https://www.silentquill.net"
    request_sub_string = "manga"
    image_attr = "data-src"
