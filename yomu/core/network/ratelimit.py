from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from numbers import Real
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, QTimer, QUrl

from .request import Request
from .response import Response


if TYPE_CHECKING:
    from .core import Network


__all__ = ("RateLimit", "TimeUnit")


class TimeUnit(IntEnum):
    HOURS, MINUTES, SECONDS, MILLISECONDS = range(4)


@dataclass(frozen=True, repr=False, slots=True)
class RateLimit:
    rate: int
    per: Real = 1
    unit: TimeUnit = TimeUnit.SECONDS
    url: str | None = None

    def __post_init__(self):
        if not isinstance(self.rate, int):
            raise TypeError("rate must be an int")
        if not isinstance(self.per, Real):
            raise TypeError("per must be a number")
        if not isinstance(self.unit, TimeUnit):
            raise TypeError("unit must be a TimeUnit enum")
        if self.url is not None and not isinstance(self.url, str):
            raise TypeError("url must be a str")

    @property
    def milliseconds(self) -> float:
        match self.unit:
            case TimeUnit.HOURS:
                return self.per * 60 * 60 * 1000
            case TimeUnit.MINUTES:
                return self.per * 60 * 1000
            case TimeUnit.SECONDS:
                return self.per * 1000
            case TimeUnit.MILLISECONDS:
                return self.per

    def __repr__(self) -> str:
        return f"<RateLimit rate={self.rate} per={self.per} unit={self.unit.name} >"


class NetworkDeque(deque[Response]):
    def remove(self, value: Response):
        try:
            super().remove(value)
        except ValueError:
            ...


class RateLimiter(QObject):
    def __init__(self, parent: RateLimitHandler, rate_limit: RateLimit) -> None:
        super().__init__(parent)
        self.rate_limit = rate_limit
        self.to_send = (NetworkDeque(), NetworkDeque(), NetworkDeque())
        self.count = 0

    def on_timeout(self) -> None:
        self.count -= 1

    def __iter__(self):
        for responses in self.to_send:
            while responses and not self.should_rate_limit():
                yield responses.popleft()
                self.count += 1
                QTimer.singleShot(
                    int(self.rate_limit.milliseconds + 500), self.on_timeout
                )

    def should_rate_limit(self) -> bool:
        return self.count >= self.rate_limit.rate

    def append(self, response: Response) -> None:
        response.cancelled.connect(self.remove)
        index: int = response.priority.value // 2
        self.to_send[index].append(response)

    def remove(self, response: Response | None = None) -> None:
        response: Response = response or self.sender()
        index: int = response.priority.value // 2
        self.to_send[index].remove(response)


class RateLimitHandler(QObject):
    def __init__(self, network: Network) -> None:
        super().__init__(network)
        self.network = network
        self.rate_limiters: dict[str, RateLimiter] = {}

        timer = QTimer(self)
        timer.setInterval(300)
        timer.timeout.connect(self.send_requests)
        timer.start()

    def send_requests(self) -> None:
        if self.network.network_online:
            for responses in self.rate_limiters.values():
                for response in responses:
                    self.network._send_response(response)

    def add_rate_limit(self, rate_limit: RateLimit) -> None:
        self.rate_limiters[QUrl(rate_limit.url).host()] = RateLimiter(self, rate_limit)

    def handle(self, response: Response) -> None:
        request = response.request
        if request.is_local_file():
            return self.network._send_response(response)

        cache_attribute = request.attribute(Request.Attribute.CacheLoadControlAttribute)
        if cache_attribute == Request.CacheLoadControl.AlwaysCache:
            return self.network._send_response(response)

        url = request.url()
        if (
            cache_attribute == Request.CacheLoadControl.PreferCache
            and self.network.cache().is_valid(url)
        ):
            request.setAttribute(
                Request.Attribute.CacheLoadControlAttribute,
                Request.CacheLoadControl.AlwaysCache,
            )
            return self.network._send_response(response)

        limiter = self.rate_limiters.get(url.host())
        if limiter is not None:
            return limiter.append(response)

        source = request.source
        if source is None or source.rate_limit is None:
            return self.network._send_response(response)

        limiter = self.rate_limiters.get(str(source.id))
        if limiter is None:
            limiter = RateLimiter(self, source.rate_limit)
            self.rate_limiters[str(source.id)] = limiter
        limiter.append(response)
