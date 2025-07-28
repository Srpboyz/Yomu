from __future__ import annotations

import os
from enum import IntEnum
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QPixmap, QMovie
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QLabel, QWidget

from yomu.core.models import Manga
from yomu.core.network import Request, Response
from yomu.core import utils

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


class LoadingStatus(IntEnum):
    NULL, CACHE, NETWORK = range(3)


class ThumbnailWidget(QLabel):
    _cancel_request = pyqtSignal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status = LoadingStatus.NULL
        self.priority = QNetworkRequest.Priority.NormalPriority

    window: Callable[[], ReaderWindow]

    @property
    def manga(self) -> Manga:
        return self.parent().manga

    def fetch_thumbnail(self, *, force_network: bool = False) -> None:
        if not self.manga.thumbnail:
            return self.setText("Thumbnail not found")
        window = self.window()
        network = window.network
        path = window.app.downloader.resolve_path(self.manga)
        if not force_network and self.manga.library and os.path.exists(path):
            request = Request(QUrl.fromLocalFile(os.path.join(path, "thumbnail.png")))
            self.status = LoadingStatus.CACHE
        else:
            if not network.is_online:
                return self.setText("Failed to load image")

            try:
                request = self.manga.get_thumbnail()
            except Exception:
                return self.setText("Failed to load image")
            else:
                self.status = LoadingStatus.NETWORK

        request.setPriority(self.priority)
        response = network.handle_request(request)
        response.finished.connect(self._thumbnail_received)
        self._cancel_request.connect(response.abort)

        movie = QMovie(os.path.join(utils.resource_path(), "icons", "loading.gif"))
        self.setMovie(movie)
        movie.start()

    def _thumbnail_received(self) -> None:
        response: Response = self.sender()

        error = response.error()
        if error == Response.Error.NoError:
            return self._load_image(
                response.read_all()
                if self.status == LoadingStatus.CACHE
                else self.manga.source.parse_thumbnail(response)
            )

        if self.status == LoadingStatus.CACHE:
            return self.fetch_thumbnail(force_network=True)

        if error != Response.Error.OperationCanceledError:
            self.manga.source.thumbnail_request_error(response)
            return self.setText("Failed to load image")

    def _load_image(self, data: bytes) -> None:
        thumbnail = QPixmap()
        if not thumbnail.loadFromData(data):
            if self.status == LoadingStatus.CACHE:
                return self.fetch_thumbnail(force_network=True)
            return self.setText("Failed to load image")

        thumbnail = thumbnail.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(thumbnail)

    def clear(self):
        super().clear()
        self._cancel_request.emit()
