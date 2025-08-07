from .armageddon import Armageddon
from .comick import Comick
from .firescans import FireScans
from .galaxydegenscans import GalaxyDegenScans
from .kappabeast import KappaBeast
from .manga18fx import Manga18fx
from .mangafire import MangaFire
from .mangadex import MangaDex
from .nyxscans import NyxScans
from .theblank import TheBlank
from .toongod import ToonGod
from .toonily import Toonily
from .webtoonxyz import WebtoonXYZ


def _default_sources() -> list:
    return [
        Armageddon,
        Comick,
        FireScans,
        GalaxyDegenScans,
        KappaBeast,
        Manga18fx,
        MangaFire,
        MangaDex,
        NyxScans,
        TheBlank,
        ToonGod,
        Toonily,
        WebtoonXYZ,
    ]
