from collections import deque
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer

from .request import Request
from .response import Response


if TYPE_CHECKING:
    from yomu.source import RateLimit, Source
    from .core import Network


class NetworkDeque(deque[Response]):
    def popleft(self):
        try:
            return super().popleft()
        except IndexError:
            return None

    def remove(self, value: Response):
        try:
            super().remove(value)
        except ValueError:
            ...


class SourceHandler(QObject):
    def __init__(self, parent: RateLimitHandler, rate_limit: RateLimit):
        super().__init__(parent)
        self.rate_limit = rate_limit
        self._responses_to_send = (NetworkDeque(), NetworkDeque(), NetworkDeque())
        self._sent_requests = 0

    def _add_request_count(self) -> None:
        self._sent_requests += 1
        timer = QTimer(self)
        timer.timeout.connect(self._remove_request_count)
        timer.setSingleShot(True)
        timer.setInterval(int(self.rate_limit.milliseconds + 500))
        timer.start()

    def _remove_request_count(self) -> None:
        self._sent_requests -= 1

    def __iter__(self):
        for responses in self._responses_to_send:
            while (
                not self.should_rate_limit()
                and (response := responses.popleft()) is not None
            ):
                yield response
                self._add_request_count()

    def should_rate_limit(self) -> None:
        if self._sent_requests >= self.rate_limit.rate:
            return True
        return False

    def append(self, response: Response) -> None:
        response.cancelled.connect(self.remove)

        index: int = response.priority.value >> 1
        self._responses_to_send[index].append(response)

    def remove(self, response: Response | None = None) -> None:
        response: Response = response or self.sender()

        index: int = response.priority.value >> 1
        self._responses_to_send[index].remove(response)


class RateLimitHandler(QObject):
    def __init__(self, network: Network) -> None:
        super().__init__(network)
        self.network = network
        self.source_handlers: dict[Source, SourceHandler] = {}

        timer = QTimer(self)
        timer.setInterval(300)
        timer.timeout.connect(self._send_rate_limited_requests)
        timer.start()

    @property
    def cache(self):
        return self.network.cache()

    def _send_rate_limited_requests(self) -> None:
        if self.network.network_online:
            for responses in self.source_handlers.values():
                for response in responses:
                    self.network._send_response(response)

    def handle_request(self, response: Response) -> None:
        request = response.request
        source = request.source
        if (
            source is None
            or source.rate_limit is None
            or response.request.is_local_file()
        ):
            return self.network._send_response(response)

        if (
            request.attribute(Request.Attribute.CacheLoadControlAttribute)
            == Request.CacheLoadControl.AlwaysCache
        ):
            return self.network._send_response(response)

        if (
            request.attribute(Request.Attribute.CacheLoadControlAttribute)
            == Request.CacheLoadControl.PreferCache
        ):
            metadata = self.network.cache().metaData(request.url())
            if metadata.isValid() and metadata.expirationDate().isValid():
                request.setAttribute(
                    Request.Attribute.CacheLoadControlAttribute,
                    Request.CacheLoadControl.AlwaysCache,
                )
                return self.network._send_response(response)

        if source not in self.source_handlers:
            self.source_handlers[source] = SourceHandler(self, source.rate_limit)
        self.source_handlers[source].append(response)
