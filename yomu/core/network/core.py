from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING
from typing_extensions import deprecated

from PyQt6.QtCore import pyqtSignal, QEventLoop, QJsonDocument, QStandardPaths
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkDiskCache,
    QNetworkInformation,
)

from .cookiejar import CookieJar
from .request import Request
from .response import Response


if TYPE_CHECKING:
    from yomu.core.app import YomuApp


logger = getLogger(__name__)


class Network(QNetworkAccessManager):
    online_changed = pyqtSignal((bool, bool))
    offline_mode_changed = pyqtSignal(bool)
    network_status_changed = pyqtSignal(QNetworkInformation.Reachability)

    response_sent = pyqtSignal(Response)
    response_finished = pyqtSignal(Response)

    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self._app = app
        self.setAutoDeleteReplies(True)
        self.setRedirectPolicy(Request.RedirectPolicy.UserVerifiedRedirectPolicy)

        QNetworkInformation.loadBackendByName(QNetworkInformation.availableBackends()[0])  # fmt: skip
        self.network_info = QNetworkInformation.instance()
        self.network_info.reachabilityChanged.connect(self._reachability_changed)  # fmt: skip
        self._app.settings.value_changed.connect(self._settings_changed)

        self._online = not self.offline_mode and self.network_online

        jar = CookieJar(self)
        app.aboutToQuit.connect(jar.save_cookies)
        self.setCookieJar(jar)

        from .ratelimit import RateLimitHandler

        self._limit_handler = RateLimitHandler(self)

        cache = QNetworkDiskCache(self)
        cache.setMaximumCacheSize(512 * 1024 * 1024)
        cache.setCacheDirectory(
            QStandardPaths.standardLocations(
                QStandardPaths.StandardLocation.CacheLocation
            )[0]
        )
        self.setCache(cache)

    @property
    def parent(self) -> None: ...

    @property
    def is_online(self) -> bool:
        return self._online

    @property
    def offline_mode(self) -> bool:
        return self._app.settings.value("offline_mode", False, bool)

    @property
    def network_online(self) -> bool:
        return self.network_info.reachability() in (
            QNetworkInformation.Reachability.Site,
            QNetworkInformation.Reachability.Online,
        )

    def _response_finished(self) -> None:
        response: Response = self.sender()
        error = response.error()

        if error not in (
            Response.Error.OperationCanceledError,
            Response.Error.NoError,
        ):
            logger.warning(
                f"{response.operation.name} request to {response.url().toString()} failed - Reason: {error.name}({response.attribute(Request.Attribute.HttpStatusCodeAttribute)}) - {response.error_string()}"
            )

        self.response_finished.emit(response)
        if response.attribute(
            Request.Attribute.AutoDeleteReplyOnFinishAttribute, self.autoDeleteReplies()
        ):
            response.deleteLater()

    def _reachability_changed(
        self, reachability: QNetworkInformation.Reachability
    ) -> None:
        self.network_status_changed.emit(reachability)

        is_online = not self.offline_mode and (
            reachability
            in (
                QNetworkInformation.Reachability.Site,
                QNetworkInformation.Reachability.Online,
            )
        )

        if self._online != is_online:
            self._online = is_online
            self.online_changed.emit(is_online, False)

    def _settings_changed(self, name: str, value: object) -> None:
        if name != "offline_mode":
            return None

        logger.info(f"Offline mode {'enabled' if value else 'disabled'}")

        is_online = not value and (
            self.network_info.reachability()
            in (
                QNetworkInformation.Reachability.Site,
                QNetworkInformation.Reachability.Online,
            )
        )

        if self._online != is_online:
            self._online = is_online
            self.online_changed.emit(is_online, True)

    def handle_request(self, request: Request) -> Response:
        response = Response(self, request)
        self._limit_handler.handle_request(response)
        return response

    def _send_response(self, response: Response) -> None:
        request = response.request
        route = request.route

        if route == Request.Route.GET:
            qreply = self.get(request, QJsonDocument.fromVariant(request.data).toJson())
        if route == Request.Route.POST:
            qreply = self.post(
                request, QJsonDocument.fromVariant(request.data).toJson()
            )
        if route == Request.Route.PUT:
            qreply = self.put(request, QJsonDocument.fromVariant(request.data).toJson())
        if route == Request.Route.DELETE:
            qreply = self.deleteResource(request)

        qreply.redirected.connect(qreply.redirectAllowed.emit)
        self._app.aboutToQuit.connect(qreply.abort)

        response._connect_reply(qreply)
        response.finished.connect(self._response_finished)
        self.response_sent.emit(response)

    @deprecated("Use `Response.wait() instead`")
    def wait_for_request(self, response: Response) -> None:
        response.set_attribute(
            Request.Attribute.AutoDeleteReplyOnFinishAttribute, False
        )
        if response.is_finished():
            return

        loop = QEventLoop(self)
        response.finished.connect(loop.quit)
        loop.exec()
        loop.deleteLater()
