from .atsumaru import Atsumaru
from .erisscans import ErisScans
from .galaxydegenscans import GalaxyDegenScans
from .lunatoons import LunaToons
from .manga18fx import Manga18fx
from .mangadex import MangaDex
from .mangadot import MangaDot
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
        MangaDot,
        MangaFire,
        NyxScans,
        PhiliaScans,
        SilentQuill,
        TempleScan,
        ToonGod,
        Toonily,
        WeebCentral,
    ]
