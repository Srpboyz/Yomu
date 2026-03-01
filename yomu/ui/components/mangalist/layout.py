from PyQt6.QtCore import QPoint, QRect, QSize
from PyQt6.QtWidgets import QLayout, QLayoutItem, QWidget, QWidgetItem


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.__itemList: list[QLayoutItem] = []

        self.row_count = 0
        self.col_counts = []

        self.__horizontalSpacing = 0
        self.__verticalSpacing = 0

        self.setContentsMargins(*(0 for _ in range(4)))
        self.setSpacing(5, 10)

    def __del__(self) -> None:
        while self.takeAt(0):
            ...

    @property
    def spacing(self) -> tuple[int, int]:
        return self.horizontalSpacing, self.verticalSpacing

    @property
    def horizontalSpacing(self) -> int:
        return self.__horizontalSpacing

    @property
    def verticalSpacing(self) -> int:
        return self.__verticalSpacing

    def setSpacing(self, horizontal: int, vertical: int) -> None:
        self.__horizontalSpacing = horizontal
        self.__verticalSpacing = vertical

    def count(self) -> int:
        return len(self.__itemList)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if index >= 0 and index < self.count():
            return self.__itemList[index]

    def addItem(self, a0: QLayoutItem | None) -> None:
        self.__itemList.append(a0)

    def insertItem(self, index: int, a0: QLayoutItem | None) -> None:
        self.__itemList.insert(index, a0)

    def takeAt(self, index: int) -> QLayoutItem | None:
        if index >= 0 and index < self.count():
            return self.__itemList.pop(index)

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
        for item in self.__itemList:
            size = size.expandedTo(item.minimumSize())

        margin = self.contentsMargins()

        size += QSize(2 * margin.left(), 2 * margin.top())
        return size

    def __doLayout(self, rect: QRect, testOnly: bool) -> int:
        x, y = rect.x(), rect.y()
        spaceX, spaceY = self.horizontalSpacing, self.verticalSpacing
        lineHeight = 0
        items: list[list[QLayoutItem]] = []
        subitems: list[QLayoutItem] = []

        for item in self.__itemList:
            if item.widget().isHidden():
                continue

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y += lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
                items.append(subitems)
                subitems = []

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                subitems.append(item)

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        items.append(subitems)

        width = self.parentWidget().width()
        for subitems in items:
            if not subitems:
                continue

            size = (
                sum(item.geometry().width() for item in subitems)
                + (len(subitems) - 1) * self.horizontalSpacing
            )

            newSize = (width - size) // 2
            if newSize > self.horizontalSpacing:
                for item in subitems:
                    geometry = item.geometry()
                    x = geometry.x() + newSize
                    item.setGeometry(QRect(QPoint(x, geometry.y()), item.sizeHint()))

        if not testOnly:
            self.row_count = len(items)
            self.col_counts = [len(row) for row in items]

        return y + lineHeight - rect.y()

    def clear(self) -> None:
        while self.count():
            self.takeAt(0).widget().deleteLater()
