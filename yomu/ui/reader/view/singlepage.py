from enum import IntEnum
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSignalBlocker,
    QSize,
)
from PyQt6.QtWidgets import QMenu, QHBoxLayout, QStackedLayout, QWidget

from yomu.core import utils as core_utils
from yomu.ui.reader.page import PageView

from .base import BaseView

if TYPE_CHECKING:
    from yomu.ui.reader import Reader


class AnimationDirection(IntEnum):
    LEFT_TO_RIGHT, RIGHT_TO_LEFT = range(2)


class FitDirection(IntEnum):
    Height, Width = range(2)


class AnimationGroup(QParallelAnimationGroup):
    def stop(self) -> None:
        self.finished.emit()
        return super().stop()


class PageWidget(QWidget):
    def __init__(self, parent: SinglePageView, page_view: PageView) -> None:
        super().__init__(parent)
        self.page_view = page_view

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(page_view)
        self.setLayout(layout)

    @property
    def page_status(self) -> PageView.Status:
        return self.page_view.status

    def image_size(self) -> QSize:
        return self.page_view.pixmap().size()


class StackLayout(QStackedLayout):
    def __init__(
        self, view: SinglePageView, animation_direction: AnimationDirection
    ) -> None:
        super().__init__(view)
        self.reader = view.reader
        self.direction = FitDirection.Height
        self.animation_direction = animation_direction
        self._animation = None

        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(0)

    currentWidget: Callable[[], PageWidget | None]

    def page_widget_at(self, index: int) -> PageWidget | None:
        if (item := self.itemAt(index)) is not None:
            return item.widget()
        return None

    def fit_to_width(self, image_size: QSize) -> QRect:
        reader_size = self.reader.size()

        width = reader_size.width()
        height = round(width * image_size.height() / image_size.width())

        if reader_size.height() > height:
            y = round((reader_size.height() - height) / 2)
            return QRect(0, y, width, height)
        return QRect(0, 0, width, height)

    def fit_to_height(self, image_size: QSize) -> QRect:
        reader_size = self.reader.size()

        width = round(reader_size.height() * (image_size.width() / image_size.height()))
        height = reader_size.height()

        if reader_size.width() > width:
            x = round((reader_size.width() - width) / 2)
            return QRect(x, 0, width, height)
        return QRect(0, 0, width, height)

    def calculate_target_geometry(self, widget: PageWidget) -> QRect:
        if widget.page_status == PageView.Status.LOADED:
            image_size = widget.image_size()
            if self.direction == FitDirection.Width:
                return self.fit_to_width(image_size)
            else:
                return self.fit_to_height(image_size)
        return QRect(QPoint(0, 0), self.reader.size())

    def _slide_to_widget(self, index: int) -> None:
        if self._animation:
            self._animation.stop()

        current_index = self.currentIndex()
        if current_index == index:
            return QStackedLayout.setCurrentIndex(self, index)

        is_next_page = index > current_index
        animation_direction = (
            is_next_page
            and self.animation_direction == AnimationDirection.LEFT_TO_RIGHT
        ) or (
            not is_next_page
            and self.animation_direction == AnimationDirection.RIGHT_TO_LEFT
        )

        current_page = self.currentWidget()
        new_page = self.page_widget_at(index)

        reader_width = self.reader.width()

        current_page_animation = QPropertyAnimation(current_page, b"geometry")
        current_page_animation.setDuration(300)
        current_page_animation.setEasingCurve(QEasingCurve.Type.Linear)
        current_page_animation.setStartValue(current_page.geometry())
        current_page_animation.setEndValue(
            QRect(
                -current_page.width() if animation_direction else reader_width,
                current_page.y(),
                current_page.width(),
                current_page.height(),
            )
        )

        new_page_geometry = self.calculate_target_geometry(new_page)
        new_page_animation = QPropertyAnimation(new_page, b"geometry")
        new_page_animation.setDuration(300)
        new_page_animation.setEasingCurve(QEasingCurve.Type.Linear)
        new_page_animation.setStartValue(
            QRect(
                reader_width if animation_direction else -new_page_geometry.width(),
                new_page_geometry.y(),
                new_page_geometry.width(),
                new_page_geometry.height(),
            )
        )
        new_page_animation.setEndValue(new_page_geometry)

        self._animation = AnimationGroup(self)
        self._animation.addAnimation(current_page_animation)
        self._animation.addAnimation(new_page_animation)

        def on_animation_finished():
            QStackedLayout.setCurrentIndex(self, index)
            self._animation = None

        new_page.show()
        self._animation.finished.connect(on_animation_finished)
        self._animation.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)

    def setCurrentIndex(self, index: int) -> None:
        self._slide_to_widget(index)

    def setCurrentWidget(self, w: QWidget | None) -> None:
        index = self.indexOf(w)
        if index != -1:
            self._slide_to_widget(index)

    def setGeometry(self, rect: QRect) -> None:
        current_widget = self.currentWidget()
        view: SinglePageView = self.parentWidget()
        if current_widget is not None:
            if current_widget.page_status == PageView.Status.LOADED:
                image_size = current_widget.image_size()
                if self.direction == FitDirection.Width:
                    rect = self.fit_to_width(image_size)
                    view.setFixedSize(
                        self.reader.size()
                        if self.reader.height() > rect.height()
                        else rect.size()
                    )
                else:
                    rect = self.fit_to_height(image_size)
                    view.setFixedSize(
                        self.reader.size()
                        if self.reader.width() > rect.width()
                        else rect.size()
                    )
            else:
                rect = QRect(QPoint(0, 0), self.reader.size())
                view.setFixedSize(self.reader.size())
        else:
            view.setFixedSize(self.reader.size())
        super().setGeometry(rect)


class SinglePageView(BaseView):
    name = "Single Page (Left-To-Right)"
    animation_direction = AnimationDirection.LEFT_TO_RIGHT

    def __init__(self, reader: Reader) -> None:
        super().__init__(reader)
        self.setLayout(StackLayout(self, self.animation_direction))
        reader.installEventFilter(self)

        self.addAction("Change Fit Direction").triggered.connect(self.change_direction)
        self.window().app.keybinds_changed.connect(self.set_keybinds)
        self.set_keybinds(core_utils.get_keybinds())

    layout: Callable[[], StackLayout]

    def eventFilter(self, a0: QWidget, a1: QEvent) -> bool:
        if a0 == self.reader and a1.type() == QEvent.Type.Resize:
            self.layout().update()
        return super().eventFilter(a0, a1)

    def set_current_index(self, page: int) -> None:
        super().set_current_index(page)
        if page > -1:
            self.layout().setCurrentIndex(page)
            self.reader.verticalScrollBar().setValue(0)
            if self.page_count > 0 and page == self.page_count - 1:
                self.reader.mark_chapter_as_read()

    def set_page_views(self, views: list[PageView]) -> None:
        layout = self.layout()
        with QSignalBlocker(self):
            for view in views:
                layout.addWidget(PageWidget(self, view))

    def context_menu(self) -> QMenu:
        menu = QMenu()
        menu.addAction("Change Fit Direction").triggered.connect(self.change_direction)
        return menu

    def change_direction(self):
        layout = self.layout()
        layout.direction = (
            FitDirection.Height
            if layout.direction == FitDirection.Width
            else FitDirection.Width
        )
        layout.update()

    def set_keybinds(self, keybinds):
        keybindingData = keybinds.get("Change Fit Direction", {"keybinds": []})
        self.actions()[0].setShortcuts(
            keybindingData["keybinds"] if keybindingData is not None else []
        )

    def page_at(self, pos: QPoint) -> PageView | None:
        page_widget = self.layout().currentWidget()
        if page_widget and page_widget.geometry().contains(self.mapFromParent(pos)):
            return page_widget.page_view

    def clear(self) -> None:
        layout = self.layout()
        with QSignalBlocker(self):
            while layout.count():
                layout.takeAt(0).widget().deleteLater()
        self._current_index = -1


class ReverseSinglePageView(SinglePageView):
    name = "Single Page (Right-To-Left)"
    animation_direction = AnimationDirection.RIGHT_TO_LEFT
