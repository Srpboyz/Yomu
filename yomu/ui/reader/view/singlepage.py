from __future__ import annotations

from enum import IntEnum
from typing import Callable, override, TYPE_CHECKING

from PyQt6.QtCore import QEvent, QPoint, QRect, QSize
from PyQt6.QtWidgets import QMenu, QHBoxLayout, QStackedLayout, QWidget

from yomu.core import utils as core_utils
from yomu.ui.reader.page import PageView

from .base import BaseView

if TYPE_CHECKING:
    from yomu.ui.reader import Reader


class PageWidget(QWidget):
    def __init__(self, parent: SinglePageView, page_view: PageView) -> None:
        super().__init__(parent)
        self.page_view = page_view

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_view)
        self.setLayout(layout)

    @property
    def page_status(self) -> PageView.Status:
        return self.page_view.status

    def image_size(self) -> QSize:
        return self.page_view.pixmap().size()


class StackLayout(QStackedLayout):
    class FitDirection(IntEnum):
        Height, Width = range(2)

    def __init__(self, view: SinglePageView) -> None:
        super().__init__(view)
        self.reader = view.reader
        self.direction = StackLayout.FitDirection.Height

        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    currentWidget: Callable[[], PageWidget | None]

    def page_widget_at(self, index: int) -> PageWidget | None:
        if (item := self.itemAt(index)) is not None:
            return item.widget()
        return None

    def fit_to_width(self, image_size: QSize) -> tuple[int, int]:
        reader_size = self.reader.size()

        width = reader_size.width()
        height = round(width * image_size.height() / image_size.width())

        return width, height

    def fit_to_height(self, image_size: QSize) -> tuple[int, int]:
        reader_size = self.reader.size()

        width = round(reader_size.height() * (image_size.width() / image_size.height()))
        height = reader_size.height()

        return width, height

    @override
    def setGeometry(self, rect: QRect) -> None:
        current_widget = self.currentWidget()
        if current_widget is not None:
            if current_widget.page_status == PageView.Status.LOADED:
                image_size = current_widget.image_size()
                width, height = (
                    self.fit_to_width(image_size)
                    if self.direction == StackLayout.FitDirection.Width
                    else self.fit_to_height(image_size)
                )
                rect = QRect(rect.x(), rect.y(), width, height)
            else:
                rect = QRect(QPoint(0, 0), self.reader.size())

        super().setGeometry(rect)


class SinglePageView(BaseView):
    name = "Single Page"

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader)

        layout = StackLayout(self)
        layout.currentChanged.connect(self._current_changed)
        self.setLayout(layout)

        self.reader.resized.connect(self._reader_resized)

        self.addAction("Change Fit Direction").triggered.connect(self.change_direction)
        self.window().app.keybinds_changed.connect(self.set_keybinds)
        self.set_keybinds(core_utils.get_keybinds())

    layout: Callable[[], StackLayout]

    def eventFilter(self, a0: QWidget, a1: QEvent) -> bool:
        if (
            a0 == self.layout().page_widget_at(self.page)
            and a1.type() == QEvent.Type.Resize
        ):
            self.setFixedSize(a1.size())
        return super().eventFilter(a0, a1)

    def _reader_resized(self, _) -> None:
        self.layout().update()

    def _current_changed(self, page: int):
        self.current_index = page
        if self.page_count < 1:
            return

        page_widget = self.layout().page_widget_at(self.page)
        if page_widget is not None:
            self.setFixedSize(page_widget.size())

        if page == self.page_count - 1:
            self.reader.mark_chapter_as_read()

    def _page_changed(self, page: int) -> None:
        if page < 0:
            return

        layout = self.layout()
        layout.setCurrentIndex(page)
        self.reader.verticalScrollBar().setValue(0)

        page_widget = layout.page_widget_at(self.page)
        if page_widget is not None:
            self.setFixedSize(page_widget.size())

    def page_at(self, pos: QPoint) -> PageView | None:
        if (widget := self.childAt(pos)) is not None:
            if isinstance(widget, PageWidget):
                return widget.page_view
            return widget
        if (widget := self.layout().currentWidget()) is not None:
            return widget.page_view
        return None

    def set_page_views(self, views: list[PageView]) -> None:
        layout = self.layout()
        layout.blockSignals(True)
        for view in views:
            page_widget = PageWidget(self, view)
            page_widget.installEventFilter(self)
            layout.addWidget(page_widget)
        layout.blockSignals(False)

    def take_page_views(self) -> list[PageView]:
        layout = self.layout()
        layout.blockSignals(True)
        views = [layout.takeAt(0).widget().page_view for _ in range(layout.count())]
        layout.blockSignals(False)
        return views

    def context_menu(self) -> QMenu:
        menu = QMenu()
        menu.addAction("Change Fit Direction").triggered.connect(self.change_direction)
        return menu

    def change_direction(self):
        layout = self.layout()
        layout.direction = (
            StackLayout.FitDirection.Height
            if layout.direction == StackLayout.FitDirection.Width
            else StackLayout.FitDirection.Width
        )
        layout.update()

    def set_keybinds(self, keybinds):
        keybindingData = keybinds.get("Change Fit Direction", {"keybinds": []})
        self.actions()[0].setShortcuts(
            keybindingData["keybinds"] if keybindingData is not None else []
        )

    def zoom_out(self) -> None: ...

    def zoom_in(self) -> None: ...

    def clear(self) -> None:
        layout = self.layout()
        layout.blockSignals(True)
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
        layout.blockSignals(False)
        self._current_index = -1
