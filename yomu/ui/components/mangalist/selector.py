from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, Qt
from PyQt6.QtGui import QKeyEvent, QEnterEvent, QHoverEvent, QMouseEvent

if TYPE_CHECKING:
    from .core import MangaList


class MangaSelector(QObject):
    def __init__(self, manga_list: MangaList) -> None:
        super().__init__(manga_list)
        self.manga_list = manga_list
        self.cursor = -1

        manga_list.installEventFilter(self)
        manga_list.view_removed.connect(self._offset_cursor)

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
            self.move_cursor_left()
        if key == Qt.Key.Key_Right:
            self.move_cursor_right()
        if key == Qt.Key.Key_Escape:
            self.clear_selected()

        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if view := self.manga_list.manga_view_at(self.cursor):
                mouse_event = QMouseEvent(
                    QEvent.Type.MouseButtonRelease,
                    view.geometry().center().toPointF(),
                    Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                QCoreApplication.postEvent(view, mouse_event)
        return False

    def _offset_cursor(self, index: int, _) -> None:
        if index <= self.cursor:
            self.cursor -= 1

    def move_cursor_up(self) -> None:
        self.set_selected(self.cursor, False)
        if self.cursor == -1:
            self.cursor = self.manga_list.count - 1
            return self.set_selected(self.cursor, True)

        layout = self.manga_list.layout()
        row = int(layout.row_count * self.cursor / self.manga_list.count) - 1
        if row >= layout.row_count or row < 0:
            row = 0
        offset = layout.col_counts[row]

        self.cursor = (
            self.manga_list.count + self.cursor - offset
            if self.cursor - offset < 0
            else self.cursor - offset
        )

        self.set_selected(self.cursor, True)

    def move_cursor_down(self) -> None:
        self.set_selected(self.cursor, False)
        if self.cursor == -1:
            self.cursor = 0
            return self.set_selected(self.cursor, True)

        layout = self.manga_list.layout()
        row = int(layout.row_count * self.cursor / self.manga_list.count) - 1
        if row >= layout.row_count or row < 0:
            row = 0
        offset = layout.col_counts[row]

        self.cursor = (
            offset - (self.manga_list.count - self.cursor)
            if self.cursor + offset >= self.manga_list.count
            else self.cursor + offset
        )

        self.set_selected(self.cursor, True)

    def move_cursor_left(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = (
            self.cursor - 1 if self.cursor - 1 >= 0 else self.manga_list.count - 1
        )
        self.set_selected(self.cursor, True)

    def move_cursor_right(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = self.cursor + 1 if self.cursor + 1 < self.manga_list.count else 0
        self.set_selected(self.cursor, True)

    def set_selected(self, index: int, selected: bool) -> None:
        if (view := self.manga_list.manga_view_at(index)) is None:
            return

        if view.visibleRegion().isNull():
            self.manga_list.verticalScrollBar().setValue(view.y())

        window = self.manga_list.window()
        center = view.geometry().center().toPointF()
        if selected:
            QCoreApplication.postEvent(
                view,
                QEnterEvent(
                    window.mapFromGlobal(center), window.pos().toPointF(), center
                ),
            )
            QCoreApplication.postEvent(
                view, QHoverEvent(QEvent.Type.HoverEnter, center, center)
            )
        else:
            QCoreApplication.postEvent(view, QEvent(QEvent.Type.Leave))
            QCoreApplication.postEvent(
                view, QHoverEvent(QEvent.Type.HoverLeave, center, center)
            )

    def clear_selected(self) -> None:
        self.set_selected(self.cursor, False)
        self.cursor = -1
