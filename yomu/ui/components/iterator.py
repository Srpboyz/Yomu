from typing import Any, Callable, Generator

from PyQt6.QtWidgets import QLayout, QWidget


def iter_layout[T: QWidget = QWidget](layout: QLayout) -> Generator[T, Any, None]:
    for i in range(layout.count()):
        if (item := layout.itemAt(i)) is not None:
            yield item.widget()


class LayoutIterator[T: QWidget = QWidget]:
    layout: Callable[[], QLayout]

    def __iter__(self) -> Generator[T, Any, None]:
        return iter_layout(self.layout())
