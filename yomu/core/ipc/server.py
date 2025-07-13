from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PyQt6.QtCore import QByteArray, QJsonDocument
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from yomu.ui import ReaderWindow

from .data import Command, SourceRequestData

if TYPE_CHECKING:
    from yomu.core.app import YomuApp


class IPCServer(QLocalServer):
    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self.app = app
        self.newConnection.connect(self._new_connection_pending)

    def listen(self) -> None:
        name = "yomu"
        not super().listen(name) and self.removeServer(name) and super().listen(name)

    def _new_connection_pending(self) -> None:
        client = self.nextPendingConnection()
        client.readyRead.connect(self.read_data)
        client.disconnected.connect(client.deleteLater)

    def read_data(self) -> None:
        client: QLocalSocket = self.sender()

        if self.app.startingUp():
            return client.write(
                QByteArray(
                    json.dumps(
                        {
                            "success": False,
                            "reason": "Yomu is starting up. Please wait until the app is ready.",
                        }
                    ).encode()
                )
            )

        if self.app.closingDown():
            return client.write(
                QByteArray(
                    json.dumps(
                        {
                            "success": False,
                            "reason": "Yomu is currently closing. Please wait to reload the app.",
                        }
                    ).encode()
                )
            )

        data = QJsonDocument.fromJson(client.readAll()).toVariant()
        match Command.from_code(data.get("cmd", -1)):
            case Command.SHOW:
                window = self.app.window
                window.activateWindow()
                client.write(
                    QByteArray(
                        json.dumps(
                            {"success": True, "winId": int(window.winId())}
                        ).encode()
                    )
                )
            case Command.NEW_WINDOW:
                window = self.app.create_window()
                window.showMaximized()
                client.write(
                    QByteArray(
                        json.dumps(
                            {"success": True, "winId": int(window.winId())}
                        ).encode()
                    )
                )
            case Command.OPEN_SOURCE:
                self.open_source(client, data)
            case _:
                client.write(
                    QByteArray(
                        json.dumps(
                            {"success": True, "reason": "Command not found"}
                        ).encode()
                    )
                )

    def open_source(self, client: QLocalSocket, data: SourceRequestData) -> None:
        name = data.get("name")
        for source in self.app.source_manager.sources:
            if source.name == name:
                break
        else:
            return client.write(
                QByteArray(
                    json.dumps(
                        {"success": False, "reason": "Source not found"}
                    ).encode()
                )
            )

        window = ReaderWindow.find(data["winId"]) or self.app.window
        window.sourcepage.source = source

        client.write(QByteArray(json.dumps({"success": True}).encode()))
