import os
from enum import IntEnum
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QMimeData, Qt, QUrl
from PyQt6.QtGui import QDrag, QPixmap, QMovie, QMouseEvent
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QLabel, QWidget

from yomu.core.downloader import Downloader
from yomu.core.models import Manga
from yomu.core.network import Request, Response
from yomu.core import utils

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow

    class Parent(QWidget):
        manga: Manga


class LoadingStatus(IntEnum):
    NULL, CACHE, NETWORK, LOADED = range(4)


class ThumbnailWidget(QLabel):
    _cancel_request = pyqtSignal()
    Status = LoadingStatus

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status = LoadingStatus.NULL
        self.priority = QNetworkRequest.Priority.NormalPriority

    parent: Callable[[], Parent]
    window: Callable[[], ReaderWindow]

    @property
    def manga(self) -> Manga:
        return self.parent().manga

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        if (
            ev.buttons() != Qt.MouseButton.LeftButton
            or (pixmap := self.pixmap()).isNull()
        ):
            return

        mimedata = QMimeData()
        mimedata.setImageData(pixmap.toImage())
        path = os.path.join(utils.temp_dir_path(), "dragged-image.jpg")
        pixmap.save(path, "JPG")
        mimedata.setUrls([QUrl.fromLocalFile(path)])

        drag = QDrag(self)
        drag.setMimeData(mimedata)
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.DropAction.CopyAction)

    def fetch_thumbnail(self, *, force_network: bool = False) -> None:
        if not self.manga.thumbnail:
            return self.setText("Thumbnail not found")

        if self.status in (LoadingStatus.CACHE, LoadingStatus.NETWORK):
            self._cancel_request.emit()

        window = self.window()
        network = window.network
        path = Downloader.resolve_path(self.manga)
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
        request.setAttribute(
            Request.Attribute.CacheLoadControlAttribute,
            Request.CacheLoadControl.PreferCache,
        )
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
                else self.manga.source.parse_thumbnail(
                    response, self.manga.to_source_manga()
                )
            )

        if self.status == LoadingStatus.CACHE:
            return self.fetch_thumbnail(force_network=True)

        if error != Response.Error.OperationCanceledError:
            self.manga.source.thumbnail_request_error(
                response, self.manga.to_source_manga()
            )
            self.status = LoadingStatus.NULL
            return self.setText("Failed to load image")

    def _load_image(self, data: bytes) -> None:
        thumbnail = QPixmap()
        if not thumbnail.loadFromData(data):
            if self.status == LoadingStatus.CACHE:
                return self.fetch_thumbnail(force_network=True)
            self.status = LoadingStatus.NULL
            return self.setText("Failed to load image")

        self.setPixmap(
            thumbnail.scaledToHeight(
                self.height(), Qt.TransformationMode.SmoothTransformation
            )
        )
        self.status = LoadingStatus.LOADED

    def clear(self):
        super().clear()
        self._cancel_request.emit()
