from __future__ import annotations

import os
from copy import copy
from typing import overload

from PyQt6.QtCore import pyqtSignal, QBuffer, QDir, QObject, Qt, QTimer, QFile
from PyQt6.QtGui import QImage
from PyQt6.QtNetwork import QNetworkInformation

from .app import YomuApp
from .models import Chapter, Manga
from .network import Network, Request, Response
from . import utils

from yomu.source.models import Page as SourcePage


class DownloadChapter(QObject):
    page_downloaded = pyqtSignal((Chapter, int, int, bytes))
    download_finished = pyqtSignal(Chapter)
    download_failed = pyqtSignal((Chapter, bool))
    aborted = pyqtSignal()

    def __init__(self, parent: QObject, network: Network, chapter: Chapter) -> None:
        super().__init__(parent)
        self.network = network
        self.chapter = chapter
        self._pages: list[SourcePage] = []
        self._index = -1
        self.cancelled = False

        self.get_pages()

    def _handle_request(self, request: Request) -> Response:
        request.source = self.chapter.source
        request.setPriority(Request.Priority.LowPriority)
        response = self.network.handle_request(request)
        self.aborted.connect(response.abort)
        return response

    def get_pages(self) -> None:
        try:
            request = self.chapter.get_pages()
        except Exception:
            return self._request_failed()

        response = self._handle_request(request)
        response.finished.connect(self._pages_received)

    def _pages_received(self) -> None:
        response: Response = self.sender()

        error = response.error()
        if error != Response.Error.NoError:
            if not self.cancelled:
                self.chapter.source.chapter_pages_request_error(
                    response, self.chapter.to_source_chapter()
                )
            return self._request_failed()

        try:
            self._pages = self.chapter.source.parse_chapter_pages(
                response, self.chapter.to_source_chapter()
            )
        except Exception:
            return self._request_failed()

        self.next_page()

    def next_page(self) -> None:
        if self.cancelled:
            return self._request_failed()

        self._index += 1
        page = self._pages[self._index]

        try:
            request = self.chapter.source.get_page(page)
        except Exception:
            return self._request_failed()

        response = self._handle_request(request)
        response.finished.connect(self._page_image_received)

    def _page_image_received(self) -> None:
        response: Response = self.sender()

        error = response.error()
        if error != Response.Error.NoError:
            if not self.cancelled:
                self.chapter.source.page_request_error(
                    response, self._pages[self._index]
                )
            return self._request_failed()

        try:
            data = self.chapter.source.parse_page(response, self._pages[self._index])
        except Exception:
            return self._request_failed()

        image = QImage()
        if not image.loadFromData(data):
            return self._request_failed()
        image = image.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)

        buffer = QBuffer(self)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "JPG"):
            return self._request_failed()

        data = buffer.buffer().data()
        buffer.deleteLater()

        length = len(self._pages)
        self.page_downloaded.emit(self.chapter, self._index, length, data)

        if self._index >= length - 1:
            self.download_finished.emit(self.chapter)
            return self.deleteLater()

        timer = QTimer(self)
        timer.setInterval(1000)
        timer.setSingleShot(True)

        timer.timeout.connect(self.next_page)
        self.aborted.connect(timer.stop)

        timer.timeout.connect(timer.deleteLater)
        self.aborted.connect(timer.deleteLater)
        timer.destroyed.connect(self._timer_deleted)

        timer.start()

    def _timer_deleted(self) -> None:
        if self.cancelled:
            self._request_failed()

    def _request_failed(self) -> None:
        self.download_failed.emit(self.chapter, self.cancelled)
        self.deleteLater()

    def abort(self) -> None:
        self.cancelled = True
        self.aborted.emit()


class DownloadThumbnail(QObject):
    thumbnail_downloaded = pyqtSignal((Manga, bytes))

    def __init__(self, parent: QObject, network: Network, manga: Manga) -> None:
        super().__init__(parent)
        self.network = network
        self.manga = manga

        self.send_request()

    def send_request(self) -> None:
        try:
            request = self.manga.get_thumbnail()
        except Exception:
            return self.deleteLater()

        request.source = self.manga.source
        request.setPriority(Request.Priority.LowPriority)

        response = self.network.handle_request(request)
        response.finished.connect(self._thumbnail_received)

    def _thumbnail_received(self) -> None:
        response: Response = self.sender()

        error = response.error()
        if error != Response.Error.NoError:
            if error != Response.Error.OperationCanceledError:
                self.manga.source.thumbnail_request_error(
                    response, self.manga.to_source_manga()
                )
            return self.deleteLater()

        try:
            data = self.manga.source.parse_thumbnail(
                response, self.manga.to_source_manga()
            )
        except Exception:
            return self.deleteLater()

        image = QImage()
        if not image.loadFromData(data):
            return self.deleteLater()
        image = image.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)

        buffer = QBuffer(self)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            return self.deleteLater()

        data = buffer.buffer().data()
        self.thumbnail_downloaded.emit(self.manga, data)
        self.deleteLater()


class Downloader(QObject):
    chapter_deleted = pyqtSignal(Chapter)
    download_started = pyqtSignal(Chapter)
    download_update = pyqtSignal((Chapter, int, int))
    download_finished = pyqtSignal(Chapter)
    download_failed = pyqtSignal((Chapter, bool))

    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self.app = app

        app.chapter_read_status_changed.connect(self._auto_delete_chapter)
        app.manga_library_status_changed.connect(
            self._manga_library_changed, Qt.ConnectionType.QueuedConnection
        )
        self.network.network_status_changed.connect(self._network_status_changed)

    @property
    def network(self) -> Network:
        return self.app.network

    def _manga_library_changed(self, manga: Manga) -> None:
        if manga.library:
            self.download_thumbnail(manga)
        else:
            self.delete_thumbnail(manga)

    def _network_status_changed(self, reachability: QNetworkInformation.Reachability):
        if reachability != QNetworkInformation.Reachability.Online:
            for download in self.findChildren(DownloadChapter):
                download.abort()

    def _auto_delete_chapter(self, chapter: Chapter) -> None:
        if (
            chapter.read
            and chapter.downloaded
            and self.app.settings.value("autodelete_chapter", False, bool)
        ):
            self.delete_chapter(chapter)

    def find_download_request(self, chapter: Chapter) -> DownloadChapter | None:
        for download in self.findChildren(
            DownloadChapter, options=Qt.FindChildOption.FindDirectChildrenOnly
        ):
            if download.chapter == chapter:
                return download

    def download_chapter(self, chapter: Chapter) -> DownloadChapter | None:
        if (
            not self.network.network_online
            or chapter.downloaded
            or self.is_downloading(chapter)
        ):
            return None

        download = DownloadChapter(self, self.network, copy(chapter))
        download.page_downloaded.connect(
            self._save_chapter_page, Qt.ConnectionType.QueuedConnection
        )
        download.download_failed.connect(
            self._chapter_failed, Qt.ConnectionType.QueuedConnection
        )
        download.download_finished.connect(
            self._chapter_finished, Qt.ConnectionType.QueuedConnection
        )
        self.download_started.emit(chapter)
        return download

    def _save_chapter_page(
        self, chapter: Chapter, index: int, total: int, data: bytes
    ) -> None:
        path = Downloader.resolve_path(chapter)
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, f"{index}.png")

        with open(path, "wb") as f:
            f.write(data)

        self.download_update.emit(chapter, index, total)

    def _chapter_failed(self, chapter: Chapter, aborted: bool) -> None:
        if aborted:
            QDir(Downloader.resolve_path(chapter)).removeRecursively()

        self.download_failed.emit(chapter, aborted)

    def _chapter_finished(self, chapter: Chapter) -> None:
        if self.app.sql.mark_chapters_download_status(chapter, downloaded=True):
            self.download_finished.emit(chapter)

    def cancel_chapter(self, chapter: Chapter) -> None:
        if (download := self.find_download_request(chapter)) is not None:
            download.abort()

    def delete_chapter(self, chapter: Chapter) -> None:
        if not chapter.downloaded:
            return

        QDir(Downloader.resolve_path(chapter)).removeRecursively()
        if self.app.sql.mark_chapters_download_status(chapter, downloaded=False):
            self.chapter_deleted.emit(chapter)

    def download_thumbnail(self, manga: Manga) -> None:
        request = DownloadThumbnail(self, self.network, manga)
        request.thumbnail_downloaded.connect(self._thumbnail_downloaded)

    def _thumbnail_downloaded(self, manga: Manga, data: bytes) -> None:
        path = Downloader.resolve_path(manga)
        os.makedirs(path, exist_ok=True)

        with open(os.path.join(path, "thumbnail.png"), "wb") as f:
            f.write(data)

    def delete_thumbnail(self, manga: Manga) -> None:
        QFile.remove(os.path.join(Downloader.resolve_path(manga), "thumbnail.png"))

    @overload
    @staticmethod
    def resolve_path(arg: Manga) -> str: ...

    @overload
    @staticmethod
    def resolve_path(arg: Chapter) -> str: ...

    @staticmethod
    def resolve_path(arg: Manga | Chapter) -> str:
        is_chapter = isinstance(arg, Chapter)
        manga = arg.manga if is_chapter else arg

        path = os.path.join(utils.app_data_path(), "downloads", str(manga.id))
        if is_chapter:
            path = os.path.join(path, str(arg.id))
        return path

    def is_downloading(self, chapter: Chapter) -> bool:
        return bool(self.find_download_request(chapter))
