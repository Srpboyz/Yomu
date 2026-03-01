from functools import wraps
from logging import Logger
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget


if TYPE_CHECKING:
    from yomu.core.app import YomuApp


class YomuExtension(QObject):
    def __init__(self, app: YomuApp) -> None:
        super().__init__(app)
        self.app = app

    def settings_widget(self) -> QWidget | None: ...

    def unload(self) -> None: ...


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
