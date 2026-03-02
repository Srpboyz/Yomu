from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QPoint, QRect, Qt
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from yomu.ui.components.iterator import LayoutIterator
from yomu.ui.reader.page import PageView
from .base import BaseView

if TYPE_CHECKING:
    from yomu.ui.reader import Reader


class HorizontalPage(QWidget):
    def __init__(self, parent: HorizontalView, page: PageView):
        super().__init__(parent)
        self.page_view = page

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page)
        self.setLayout(layout)

    @property
    def status(self) -> PageView.Status:
        return self.page_view.status

    @property
    def aspect_ratio(self) -> float:
        if self.status != PageView.Status.LOADED:
            return 1.0
        size = self.page_view.pixmap().size()
        return size.width() / size.height()


class HorizontalLayout(QHBoxLayout):
    def setGeometry(self, a0: QRect) -> None:
        left, height = 0, self.parentWidget().height()
        for i in range(self.count()):
            page: HorizontalPage = self.itemAt(i).widget()
            width = round(height * page.aspect_ratio)
            page.setGeometry(left, 0, width, height)
            left += width
        self.parentWidget().setFixedWidth(left)


class HorizontalView(BaseView, LayoutIterator[HorizontalPage]):
    name = "Horizontal"

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader)
        layout = HorizontalLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.setSpacing(0)
        self.setLayout(layout)

        reader.installEventFilter(self)
        scrollbar = reader.horizontalScrollBar()
        scrollbar.rangeChanged.disconnect(reader._range_changed)
        scrollbar.valueChanged.connect(self.scrollbar_value_changed)
        self.setFixedHeight(
            reader.height() - (scrollbar.height() if scrollbar.isVisible() else 0)
        )

    def eventFilter(self, a0: QWidget, a1: QEvent) -> bool:
        if a0 == self.reader and a1.type() == QEvent.Type.Resize:
            scrollbar = a0.horizontalScrollBar()
            value = scrollbar.value()
            new_height = a1.size().height()
            self.setFixedHeight(
                new_height - (scrollbar.height() if scrollbar.isVisible() else 0)
            )
            scrollbar.setValue(round(value * new_height / a1.oldSize().height()))
        return super().eventFilter(a0, a1)

    def scrollbar_value_changed(self) -> None:
        layout = self.layout()
        if not layout.count() or self.current_index < 0:
            return

        current_page: HorizontalPage = layout.itemAt(self.current_index).widget()
        for i in range(layout.count()):
            widget: HorizontalPage = layout.itemAt(i).widget()
            if (
                not widget.visibleRegion().isEmpty()
                and self.current_index != i
                and current_page.visibleRegion().isEmpty()
            ):
                self.current_index = i
                break

        scrollBar = self.reader.horizontalScrollBar()
        if (
            self.current_index == self.page_count - 1
            or scrollBar.value() == scrollBar.maximum()
        ):
            self.reader.mark_chapter_as_read()

    def set_current_index(self, page: int) -> None:
        super().set_current_index(page)
        if page > -1:
            scrollbar = self.reader.horizontalScrollBar()
            widget = self.layout().itemAt(page).widget()
            if not (widget.x() < scrollbar.value() < (widget.x() + widget.width())):
                scrollbar.setValue(widget.x())

    def set_page_views(self, views: list[PageView]) -> None:
        layout = self.layout()
        for view in views:
            layout.addWidget(HorizontalPage(self, view))

    def clear(self) -> None:
        layout = self.layout()
        while layout.count():
            layout.takeAt(0).widget().deleteLater()

    def page_at(self, pos: QPoint) -> PageView | None:
        pos = self.mapFromParent(pos)
        for page_widget in self:
            if page_widget.geometry().contains(pos):
                return page_widget.page_view

    def unload(self) -> None:
        reader = self.reader
        reader.horizontalScrollBar().rangeChanged.connect(reader._range_changed)
