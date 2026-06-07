from argparse import ArgumentParser, Namespace
from .app import YomuApp
from .ipc import IPCSocket


def parse_args(argv: list[str]) -> Namespace:
    parser = ArgumentParser("yomu")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {YomuApp.applicationVersion()}",
    )
    parser.add_argument("--show", action="store_true", help="Show the window")
    parser.add_argument(
        "-n", "--new-window", action="store_true", help="Opens a new window"
    )
    parser.add_argument(
        "-s",
        "--source",
        help="Open a source. This won't work unless app is already running",
    )
    return parser.parse_args(argv)


def handle_args(socket: IPCSocket, args: Namespace) -> int:
    show_window = args.show or not args.new_window
    if show_window:
        data = socket.show_window()
        if not data["success"]:
            YomuApp.display_message(
                f"Failed to show window. {data.get('reason', 'No reason provided')}"
            )
            return 1
        win_id = data["winId"]
    else:
        data = socket.open_window()
        if not data["success"]:
            YomuApp.display_message(f"Failed to open a new window. {data['reason']}")
            return 1
        win_id = data["winId"]

    if args.source:
        data = socket.open_source(args.source, win_id)
        if not data["success"]:
            YomuApp.display_message(f"Failed to open a new window. {data['reason']}")
            return 1

    socket.disconnectFromServer()
    return 0


def main(argv: list[str]) -> int:
    args = parse_args(argv[1:])
    socket = IPCSocket()
    if socket.connectToServer():
        return handle_args(socket=socket, args=args)
    return YomuApp(argv=argv).exec()
