from enum import IntEnum
from typing import Any, overload, TYPE_CHECKING

from PyQt6.QtCore import QUrl, QUrlQuery
from PyQt6.QtNetwork import QNetworkRequest

from yomu.core.utils import MISSING

if TYPE_CHECKING:
    from yomu.source import Source

__all__ = ("Request", "Url")


class Url(QUrl):
    @overload
    def __init__(self, url: str) -> None: ...

    @overload
    def __init__(self, url: str, *, params: dict) -> None: ...

    def __init__(self, url: str, *, params: dict = None) -> None:
        super().__init__(url)
        if params is not None:
            self.set_params(params)

    def query(
        self,
        options: QUrl.ComponentFormattingOption = QUrl.ComponentFormattingOption.PrettyDecoded,
    ) -> QUrlQuery:
        return QUrlQuery(super().query(options))

    def add_params(self, params: dict) -> None:
        self.set_params(params=params, replace=False)

    def set_params(self, params: dict, *, replace: bool = True) -> None:
        query = self.query() if not replace else QUrlQuery()
        for param, value in params.items():
            if isinstance(value, list):
                for val in value:
                    query.addQueryItem(param, str(val))
            else:
                query.addQueryItem(param, str(value))
        self.setQuery(query)


def _default_user_agent() -> str:
    from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion, qWebEngineVersion
    import sys

    platform = (
        "X11; Linux x86_64"
        if sys.platform == "linux"
        else "Windows NT 10.0; Win64; x64"
    )
    return f"Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/{qWebEngineVersion()} Chrome/{qWebEngineChromiumVersion()} Safari/537.36"


class Request(QNetworkRequest):
    DEFAULT_USER_AGENT = _default_user_agent()

    class Route(IntEnum):
        GET, POST, PUT, DELETE = range(4)

    def __init__(
        self,
        url: str | Url,
        *,
        route: Route = Route.GET,
        data: dict = None,
        source: Source | None = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        super().__init__(Url(url))

        self.route = route
        self.data = data
        self.source = source

        self.setHeader(Request.KnownHeaders.UserAgentHeader, user_agent)
        self.setAttribute(Request.Attribute.CacheSaveControlAttribute, True)
        self.setAttribute(
            Request.Attribute.CacheLoadControlAttribute,
            Request.CacheLoadControl.PreferNetwork,
        )

    def __repr__(self) -> str:
        return f"<Request route={self.route.name} url='{self.url().toString()}'>"

    def attribute(self, code, defaultValue: Any = MISSING) -> Any:
        return super().attribute(code, defaultValue)

    def is_local_file(self) -> bool:
        return self.url().isLocalFile()

    def url(self) -> Url:
        return Url(super().url())


del _default_user_agent
