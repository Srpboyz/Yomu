from .atsumaru import Atsumaru
from .erisscans import ErisScans
from .galaxydegenscans import GalaxyDegenScans
from .lunatoons import LunaToons
from .manga18fx import Manga18fx
from .mangadex import MangaDex
from .mangadotnet import Mangadotnet
from .mangafire import MangaFire
from .nyxscans import NyxScans
from .philiascans import PhiliaScans
from .silentquill import SilentQuill
from .templescan import TempleScan
from .toongod import ToonGod
from .toonily import Toonily
from .weebcentral import WeebCentral


def _default_sources() -> list:
    return [
        Atsumaru,
        ErisScans,
        GalaxyDegenScans,
        LunaToons,
        Manga18fx,
        MangaDex,
        Mangadotnet,
        MangaFire,
        NyxScans,
        PhiliaScans,
        SilentQuill,
        TempleScan,
        ToonGod,
        Toonily,
        WeebCentral,
    ]
