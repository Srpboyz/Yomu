from __future__ import annotations

import json

from PyQt6.QtCore import QByteArray
from PyQt6.QtNetwork import QLocalSocket

from .data import Command, ReturnData, WindowReturnData, IPC_NAME


class IPCSocket(QLocalSocket):
    def connectToServer(self) -> bool:
        super().connectToServer(IPC_NAME)
        return self.waitForConnected()

    def open_window(self) -> WindowReturnData:
        return self._send_data(
            QByteArray(json.dumps({"cmd": (Command.NEW_WINDOW)}).encode())
        )

    def show_window(self) -> WindowReturnData:
        return self._send_data(QByteArray(json.dumps({"cmd": Command.SHOW}).encode()))

    def open_source(self, name: str, winId: int) -> ReturnData:
        return self._send_data(
            QByteArray(
                json.dumps(
                    {"cmd": Command.OPEN_SOURCE, "name": name, "winId": winId}
                ).encode()
            )
        )

    def _send_data(self, data: QByteArray) -> ReturnData:
        self.write(data)
        self.waitForReadyRead()
        return json.loads(self.readAll().data())
