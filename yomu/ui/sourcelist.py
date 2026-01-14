from __future__ import annotations

import inspect
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PyQt6.QtGui import QEnterEvent, QHoverEvent, QMouseEvent

from yomu.source import Source
from .components.cardlist import CardIconItem, CardList
from .stack import StackWidgetMixin

if TYPE_CHECKING:
    from .window import ReaderWindow
    from .components.mangalist import MangaList


class SourceItem(CardIconItem):
    def __init__(self, parent: SourceList, source: Source) -> None:
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(inspect.getfile(source.__class__))),
            "icon.ico",
        )

        super().__init__(parent, source.name, icon_path)
        self.source = source


class SourceList(CardList, StackWidgetMixin):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        for source in sorted(
            window.app.source_manager.sources, key=lambda source: source.name
        ):
            self.add_card(SourceItem(self, source))
        self.selector = SourceSelector(self)

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if (
            isinstance(a0, SourceItem)
            and a1.type() == QEvent.Type.MouseButtonRelease
            and a1.button() == Qt.MouseButton.LeftButton
        ):
            self.window().sourcepage.source = a0.source
        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def set_current_widget(self) -> None:
        window = self.window()
        window.titlebar.refresh_button.hide()

        if window.network.is_online:
            return window.setWindowTitle("Source List")

        window.display_message(
            "You are currently offline. Please connect to the internet to utilize sources."
        )
        window.current_widget = window.library

    def clear_widget(self) -> None:
        self.window().titlebar.refresh_button.show()


class SourceSelector(QObject):
    def __init__(self, source_list: SourceList) -> None:
        super().__init__(source_list)
        self.source_list = source_list
        self.cursor = -1
        source_list.installEventFilter(self)

    def eventFilter(self, a0: MangaList, a1: QEvent) -> bool:
        if a1.type() == QEvent.Type.KeyPress:
            return self.key_event(a1.clone())
        return super().eventFilter(a0, a1)

    def key_event(self, event: QKeyEvent) -> None:
        key = event.key()
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Up:
                self.move_cursor_up()
                return True

            if key == Qt.Key.Key_Down:
                self.move_cursor_down()
                return True

        if key == Qt.Key.Key_Left:
            self.move_cursor_up()
        elif key == Qt.Key.Key_Right:
            self.move_cursor_down()
        elif key == Qt.Key.Key_Escape:
            self.clear_selected()

        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if (item := self.source_list.layout().itemAt(self.cursor)) is None:
                return

            source_card = item.widget()
            mouse_event = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                source_card.geometry().center().toPointF(),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QCoreApplication.postEvent(source_card, mouse_event)
        return False

    def move_cursor_up(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = (
            self.cursor - 1
            if self.cursor - 1 >= 0
            else self.source_list.layout().count() - 1
        )
        self.set_selected(self.cursor, True)

    def move_cursor_down(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = (
            self.cursor + 1
            if self.cursor + 1 < self.source_list.layout().count()
            else 0
        )
        self.set_selected(self.cursor, True)

    def set_selected(self, index: int, selected: bool) -> None:
        if (item := self.source_list.layout().itemAt(index)) is None:
            return
        source_card = item.widget()

        if source_card.visibleRegion().isNull():
            self.source_list.verticalScrollBar().setValue(source_card.y())

        window = self.source_list.window()
        center = source_card.geometry().center().toPointF()
        if selected:
            QCoreApplication.postEvent(
                source_card,
                QEnterEvent(
                    window.mapFromGlobal(center), window.pos().toPointF(), center
                ),
            )
            QCoreApplication.postEvent(
                source_card, QHoverEvent(QEvent.Type.HoverEnter, center, center)
            )
        else:
            QCoreApplication.postEvent(source_card, QEvent(QEvent.Type.Leave))
            QCoreApplication.postEvent(
                source_card, QHoverEvent(QEvent.Type.HoverLeave, center, center)
            )

    def clear_selected(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = -1
