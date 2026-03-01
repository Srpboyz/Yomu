import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent, QMovie, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from yomu.ui.components.cardlist import CardList, BaseCardItem

from yomu.core import utils
from yomu.core.models import Chapter

if TYPE_CHECKING:
    from yomu.core.app import YomuApp


class ChapterListItem(BaseCardItem):
    def __init__(self, parent: ChapterList, chapter: Chapter) -> None:
        super().__init__(parent)
        self.installEventFilter(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chapter = chapter
        self.selected = False

        self.setProperty("selected", False)
        self.setProperty("read", chapter.read)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.title_widget = QLabel(chapter.title, self)
        self.title_widget.setObjectName("Title")

        self.timestamp_widget = QLabel(chapter.uploaded.strftime("%m/%d/%y"), self)
        self.timestamp_widget.setObjectName("Timestamp")

        self.downloaded_icon = QLabel(self)
        self.downloaded_icon.setPixmap(
            QPixmap(os.path.join(utils.resource_path(), "icons", "check.svg")).scaled(
                20, 20, transformMode=Qt.TransformationMode.SmoothTransformation
            )
        )
        if not chapter.downloaded:
            self.downloaded_icon.hide()

        vLayout = QVBoxLayout()
        vLayout.addWidget(self.title_widget)
        vLayout.addWidget(self.timestamp_widget)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(vLayout)
        layout.addWidget(self.downloaded_icon, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.DynamicPropertyChange:
            style = self.style()
            for child in self.findChildren(QWidget):
                style.polish(child)
            style.polish(self)
        return super().event(e)

    def mark_as_read(self, read: bool) -> None:
        self.chapter.read = read
        self.setProperty("read", read)

    def mark_as_downloaded(self, downloaded: bool) -> None:
        self.chapter.downloaded = downloaded
        self.downloaded_icon.show() if downloaded else self.downloaded_icon.hide()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.setProperty("selected", selected)


class ChapterSelector(QObject):
    def __init__(self, chapter_list: ChapterList):
        super().__init__(chapter_list)
        self.chapter_list = chapter_list
        self.selected_chapters: set[ChapterListItem] = set()
        self.current_index = 0

    def eventFilter(self, a0: ChapterListItem, a1: QEvent):
        event_type = a1.type()
        if (
            event_type == QEvent.Type.MouseButtonRelease
            and a1.button() == Qt.MouseButton.LeftButton
        ):
            modifiers = a1.modifiers()
            if modifiers == Qt.KeyboardModifier.ControlModifier:
                self.handle_ctrl_select(a0)
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                self.handle_shift_select(a0)
            elif (
                modifiers
                == Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ShiftModifier
            ):
                self.handle_ctrl_shift_select()
        return False

    def handle_ctrl_select(self, item: ChapterListItem) -> None:
        self.select_chapter(item) if not item.selected else self.deselect_chapter(item)
        self.current_index = self.chapter_list.layout().indexOf(item)

    def handle_shift_select(self, item: ChapterListItem) -> None:
        layout = self.chapter_list.layout()
        index = layout.indexOf(item)

        iterator = (
            range(index, self.current_index + 1)
            if index < self.current_index
            else range(self.current_index, index + 1)
        )

        func = self.select_chapter if not item.selected else self.deselect_chapter

        for i in iterator:
            func(layout.itemAt(i).widget())

        self.current_index = index

    def handle_ctrl_shift_select(self) -> None:
        layout = self.chapter_list.layout()
        func = (
            self.select_chapter
            if len(self.selected_chapters) != layout.count() - 1
            else self.deselect_chapter
        )

        for i in range(1, layout.count()):
            func(layout.itemAt(i).widget())

        if not self.selected_chapters:
            self.current_index = 0
        else:
            self.current_index = layout.count() - 1

    def select_chapter(self, item: ChapterListItem) -> None:
        item.set_selected(True)
        self.selected_chapters.add(item)

    def deselect_chapter(self, item: ChapterListItem) -> None:
        item.set_selected(False)
        self.selected_chapters.discard(item)

    def clear_selection(self, unselect: bool = False) -> None:
        if unselect:
            for chapter in self.selected_chapters:
                chapter.set_selected(False)

        self.selected_chapters.clear()
        self.current_index = 0


class ChapterList(CardList[ChapterListItem]):
    items_changed = pyqtSignal()
    item_clicked = pyqtSignal(int)
    _mark_as_read_request = pyqtSignal((list, bool))
    _download_chapters_request = pyqtSignal((list, bool))

    def __init__(self, parent: QWidget, app: YomuApp) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setContentsMargins(0, 0, 0, 0)
        self._chapters = []

        self.sql = app.sql

        widget = self.widget()
        widget.setContentsMargins(0, 0, 0, 0)
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.chapter_selector = ChapterSelector(self)

        self.loading_icon = QLabel(self)
        self.loading_icon.setObjectName("Loading")
        self.loading_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        movie = QMovie(os.path.join(utils.resource_path(), "icons", "loading.gif"))
        self.loading_icon.setMovie(movie)
        movie.start()

        layout = self.layout()
        layout.addWidget(self.loading_icon)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        app.chapter_read_status_changed.connect(
            self._chapter_read_updated, Qt.ConnectionType.QueuedConnection
        )
        app.chapter_download_status_changed.connect(
            self._chapter_downloaded_updated, Qt.ConnectionType.QueuedConnection
        )

    @property
    def chapters(self) -> list[Chapter]:
        return self._chapters

    def eventFilter(self, a0: QWidget, a1: QEvent):
        if not isinstance(a0, ChapterListItem):
            return super().eventFilter(a0, a1)

        event_type = a1.type()
        if (
            event_type == QEvent.Type.MouseButtonRelease
            and a1.button() == Qt.MouseButton.LeftButton
            and a1.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            self.item_clicked.emit(self.layout().indexOf(a0) - 1)
        if event_type == QEvent.Type.ContextMenu:
            self._handle_context_menu(a0, a1)

        return super().eventFilter(a0, a1)

    def _handle_context_menu(
        self, item: ChapterListItem, event: QContextMenuEvent
    ) -> None:
        self.chapter_selector.select_chapter(item)
        chapter = item.chapter

        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        open_chapter = menu.addAction("Open Chapter")

        menu.addSeparator()

        mark_read = menu.addAction("Mark as Read")
        mark_read.setVisible(not chapter.read)

        mark_unread = menu.addAction("Mark as Unread")
        mark_unread.setVisible(chapter.read)

        download_ch = menu.addAction("Download")
        download_ch.setVisible(not chapter.downloaded)

        delete_ch = menu.addAction("Delete")
        delete_ch.setVisible(chapter.downloaded)

        selected_action = menu.exec(event.globalPos())

        if selected_action == open_chapter:
            self.item_clicked.emit(self.layout().indexOf(item) - 1)
        elif selected_action == mark_read:
            self._mark_as_read(True)
        elif selected_action == mark_unread:
            self._mark_as_read(False)
        elif selected_action == download_ch:
            self._download_chapters(True)
        elif selected_action == delete_ch:
            self._download_chapters(False)

        self.chapter_selector.clear_selection(unselect=True)

    def _mark_as_read(self, read: bool) -> None:
        self._mark_as_read_request.emit(
            sorted(
                filter(
                    lambda chapter: chapter.read != read,
                    (item.chapter for item in self.chapter_selector.selected_chapters),
                ),
                key=lambda chapter: chapter.number,
            ),
            read,
        )

    def _download_chapters(self, download: bool) -> None:
        self._download_chapters_request.emit(
            sorted(
                filter(
                    lambda chapter: chapter.downloaded != download,
                    (item.chapter for item in self.chapter_selector.selected_chapters),
                ),
                key=lambda chapter: chapter.number,
            ),
            download,
        )

    def _chapter_read_updated(self, chapter: Chapter):
        layout = self.layout()
        for i in range(1, layout.count()):
            chapter_item: ChapterListItem = layout.itemAt(i).widget()
            if chapter_item.chapter == chapter:
                chapter_item.mark_as_read(chapter.read)
                return

    def _chapter_downloaded_updated(self, chapter: Chapter):
        layout = self.layout()
        for i in range(1, layout.count()):
            chapter_item: ChapterListItem = layout.itemAt(i).widget()
            if chapter_item.chapter == chapter:
                chapter_item.mark_as_downloaded(chapter.downloaded)
                return

    def display_chapters(self, chapters: list[Chapter]) -> None:
        self.clear()

        chapters = sorted(chapters, key=lambda chapter: chapter.number)
        for chapter in chapters:
            item = ChapterListItem(self, chapter)
            item.installEventFilter(self.chapter_selector)
            self.add_card(item)

        self.loading_icon.hide()
        self.layout().setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chapters = chapters
        self.items_changed.emit()

    def flip_direction(self) -> None:
        self.layout().setDirection(
            QVBoxLayout.Direction.BottomToTop
            if self.layout().direction() == QVBoxLayout.Direction.TopToBottom
            else QVBoxLayout.Direction.TopToBottom
        )

    def clear(self) -> None:
        layout = self.layout()
        for _ in range(layout.count() - 1):
            layout.takeAt(1).widget().deleteLater()
        self.chapter_selector.clear_selection()

        layout.setDirection(QVBoxLayout.Direction.BottomToTop)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalScrollBar().setValue(0)
        self.loading_icon.show()
