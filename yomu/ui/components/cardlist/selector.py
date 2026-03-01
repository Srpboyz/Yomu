from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PyQt6.QtGui import QEnterEvent, QHoverEvent, QKeyEvent, QMouseEvent
from PyQt6.QtWidgets import QBoxLayout

from .carditem import CardSpacer

if TYPE_CHECKING:
    from .core import CardList


class CardSelector(QObject):
    def __init__(self, card_list: CardList) -> None:
        super().__init__(card_list)
        self.card_list = card_list
        card_list.installEventFilter(self)
        self.cursor = -1

    def eventFilter(self, a0: CardList, a1: QEvent) -> bool:
        if a1.type() == QEvent.Type.KeyPress:
            return self.key_event(a1.clone())
        return super().eventFilter(a0, a1)

    def key_event(self, event: QKeyEvent) -> bool:
        key = event.key()
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Up:
                if (
                    self.card_list.layout().direction()
                    == QBoxLayout.Direction.TopToBottom
                ):
                    self.move_cursor_up()
                else:
                    self.move_cursor_down()
                return True

            if key == Qt.Key.Key_Down:
                if (
                    self.card_list.layout().direction()
                    == QBoxLayout.Direction.TopToBottom
                ):
                    self.move_cursor_down()
                else:
                    self.move_cursor_up()
                return True

        if key == Qt.Key.Key_Left:
            self.move_cursor_up()
        elif key == Qt.Key.Key_Right:
            self.move_cursor_down()
        elif key == Qt.Key.Key_Escape:
            self.clear_selected()

        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if (item := self.card_list.layout().itemAt(self.cursor)) is None:
                return

            card = item.widget()
            mouse_event = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                card.geometry().center().toPointF(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QCoreApplication.postEvent(card, mouse_event)
        return False

    def move_cursor_up(self) -> None:
        self.set_selected(self.cursor, False)
        layout, current_index = self.card_list.layout(), self.cursor
        self.cursor = self.cursor - 1 if self.cursor - 1 >= 0 else layout.count() - 1
        while self.cursor != current_index:
            card = layout.widgetAt(self.cursor)
            if not isinstance(card, CardSpacer):
                return self.set_selected(self.cursor, True)
            self.cursor = (
                self.cursor - 1 if self.cursor - 1 >= 0 else layout.count() - 1
            )

    def move_cursor_down(self) -> None:
        self.set_selected(self.cursor, False)
        layout, current_index = self.card_list.layout(), self.cursor
        self.cursor = self.cursor + 1 if self.cursor + 1 < layout.count() else 0
        while self.cursor != current_index:
            card = layout.widgetAt(self.cursor)
            if not isinstance(card, CardSpacer):
                return self.set_selected(self.cursor, True)
            self.cursor = self.cursor + 1 if self.cursor + 1 < layout.count() else 0

    def set_selected(self, index: int, selected: bool) -> None:
        if (item := self.card_list.layout().itemAt(index)) is None:
            return

        card = item.widget()
        if card.visibleRegion().isNull():
            self.card_list.verticalScrollBar().setValue(card.y())

        window = self.card_list.window()
        center = card.geometry().center().toPointF()
        if selected:
            QCoreApplication.postEvent(
                card,
                QEnterEvent(
                    window.mapFromGlobal(center), window.pos().toPointF(), center
                ),
            )
            QCoreApplication.postEvent(
                card, QHoverEvent(QEvent.Type.HoverEnter, center, center)
            )
        else:
            QCoreApplication.postEvent(card, QEvent(QEvent.Type.Leave))
            QCoreApplication.postEvent(
                card, QHoverEvent(QEvent.Type.HoverLeave, center, center)
            )

    def clear_selected(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = -1
