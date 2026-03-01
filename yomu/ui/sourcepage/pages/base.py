import os
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from yomu.core import utils
from yomu.source import Manga as SourceManga
from yomu.ui.components.mangalist import MangaList

if TYPE_CHECKING:
    from yomu.core.app import YomuApp
    from yomu.source import Source
    from yomu.ui import ReaderWindow
    from yomu.ui.sourcepage import SourcePage


class BasePage(QWidget):
    page_loaded = pyqtSignal()
    _cancel_request = pyqtSignal()

    def __init__(self, parent: SourcePage, app: YomuApp) -> None:
        super().__init__(parent)
        self.sql = app.sql
        self._manga_list = MangaList(self, app)

        self._loading_icon = QLabel(self)
        self._loading_icon.setMovie(
            QMovie(os.path.join(utils.resource_path(), "icons", "loading.gif"))
        )
        self._loading_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_icon.hide()

        layout = QVBoxLayout(self)
        layout.addWidget(self._loading_icon)
        layout.addWidget(self._manga_list)
        self.setLayout(layout)

    def parent(self) -> SourcePage:
        return super().parent().parent()

    window: Callable[[], ReaderWindow]
    layout: Callable[[], QVBoxLayout]

    @property
    def source(self) -> Source:
        return self.parent().source

    @property
    def manga_list(self) -> MangaList:
        return self._manga_list

    def is_current_widget(self) -> bool:
        return self.parent().is_current_widget and self.parent().currentWidget() == self

    def insert_mangas(self, sourceMangas: list[SourceManga]) -> None:
        mangas = self.sql.add_and_get_mangas(self.parent().source, sourceMangas)
        for manga in mangas:
            self._manga_list.add_manga(manga).fetch_thumbnail()

    def set_current_widget(self) -> None: ...

    def clear_widget(self) -> None:
        self._manga_list.clear()
