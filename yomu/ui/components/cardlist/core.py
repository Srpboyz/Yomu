from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from .carditem import BaseCardItem, CardSpacer
from .selector import CardSelector

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow


class VerticalBoxLayout[T: BaseCardItem](QVBoxLayout):
    def widgetAt(self, index: int) -> T | None:
        if (item := self.itemAt(index)) is not None:
            return item.widget()
        return None

    def addWidget(
        self, a0: T, stretch: int = 0, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag(0)
    ) -> None:
        return super().addWidget(a0, stretch, alignment)

    def insertWidget(
        self,
        index: int,
        widget: T,
        stretch: int = 0,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag(0),
    ) -> None:
        return super().insertWidget(index, widget, stretch, alignment)

    def removeWidget(self, w: T) -> None:
        return super().removeWidget(w)


class CardList[T: BaseCardItem = BaseCardItem](QScrollArea):
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

        self.selector = CardSelector(self)

    window: Callable[[], ReaderWindow]
    widget: Callable[[], QWidget]

    def layout(self) -> VerticalBoxLayout[T]:
        return self.widget().layout()

    def add_card(self, card: T) -> None:
        if isinstance(card, BaseCardItem):
            self.layout().addWidget(card)

    def insert_card(self, index: int, card: T) -> None:
        if isinstance(card, BaseCardItem):
            self.layout().insertWidget(index, card)

    def remove_card(self, card: BaseCardItem) -> None:
        self.layout().removeWidget(card)

    def add_spacer(self, text: str = "") -> None:
        self.layout().addWidget(CardSpacer(self, text))

    def insert_spacer(self, index: int, text: str = "") -> None:
        self.layout().insertWidget(index, CardSpacer(self, text))
