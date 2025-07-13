from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .carditem import BaseCardItem

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


class VerticalBoxLayout(QVBoxLayout):
    def widgetAt(self, index: int) -> BaseCardItem | None:
        if (item := self.itemAt(index)) is not None:
            return item.widget()
        return None


class CardList(QScrollArea):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setWidgetResizable(True)
        self.setContentsMargins(0, 0, 0, 0)

        widget = QWidget(self)
        layout = VerticalBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        widget.setLayout(layout)

        pallete = widget.palette()
        pallete.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        widget.setPalette(pallete)

        self.setWidget(widget)

    window: Callable[[], ReaderWindow]
    widget: Callable[[], QWidget]

    def layout(self) -> VerticalBoxLayout:
        return self.widget().layout()

    def add_card(self, card: BaseCardItem) -> None:
        if isinstance(card, BaseCardItem):
            self.layout().addWidget(card)
