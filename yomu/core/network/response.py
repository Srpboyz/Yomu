from __future__ import annotations

from typing import Any, TYPE_CHECKING
import json

from PyQt6.QtCore import pyqtSignal, QByteArray, QEventLoop, QObject
from PyQt6.QtNetwork import QHttpHeaders, QNetworkReply

from yomu.core.utils import MISSING

from .request import Request, Url

if TYPE_CHECKING:
    from yomu.source.core import Source

__all__ = ("Response",)


class Response(QObject):
    started = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()
    failed = pyqtSignal()

    Error = QNetworkReply.NetworkError

    def __init__(self, parent: QObject, request: Request):
        super().__init__(parent)
        self._request = request

        self._data = QByteArray()
        self._error_string = ""

        self._error = Response.Error.NoError
        self._attributes = {}
        self._headers: QHttpHeaders = QHttpHeaders()
        self._is_finished = False

    @property
    def request(self) -> Request:
        return self._request

    @property
    def priority(self) -> Request.Priority:
        return self.request.priority()

    @property
    def route(self) -> Request.Route:
        return self.request.route

    @property
    def source(self) -> Source | None:
        return self.request.source

    @property
    def headers(self) -> QHttpHeaders:
        return QHttpHeaders(self._headers)

    operation = route

    def _connect_reply(self, reply: QNetworkReply) -> None:
        reply.finished.connect(self._reply_finished)
        self.cancelled.connect(reply.abort)

    def _reply_finished(self) -> None:
        reply: QNetworkReply = self.sender()
        self._attributes = {
            attr: value if (value := reply.attribute(attr)) is not None else MISSING
            for attr in Request.Attribute
        }
        self._headers = reply.headers()

        error = reply.error()
        if reply.error() == Response.Error.NoError:
            self._data = reply.readAll()
        else:
            self._error = error
            self._error_string = reply.errorString()

        self._is_finished = True
        self.finished.emit()

    def attribute(
        self, attribute: Request.Attribute, defaultValue: Any = MISSING
    ) -> Any:
        value = self._attributes.get(attribute, defaultValue)
        if value is MISSING:
            return defaultValue
        return value

    def set_attribute(self, attribute: Request.Attribute, value: Any) -> None:
        self._attributes[attribute] = value

    def is_finished(self) -> bool:
        return self._is_finished

    def url(self) -> Url:
        return self.request.url()

    def error(self) -> Error:
        return self._error

    def error_string(self) -> str:
        return self._error_string

    def read(self, size: int, *, start: int = 0):
        max_size = self._data.size()
        return self._data[start : min(size, max_size)]

    def read_all(self) -> QByteArray:
        return QByteArray(self._data)

    def json(self) -> Any:
        return json.loads(self.read_all().data())

    def wait(self) -> None:
        if self.is_finished():
            return

        self.set_attribute(Request.Attribute.AutoDeleteReplyOnFinishAttribute, False)
        loop = QEventLoop(self)
        self.finished.connect(loop.quit)
        loop.exec()
        loop.deleteLater()

    def abort(self) -> None:
        if not self._is_finished:
            self.cancelled.emit()

    cancel = abort

    def deleteLater(self) -> None:
        self.abort()
        super().deleteLater()
