import os
from typing import Callable, TYPE_CHECKING, overload

from PyQt6.QtCore import QChildEvent, QEvent, Qt
from PyQt6.QtGui import QFocusEvent, QHideEvent, QIcon, QShowEvent
from PyQt6.QtWidgets import QFrame, QLabel, QToolButton, QVBoxLayout, QWidget

from yomu.core import utils
from yomu.ui.components.cardlist.core import VerticalBoxLayout
from yomu.ui.components.cardlist.selector import CardSelector
from yomu.ui.components.iterator import LayoutIterator

if TYPE_CHECKING:
    from .window import ReaderWindow


class MenuItem(QLabel):
    def __init__(self, parent: MenuWidget, widget: QWidget, name: str):
        super().__init__(name, parent)
        self.widget = widget
        widget.destroyed.connect(self.deleteLater)

        self.setMinimumWidth(300)
        self.installEventFilter(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MenuWidget(QFrame, LayoutIterator[MenuItem]):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)

        layout = VerticalBoxLayout(self)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(0)
        self.setLayout(layout)
        CardSelector(self)

        button = self._menu_button = QToolButton(self)
        button.setToolTip("Menu")
        button.setIcon(QIcon(os.path.join(utils.resource_path(), "icons", "menu.svg")))
        button.pressed.connect(self.toggle_visibility)

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

    def childEvent(self, a0: QChildEvent) -> None:
        super().childEvent(a0)
        if a0.removed():
            self.layout().activate()
            self.adjustSize()

    def leaveEvent(self, a0: QEvent | None) -> None:
        super().leaveEvent(a0)
        self.hide()

    def focusOutEvent(self, a0: QFocusEvent | None) -> None:
        super().focusOutEvent(a0)
        self.hide()

    def toggle_visibility(self):
        self.show() if self.isHidden() else self.hide()

    def showEvent(self, a0: QShowEvent | None) -> None:
        window = self.window()
        if window.isFullScreen():
            window.titlebar.show()

    def hideEvent(self, a0: QHideEvent | None) -> None:
        window = self.window()
        if window.isFullScreen() and (
            self.cursor().pos().isNull() or not window.titlebar.underMouse()
        ):
            window.titlebar.hide()

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
        for item in self:
            if item.widget == widget:
                return item.deleteLater()

    def show(self) -> None:
        super().show()
        self.raise_()
        self.setFocus()
