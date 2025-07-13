import os
from typing import Iterable, overload

from PyQt6.QtCore import QDateTime, QObject, QUrl
from PyQt6.QtNetwork import QNetworkCookie, QNetworkCookieJar

from yomu.core import utils


class CookieJar(QNetworkCookieJar):
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)

        cookie_file = os.path.join(utils.app_data_path(), "cookies.txt")
        if not os.path.exists(cookie_file):
            with open(cookie_file, "w") as f:
                return

        with open(cookie_file, "rb") as f:
            cookies = QNetworkCookie.parseCookies(f.read())

        self.setAllCookies(
            list(
                filter(
                    lambda cookie: cookie.expirationDate().toMSecsSinceEpoch()
                    > QDateTime.currentMSecsSinceEpoch(),
                    cookies,
                )
            )
        )

    @overload
    def setCookiesFromUrl(
        self, cookieList: Iterable[QNetworkCookie], url: str
    ) -> bool: ...

    @overload
    def setCookiesFromUrl(
        self, cookieList: Iterable[QNetworkCookie], url: QUrl
    ) -> bool: ...

    def setCookiesFromUrl(
        self, cookieList: Iterable[QNetworkCookie], url: str | QUrl
    ) -> bool:
        _url = QUrl(url) if isinstance(url, str) else url
        return super().setCookiesFromUrl(cookieList, _url)

    def save_cookies(self) -> None:
        cookies = [
            cookie.toRawForm().data()
            for cookie in self.allCookies()
            if not cookie.isSessionCookie()
            and cookie.expirationDate().toMSecsSinceEpoch()
            > QDateTime.currentMSecsSinceEpoch()
        ]
        with open(os.path.join(utils.app_data_path(), "cookies.txt"), "wb") as f:
            f.write(b"\n".join(cookies))
