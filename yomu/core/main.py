from PyQt6.QtCore import QCommandLineOption, QCommandLineParser, QObject

from .app import YomuApp
from .ipc import IPCSocket


def _run_cli(socket: IPCSocket, argv: list[str]) -> int:
    parser = QCommandLineParser()
    parser.addHelpOption()
    parser.addVersionOption()

    showWindow = QCommandLineOption(["show"], socket.tr("Show the window"))
    newWindow = QCommandLineOption(["n", "new-window"], socket.tr("Opens a new window"))
    openSource = QCommandLineOption(
        ["s", "source"], QObject.tr("Open a source"), "source"
    )

    parser.addOption(showWindow)
    parser.addOption(newWindow)
    parser.addOption(openSource)
    parser.process(argv)

    showWindow = parser.isSet(showWindow) or not parser.isSet(newWindow)
    if showWindow:
        data = socket.show_window()
        if not data["success"]:
            YomuApp.display_message(
                f"Failed to show window. {data.get('reason', 'No reason provided')}"
            )
            return 1
        winId = data["winId"]
    else:
        data = socket.open_window()
        if not data["success"]:
            YomuApp.display_message(f"Failed to open a new window. {data['reason']}")
            return 1
        winId = data["winId"]

    if parser.isSet(openSource):
        data = socket.open_source(parser.value(openSource), winId)
        if not data["success"]:
            YomuApp.display_message(f"Failed to open a new window. {data['reason']}")
            return 1

    socket.disconnectFromServer()
    return 0


def main(argv: list[str]) -> int:
    socket = IPCSocket()
    if socket.connectToServer():
        return _run_cli(socket=socket, argv=argv)
    return YomuApp(argv=argv).exec()
