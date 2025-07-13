from __future__ import annotations

from functools import wraps
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QObject

from yomu.ui import ReaderWindow

if TYPE_CHECKING:
    from yomu.core.app import YomuApp


class YomuExtension(QObject):
    settings_requested = pyqtSignal(ReaderWindow)

    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self.app = app

    def unload(self) -> None: ...


def pyqtSlot(func: Callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception:
            ...

    return wrapper
