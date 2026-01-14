from __future__ import annotations

import logging
import os
import sys
from types import TracebackType
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QDir, QEventLoop, QFileSystemWatcher, QSettings, Qt
from PyQt6.QtGui import QColor, QFontDatabase, QIcon, QMouseEvent, QPalette, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from yomu.source import Source
from yomu.ui import ReaderWindow

from .ipc import IPCServer
from .extensionmanager import ExtensionInfo, ExtensionManager
from .models import Category, Chapter, Manga
from .nativeeventfilter import NativeEventFilter
from . import utils

if TYPE_CHECKING:
    from yomu.extension import YomuExtension


__all__ = ("YomuApp",)


QApplication.setApplicationName("Yomu")
QApplication.setApplicationDisplayName("Yomu")
QApplication.setApplicationVersion("1.2.5")
if sys.platform == "linux":
    QApplication.setDesktopFileName("yomu")


logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(utils.app_data_path(), "yomu.log"),
    format="%(levelname)s:%(asctime)s:%(name)s - %(lineno)d: %(message)s",
)
logger = logging.getLogger("yomu")


class AppSettings(QSettings):
    value_changed = pyqtSignal((str, object))

    def __init__(self, parent: YomuApp) -> None:
        path = os.path.join(utils.app_data_path(), "config.ini")
        super().__init__(path, AppSettings.Format.IniFormat, parent)

    def value[T](self, key: str, defaultValue: T, type: type[T] | None = None) -> T:
        return super().value(key, defaultValue, type)

    def setValue(self, key: str, value: object) -> None:
        super().setValue(key, value)
        self.value_changed.emit(key, value)


class YomuSplashScreen(QSplashScreen):
    def mousePressEvent(self, a0: QMouseEvent | None) -> None: ...


class YomuApp(QApplication):
    aboutToStart = pyqtSignal()
    keybinds_changed = pyqtSignal(dict)

    window_created = pyqtSignal(ReaderWindow)
    window_closed = pyqtSignal(ReaderWindow)

    extension_disabled = pyqtSignal(ExtensionInfo)

    category_created = pyqtSignal(Category)
    category_deleted = pyqtSignal(Category)
    category_manga_added = pyqtSignal(Category, Manga)
    category_manga_removed = pyqtSignal(Category, Manga)

    manga_details_updated = pyqtSignal(Manga)
    manga_library_status_changed = pyqtSignal(Manga)
    manga_thumbnail_changed = pyqtSignal(Manga)
    chapter_list_updated = pyqtSignal(Manga)
    chapter_read_status_changed = pyqtSignal(Chapter)
    chapter_download_status_changed = pyqtSignal(Chapter)

    source_filters_updated = pyqtSignal((Source, dict))

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)

        self._native_event_filter = NativeEventFilter()
        self.installNativeEventFilter(self._native_event_filter)

        icons = os.path.join(utils.resource_path(), "icons")
        self.setWindowIcon(QIcon(os.path.join(icons, "app.ico")))

        pixmap = QPixmap(os.path.join(icons, "splashscreen.png"))
        self.splash_screen = YomuSplashScreen(pixmap)
        self.splash_screen.show()
        self.processEvents(QEventLoop.ProcessEventsFlag.WaitForMoreEvents)

        self.ipc_server = IPCServer(self)
        self.ipc_server.listen()

        # Create dark mode for cross platform
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.Light, QColor(120, 120, 120))
        palette.setColor(QPalette.ColorRole.Midlight, QColor(90, 90, 90))
        palette.setColor(QPalette.ColorRole.Dark, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Mid, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(153, 235, 255))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 120, 212))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(0, 26, 104))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(0, 26, 104))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(60, 60, 60))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(212, 212, 212))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Accent, QColor(0, 120, 212))
        palette.setColor(QPalette.ColorRole.NoRole, QColor(0, 0, 0))
        self.setPalette(palette)

        self._windows: list[ReaderWindow] = []

        from .downloader import Downloader
        from .network import Network
        from .sourcemanager import SourceManager
        from .sql import Sql
        from .updater import Updater

        self.settings = AppSettings(self)
        self.network = Network(self)
        self.downloader = Downloader(self)
        self.updater = Updater(self)
        self.source_manager = SourceManager(self)
        self.sql = Sql(self)
        self.extension_manager = ExtensionManager(self)

        path = os.path.join(utils.app_data_path(), "fonts")
        if not os.path.exists(path):
            os.makedirs(path)

        for font in os.scandir(path):
            if font.is_file():
                QFontDatabase.addApplicationFont(font.path)

        def set_styles(file):
            with open(file) as f:
                self.setStyleSheet(f.read())

        path = os.path.join(utils.resource_path(), "styles.qss")
        QFileSystemWatcher([path], self).fileChanged.connect(set_styles)
        set_styles(path)

        def keybinds_updated():
            self.keybinds_changed.emit(utils.get_keybinds())

        app_data_path = utils.app_data_path()
        path = os.path.join(app_data_path, "keybinds.json")
        QFileSystemWatcher([path], self).fileChanged.connect(keybinds_updated)

    @property
    def windows(self) -> tuple[ReaderWindow]:
        return tuple(self._windows)

    @property
    def window(self) -> ReaderWindow | None:
        try:
            return self._windows[0]
        except IndexError:
            return None

    @staticmethod
    def instance() -> YomuApp:
        return QApplication.instance()

    @staticmethod
    def display_message(message: str):
        dialog = QMessageBox()
        dialog.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setWindowTitle("Yomu")
        dialog.setText(message)
        dialog.exec()

    def __excepthook__(
        self,
        exctype: type[BaseException],
        value: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        error = f"{exctype.__name__}: {value}"
        logger.exception(error, exc_info=(exctype, value, traceback))
        YomuApp.display_message("Yomu crashed. Check logs for info")
        YomuApp.exit(1)

    def create_window(self) -> ReaderWindow:
        window = ReaderWindow(self)
        self._windows.append(window)
        window.closed.connect(self._window_closed)
        self.window_created.emit(window)
        return window

    def _window_closed(self) -> None:
        window = self.sender()
        try:
            self._windows.remove(window)
        except ValueError:
            ...
        else:
            self.window_closed.emit(window)
        finally:
            if not self._windows:
                self.quit()

    def handle_extension_dependency(self, extension: YomuExtension):
        for wrapper in self.extension_manager._extensions.values():
            if wrapper.ext is not None and wrapper.ext == extension:
                return self.extension_manager.handle_dependency(wrapper.info.path)

    def exec(self) -> int:
        self.source_manager._load_sources()
        self.extension_manager._load_extensions()

        window = self.create_window()
        self.splash_screen.finish(window)
        window.showMaximized()

        sys.excepthook = self.__excepthook__

        self.aboutToStart.emit()
        exit_code = super().exec()

        self.sql.commit()
        self.ipc_server.close()
        QDir(utils.temp_dir_path()).removeRecursively()

        return exit_code

    @staticmethod
    def exit(returnCode: int = 0) -> None:
        QApplication.closeAllWindows()
        QApplication.exit(returnCode)

    @staticmethod
    def quit() -> None:
        QApplication.closeAllWindows()
        QApplication.quit()
