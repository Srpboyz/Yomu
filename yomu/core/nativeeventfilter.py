from __future__ import annotations

import sys

from PyQt6.QtCore import QAbstractNativeEventFilter, QByteArray, QEvent, Qt
from PyQt6.QtGui import QEnterEvent, QHoverEvent, QMouseEvent
from PyQt6.QtWidgets import QApplication
from PyQt6.sip import voidptr

from yomu.ui.window import ReaderWindow

if sys.platform == "win32":
    from ctypes import cast, c_int, POINTER, Structure
    from ctypes.wintypes import HWND, MSG, RECT, UINT
    import win32api
    import win32gui
    import win32con

    class MARGINS(Structure):
        _fields_ = [
            ("cxLeftWidth", c_int),
            ("cxRightWidth", c_int),
            ("cyTopHeight", c_int),
            ("cyBottomHeight", c_int),
        ]

    class PWINDOWPOS(Structure):
        _fields_ = [
            ("hWnd", HWND),
            ("hwndInsertAfter", HWND),
            ("x", c_int),
            ("y", c_int),
            ("cx", c_int),
            ("cy", c_int),
            ("flags", UINT),
        ]

    class NCCALCSIZE_PARAMS(Structure):
        _fields_ = [("rgrc", RECT * 3), ("lppos", POINTER(PWINDOWPOS))]

    LPNCCALCSIZE_PARAMS = POINTER(NCCALCSIZE_PARAMS)

    def resize_border_thickness(window: ReaderWindow, *, horizontal: bool):
        frame = win32con.SM_CXSIZEFRAME if horizontal else win32con.SM_CYSIZEFRAME
        result = win32api.GetSystemMetrics(frame) + win32api.GetSystemMetrics(92)

        if result > 0:
            return result

        thickness = 8
        return round(thickness * window.devicePixelRatio())

    def is_zoomed(hWnd: int):
        windowPlacement = win32gui.GetWindowPlacement(hWnd)
        if not windowPlacement:
            return False

        return windowPlacement[1] == win32con.SW_MAXIMIZE


class NativeEventFilter(QAbstractNativeEventFilter):
    def nativeEventFilter(
        self, eventType: QByteArray, message: voidptr
    ) -> tuple[bool, int]:
        retval, result = False, 0

        if eventType not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return retval, result

        msg = MSG.from_address(int(message))
        if not msg.hWnd:
            return retval, result

        window: ReaderWindow | None = ReaderWindow.find(msg.hWnd)
        if not isinstance(window, ReaderWindow):
            return retval, result

        if msg.message == win32con.WM_NCHITTEST and not window.isFullScreen():
            pos = window.mapFromGlobal(window.cursor().pos())
            x, y = pos.x(), pos.y()

            widget = window.titlebar.childAt(x, y)
            if widget in (
                window.titlebar.normal_button,
                window.titlebar.maximize_button,
            ):
                e = QEnterEvent(
                    widget.mapFromGlobal(window.cursor().pos()).toPointF(),
                    window.pos().toPointF(),
                    window.cursor().pos().toPointF(),
                )
                QApplication.postEvent(widget, e)

                e = QHoverEvent(QEvent.Type.HoverEnter, pos.toPointF(), pos.toPointF())
                QApplication.postEvent(widget, e)

                return True, win32con.HTMAXBUTTON

            widget = (
                window.titlebar.normal_button
                if window.isMaximized() or window.isFullScreen()
                else window.titlebar.maximize_button
            )
            QApplication.postEvent(widget, QEvent(QEvent.Type.Leave))

            e = QHoverEvent(QEvent.Type.HoverLeave, pos.toPointF(), pos.toPointF())
            QApplication.postEvent(widget, e)

            if window.isMaximized():
                return retval, result

            left = x < 5
            top = y < 5
            right = x > window.width() - 5
            bottom = y > window.height() - 5

            if top and left:
                return True, win32con.HTTOPLEFT
            elif top and right:
                return True, win32con.HTTOPRIGHT
            elif bottom and left:
                return True, win32con.HTBOTTOMLEFT
            elif bottom and right:
                return True, win32con.HTBOTTOMRIGHT
            elif left:
                return True, win32con.HTLEFT
            elif top:
                return True, win32con.HTTOP
            elif right:
                return True, win32con.HTRIGHT
            elif bottom:
                return True, win32con.HTBOTTOM

        elif msg.message == win32con.WM_NCMOUSEMOVE:
            pos = window.mapFromGlobal(window.cursor().pos()).toPointF()
            widget = window.titlebar.childAt(pos)
            if widget in (
                window.titlebar.normal_button,
                window.titlebar.maximize_button,
            ):
                e = QMouseEvent(
                    QEvent.Type.MouseMove,
                    pos,
                    Qt.MouseButton.NoButton,
                    Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.postEvent(widget, e)

                e = QHoverEvent(QEvent.Type.HoverMove, pos, pos)
                QApplication.postEvent(widget, e)

        elif msg.message in (win32con.WM_NCLBUTTONDOWN, win32con.WM_NCRBUTTONDOWN):
            pos = window.mapFromGlobal(window.cursor().pos())
            widget = window.titlebar.childAt(pos)
            if widget in (
                window.titlebar.normal_button,
                window.titlebar.maximize_button,
            ):
                button = (
                    Qt.MouseButton.LeftButton
                    if msg.message == win32con.WM_NCLBUTTONDOWN
                    else Qt.MouseButton.RightButton
                )
                e = QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    pos.toPointF(),
                    button,
                    button,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.postEvent(widget, e)
                if button == Qt.MouseButton.LeftButton:
                    widget.pressed.emit()

                return True, 0

        elif msg.message in (win32con.WM_NCLBUTTONDBLCLK, win32con.WM_NCRBUTTONDBLCLK):
            pos = window.mapFromGlobal(window.cursor().pos())
            widget = window.titlebar.childAt(pos)
            if widget in (
                window.titlebar.normal_button,
                window.titlebar.maximize_button,
            ):
                button = (
                    Qt.MouseButton.LeftButton
                    if msg.message == win32con.WM_NCLBUTTONDBLCLK
                    else Qt.MouseButton.RightButton
                )
                e = QMouseEvent(
                    QEvent.Type.MouseButtonDblClick,
                    pos.toPointF(),
                    button,
                    button,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.postEvent(widget, e)
                return True, 0

        elif msg.message in (win32con.WM_NCLBUTTONUP, win32con.WM_NCRBUTTONUP):
            pos = window.mapFromGlobal(window.cursor().pos())
            widget = window.titlebar.childAt(pos)
            if widget in (
                window.titlebar.normal_button,
                window.titlebar.maximize_button,
            ):
                button = (
                    Qt.MouseButton.LeftButton
                    if msg.message == win32con.WM_NCLBUTTONUP
                    else Qt.MouseButton.RightButton
                )
                e = QMouseEvent(
                    QEvent.Type.MouseButtonRelease,
                    pos.toPointF(),
                    button,
                    button,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.postEvent(widget, e)
                if button == Qt.MouseButton.LeftButton:
                    widget.released.emit()

                return True, 0

        elif msg.message == win32con.WM_NCCALCSIZE:
            if not msg.wParam:
                return True, 0

            rect = cast(msg.lParam, LPNCCALCSIZE_PARAMS).contents.rgrc[0]

            is_maximized = is_zoomed(msg.hWnd)
            is_fullscreen = window.isFullScreen()

            if is_maximized and not is_fullscreen:
                thickness = resize_border_thickness(self, horizontal=True)
                rect.left += thickness
                rect.right -= thickness

                thickness = resize_border_thickness(self, horizontal=False)
                rect.top += thickness
                rect.bottom -= thickness
                result = win32con.WVR_REDRAW

            return True, result

        return retval, result
