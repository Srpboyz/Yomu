import os

from PyQt6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QScrollArea

from yomu.core import utils


class AutoScroller(QObject):
    SCROLL_ICON_SIZE = 28
    MAX_SCROLL_SPEED = 1200

    def __init__(self, scrollarea: QScrollArea) -> None:
        super().__init__(scrollarea)
        self.scrollarea = scrollarea

        self.scroll_icon = QLabel(scrollarea)
        self.scroll_icon.setPixmap(
            QPixmap(os.path.join(utils.icon_path(), "scroll.png")).scaled(
                AutoScroller.SCROLL_ICON_SIZE,
                AutoScroller.SCROLL_ICON_SIZE,
                transformMode=Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.scroll_icon.hide()
        self.is_scrolling = False

        scrollarea.installEventFilter(self)
        scrollarea.setMouseTracking(True)

        timer = QTimer(self)
        timer.setInterval(25)
        timer.timeout.connect(self.change_scroll_position)
        timer.start()

    def eventFilter(self, scrollarea: QScrollArea, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease:
            if not self.is_scrolling:
                if event.button() == Qt.MouseButton.MiddleButton:
                    self.display_scroll_icon(event.position().toPoint())
                    self.is_scrolling = True
            else:
                self.scroll_icon.hide()
                self.is_scrolling = False
        elif event.type() in (QEvent.Type.Leave, QEvent.Type.KeyPress):
            self.scroll_icon.hide()
            self.is_scrolling = False

        return super().eventFilter(scrollarea, event)

    def change_scroll_position(self) -> None:
        if not self.is_scrolling:
            return

        original_point = self.scroll_icon.mapToParent(self.scroll_icon.rect().center())
        point = self.scrollarea.mapFromGlobal(self.scrollarea.cursor().pos())

        offset = min(
            round((point.x() - original_point.x()) / 5),
            AutoScroller.MAX_SCROLL_SPEED,
        )
        scrollbar = self.scrollarea.horizontalScrollBar()
        scrollbar.setValue(scrollbar.value() + offset)

        offset = min(
            round((point.y() - original_point.y()) / 5),
            AutoScroller.MAX_SCROLL_SPEED,
        )
        scrollbar = self.scrollarea.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + offset)

    def display_scroll_icon(self, point: QPoint) -> None:
        half_size = round(AutoScroller.SCROLL_ICON_SIZE / 2)
        self.scroll_icon.setGeometry(
            QRect(
                max(0, point.x() - half_size),
                max(0, point.y() - half_size),
                AutoScroller.SCROLL_ICON_SIZE,
                AutoScroller.SCROLL_ICON_SIZE,
            )
        )
        self.scroll_icon.show()
