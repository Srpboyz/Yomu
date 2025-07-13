from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QPropertyAnimation, QSize, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QFrame, QWidget


class OverlayWidgetMixin:
    def event(self, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            return True
        return super().event(event)

    def overlay_resized(self, size: QSize) -> None: ...


if TYPE_CHECKING:

    class OverlayWidget(QWidget, OverlayWidgetMixin): ...


class Overlay(QFrame):
    resized = pyqtSignal(QSize)

    class State(IntEnum):
        SHOWN, ANIMATING, HIDDEN = range(3)

    def __init__(self, parent: QFrame):
        super().__init__(parent)
        self._state = Overlay.State.SHOWN

        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)

        self._animation = QPropertyAnimation(effect, b"opacity", self)
        self._animation.setDuration(500)
        self._animation.setStartValue(0)
        self._animation.setEndValue(1)
        self._animation.finished.connect(self._animation_finished)

    @property
    def state(self) -> State:
        return self._state

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.resized.emit(a0.size())

    def _animation_finished(self) -> None:
        shown = bool(self._animation.currentValue())
        self._state = Overlay.State.SHOWN if shown else Overlay.State.HIDDEN
        self.setEnabled(shown)

    def add_overlay(self, widget: OverlayWidget) -> None:
        if isinstance(widget, OverlayWidgetMixin) and isinstance(widget, QWidget):
            widget.setParent(self)
            self.resized.connect(widget.overlay_resized)

    def isHidden(self) -> bool:
        return self.state == Overlay.State.HIDDEN

    def show(self) -> None:
        if self.state != Overlay.State.HIDDEN:
            return

        self._state = Overlay.State.ANIMATING
        self._animation.setDirection(QPropertyAnimation.Direction.Forward)
        self._animation.start()

    def hide(self) -> None:
        if self.state != Overlay.State.SHOWN:
            return

        self._state = Overlay.State.ANIMATING
        self._animation.setDirection(QPropertyAnimation.Direction.Backward)
        self._animation.start()
