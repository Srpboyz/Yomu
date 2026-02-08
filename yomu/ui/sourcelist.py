from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QMouseEvent

from yomu.core import utils
from yomu.core.downloader import Downloader
from yomu.source import Source
from .components.cardlist import CardIconItem, CardList
from .stack import StackWidgetMixin

if TYPE_CHECKING:
    from .window import ReaderWindow


class SourceItem(CardIconItem):
    def __init__(self, parent: SourceList, source: Source) -> None:
        icon_path = Downloader.resolve_path(source)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(utils.icon_path(), "webview.svg")

        super().__init__(parent, source.name, icon_path)
        self.source = source


class SourceList(CardList, StackWidgetMixin):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        for source in sorted(
            window.app.source_manager.sources, key=lambda source: source.name
        ):
            self.add_card(SourceItem(self, source))

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if (
            isinstance(a0, SourceItem)
            and a1.type() == QEvent.Type.MouseButtonRelease
            and a1.button() == Qt.MouseButton.LeftButton
        ):
            self.window().sourcepage.source = a0.source
        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def set_current_widget(self) -> None:
        window = self.window()
        window.titlebar.refresh_button.hide()

        if window.network.is_online:
            return window.setWindowTitle("Source List")

        window.display_message(
            "You are currently offline. Please connect to the internet to utilize sources."
        )
        window.current_widget = window.library

    def clear_widget(self) -> None:
        self.window().titlebar.refresh_button.show()
