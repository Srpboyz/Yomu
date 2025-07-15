from __future__ import annotations

import os
from collections.abc import Sequence
from copy import copy
from enum import IntEnum
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QObject, QRect, QSize, Qt
from PyQt6.QtGui import QMouseEvent, QResizeEvent, QWheelEvent
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QMenu, QScrollArea, QScrollBar

from yomu.core import utils as core_utils
from yomu.core.models import Chapter, Page
from yomu.core.network import Response
from yomu.source import Page as SourcePage
from yomu.ui.stack import StackWidgetMixin

from .page import PageView
from .overlay import Overlay
from .overlay.bar import NavigationBar, PageBar, BaseBar
from .view import SinglePageView, WebtoonView

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow

    from .view.base import BaseView


class Reader(QScrollArea, StackWidgetMixin):
    class Status(IntEnum):
        NULL, LOADING, FAILED = range(3)

    views: dict[str, BaseView] = {
        SinglePageView.name: SinglePageView,
        WebtoonView.name: WebtoonView,
    }

    chapter_changed = pyqtSignal(Chapter)
    view_changed = pyqtSignal(str)
    status_changed = pyqtSignal(Status)
    resized = pyqtSignal(QSize)
    _cancel_request = pyqtSignal()

    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self.setObjectName("Reader")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizeAdjustPolicy(Reader.SizeAdjustPolicy.AdjustToContents)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus | Qt.FocusPolicy.WheelFocus)
        self._status = Reader.Status.NULL

        self.sql = window.app.sql

        self.current_view: BaseView = WebtoonView(self)
        self.overlay = Overlay(self.viewport())

        self.info_bar = NavigationBar(self)
        self.page_bar = PageBar(self)

        self.overlay.add_overlay(self.info_bar)
        self.overlay.add_overlay(self.page_bar)

        self._chapters: list[Chapter] = [
            Chapter(
                id=-1,
                number=-1,
                manga=None,
                title="Reader",
                url="/reader",
                uploaded=0,
                downloaded=False,
                read=False,
            )
        ]
        self._current_chapter_index = 0

        self.setWidgetResizable(True)
        self.setWidget(self.current_view)

        self.verticalScrollBar().valueChanged.connect(self._value_changed)
        self.horizontalScrollBar().rangeChanged.connect(self._range_changed)
        self.current_view.page_changed.connect(self.page_bar.set_value)
        self.page_bar.value_changed.connect(self._scroll_to)

        self.addAction("Change Reader Mode").triggered.connect(self.change_view)
        self.addAction("Previous Page").triggered.connect(self.previous_page)
        self.addAction("Next Page").triggered.connect(self.next_page)
        self.addAction("Previous Chapter").triggered.connect(self.previous_chapter)
        self.addAction("Next Chapter").triggered.connect(self.next_chapter)
        self.addAction("Zoom Out").triggered.connect(self.zoom_out)
        self.addAction("Zoom In").triggered.connect(self.zoom_in)

        window.app.keybinds_changed.connect(self._set_keybinds)
        window.titlebar.refresh_button.released.connect(self._refresh)
        self._set_keybinds(core_utils.get_keybinds())

    window: Callable[[], ReaderWindow]
    verticalScrollBar: Callable[[], QScrollBar]
    horizontalScrollBar: Callable[[], QScrollBar]

    @property
    def chapter(self) -> Chapter:
        return self._chapters[self._current_chapter_index]

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, status: Status) -> None:
        self._status = status
        self.status_changed.emit(status)

    @classmethod
    def add_view(cls, view: type[BaseView]) -> bool:
        name = view.name
        if name in cls.views or not issubclass(view, BaseView):
            return False

        cls.views[name] = view
        return True

    @classmethod
    def remove_view(cls, name: str) -> bool:
        cls.views.pop(name, None)

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if isinstance(a0, BaseBar) and a1.type() == QEvent.Type.Wheel and a0.isHidden():
            self.window().app.postEvent(self.viewport(), a1.clone())
        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def wheelEvent(self, a0: QWheelEvent) -> None:
        if a0.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.current_view.zoom_in() if a0.angleDelta().y() > 0 else self.current_view.zoom_out()
            return a0.ignore()
        return super().wheelEvent(a0)

    def viewportEvent(self, a0: QEvent) -> bool:
        ret = super().viewportEvent(a0)
        if (
            a0.type() == QEvent.Type.MouseButtonRelease
            and a0.button() == Qt.MouseButton.LeftButton
        ):
            self.overlay.show() if self.overlay.isHidden() else self.overlay.hide()
        return ret

    def contextMenuEvent(self, a0):
        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.addAction("Change View").triggered.connect(self.change_view)

        pos = (
            self.current_view.visibleRegion().boundingRect().topLeft()
            + self.cursor().pos()
        )
        page = self.current_view.page_at(pos)
        if page is not None:
            if page.status == PageView.Status.FAILED:
                menu.addAction("Reload").triggered.connect(page.fetch_page)
            elif page.status == PageView.Status.LOADED:
                menu.addAction("Copy Image").triggered.connect(
                    page.copy_image_to_clipboard
                )

        if (viewMenu := self.current_view.context_menu()) is not None:
            menu.addSeparator()
            for action in viewMenu.actions():
                menu.addAction(action)
                if menu.parent() == viewMenu:
                    action.setParent(menu)

        if self.current_view.supports_zoom:
            menu.addSeparator()
            menu.addAction(self.tr("Zoom Out")).triggered.connect(self.zoom_out)
            menu.addAction(self.tr("Zoom In")).triggered.connect(self.zoom_in)

        menu.addSeparator()
        menu.addAction(self.tr("Previous Page")).triggered.connect(self.previous_page)
        menu.addAction(self.tr("Next Page")).triggered.connect(self.next_page)

        menu.addSeparator()
        menu.addAction(self.tr("Previous Chapter")).triggered.connect(
            self.previous_chapter
        )
        menu.addAction(self.tr("Next Chapter")).triggered.connect(self.next_chapter)

        menu.exec(a0.globalPos())

    def resizeEvent(self, a0: QResizeEvent) -> None:
        super().resizeEvent(a0)
        self.resized.emit(a0.size())

    def _range_changed(self, min: int, max: int) -> None:
        self.horizontalScrollBar().setValue(int((min + max) / 2))

    def _value_changed(self, _) -> None:
        if self.status != Reader.Status.LOADING:
            self.overlay.hide()

    def _scroll_to(self, page: int) -> None:
        scrollbar = self.verticalScrollBar()
        scrollbar.valueChanged.disconnect(self._value_changed)
        self.current_view.current_index = page
        scrollbar.valueChanged.connect(self._value_changed)

    def _fetch_pages(self) -> None:
        if not self.chapter.downloaded:
            request = self.chapter.get_pages()
            request.setPriority(QNetworkRequest.Priority.HighPriority)
            response = self.window().network.handle_request(request)
            self._cancel_request.connect(response.abort)
            return response.finished.connect(self._pages_fetched)

        path = self.window().app.downloader.resolve_path(self.chapter)
        pages = [
            PageView(
                self.current_view,
                Page(
                    i,
                    chapter=self.chapter,
                    url=os.path.join(path, f"{i}.png"),
                    downloaded=True,
                ),
            )
            for i in range(len(os.listdir(path)))
        ]

        self._set_pages(pages)

    def _pages_fetched(self) -> None:
        response: Response = self.sender()
        window = self.window()

        error = response.error()
        if error == Response.Error.OperationCanceledError:
            return

        if error != Response.Error.NoError:
            self.chapter.source.chapter_pages_request_error(response)
            return self.display_message("Error fetching chapter")

        try:
            pages = self.chapter.source.parse_chapter_pages(response)
        except Exception as e:
            window.logger.error(
                f"Failed to parse chapter for {self.chapter.source.name}", exc_info=e
            )
            return self.display_message("Error fetching chapter")

        if not isinstance(pages, Sequence) or not all(
            isinstance(page, SourcePage) for page in pages
        ):
            return self.display_message("Error fetching chapter")

        if not pages:
            return self.display_message("No pages were received")

        pages = [
            PageView(self.current_view, Page.from_source_page(self.chapter, page))
            for page in sorted(pages, key=lambda page: page.number)
        ]
        self._set_pages(pages)

    def _set_pages(self, pages: list[PageView]) -> None:
        self.current_view.set_page_views(pages)
        self.page_bar.set_total_pages(self.current_view.page_count - 1)
        self.current_view.current_index = 0
        self.status = Reader.Status.NULL

    def _set_keybinds(self, keybinds: dict[str, core_utils.Keybind]) -> None:
        for action in self.actions():
            data = keybinds.get(action.text(), {"keybinds": []})
            action.setShortcuts(data["keybinds"] if data is not None else [])

    def _refresh(self) -> None:
        if self.window().current_widget != self:
            return

        self._cancel_request.emit()

        self.current_view.clear()
        self.page_bar.set_total_pages(0)

        self._fetch_pages()
        self.verticalScrollBar().setValue(0)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self.overlay.setGeometry(rect)

    def setWidget(self, w: BaseView) -> None:
        super().setWidget(w)
        self.overlay.raise_()

    def display_message(self, message: str) -> None:
        window = self.window()
        window.display_message(message)
        self.status = Reader.Status.FAILED
        window.go_to_previous_page()

    def set_view(self, name: str) -> None:
        all_views = Reader.views
        if name not in all_views or name == self.current_view.name:
            return

        self.current_view = all_views[name](self)
        self.current_view.page_changed.connect(self.page_bar.set_value)

        original_view: BaseView = self.takeWidget()

        current_index = original_view.current_index
        pages = original_view.take_page_views()

        self.current_view.set_page_views(pages)
        self.setWidget(self.current_view)

        self.current_view.current_index = current_index

        self.view_changed.emit(name)
        original_view.deleteLater()

    def change_view(self) -> None:
        all_views = Reader.views

        try:
            index = tuple(all_views.values()).index(type(self.current_view))
        except ValueError:
            index = 0
        else:
            index = index + 1 if index < len(all_views) - 1 else 0

        self.set_view(tuple(all_views.keys())[index])

    def _set_chapter(self, chapter: Chapter) -> None:
        if self.status == Reader.Status.LOADING:
            self._cancel_request.emit()

        self.status = Reader.Status.LOADING
        self.info_bar.set_title(chapter.title)
        self.page_bar.reset()

        self.chapter_changed.emit(chapter)

        self.current_view.clear()
        self._fetch_pages()

    def set_chapters(self, chapters: list[Chapter], index: int) -> None:
        current_chapter = self.chapter

        self._chapters = copy(chapters)
        self._current_chapter_index = index
        self.window().current_widget = self

        chapter = chapters[index]
        if current_chapter == chapter:
            if self.status != Reader.Status.FAILED:
                return

        self._set_chapter(chapters[index])

    def previous_page(self) -> None:
        if self.current_view.page > 0:
            self.page_bar.previous_page()

    def next_page(self) -> None:
        if self.current_view.page < self.current_view.page_count - 1:
            self.page_bar.next_page()

    def previous_chapter(self) -> None:
        if self._current_chapter_index > 0:
            self._current_chapter_index -= 1
            self._set_chapter(self._chapters[self._current_chapter_index])

    def next_chapter(self) -> None:
        self.mark_chapter_as_read()
        if self._current_chapter_index < len(self._chapters) - 1:
            self._current_chapter_index += 1
            self._set_chapter(self._chapters[self._current_chapter_index])

    def zoom_out(self) -> None:
        self.current_view.zoom_out()

    def zoom_in(self) -> None:
        self.current_view.zoom_in()

    def mark_chapter_as_read(self) -> None:
        if not self.chapter.read:
            self.sql.mark_chapters_read_status([self.chapter], read=True)

    def set_current_widget(self) -> None:
        self.window().setWindowTitle(self.chapter.manga.title)
