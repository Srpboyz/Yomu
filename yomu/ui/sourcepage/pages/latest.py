from __future__ import annotations

from logging import getLogger
from enum import IntEnum

from PyQt6.QtCore import Qt

from yomu.core.network import Response, Request
from yomu.source import MangaList

from .base import BasePage

logger = getLogger(__name__)


class LatestWidget(BasePage):
    class Status(IntEnum):
        NULL, LOADING, CAN_LOAD_MORE, FINISHED = range(4)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._page = 0
        self._status = LatestWidget.Status.NULL

        self.manga_list.verticalScrollBar().valueChanged.connect(self._value_changed)
        self._loading_icon.movie().start()
        self._loading_icon.show()
        self.manga_list.hide()

        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.page_loaded.connect(
            self._page_finished_loading, Qt.ConnectionType.QueuedConnection
        )

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, status: Status) -> None:
        self._status = status
        if status in (LatestWidget.Status.CAN_LOAD_MORE, LatestWidget.Status.FINISHED):
            self._loading_icon.movie().stop()
            self._loading_icon.hide()
            self.manga_list.show()
        elif status == LatestWidget.Status.NULL:
            self._page = 0
            self._cancel_request.emit()
            self._loading_icon.movie().start()
            self._loading_icon.show()
            self.manga_list.hide()

    def _value_changed(self):
        scrollbar = self.manga_list.verticalScrollBar()
        if scrollbar.value() == scrollbar.maximum() and self.is_current_widget():
            self.load_page()

    def _page_finished_loading(self):
        if (
            not self.manga_list.verticalScrollBar().maximum()
            and self.is_current_widget()
        ):
            self.load_page()

    def load_page(self) -> None:
        if self.status in (LatestWidget.Status.LOADING, LatestWidget.Status.FINISHED):
            return

        self._page += 1
        try:
            request = self.source.get_latest(self._page)
        except Exception:
            return self._error_occured()

        request.setPriority(Request.Priority.HighPriority)
        request.setAttribute(
            Request.Attribute.CacheLoadControlAttribute,
            Request.CacheLoadControl.AlwaysNetwork,
        )
        request.setAttribute(Request.Attribute.CacheSaveControlAttribute, False)

        if (response := self.window().network.handle_request(request)) is None:
            return self._error_occured()

        response.finished.connect(self._page_data_received)
        self._cancel_request.connect(response.abort)
        self.status = LatestWidget.Status.LOADING

    def _page_data_received(self) -> None:
        response: Response = self.sender()

        error = response.error()
        if error == Response.Error.OperationCanceledError:
            return None

        if error != Response.Error.NoError:
            self.source.latest_request_error(response, self._page)
            return self._error_occured()

        try:
            manga_list = self.source.parse_latest(response, self._page)
        except Exception as e:
            logger.exception(
                f"Failed to parse page {self._page} of latest update for {self.source.name}",
                exc_info=e,
            )
            return self._error_occured()

        if not isinstance(manga_list, MangaList):
            logger.error(
                f"{self.source.name} returned a {type(manga_list).__name__} instead of a MangaList for the latest parse"
            )
            return self._error_occured()

        self.insert_mangas(list(dict.fromkeys(manga_list.mangas)))
        self.status = (
            LatestWidget.Status.CAN_LOAD_MORE
            if manga_list.has_next_page
            else LatestWidget.Status.FINISHED
        )

        self.manga_list.show()
        self.page_loaded.emit()

    def _error_occured(self, *, message: str | None = None) -> None:
        if message is None:
            message = f"Error fetching page {self._page} of latest updates"

        self.status = LatestWidget.Status.FINISHED
        self.window().display_message(message)

    def set_current_widget(self) -> None:
        if (
            not self.manga_list.count
            or not self.manga_list.verticalScrollBar().maximum()
        ):
            self.load_page()

    def clear_widget(self) -> None:
        self.status = LatestWidget.Status.NULL
        super().clear_widget()
