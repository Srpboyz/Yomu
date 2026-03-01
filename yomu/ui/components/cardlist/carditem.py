from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel


if TYPE_CHECKING:
    from .core import CardList


class BaseCardItem(QFrame):
    def __init__(self, parent: CardList) -> None:
        super().__init__(parent)


class CardItem(BaseCardItem):
    def __init__(self, parent: CardList, name: str) -> None:
        super().__init__(parent)
        self.installEventFilter(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.name_widget = QLabel(name, self)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.name_widget)
        self.setLayout(layout)

    layout: Callable[[], QHBoxLayout]


class CardIconItem(CardItem):
    def __init__(self, parent: CardList, name: str, icon_path: str) -> None:
        super().__init__(parent, name)

        self.icon_widget = QLabel(self)
        self.icon_widget.setPixmap(
            QPixmap(icon_path).scaled(
                32, 32, transformMode=Qt.TransformationMode.SmoothTransformation
            )
        )

        self.layout().insertWidget(0, self.icon_widget)


class CardSpacer(BaseCardItem):
    def __init__(self, parent: CardList, text: str = "") -> None:
        super().__init__(parent)

        self.text_widget = QLabel(text, self)
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_widget)
        self.setLayout(layout)
