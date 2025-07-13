from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QMenu, QWidget

from yomu.core import utils

from .components.cardlist import CardIconItem, CardList
from .stack import StackWidgetMixin

if TYPE_CHECKING:
    from yomu.core.extensionmanager import ExtensionInfo
    from .window import ReaderWindow


class ExtensionItem(CardIconItem):
    def __init__(self, parent: ExtensionList, ext: ExtensionInfo) -> None:
        icon_path = (
            os.path.join(ext.path, ext.icon)
            if ext.icon
            else os.path.join(utils.resource_path(), "icons", "blank.png")
        )

        super().__init__(parent, ext.name, icon_path)
        self.setProperty("extEnabled", ext.enabled)
        self.extId = ext.id

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.Type.DynamicPropertyChange:
            style = self.style()
            for child in self.findChildren(QWidget):
                style.polish(child)
            style.polish(self)
        return super().event(e)

    @property
    def ext_enabled(self) -> bool:
        return self.property("extEnabled")

    def disable(self) -> None:
        self.setProperty("extEnabled", False)


class ExtensionList(CardList, StackWidgetMixin):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self.extension_manager = window.app.extension_manager

        window.app.extension_disabled.connect(self._extension_disabled)
        for ext in self.extension_manager.extensions:
            self.add_card(ExtensionItem(self, ext))

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if isinstance(a0, ExtensionItem):
            if (
                a1.type() == QEvent.Type.MouseButtonRelease
                and a1.button() == Qt.MouseButton.LeftButton
            ):
                self.extension_manager.request_settings(a0.extId, self.window())
            elif a1.type() == QEvent.Type.ContextMenu:
                menu = QMenu(self)
                menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

                enable_action = menu.addAction("Enable")
                disable_action = menu.addAction("Disable")

                if a0.ext_enabled:
                    enable_action.setVisible(False)
                else:
                    disable_action.setVisible(False)

                triggered = menu.exec(a1.globalPos())
                if triggered == enable_action:
                    self.extension_manager.enable_extension(a0.extId)
                elif triggered == disable_action:
                    self.extension_manager.disable_extension(a0.extId)
                return True

        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def _extension_disabled(self, extension: ExtensionInfo) -> None:
        layout = self.layout()
        for i in range(layout.count()):
            item: ExtensionItem = layout.itemAt(i).widget()
            if item.extId == extension.id:
                return item.disable()

    def set_current_widget(self) -> None:
        window = self.window()
        window.setWindowTitle("Extension List")
        window.titlebar.refresh_button.hide()

    def clear_widget(self) -> None:
        self.window().titlebar.refresh_button.show()
