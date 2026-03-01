from typing import TYPE_CHECKING

from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtGui import QEnterEvent, QHoverEvent, QKeyEvent
from PyQt6.QtWidgets import QInputDialog

if TYPE_CHECKING:
    from . import MangaList, MangaView


class Find(QInputDialog):
    def __init__(self, manga_list: MangaList) -> None:
        super().__init__(manga_list)
        self.manga_list = manga_list
        self._current_index = -1
        self._text = ""

        self.setWindowTitle("Find")
        self.setOption(QInputDialog.InputDialogOption.NoButtons)
        self.setLabelText("Name to search")
        self.setInputMode(QInputDialog.InputMode.TextInput)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.find(self.textValue())
        return super().keyPressEvent(a0)

    def search_for(self, name: str, start: int, end: int) -> bool:
        for i in range(start, end):
            view = self.manga_list.manga_view_at(i)
            if view is not None and not view.isHidden():
                index = view.manga.title.lower().find(name)
                if index != -1:
                    self.setLabelText(f"Found Manga")
                    self.set_selected(view, True)
                    self._current_index = i
                    return True
        return False

    def find(self, name: str) -> None:
        previous_text = self._text
        self._text = name

        if self._current_index > -1:
            view = self.manga_list.manga_view_at(self._current_index)
            if view is not None:
                self.set_selected(view, False)

        if not name:
            self._current_index = -1
            self.manga_list.verticalScrollBar().setValue(0)
            return self.setLabelText("Name to search")

        name = name.lower()
        start = self._current_index + 1 if previous_text == name else 0

        if not self.search_for(
            name, start, self.manga_list.count
        ) and not self.search_for(name, 0, start):
            self._current_index = -1
            self.manga_list.verticalScrollBar().setValue(0)
            self.setLabelText("No manga found")

    def set_selected(self, view: MangaView, selected: bool) -> None:
        self.manga_list.verticalScrollBar().setValue(view.y())

        center = view.geometry().center().toPointF()
        if selected:
            window = self.manga_list.window()
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
