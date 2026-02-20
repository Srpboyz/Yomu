from __future__ import annotations

import os
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import QContextMenuEvent, QIcon, QMouseEvent
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMenu, QSizePolicy, QToolButton

from yomu.core import utils

if TYPE_CHECKING:
    from .window import ReaderWindow


class TitlebarLayout(QHBoxLayout):
    def __init__(self, titlebar: TitleBar) -> None:
        super().__init__(titlebar)
        self.titlebar = titlebar

    def setGeometry(self, a0: QRect) -> None:
        super().setGeometry(a0)
        titleWidget = self.titlebar._title_widget

        left = 0
        for i in range(self.indexOf(titleWidget) - 1, -1, -1):
            widget = self.itemAt(i).widget()
            if not widget.isHidden():
                left = widget.geometry().right()
                break

        title_geometry = titleWidget.geometry()
        if title_geometry.width() < a0.width():
            titleWidget.setGeometry(
                QRect(
                    max(left, round((a0.width() - title_geometry.width()) / 2)),
                    title_geometry.y(),
                    title_geometry.width(),
                    title_geometry.height(),
                )
            )


class TitleBar(QFrame):
    """The window bar to move the :class:`Window`"""

    def __init__(self, window: ReaderWindow) -> None:
        """
        Parameters
        ----------
        window : Window
            The window that holds all widgets
        """
        super().__init__(window)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum
        )

        icon_path = os.path.join(utils.resource_path(), "icons")

        self.refresh_button = QToolButton(self)
        self.refresh_button.setToolTip("Refresh")
        path = os.path.join(icon_path, "refresh.svg")
        self.refresh_button.setIcon(QIcon(path))

        self._title_widget = QLabel("Library", self)
        self._title_widget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self._title_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.minimize_button = QToolButton(self)
        path = os.path.join(icon_path, "minimize.svg")
        self.minimize_button.setIcon(QIcon(path))
        self.minimize_button.released.connect(window.showMinimized)

        self.normal_button = QToolButton(self)
        path = os.path.join(icon_path, "normal.svg")
        self.normal_button.setIcon(QIcon(path))
        self.normal_button.released.connect(window.showNormal)

        self.maximize_button = QToolButton(self)
        path = os.path.join(icon_path, "maximize.svg")
        self.maximize_button.setIcon(QIcon(path))
        self.maximize_button.released.connect(window.showMaximized)
        self.maximize_button.hide()

        self.close_button = QToolButton(self)
        path = os.path.join(icon_path, "close.svg")
        self.close_button.setIcon(QIcon(path))
        self.close_button.released.connect(window.close)
        self.close_button.setStyleSheet(
            """QToolButton:hover {background-color: #FF0000}"""
        )

        layout = TitlebarLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._title_widget, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.minimize_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.normal_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.maximize_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.close_button, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)

        window.window_state_changed.connect(self._window_state_changed)

    window: Callable[[], ReaderWindow]
    layout: Callable[[], QHBoxLayout]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Start the window movement if left click is pressed

        Parameters
        ----------
        event : QMouseEvent
            The mouse event
        """
        window = self.window()
        if not window.isFullScreen() and event.buttons() == Qt.MouseButton.LeftButton:
            window.windowHandle().startSystemMove()
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, a0: QMouseEvent) -> None:
        """Change the window state if the title bar is double clicked

        Parameters
        ----------
        a0 : QMouseEvent
            The mouse event
        """
        if (
            a0.button() == Qt.MouseButton.LeftButton
            and not self.window().isFullScreen()
        ):
            if self.maximize_button.isHidden():
                self.normal_button.click()
            else:
                self.maximize_button.click()
        return super().mouseDoubleClickEvent(a0)

    def contextMenuEvent(self, a0: QContextMenuEvent) -> None:
        child = self.childAt(a0.pos())
        if child is not None and isinstance(child, QToolButton):
            return

        menu = QMenu(self)
        menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        menu.addAction("Toggle Fullscreen").triggered.connect(
            self.window().toggle_fullscreen
        )
        menu.exec(a0.globalPos())

    def _window_state_changed(self, state: Qt.WindowState) -> None:
        """Change the buttons when the window state changes

        Parameters
        ----------
        state : Qt.WindowState
            The current state of the window
        """
        if state in (Qt.WindowState.WindowMaximized, Qt.WindowState.WindowFullScreen):
            self.normal_button.show()
            self.maximize_button.hide()
        else:
            self.normal_button.hide()
            self.maximize_button.show()

    def setWindowTitle(self, title: str) -> None:
        self._title_widget.setText(title)

    def button_at(self, pos: QPointF) -> QToolButton | None:
        widget = self.childAt(pos)
        if isinstance(widget, QToolButton):
            return widget
        return None

    def insert_button(self, button: QToolButton, *, index: int = -1) -> None:
        layout = self.layout()
        if index < 0:
            index = layout.indexOf(self._title_widget)
        layout.insertWidget(index, button)
