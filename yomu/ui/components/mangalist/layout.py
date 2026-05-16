from PyQt6.QtCore import QPoint, QRect, QSize
from PyQt6.QtWidgets import QLayout, QLayoutItem, QWidget, QWidgetItem


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []

        self.row_count = 0
        self.col_counts = []

        self.horizontal_spacing = 0
        self.vertical_spacing = 0

        self.setContentsMargins(*(0 for _ in range(4)))
        self.setSpacing(5, 10)

    def __del__(self) -> None:
        while self.takeAt(0):
            ...

    @property
    def spacing(self) -> tuple[int, int]:
        return self.horizontal_spacing, self.vertical_spacing

    def setSpacing(self, horizontal: int, vertical: int) -> None:
        self.horizontal_spacing = horizontal
        self.vertical_spacing = vertical

    def count(self, *, include_hidden: bool = True) -> int:
        return len(
            self._items
            if include_hidden
            else tuple(filter(lambda item: item.widget().isVisible(), self._items))
        )

    def itemAt(self, index: int, *, include_hidden: bool = True) -> QLayoutItem | None:
        items = (
            self._items
            if include_hidden
            else tuple(filter(lambda item: item.widget().isVisible(), self._items))
        )
        if index >= 0 and index < len(items):
            return items[index]

    def addItem(self, a0: QLayoutItem) -> None:
        self._items.append(a0)

    def insertItem(self, index: int, a0: QLayoutItem) -> None:
        self._items.insert(index, a0)

    def takeAt(self, index: int) -> QLayoutItem | None:
        if index >= 0 and index < self.count(include_hidden=True):
            return self._items.pop(index)
        return None

    def insertWidget(self, index: int, widget: QWidget) -> None:
        self.addChildWidget(widget)
        self.insertItem(index, QWidgetItem(widget))

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self.__doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self.__doLayout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())

        margin = self.contentsMargins()

        size += QSize(2 * margin.left(), 2 * margin.top())
        return size

    def __doLayout(self, rect: QRect, testOnly: bool) -> int:
        x, y = rect.x(), rect.y()
        space_x, spaceY = self.horizontal_spacing, self.vertical_spacing
        line_height = 0
        items: list[list[QLayoutItem]] = []
        subitems: list[QLayoutItem] = []

        for item in self._items:
            if item.widget().isHidden():
                continue

            nextX = x + item.sizeHint().width() + space_x
            if nextX - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + spaceY
                nextX = x + item.sizeHint().width() + space_x
                line_height = 0
                items.append(subitems)
                subitems = []

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                subitems.append(item)

            x = nextX
            line_height = max(line_height, item.sizeHint().height())
        items.append(subitems)

        width = self.parentWidget().width()
        for subitems in items:
            if not subitems:
                continue

            size = (
                sum(item.geometry().width() for item in subitems)
                + (len(subitems) - 1) * space_x
            )

            newSize = (width - size) // 2
            if newSize > space_x:
                for item in subitems:
                    geometry = item.geometry()
                    x = geometry.x() + newSize
                    item.setGeometry(QRect(QPoint(x, geometry.y()), item.sizeHint()))

        if not testOnly:
            self.row_count = len(items)
            self.col_counts = [len(row) for row in items]

        return y + line_height - rect.y()

    def clear(self) -> None:
        while self._items:
            self._items.pop().widget().deleteLater()
