from __future__ import annotations

import os
from copy import deepcopy
from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, QEvent, QObject, Qt, QUrl
from PyQt6.QtGui import QIcon, QMouseEvent
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWidgets import QTabWidget, QToolButton
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView

from yomu.core import utils
from yomu.source import Source, FilterOption
from yomu.ui.stack import StackWidgetMixin

from .filters import FilterDialog
from .pages.latest import LatestWidget
from .pages.search import SearchWidget

if TYPE_CHECKING:
    from yomu.ui import ReaderWindow
    from .pages import BasePage


class SourcePage(QTabWidget, StackWidgetMixin):
    source_changed = pyqtSignal(Source)

    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self._source: Source = window.app.source_manager.sources[0]

        self.latest = LatestWidget(self, window.app)
        self.search = SearchWidget(self, window.app)

        self.addTab(self.latest, "Latest")
        self.addTab(self.search, "Search")
        self.setContentsMargins(0, 0, 0, 0)
        self.setDocumentMode(True)

        self.currentChanged.connect(self._current_changed)

        tabBar = self.tabBar()
        tabBar.installEventFilter(self)
        tabBar.setMouseTracking(True)
        tabBar.setExpanding(True)

        self._web_view_button = QToolButton(self)
        self._web_view_button.setToolTip("Webview")
        path = os.path.join(utils.resource_path(), "icons", "webview.svg")
        self._web_view_button.setIcon(QIcon(path))
        self._web_view_button.pressed.connect(self._open_web_view)
        self._web_view_button.hide()

        self._web_view = QWebEngineView(self)
        self._web_view.setWindowFlag(Qt.WindowType.Window)
        self._web_view.setWindowModality(Qt.WindowModality.WindowModal)
        self._web_view.setHtml("<body></body>")

        self._filter_dialog = FilterDialog(self)
        self._filter_dialog.accepted.connect(self.reset)

        self._filter_button = QToolButton(self)
        self._filter_button.setToolTip("Filter")
        path = os.path.join(utils.resource_path(), "icons", "filter.svg")
        self._filter_button.setIcon(QIcon(path))
        self._filter_button.pressed.connect(self._filter_dialog_requested)
        self._filter_button.hide()

        titlebar = window.titlebar
        titlebar.insert_button(self._web_view_button, index=3)
        titlebar.insert_button(self._filter_button, index=4)

    window: Callable[[], ReaderWindow]
    currentWidget: Callable[[], BasePage]
    widget: Callable[[int], BasePage]

    @property
    def source(self) -> Source:
        return self._source

    @source.setter
    def source(self, source: Source) -> None:
        if self._source != source:
            self._source = source
            self.source_changed.emit(source)

            self._filter_button.setEnabled(source.has_filters)

            self.setTabVisible(self.indexOf(self.latest), source.supports_latest)
            self.setTabVisible(self.indexOf(self.search), source.supports_search)
            self.reset(new_source=True)

        self.window().current_widget = self

    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> TYPE_CHECKING:
        if a0 == (tab_bar := self.tabBar()):
            if a1.type() == QEvent.Type.MouseMove:
                index = tab_bar.tabAt(self.mapFromGlobal(self.cursor().pos()))
                if index != tab_bar.currentIndex():
                    tab_bar.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    tab_bar.setCursor(Qt.CursorShape.ArrowCursor)
            elif a1.type() == QEvent.Type.Leave:
                index = tab_bar.tabAt(self.mapFromGlobal(self.cursor().pos()))
                if index != tab_bar.currentIndex():
                    tab_bar.setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(a0, a1)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.MouseButton.BackButton:
            a0.ignore()
        return super().mousePressEvent(a0)

    def _current_changed(self, index: int) -> None:
        self.widget(index).set_current_widget()

    def _open_web_view(self) -> None:
        try:
            url = QUrl(self.source.BASE_URL)
        except Exception:
            return

        if (page := self._web_view.page()) is not None:
            page.deleteLater()

        profile = QWebEngineProfile()
        profile.cookieStore().cookieAdded.connect(self._add_web_view_cookie)

        page = QWebEnginePage(profile, self._web_view)
        profile.setParent(page)

        self._web_view.setPage(page)
        self._web_view.setFixedSize(self.size() * 0.75)

        page.load(url)
        self._web_view.show()

    def _add_web_view_cookie(self, cookie: QNetworkCookie) -> None:
        if cookie.name() == "cf_clearance":
            self.window().network.cookieJar().setCookiesFromUrl(
                [QNetworkCookie(cookie)], self.source.BASE_URL
            )

    def _source_filters_updated(self, filters: dict[str, FilterOption]) -> None:
        self.window().app.source_manager.update_source_filters(self.source, filters)

    def _filter_dialog_requested(self) -> None:
        self._filter_dialog.exec(deepcopy(self.source.filters))

    def reset(self, *, new_source: bool = False) -> None:
        if self.is_current_widget:
            self.latest.clear_widget()
            self.search.clear_widget()
            self.currentWidget().set_current_widget()
        elif new_source:
            count = self.tabBar().count()
            for i in range(count):
                self.widget(i).clear_widget()

            for i in range(count):
                if self.isTabVisible(i):
                    self.setCurrentIndex(i)
                    break

    def set_current_widget(self) -> None:
        super().set_current_widget()
        window = self.window()
        if not window.network.is_online:
            window.display_message(
                "You are currently offline. Please connect to the internet to utilize sources."
            )
            window.current_widget = window.library
            return None

        self.currentWidget().set_current_widget()

        window.setWindowTitle(self.source.name)
        window.titlebar.refresh_button.released.connect(self.reset)

        self._web_view_button.show()
        self._filter_button.setVisible(self._filter_button.isEnabled())

    def clear_widget(self) -> None:
        super().clear_widget()
        self.window().titlebar.refresh_button.released.disconnect(self.reset)
        self._web_view_button.hide()
        self._filter_button.hide()
