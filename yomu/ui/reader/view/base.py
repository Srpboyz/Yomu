from __future__ import annotations

from abc import ABC, ABCMeta, abstractmethod
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QPoint
from PyQt6.QtWidgets import QMenu, QWidget

from yomu.core.models import Chapter, Page

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow
    from yomu.ui.reader import Reader
    from yomu.ui.reader.page import PageView


class ViewMeta(type(QWidget), ABCMeta): ...


class BaseView(QWidget, ABC, metaclass=ViewMeta):
    name: str
    supports_zoom: bool = False

    page_changed = pyqtSignal(int)
    zoomed = pyqtSignal()

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader)
        self.reader = reader

        self._current_index = -1
        self.page_changed.connect(self._page_changed)

    def __init_subclass__(cls) -> None:
        if not isinstance(getattr(cls, "name", None), str):
            cls.name = cls.__name__
        return super().__init_subclass__()

    window: Callable[[], ReaderWindow]

    @property
    def parent(self) -> Reader:
        return self.reader

    @property
    def chapter(self) -> Chapter:
        return self.reader.chapter

    @property
    def current_index(self) -> int:
        return self._current_index

    @current_index.setter
    def current_index(self, index: int) -> None:
        if index != self._current_index:
            self._current_index = index
            self.page_changed.emit(index)

    page = current_index

    @property
    def page_count(self) -> int:
        return self.layout().count()

    @abstractmethod
    def set_page_views(self, pages: list[Page]) -> None: ...

    @abstractmethod
    def take_page_views(self) -> list[PageView]: ...

    @abstractmethod
    def _page_changed(self, page: int) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def zoom_out(self) -> None: ...

    @abstractmethod
    def zoom_in(self) -> None: ...

    @abstractmethod
    def page_at(self, pos: QPoint) -> PageView | None: ...

    def context_menu(self) -> QMenu | None: ...
