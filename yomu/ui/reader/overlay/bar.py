from __future__ import annotations

import os
from abc import ABC, ABCMeta, abstractmethod
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QObject, QSignalBlocker, QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider

from yomu.core import utils

from . import OverlayWidgetMixin

if TYPE_CHECKING:
    from .. import Reader
    from .core import Overlay


class BarMeta(type(QFrame), ABCMeta): ...


class BaseBar(OverlayWidgetMixin, QFrame, ABC, metaclass=BarMeta):
    def __init__(self, parent: Overlay) -> None:
        super().__init__(parent)
        self.installEventFilter(parent)

        iconPath = os.path.join(utils.resource_path(), "icons")

        self.previous_button = QPushButton(self)
        self.previous_button.setIcon(
            QIcon(QPixmap(os.path.join(iconPath, "previous.svg")))
        )
        self.previous_button.setToolTip("Previous Chapter")
        self.previous_button.installEventFilter(self)
        self.previous_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.next_button = QPushButton(self)
        self.next_button.setIcon(QIcon(QPixmap(os.path.join(iconPath, "next.svg"))))
        self.next_button.setToolTip("Next Chapter")
        self.next_button.installEventFilter(self)
        self.next_button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.previous_button)
        layout.addWidget(self.next_button)
        self.setLayout(layout)

    parent: Callable[[], Overlay]
    layout: Callable[[], QHBoxLayout]

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if isinstance(a0, QPushButton):
            if a1.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
                return True
            if a1.type() == QEvent.Type.MouseButtonRelease:
                a1.accept()
                return True
        return super().eventFilter(a0, a1)

    @abstractmethod
    def overlay_resized(self, size: QSize) -> None: ...


class NavigationBar(BaseBar):
    def __init__(self, parent: Reader) -> None:
        super().__init__(parent.overlay)
        self.setFixedHeight(40)

        self.previous_button.pressed.connect(parent.previous_chapter)
        self.next_button.pressed.connect(parent.next_chapter)

        self.title_widget = QLabel(self)
        self.layout().insertWidget(1, self.title_widget)

    def overlay_resized(self, _) -> None:
        self.setFixedWidth(self.parent().width())

    def set_title(self, title: str | None) -> None:
        self.title_widget.setText(title)


class PageSlider(QFrame):
    value_changed = pyqtSignal(int)

    def __init__(self, parent: PageBar) -> None:
        super().__init__(parent)

        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.valueChanged.connect(self._value_changed)
        self.slider.setTickInterval(1)
        self.slider.setMinimum(0)

        self.page_num = QLabel(f"0/0", self)

        layout = QHBoxLayout(self)
        layout.addWidget(self.slider)
        layout.addWidget(self.page_num)
        self.setLayout(layout)

    def set_total_pages(self, a0: int) -> None:
        with QSignalBlocker(self):
            self.slider.setMaximum(a0)
            self.page_num.setText(f"{self.slider.value() + 1}/{a0 + 1}")

    def _value_changed(self, value: int) -> None:
        self.page_num.setText(f"{value + 1}/{self.slider.maximum() + 1}")
        self.value_changed.emit(value)

    def set_value(self, a0: int) -> None:
        with QSignalBlocker(self):
            self.slider.setValue(a0)
            self.page_num.setText(f"{a0 + 1}/{self.slider.maximum() + 1}")

    def previous_page(self) -> None:
        value = self.slider.value() - 1
        if value >= 0:
            self.slider.setValue(value)

    def next_page(self) -> None:
        value = self.slider.value() + 1
        if value <= self.slider.maximum():
            self.slider.setValue(value)

    def reset(self) -> None:
        with QSignalBlocker(self):
            self.slider.setValue(0)
            self.slider.setMaximum(0)
            self.page_num.setText(f"0/0")


class PageBar(BaseBar):
    value_changed = pyqtSignal(int)

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader.overlay)
        self.setFixedHeight(60)

        self.slider_widget = PageSlider(self)
        self.slider_widget.value_changed.connect(self.value_changed.emit)

        self.previous_button.pressed.connect(self.previous_page)
        self.next_button.pressed.connect(self.next_page)

        self.layout().insertWidget(1, self.slider_widget)

    def overlay_resized(self, size: QSize) -> None:
        pos = self.parent().pos()
        x, y = pos.x(), pos.y()

        height = self.height()
        width = int(size.width() * 1136 / 1536)

        x += (size.width() - width) // 2
        y += int(size.height() * 785 / 816) - int(height * 0.9)

        self.setGeometry(x, y, width, height)

    def set_total_pages(self, a0: int) -> None:
        self.slider_widget.set_total_pages(a0)

    def set_value(self, a0: int) -> None:
        self.slider_widget.set_value(a0)

    def previous_page(self) -> None:
        self.slider_widget.previous_page()

    def next_page(self) -> None:
        self.slider_widget.next_page()

    def reset(self) -> None:
        self.slider_widget.reset()
