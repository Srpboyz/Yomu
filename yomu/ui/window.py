from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QObject, QPointF, Qt
from PyQt6.QtGui import QCloseEvent, QMouseEvent
from PyQt6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from yomu.core import utils
from .downloads import Downloads
from .extensionlist import ExtensionList

from .library import Library
from .mangacard import MangaCard
from .menu import MenuWidget
from .reader import Reader
from .settings import Settings
from .sourcelist import SourceList
from .sourcepage import SourcePage
from .stack import Stack
from .titlebar import TitleBar

if TYPE_CHECKING:
    from logging import Logger
    from yomu.core.app import YomuApp


class ReaderWindow(QWidget):
    activation_changed = pyqtSignal(bool)
    window_state_changed = pyqtSignal(Qt.WindowState)
    current_widget_changed = pyqtSignal(QWidget)
    closed = pyqtSignal()

    def __init__(self, app: YomuApp) -> None:
        super().__init__()
        self._app = app

        self.setWindowFlag(Qt.WindowType.Window)
        self.setProperty("active", True)
        QWidget.setWindowTitle(self, "Yomu")

        self.network = app.network

        self.titlebar = TitleBar(self)
        self.menu = MenuWidget(self)
        self.stack = Stack(self)

        self.library = Library(self)
        self.sourcelist = SourceList(self)
        self.sourcepage = SourcePage(self)
        self.mangacard = MangaCard(self)
        self.reader = Reader(self)
        self.downloads = Downloads(self)
        self.extensionlist = ExtensionList(self)
        self.settings = Settings(self)

        self.menu.add_widget(self.library, "Library")
        self.menu.add_widget(self.sourcelist, "Sources")
        self.menu.add_widget(self.extensionlist, "Extensions")
        self.menu.add_widget(self.downloads, "Downloads")
        self.menu.add_widget(self.settings, "Settings")

        self.stack.add_widget(self.library)
        self.stack.add_widget(self.sourcelist)
        self.stack.add_widget(self.sourcepage)
        self.stack.add_widget(self.mangacard)
        self.stack.add_widget(self.extensionlist)
        self.stack.add_widget(self.downloads)
        self.stack.add_widget(self.reader)
        self.library.set_current_widget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.titlebar)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.resize(self.screen().size() * 0.7)

        self.addAction("Refresh").triggered.connect(self.titlebar.refresh_button.click)

        fullscreen = self.addAction("Toggle Fullscreen")
        fullscreen.triggered.connect(self.toggle_fullscreen)
        app.keybinds_changed.connect(self._set_keybinds)
        self._set_keybinds(utils.get_keybinds())
        self.setMouseTracking(True)

        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.windowHandle().installEventFilter(self)

    @property
    def app(self) -> YomuApp:
        return self._app

    application = app

    @property
    def logger(self) -> Logger:
        return self.app.logger

    @property
    def current_widget(self) -> QWidget:
        return self.stack.current_widget

    @current_widget.setter
    def current_widget(self, widget: QWidget):
        return self.stack.set_current_widget(widget)

    @staticmethod
    def find(winId: int) -> ReaderWindow | None:
        widget = QWidget.find(winId)
        return widget if isinstance(widget, ReaderWindow) else None

    def _set_keybinds(self, keybinds):
        for action in self.actions():
            keybindingData = keybinds.get(action.text(), {"keybinds": []})
            action.setShortcuts(
                keybindingData["keybinds"] if keybindingData is not None else []
            )

    def event(self, a0: QEvent) -> bool:
        if a0.type() == QEvent.Type.DynamicPropertyChange:
            style = self.style()
            style.polish(self)
            for child in self.findChildren(
                QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
            ):
                style.polish(child)
        return super().event(a0)

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if a0 == self.windowHandle():
            self.windowHandleEvent(a1)
        return super().eventFilter(a0, a1)

    def changeEvent(self, a0: QEvent) -> None:
        """Overridden to emit :attr:`Window.windowStateChanged`"""
        if a0.type() == QEvent.Type.ActivationChange:
            is_active = self.isActiveWindow()
            self.setProperty("active", is_active)
            self.activation_changed.emit(is_active)
            self.current_widget.setFocus()
        elif a0.type() == QEvent.Type.WindowStateChange:
            state = self.windowState()
            (
                self.titlebar.hide()
                if state == Qt.WindowState.WindowFullScreen
                else self.titlebar.show()
            )
            self.window_state_changed.emit(state)
        return super().changeEvent(a0)

    def windowHandleEvent(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseMove and self.isFullScreen():
            (
                self.titlebar.show()
                if event.position().y() <= 8
                or self.titlebar.underMouse()
                or self.menu.underMouse()
                else self.titlebar.hide()
            )

    def closeEvent(self, a0: QCloseEvent) -> None:
        super().closeEvent(a0)
        self.closed.emit()

    def setWindowTitle(self, title: str) -> None:
        self.titlebar.setWindowTitle(title)

    def isNormal(self) -> bool:
        state = self.windowState() & ~Qt.WindowState.WindowActive
        return state == Qt.WindowState.WindowNoState

    def toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def activateWindow(self) -> None:
        self.show()
        super().activateWindow()

    def display_message(self, message: str) -> None:
        dialog = QMessageBox(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Yomu")
        dialog.setText(message)
        dialog.exec()

    def go_to_previous_page(self) -> None:
        self.stack.previous_widget()


if sys.platform == "win32":
    from ctypes import byref, c_int, Structure, windll
    from win32com.propsys import propsys, pscon  # type: ignore
    from win32com.shell import shell  # type: ignore

    import os
    import pythoncom
    import win32con
    import win32gui

    class MARGINS(Structure):
        _fields_ = [
            ("cxLeftWidth", c_int),
            ("cxRightWidth", c_int),
            ("cyTopHeight", c_int),
            ("cyBottomHeight", c_int),
        ]

    class Win32ReaderWindow(ReaderWindow):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            hwnd = int(self.winId())
            margins = MARGINS(-1, -1, -1, -1)
            dwmapi = windll.LoadLibrary("dwmapi")
            dwmapi.DwmExtendFrameIntoClientArea(hwnd, byref(margins))

            value = (
                win32con.WS_CAPTION
                | win32con.WS_THICKFRAME
                | win32con.CS_DBLCLKS
                | win32con.WS_MINIMIZEBOX
                | win32con.WS_MAXIMIZEBOX
            )
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, value)

    def __create_jumplist():
        jumplist = pythoncom.CoCreateInstance(
            shell.CLSID_DestinationList,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_ICustomDestinationList,
        )

        link = pythoncom.CoCreateInstance(
            shell.CLSID_ShellLink,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IShellLink,
        )

        link.SetPath(sys.executable)
        link.SetArguments(
            " ".join(
                map(
                    lambda arg: '"' + arg.replace('"', '\\"') + '"',
                    ["--new-window"],
                )
            )
        )
        link.SetWorkingDirectory(os.path.dirname(sys.executable))
        link.SetIconLocation(
            os.path.abspath(os.path.join(utils.resource_path(), "icons", "app.ico")), 0
        )
        properties = link.QueryInterface(propsys.IID_IPropertyStore)
        properties.SetValue(pscon.PKEY_Title, propsys.PROPVARIANTType("New Window"))
        properties.Commit()

        collection = pythoncom.CoCreateInstance(
            shell.CLSID_EnumerableObjectCollection,
            None,
            pythoncom.CLSCTX_INPROC_SERVER,
            shell.IID_IObjectCollection,
        )
        collection.AddObject(link)

        jumplist.BeginList()
        jumplist.AddUserTasks(collection)
        jumplist.CommitList()

    if os.path.basename(sys.executable) not in ("python.exe", "pythonw.exe"):
        __create_jumplist()
    del __create_jumplist

elif sys.platform == "linux":

    class LinuxReaderWindow(ReaderWindow):
        def __init__(self, app: YomuApp) -> None:
            super().__init__(app)
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        def windowHandleEvent(self, event: QEvent) -> None:
            super().windowHandleEvent(event)

            if event.type() == QEvent.Type.WindowStateChange:
                if self.windowState() in (
                    Qt.WindowState.WindowMaximized,
                    Qt.WindowState.WindowFullScreen,
                ):
                    return self.setCursor(Qt.CursorShape.ArrowCursor)

            if not isinstance(event, QMouseEvent):
                return

            pos = event.position()
            if event.type() == QEvent.Type.MouseMove and self.isNormal():
                if self.titlebar.button_at(pos) is not None:
                    return self.setCursor(Qt.CursorShape.ArrowCursor)
                return self.update_cursor(pos)

            if event.type() == QEvent.Type.MouseButtonPress:
                if (
                    event.button() == Qt.MouseButton.LeftButton
                    and self.isNormal()
                    and self.titlebar.button_at(pos) is None
                ):
                    self.handle_resize(pos)

        def update_cursor(self, pos: QPointF) -> None:
            x, y, offset = pos.x(), pos.y(), 7
            if x < offset:
                if y < offset:
                    return self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                if y > self.height() - offset:
                    return self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                return self.setCursor(Qt.CursorShape.SizeHorCursor)

            if x > self.width() - offset:
                if y < offset:
                    return self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                if y > self.height() - offset:
                    return self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                return self.setCursor(Qt.CursorShape.SizeHorCursor)

            if y < offset or y > self.height() - offset:
                return self.setCursor(Qt.CursorShape.SizeVerCursor)

            self.setCursor(Qt.CursorShape.ArrowCursor)

        def handle_resize(self, pos: QPointF) -> None:
            x, y = (pos.x(), pos.y())
            offset, edge = 7, 0

            if x < offset:
                edge |= Qt.Edge.LeftEdge.value
            elif x > (self.width() - offset):
                edge |= Qt.Edge.RightEdge.value

            if y < offset:
                edge |= Qt.Edge.TopEdge.value
            elif y > (self.height() - offset):
                edge |= Qt.Edge.BottomEdge.value

            if edge > 0:
                self.windowHandle().startSystemResize(Qt.Edge(edge))
