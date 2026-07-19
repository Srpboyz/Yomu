import json
import os
from functools import wraps
from logging import Logger
from typing import Callable, TypedDict

from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer, QStandardPaths

from .config import RESOURCES_DIR


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
    """Returns the resource dir path

    Returns
    -------
    str
        The path
    """
    if RESOURCES_DIR is not None:
        path = os.path.join(RESOURCES_DIR, "yomu", "resources")
        if os.path.exists(path):
            return path

    path = __file__
    for _ in range(3):
        path = os.path.dirname(path)

    path = os.path.join(path, "resources")
    if not os.path.exists(path):
        raise FileNotFoundError("Can't find resources directory")
    return path


def icon_path() -> str:
    return os.path.join(resource_path(), "icons")


class Keybind(TypedDict):
    description: str
    keybinds: list[str]


type Keybindings = dict[str, Keybind]


def get_keybinds() -> Keybindings:
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


def pyqtSlot(logger: Logger | None = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                if logger is not None:
                    logger.exception(
                        f"An exception occured while running {func.__name__}",
                        exc_info=e,
                    )

        return wrapper

    return decorator


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
