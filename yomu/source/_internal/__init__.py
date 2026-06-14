from .armageddon import Armageddon
from .atsumaru import Atsumaru
from .comix import Comix
from .divascans import DivaScans
from .erisscans import ErisScans
from .firescans import FireScans
from .galaxydegenscans import GalaxyDegenScans
from .kappabeast import KappaBeast
from .manga18fx import Manga18fx
from .mangadex import MangaDex
from .mangadotnet import Mangadotnet
from .nyxscans import NyxScans
from .philiascans import PhiliaScans
from .templescan import TempleScan
from .theblank import TheBlank
from .toongod import ToonGod
from .toonily import Toonily
from .webtoonxyz import WebtoonXYZ
from .weebcentral import WeebCentral


def _default_sources() -> list:
    return [
        Armageddon,
        Atsumaru,
        Comix,
        DivaScans,
        ErisScans,
        FireScans,
        GalaxyDegenScans,
        KappaBeast,
        Manga18fx,
        MangaDex,
        Mangadotnet,
        NyxScans,
        PhiliaScans,
        TempleScan,
        TheBlank,
        ToonGod,
        Toonily,
        WebtoonXYZ,
        WeebCentral,
    ]
