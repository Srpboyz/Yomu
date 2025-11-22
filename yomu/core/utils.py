import json
import os
from typing import TypedDict

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer, QStandardPaths


def app_data_path() -> str:
    """Returns the app data path

    Returns
    -------
    str
        The path
    """
    path = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    return path


def temp_dir_path() -> str:
    """Returns the temporary dir path

    Returns
    -------
    str
        The path
    """
    path = os.path.join(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.TempLocation),
        QCoreApplication.applicationName(),
    )
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def resource_path() -> str:
    path = __file__
    for _ in range(3):
        path = os.path.dirname(path)
    return os.path.join(path, "resources")


def icon_path() -> str:
    return os.path.join(resource_path(), "icons")


class Keybind(TypedDict):
    description: str
    keybinds: list[str]


def get_keybinds() -> dict[str, Keybind]:
    with open(os.path.join(resource_path(), "keybinds.json")) as f:
        keybinds: dict[str, dict[str, str | list[str]]] = json.load(f)

    extra_keybinds_path = os.path.join(app_data_path(), "keybinds.json")
    if not os.path.exists(extra_keybinds_path):
        with open(extra_keybinds_path, "w") as f:
            json.dump({}, f)

    try:
        with open(extra_keybinds_path) as f:
            updated_keybinds: dict[str, list[str]] = json.load(f)
    except Exception:
        ...
    else:
        for key, data in updated_keybinds.items():
            keybinds[key].update(data)

    return keybinds


def sleep(
    seconds: int,
    *,
    processFlags: QEventLoop.ProcessEventsFlag = QEventLoop.ProcessEventsFlag.AllEvents,
):
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.exit)
    loop.exec(processFlags)
    loop.deleteLater()


class _MissingValue:
    def __bool__(self) -> bool:
        return False

    def __eq__(self, value) -> bool:
        return self is value

    def __hash__(self):
        return id(self)

    def __repr__(self) -> str:
        return "..."


MISSING = _MissingValue()
del _MissingValue
