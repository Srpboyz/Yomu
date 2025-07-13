from __future__ import annotations

import os
from typing import Callable, TYPE_CHECKING, overload

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QFocusEvent, QIcon
from PyQt6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout, QWidget

from yomu.core import utils

if TYPE_CHECKING:
    from .window import ReaderWindow


class MenuItem(QLabel):
    def __init__(self, parent: MenuWidget, widget: QWidget, name: str):
        super().__init__(name, parent)
        self.setMinimumWidth(300)
        self.installEventFilter(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.widget = widget


class MenuWidget(QFrame):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)

        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._menu_button = QToolButton(self)
        self._menu_button.setToolTip("Menu")
        self._menu_button.setIcon(
            QIcon(os.path.join(utils.resource_path(), "icons", "menu.svg"))
        )
        self._menu_button.pressed.connect(self._menu_button_pressed)

        window.titlebar.insert_button(self._menu_button, index=0)

        self.move(0, window.titlebar.height() - 2)
        self.hide()

    window: Callable[[], ReaderWindow]
    layout: Callable[[], QVBoxLayout]

    def eventFilter(self, a0: MenuItem, a1: QEvent) -> bool:
        window = self.window()
        if (
            a1.type() == QEvent.Type.MouseButtonRelease
            and a1.button() == Qt.MouseButton.LeftButton
        ):
            self.hide()
            if window.stack.has_widget(a0.widget):
                window.current_widget = a0.widget
            else:
                a0.widget.show()
        return super().eventFilter(a0, a1)

    def leaveEvent(self, a0: QEvent | None) -> None:
        super().leaveEvent(a0)
        self.hide()

    def focusOutEvent(self, a0: QFocusEvent | None) -> None:
        super().focusOutEvent(a0)
        self.hide()

    def _menu_button_pressed(self):
        self.show() if self.isHidden() else self.hide()

    @overload
    def add_widget(self, widget: QWidget) -> None: ...

    @overload
    def add_widget(self, widget: QWidget, name: str = None) -> None: ...

    def add_widget(self, widget: QWidget, name: str = None) -> None:
        self.layout().addWidget(MenuItem(self, widget, name or widget.objectName()))

    @overload
    def insert_widget(self, index: int, widget: QWidget) -> None: ...

    @overload
    def insert_widget(self, index: int, widget: QWidget, name: str = None) -> None: ...

    def insert_widget(self, index: int, widget: QWidget, name: str = None) -> None:
        self.layout().insertWidget(
            index, MenuItem(self, widget, name or widget.objectName())
        )

    def remove_widget(self, widget: QWidget) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            item: MenuItem = layout.itemAt(i).widget()
            if item.widget == widget:
                return item.deleteLater()

    def show(self) -> None:
        super().show()
        self.raise_()
        self.setFocus()
