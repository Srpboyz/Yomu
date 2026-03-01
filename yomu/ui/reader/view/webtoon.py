from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QPoint, QSizeF, Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from yomu.ui.reader.page import PageView

from .base import BaseView

if TYPE_CHECKING:
    from yomu.ui.reader import Reader


class WebtoonPage(QWidget):
    def __init__(self, parent: WebtoonView, page: PageView):
        super().__init__(parent)
        self.page_view = page
        self.scale = 1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page)
        self.setLayout(layout)

        page.status_changed.connect(self._status_changed)
        self._status_changed(page.status)

    def _status_changed(self, status: PageView.Status) -> None:
        if status in (PageView.Status.NULL, PageView.Status.LOADING):
            size = (QSizeF(922, 922) * self.scale).toSize()
            return self.setFixedSize(size)
        if status == PageView.Status.LOADED:
            size = self.page_view.pixmap().size()

            height = 922 * size.height() / size.width()
            new_size = QSizeF(922, height).toSize()

            self.setFixedSize(new_size * self.scale)

    def scale_page(self, factor: float) -> None:
        self.setFixedSize(self.size() * factor)
        self.scale *= factor


class WebtoonView(BaseView):
    name = "Webtoon"
    supports_zoom = True

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        self._loading = True
        self.scale_factor = 1

        scrollbar = reader.verticalScrollBar()
        scrollbar.valueChanged.connect(self.mark_chapter_as_read)
        scrollbar.valueChanged.connect(self._set_surrent_page)

        self.zoomed.connect(self._set_surrent_page)
        self.page_changed.connect(self._set_surrent_page)

    layout: Callable[[], QVBoxLayout]

    def set_current_index(self, page: int) -> None:
        super().set_current_index(page)
        if page > -1:
            scrollbar = self.reader.verticalScrollBar()
            widget = self.layout().itemAt(page).widget()
            if not (widget.y() < scrollbar.value() < (widget.y() + widget.height())):
                scrollbar.setValue(widget.y())

    def _set_surrent_page(self) -> None:
        layout = self.layout()
        if not layout.count() or self.current_index < 0:
            return

        current_page: PageView = layout.itemAt(self.current_index).widget()
        for i in range(layout.count()):
            widget: PageView = layout.itemAt(i).widget()
            if (
                not widget.visibleRegion().isEmpty()
                and self.current_index != i
                and current_page.visibleRegion().isEmpty()
            ):
                self.current_index = i
                break

    def set_page_views(self, views: list[PageView]) -> None:
        self._loading = True

        layout = self.layout()
        for view in views:
            webtoon_page = WebtoonPage(self, view)
            layout.addWidget(webtoon_page)

        self._loading = False
        self.scale_pages(self.scale_factor)

    def scale_pages(self, scaleFactor: float) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            layout.itemAt(i).widget().scale_page(scaleFactor)

    def page_at(self, pos: QPoint) -> PageView | None:
        pos, layout = self.mapFromParent(pos), self.layout()
        for i in range(layout.count()):
            page_widget: WebtoonPage = layout.itemAt(i).widget()
            if page_widget.geometry().contains(pos):
                return page_widget.page_view

    def zoom_out(self):
        factor = 0.8
        if self.scale_factor <= factor**5:
            return

        scrollbar = self.reader.verticalScrollBar()
        value = int(scrollbar.value() / 1.25)

        self.scale_pages(factor)
        self.scale_factor *= factor
        scrollbar.setValue(value)

        self.zoomed.emit()

    def zoom_in(self) -> None:
        factor = 1.25
        if self.scale_factor >= factor**5:
            return

        scrollbar = self.reader.verticalScrollBar()
        value = int(scrollbar.value() * 1.25)

        self.scale_pages(factor)
        self.scale_factor *= factor
        scrollbar.setValue(value)

        self.zoomed.emit()

    def mark_chapter_as_read(self) -> None:
        scrollBar = self.reader.verticalScrollBar()
        if not self._loading and (
            self.current_index == self.page_count - 1
            or scrollBar.value() == scrollBar.maximum()
        ):
            self.reader.mark_chapter_as_read()

    def clear(self) -> None:
        self._loading = True

        layout = self.layout()
        while layout.count():
            layout.takeAt(0).widget().deleteLater()
        self._current_index = -1
