from __future__ import annotations

import os
from enum import IntEnum
from logging import getLogger
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel

from yomu.core.models import Page
from yomu.core.network import Request, Response
from yomu.core import utils

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow

    from .view.base import BaseView

logger = getLogger(__name__)


class PageView(QLabel):
    class Status(IntEnum):
        NULL, LOADING, LOADED, FAILED = range(4)

    _cancel_request = pyqtSignal()
    status_changed = pyqtSignal(Status)
    finished = pyqtSignal()

    def __init__(self, parent: BaseView, page: Page) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.page = page
        self.status = PageView.Status.NULL

        self.fetch_page()
        self.show()

    window: Callable[[], ReaderWindow]

    @property
    def status(self) -> PageView.Status:
        return self._status

    @status.setter
    def status(self, status: Status) -> None:
        self._status = status
        if status in (PageView.Status.NULL, PageView.Status.LOADING):
            self.setScaledContents(False)
            movie = QMovie(os.path.join(utils.resource_path(), "icons", "loading.gif"))
            self.setMovie(movie)
            movie.start()
        elif status == PageView.Status.FAILED:
            self.setText("Failed to load image")

        self.status_changed.emit(status)

    def fetch_page(self) -> None:
        if self.status not in (PageView.Status.NULL, PageView.Status.FAILED):
            return

        window = self.window()
        if not self.page.downloaded:
            if not window.network.is_online:
                self.status = PageView.Status.FAILED
                return

            try:
                request = self.page.get()
            except Exception:
                self.status = PageView.Status.FAILED
                return
            request.setPriority(Request.Priority.HighPriority)

        else:
            request = Request(QUrl.fromLocalFile(self.page.url))

        response = window.network.handle_request(request)
        response.finished.connect(self._page_fetched)
        self._cancel_request.connect(response.abort)
        self.status = PageView.Status.LOADING

    def _page_fetched(self) -> None:
        response: Response = self.sender()

        if response.error() == Response.Error.NoError:
            if self.page.downloaded:
                data = response.read_all()
            else:
                try:
                    data = self.page.chapter.source.parse_page(
                        response, self.page.to_source_page()
                    )
                except Exception as e:
                    logger.error("Failed to parse page", exc_info=e)
                    self.status = PageView.Status.FAILED
                    return

            self._load_image(data)
        else:
            self.page.source.page_request_error(response, self.page.to_source_page())
            self.status = PageView.Status.FAILED

    def _load_image(self, data: bytes) -> None:
        thumbnail = QPixmap()
        if not thumbnail.loadFromData(data):
            self.status = PageView.Status.FAILED
            return

        self.setScaledContents(True)
        self.setPixmap(
            thumbnail.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
        )

        self.status = PageView.Status.LOADED
        self.finished.emit()

    def copy_image_to_clipboard(self) -> None:
        QApplication.clipboard().setPixmap(self.pixmap())

    def deleteLater(self) -> None:
        self._cancel_request.emit()
        super().deleteLater()
