from __future__ import annotations

import os
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtWidgets import QStackedLayout, QToolButton, QWidget

from yomu.core import utils


class StackWidgetMixin:
    def set_current_widget(self) -> None: ...
    def clear_widget(self) -> None: ...


if TYPE_CHECKING:
    from .window import ReaderWindow

    class StackWidget(QWidget, StackWidgetMixin): ...


class StackLayout(QStackedLayout):
    def setGeometry(self, rect: QRect) -> None:
        w = self.currentWidget()
        if w.maximumWidth() < rect.width():
            rect.setX(round((rect.width() - w.maximumWidth()) / 2))
        w.setGeometry(rect)


class Stack(QWidget):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self._history = []

        self._back_button = QToolButton(self)
        self._back_button.setToolTip("Back")
        path = os.path.join(utils.resource_path(), "icons", "back.svg")
        self._back_button.setIcon(QIcon(path))
        self._back_button.pressed.connect(self.previous_widget)
        self._back_button.setEnabled(False)

        window.titlebar.insert_button(self._back_button, index=1)

        self.setContentsMargins(0, 0, 0, 0)
        self.setLayout(StackLayout(self))

    window: Callable[[], ReaderWindow]
    layout: Callable[[], StackLayout]

    @property
    def count(self) -> int:
        return self.layout().count()

    @property
    def current_widget(self) -> StackWidget:
        return self.layout().currentWidget()

    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            self.previous_widget()
        return super().mouseReleaseEvent(a0)

    def widget(self, a0: int) -> StackWidget:
        return self.layout().widget(a0)

    def set_current_widget(
        self, w: StackWidget, *, add_to_history: bool = True
    ) -> None:
        previous_widget = self.current_widget
        if previous_widget == w:
            return

        previous_widget.clear_widget()
        if add_to_history:
            self._history.append(previous_widget)

        self.layout().setCurrentWidget(w)
        w.set_current_widget()
        w.setFocus()

        window = self.window()
        window.current_widget_changed.emit(w)

        if w == window.library:
            self._back_button.setEnabled(False)
            self._history.clear()
        else:
            self._back_button.setEnabled(True)

    def add_widget(self, widget: StackWidget) -> bool:
        if isinstance(widget, StackWidgetMixin):
            self.layout().addWidget(widget)
            return True
        return False

    def insert_widget(self, index: int, widget: StackWidget) -> bool:
        if isinstance(widget, StackWidgetMixin):
            self.layout().insertWidget(index, widget)
            return True
        return False

    def remove_widget(self, widget: StackWidget) -> None:
        self.layout().removeWidget(widget)

    def has_widget(self, widget: QWidget) -> bool:
        for i in range(self.count):
            if self.widget(i) == widget:
                return True
        return False

    def previous_widget(self) -> None:
        window = self.window()
        current_widget = self.current_widget
        set_current_widget = lambda w: self.set_current_widget(w, add_to_history=False)
        page = self._history.pop() if self._history else window.library

        if current_widget == window.reader:
            return set_current_widget(window.mangacard)

        if current_widget == window.sourcepage:
            return set_current_widget(window.sourcelist)

        if current_widget in (window.sourcelist, window.downloads):
            return set_current_widget(window.library)

        return set_current_widget(page)
