from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QObject, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QMenu, QScrollArea, QScrollBar, QWidget

from yomu.core import utils

from .find import Find
from .layout import FlowLayout
from .mangaview import MangaView

if TYPE_CHECKING:
    from yomu.core.app import YomuApp
    from yomu.core.models import Manga
    from yomu.ui import ReaderWindow


class MangaList(QScrollArea):
    view_added = pyqtSignal(MangaView)
    view_removed = pyqtSignal((int, MangaView))

    def __init__(self, parent: QWidget, app: YomuApp) -> None:
        super().__init__(parent)
        self.app = app

        body = QWidget(self)
        body.setLayout(FlowLayout(body))
        body.setMouseTracking(True)
        self.setContentsMargins(0, 0, 0, 0)
        self.setWidgetResizable(True)
        self.setWidget(body)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.addAction("Find").triggered.connect(self.find_manga)
        app.keybinds_changed.connect(self._set_keybinds)
        self._set_keybinds(utils.get_keybinds())
        self.setMouseTracking(True)

    window: Callable[[], ReaderWindow]
    verticalScrollBar: Callable[[], QScrollBar]
    horizontalScrollBar: Callable[[], QScrollBar]
    widget: Callable[[], QWidget]

    def layout(self) -> FlowLayout:
        return self.widget().layout()

    @property
    def count(self) -> int:
        return self.widget().layout().count()

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if isinstance(a0, MangaView):
            if (
                a1.type() == QEvent.Type.MouseButtonRelease
                and a1.button() == Qt.MouseButton.LeftButton
            ):
                self.window().mangacard.manga = a0.manga
                return True

            if a1.type() == QEvent.Type.ContextMenu:
                menu = QMenu(self)
                menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

                text = "Remove From Library" if a0.manga.library else "Add To Library"
                library = menu.addAction(text)
                copy = menu.addAction("Copy Title")

                action = menu.exec(a1.globalPos())
                if action == library:
                    self.app.sql.set_library(a0.manga, library=not a0.manga.library)
                elif action == copy:
                    self.app.clipboard().setText(a0.manga.title)
                return True

        return super().eventFilter(a0, a1)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        for i in range(self.count):
            self.manga_view_at(i).title_widget.setSelection(0, 0)
        return super().mousePressEvent(event)

    def _set_keybinds(self, keybinds: dict[str, utils.Keybind]) -> None:
        for action in self.actions():
            data = keybinds.get(action.text(), {"keybinds": []})
            action.setShortcuts(data["keybinds"] if data is not None else [])

    def item_at(self, index: int):
        return self.layout().itemAt(index)

    def take_at(self, index: int):
        return self.layout().takeAt(index)

    def manga_view_at(self, index: int) -> MangaView | None:
        if (item := self.item_at(index)) is not None:
            return item.widget()

    def find_manga(self) -> None:
        Find(self).exec()

    def add_manga(self, manga: Manga) -> MangaView:
        view = MangaView(self, manga)
        self.app.manga_library_status_changed.connect(view.library_status_changed)
        self.app.manga_thumbnail_changed.connect(view.thumbnail_changed)
        self.app.manga_details_updated.connect(view.detail_changed)
        view.installEventFilter(self)
        self.layout().addWidget(view)
        self.view_added.emit(view)
        return view

    def insert_manga(self, index: int, manga: Manga) -> MangaView:
        view = MangaView(self, manga)
        self.app.manga_library_status_changed.connect(view.library_status_changed)
        self.app.manga_thumbnail_changed.connect(view.thumbnail_changed)
        self.app.manga_details_updated.connect(view.detail_changed)
        view.installEventFilter(self)
        self.layout().insertWidget(index, view)
        return view

    def remove_manga(self, manga: Manga) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            view = self.manga_view_at(i)
            if view is not None and view.manga == manga:
                layout.takeAt(i)
                self.view_removed.emit(i, view)
                return view.deleteLater()

    def clear(self) -> None:
        self.layout().clear()
        self.verticalScrollBar().setMaximum(0)
