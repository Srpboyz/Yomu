from __future__ import annotations

from copy import copy
import inspect
import os

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget

from yomu.core.models import Manga
from yomu.core import utils
from yomu.ui.components.thumbnail import ThumbnailWidget


class MangaView(QFrame):
    def __init__(self, parent: QWidget, manga: Manga) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._manga = copy(manga)

        self.thumbnail_widget = ThumbnailWidget(self)
        self.thumbnail_widget.setFixedSize(195, 279)

        self.title_widget = QLabel(manga.title, self)
        self.title_widget.installEventFilter(self)
        self.title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_widget.setFixedWidth(230)
        self.title_widget.setWordWrap(True)
        self.title_widget.setMouseTracking(True)
        self.title_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.library_icon = QLabel(self.thumbnail_widget)
        self.library_icon.setPixmap(
            QPixmap(os.path.join(utils.resource_path(), "icons", "book.png")).scaled(
                20, 20
            )
        )
        self.library_icon.setVisible(manga.library)
        self.library_icon.move(2, 2)

        source = self.manga.source
        path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.getfile(source.__class__))),
            "icon.ico",
        )

        source_icon = QLabel(self.thumbnail_widget)
        source_icon.setPixmap(
            QPixmap(path).scaled(
                20, 20, transformMode=Qt.TransformationMode.SmoothTransformation
            )
        )
        source_icon.move(173, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 9, 0, 9)
        layout.addWidget(self.thumbnail_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def manga(self) -> Manga:
        return self._manga

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.DynamicPropertyChange:
            self.style().polish(self)
        return super().event(e)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a0 == self.title_widget:
            if a1.type() == QEvent.Type.ContextMenu:
                a1.ignore()
                return True

            if a1.type() in (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
            ):
                QApplication.postEvent(self, a1.clone())
        return super().eventFilter(a0, a1)

    def library_status_changed(self, manga: Manga) -> None:
        if self.manga != manga:
            return

        self._manga = copy(manga)
        self.library_icon.setVisible(manga.library)

    def detail_changed(self, manga: Manga) -> None:
        if self.manga != manga:
            return

        if self.manga.title != manga.title:
            self.title_widget.setText(manga.title)
        self._manga = copy(manga)

    def thumbnail_changed(self, manga: Manga) -> None:
        if self.manga != manga:
            return

        self._manga = copy(manga)
        if not self.thumbnail_widget.pixmap().isNull():
            self.thumbnail_widget.priority = QNetworkRequest.Priority.HighPriority
            self.fetch_thumbnail()

    def fetch_thumbnail(self) -> None:
        self.thumbnail_widget.fetch_thumbnail()

    def deleteLater(self) -> None:
        self.thumbnail_widget._cancel_request.emit()
        return super().deleteLater()
