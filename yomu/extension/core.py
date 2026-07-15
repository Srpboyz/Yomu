from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget

from yomu.core.utils import pyqtSlot


if TYPE_CHECKING:
    from yomu.core.app import YomuApp


class YomuExtension(QObject):
    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self.app = app

    def settings_widget(self) -> QWidget | None: ...

    def unload(self) -> None: ...
