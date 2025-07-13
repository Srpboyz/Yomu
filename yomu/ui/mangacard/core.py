from __future__ import annotations

import os
from copy import copy
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QSize, Qt
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
)

from yomu.core.network import Request
from yomu.core.models import Chapter, Manga
from yomu.core import utils
from yomu.ui.components.thumbnail import ThumbnailWidget
from yomu.ui.stack import StackWidgetMixin

from .chapterlist import ChapterList

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


MARKDOWN = """# {title}

Description: {description}

Author: {author}

Artist: {artist}

Source: {source}"""


class MangaCard(QFrame, StackWidgetMixin):
    manga_changed = pyqtSignal(Manga)

    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self._manga: Manga = None
        self.setMaximumWidth(750)
        self.app = window.app

        self.details_widget = QTextBrowser(self)
        self.details_widget.setReadOnly(True)
        self.details_widget.setOpenExternalLinks(True)

        self.thumbnail_widget = ThumbnailWidget(self)
        self.thumbnail_widget.setObjectName("Thumbnail")
        self.thumbnail_widget.setFixedSize(QSize(195, 279) * 1.2)
        self.thumbnail_widget.priority = Request.Priority.HighPriority

        info_layout = QHBoxLayout()
        info_layout.setSpacing(10)
        info_layout.addWidget(
            self.thumbnail_widget, alignment=Qt.AlignmentFlag.AlignCenter
        )
        info_layout.addWidget(self.details_widget)

        icon_path = os.path.join(utils.resource_path(), "icons")

        label = QLabel("Chapter List", self)
        label.setObjectName("ChapterList")

        self.chapter_list = ChapterList(self, window.app)
        self.chapter_list.item_clicked.connect(self._set_chapter)

        flip_button = QToolButton(self)
        flip_button.setObjectName("Flip")
        flip_button.setIcon(QIcon(os.path.join(icon_path, "flip.png")))
        flip_button.setCursor(Qt.CursorShape.PointingHandCursor)
        flip_button.clicked.connect(self.chapter_list.flip_direction)

        chapter_info_layout = QHBoxLayout()
        chapter_info_layout.addWidget(label)
        chapter_info_layout.addWidget(flip_button, stretch=2)

        layout = QVBoxLayout(self)
        layout.addLayout(info_layout)
        layout.addLayout(chapter_info_layout)
        layout.addWidget(self.chapter_list)
        self.setLayout(layout)

        self._plus_button = QToolButton(self)
        self._plus_button.setToolTip("Add To Library")
        path = os.path.join(icon_path, "plus.svg")
        self._plus_button.setIcon(QIcon(path))
        self._plus_button.pressed.connect(self.add_to_library)
        self._plus_button.hide()

        self._minus_button = QToolButton(self)
        self._minus_button.setToolTip("Remove From Library")
        path = os.path.join(icon_path, "minus.svg")
        self._minus_button.setIcon(QIcon(path))
        self._minus_button.pressed.connect(self.remove_from_library)
        self._minus_button.hide()

        window.titlebar.refresh_button.pressed.connect(self._refresh_button_pressed)
        window.titlebar.insert_button(self._plus_button, index=5)
        window.titlebar.insert_button(self._minus_button, index=6)

        self.app.manga_details_updated.connect(self._manga_details_updated)
        self.app.manga_thumbnail_changed.connect(self._manga_thumbnail_updated)
        self.app.manga_library_status_changed.connect(self._library_status_changed)
        self.app.chapter_list_updated.connect(self._chapter_list_updated)
        self.app.updater.chapter_update_finished.connect(self._chapter_update_finished)

        self.chapter_list._mark_as_read_request.connect(self._mark_chapters_as_read)
        self.chapter_list._download_chapters_request.connect(self._download_chapters)

    window: Callable[[], ReaderWindow]

    @property
    def manga(self) -> Manga:
        return self._manga

    @manga.setter
    def manga(self, manga: Manga) -> None:
        if self.manga != manga:
            self._manga = copy(manga)

            self.refresh_manga_details()

            self.chapter_list.clear()
            self.manga_changed.emit(manga)

            if not manga.initialized:
                self.update_manga()
            else:
                self._load_sql_chapters()

            self.thumbnail_widget.clear()
            self.thumbnail_widget.fetch_thumbnail()

        self.window().current_widget = self
        self.setFocusProxy(self.chapter_list)

    def _refresh_button_pressed(self) -> None:
        if self.window().current_widget == self:
            self.update_manga()

    def _chapter_update_finished(self, manga: Manga, success: bool) -> None:
        if manga == self.manga and not success:
            self._load_sql_chapters()

    def _manga_details_updated(self, manga: Manga) -> None:
        if self.manga == manga:
            self._manga = copy(manga)
            self.refresh_manga_details()

    def _manga_thumbnail_updated(self, manga: Manga) -> None:
        if self.manga == manga:
            self._manga = copy(manga)
            self.thumbnail_widget.fetch_thumbnail()

    def _chapter_list_updated(self, manga: Manga) -> None:
        if self.manga == manga:
            self._load_sql_chapters()

    def _library_status_changed(self, manga: Manga) -> None:
        if self.manga != manga:
            return None

        self._manga.library = manga.library
        if self.window().current_widget == self:
            if manga.library:
                self._plus_button.hide()
                self._minus_button.show()
            else:
                self._plus_button.show()
                self._minus_button.hide()

    def _load_sql_chapters(self) -> None:
        chapters = self.window().app.sql.get_chapters(self.manga)
        self.chapter_list.display_chapters(chapters)

    def _mark_chapters_as_read(self, chapters: list[Chapter], read: bool) -> None:
        self.app.sql.mark_chapters_read_status(chapters, read=read)

    def _download_chapters(self, chapters: list[Chapter], download: bool) -> None:
        func = (
            self.app.downloader.download_chapter
            if download
            else self.app.downloader.delete_chapter
        )

        for chapter in chapters:
            func(chapter)

    def _set_chapter(self, index: int) -> None:
        chapters = self.chapter_list.chapters
        chapter = chapters[index]

        window = self.window()
        if window.network.is_online or chapter.downloaded:
            return window.reader.set_chapters(chapters, index)

        window.display_message(
            "This chapter isn't downloaded. Please connect to the internet to view/download the chapter."
        )

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def update_manga(self) -> None:
        window = self.window()
        if not window.network.is_online:
            return

        if not window.app.updater.update_manga_details(
            self.manga, priority=Request.Priority.HighPriority
        ):
            window.display_message("Failed to update manga info")

        if not window.app.updater.update_manga_chapters(
            self.manga, priority=Request.Priority.HighPriority
        ):
            window.display_message("Failed to update chapters")
        else:
            self.chapter_list.clear()

    def refresh_manga_details(self) -> None:
        details = {
            "title": self.manga.title,
            "description": self.manga.description or "N/A",
            "author": self.manga.author or "N/A",
            "artist": self.manga.artist or "N/A",
            "source": self.manga.source.name,
        }

        self.details_widget.setMarkdown(MARKDOWN.format(**details))

    def add_to_library(self):
        self.window().app.sql.set_library(self.manga, library=True)

    def remove_from_library(self):
        self.window().app.sql.set_library(self.manga, library=False)

    def set_current_widget(self) -> None:
        self.window().setWindowTitle(self.manga.title)
        if self.manga.library:
            self._minus_button.show()
        else:
            self._plus_button.show()

    def clear_widget(self) -> None:
        self._plus_button.hide()
        self._minus_button.hide()
