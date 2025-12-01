from .armageddon import Armageddon
from .comix import Comix
from .firescans import FireScans
from .galaxydegenscans import GalaxyDegenScans
from .kappabeast import KappaBeast
from .manga18fx import Manga18fx
from .mangadex import MangaDex
from .nyxscans import NyxScans
from .templescan import TempleScan
from .theblank import TheBlank
from .toongod import ToonGod
from .toonily import Toonily
from .webtoonxyz import WebtoonXYZ


def _default_sources() -> list:
    return [
        Armageddon,
        Comix,
        FireScans,
        GalaxyDegenScans,
        KappaBeast,
        Manga18fx,
        MangaDex,
        NyxScans,
        TempleScan,
        TheBlank,
        ToonGod,
        Toonily,
        WebtoonXYZ,
    ]
