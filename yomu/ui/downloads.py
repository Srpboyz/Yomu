from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu

from yomu.core.models import Chapter
from yomu.ui.components.cardlist import BaseCardItem, CardList
from .stack import StackWidgetMixin

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


class DownloadItem(BaseCardItem):
    def __init__(self, parent: Downloads, chapter: Chapter) -> None:
        super().__init__(parent)
        self.installEventFilter(parent)
        self.setFixedHeight(60)
        self.chapter = chapter

        self.title_widget = QLabel(f"{chapter.manga.title} - {chapter.title}", self)
        self.title_widget.setObjectName("Title")

        self.pages_widget = QLabel(self)
        self.pages_widget.setObjectName("Pages")
        self.pages_widget.setText("(0/0)")

        self.progress_bar = QFrame(self)
        self.progress_bar.setFixedSize(3, 2)
        self.progress_bar.move(2, self.height() - 2)
        self.progress_bar.hide()

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.title_widget)
        layout.addWidget(self.pages_widget)
        self.setLayout(layout)

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        super().resizeEvent(a0)

        current_size = round(
            self.progress_bar.width() * a0.size().width() / a0.oldSize().width()
        )
        self.progress_bar.setFixedWidth(max(current_size, 3))

    def download_update(self, page: int, total: int) -> None:
        self.pages_widget.setText(f"({page + 1}/{total})")
        self.progress_bar.setFixedWidth(round(self.width() * (page + 1) / total))
        self.progress_bar.show()


class Downloads(CardList, StackWidgetMixin):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self.downloader = window.app.downloader

        self.downloader.download_started.connect(self.add_chapter)
        self.downloader.download_update.connect(self.update_chapter)
        self.downloader.download_finished.connect(self.remove_chapter)
        self.downloader.download_failed.connect(self.remove_chapter)

        self.layout().setSpacing(10)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if isinstance(a0, DownloadItem) and a1.type() == QEvent.Type.ContextMenu:
            menu = QMenu(self)
            menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            action = menu.addAction("Cancel")
            if menu.exec(a1.globalPos()) == action:
                self.downloader.cancel_chapter(a0.chapter)
            return True

        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def add_chapter(self, chapter: Chapter) -> None:
        self.add_card(DownloadItem(self, chapter))

    def update_chapter(self, chapter: Chapter, page: int, total: int) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            widget: DownloadItem = layout.itemAt(i).widget()
            if widget.chapter == chapter:
                return widget.download_update(page, total)

    def remove_chapter(self, chapter: Chapter, _=...) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            widget: DownloadItem = layout.widgetAt(i)
            if widget.chapter == chapter:
                return widget.deleteLater()

    def set_current_widget(self) -> None:
        window = self.window()
        window.setWindowTitle("Downloads")
        window.titlebar.refresh_button.hide()

    def clear_widget(self) -> None:
        self.window().titlebar.refresh_button.show()
