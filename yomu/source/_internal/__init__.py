from .armageddon import Armageddon
from .atsumaru import Atsumaru
from .divascans import DivaScans
from .erisscans import ErisScans
from .firescans import FireScans
from .galaxydegenscans import GalaxyDegenScans
from .manga18fx import Manga18fx
from .mangadex import MangaDex
from .mangadotnet import Mangadotnet
from .nyxscans import NyxScans
from .philiascans import PhiliaScans
from .templescan import TempleScan
from .toongod import ToonGod
from .toonily import Toonily
from .webtoonxyz import WebtoonXYZ
from .weebcentral import WeebCentral


def _default_sources() -> list:
    return [
        Armageddon,
        Atsumaru,
        DivaScans,
        ErisScans,
        FireScans,
        GalaxyDegenScans,
        Manga18fx,
        MangaDex,
        Mangadotnet,
        NyxScans,
        PhiliaScans,
        TempleScan,
        ToonGod,
        Toonily,
        WebtoonXYZ,
        WeebCentral,
    ]
