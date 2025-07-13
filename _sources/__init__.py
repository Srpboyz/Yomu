from .comick import Comick
from .firescans import FireScans
from .flamecomics import FlameComics
from .galaxydegenscans import GalaxyDegenScans
from .kappabeast import KappaBeast
from .kdtscans import KDTScans
from .manga18fx import Manga18fx
from .mangafire import MangaFire
from .mangadex import MangaDex
from .mangakakalot import Mangakakalot
from .nyxscans import NyxScans
from .theblank import TheBlank
from .toongod import ToonGod
from .toonily import Toonily
from .webtoonxyz import WebtoonXYZ


def _default_sources() -> list:
    return [
        Comick,
        FireScans,
        FlameComics,
        GalaxyDegenScans,
        KappaBeast,
        KDTScans,
        Manga18fx,
        MangaFire,
        MangaDex,
        Mangakakalot,
        NyxScans,
        TheBlank,
        ToonGod,
        Toonily,
        WebtoonXYZ,
    ]
