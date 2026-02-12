from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import (
    QInputDialog,
    QLineEdit,
    QMenu,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from yomu.core.models import Category, Manga
from yomu.core import utils as core_utils

from .components.mangalist import MangaList, MangaView
from .stack import StackWidgetMixin

if TYPE_CHECKING:
    from yomu.source import Source
    from yomu.ui import ReaderWindow


class Library(QWidget, StackWidgetMixin):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self._manga_list = MangaList(self, window.app)
        self._manga_list.installEventFilter(self)

        self.sql = window.app.sql
        self.current_source: Source | None = None

        self.tab_bar = QTabBar(self)
        self.tab_bar.installEventFilter(self)
        self.tab_bar.currentChanged.connect(self._tab_changed)
        self.tab_bar.addTab("All")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tab_bar)
        layout.addWidget(self._manga_list)
        self.setLayout(layout)

        window.app.manga_library_status_changed.connect(self._library_status_changed)
        window.app.category_created.connect(self._category_created)
        window.app.category_deleted.connect(self._category_deleted)
        window.app.category_manga_added.connect(self._category_manga_added)
        window.app.category_manga_removed.connect(self._category_manga_removed)

        library = self.sql.get_library()
        for manga in library:
            view = self._manga_list.add_manga(manga)
            view.installEventFilter(self)
            view.fetch_thumbnail()

        self._categories = {
            category.name: category for category in self.sql.get_categories()
        }
        for category in self._categories.keys():
            self.tab_bar.addTab(category)

        if self.tab_bar.count() == 1:
            self.tab_bar.hide()

        self.addAction("Add Category").triggered.connect(self.add_category)
        window.app.keybinds_changed.connect(self._set_keybinds)
        self._set_keybinds(core_utils.get_keybinds())

        self.setFocusProxy(self._manga_list)

    window: Callable[[], ReaderWindow]

    @property
    def manga_count(self) -> int:
        return self._manga_list.count

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        if isinstance(a0, MangaView):
            return self.mangaViewEvent(a0, a1)
        if a0 == self._manga_list and a1.type() == QEvent.Type.ContextMenu:
            menu = QMenu(self)
            menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

            create_category = menu.addAction("Create Category")
            delete_category = menu.addAction("Delete Category")

            index = self.tab_bar.currentIndex()
            if not index:
                delete_category.setVisible(False)

            action = menu.exec(a1.globalPos())
            if action == create_category:
                self.add_category()
            elif action == delete_category:
                self.sql.delete_category(
                    self._categories.get(self.tab_bar.tabText(index))
                )
        elif a0 == self.tab_bar:
            if a1.type() == QEvent.Type.ContextMenu:
                menu = QMenu(self)
                menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

                create_category = menu.addAction("Create Category")
                delete_category = menu.addAction("Delete Category")

                index = self.tab_bar.tabAt(a1.pos())
                if not index:
                    delete_category.setVisible(False)

                action = menu.exec(a1.globalPos())
                if action == create_category:
                    self.add_category()
                elif action == delete_category:
                    self.sql.delete_category(
                        self._categories.get(self.tab_bar.tabText(index))
                    )

                return True
            if a1.type() == QEvent.Type.MouseMove:
                index = self.tab_bar.tabAt(self.mapFromGlobal(self.cursor().pos()))
                if index != self.tab_bar.currentIndex():
                    self.tab_bar.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.tab_bar.setCursor(Qt.CursorShape.ArrowCursor)
            elif a1.type() == QEvent.Type.Leave:
                index = self.tab_bar.tabAt(self.mapFromGlobal(self.cursor().pos()))
                if index != self.tab_bar.currentIndex():
                    self.tab_bar.setCursor(Qt.CursorShape.ArrowCursor)
        return super().eventFilter(a0, a1)

    def mangaViewEvent(self, view: MangaView, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ContextMenu:
            menu = QMenu(self)
            menu.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

            remove_from_library = menu.addAction("Remove From Library")
            category_menu = menu.addMenu("Add to Category")

            current_index = self.tab_bar.currentIndex()
            keys = self._categories.keys()
            if len(keys) > 0:
                for name in keys:
                    _ = category_menu.addAction(name)
                    if current_index:
                        _.setVisible(False)
            else:
                category_menu.menuAction().setVisible(False)

            remove_manga_from_category = menu.addAction("Remove From Category")
            if current_index:
                category_menu.menuAction().setVisible(False)
            else:
                remove_manga_from_category.setVisible(False)

            triggered = menu.exec(event.globalPos())
            if triggered == remove_from_library:
                self.sql.set_library(view.manga, library=False)
            elif triggered in category_menu.actions():
                self.sql.add_manga_to_category(
                    view.manga, self._categories.get(triggered.text())
                )
            elif triggered == remove_manga_from_category:
                category = self._categories.get(
                    self.tab_bar.tabText(self.tab_bar.currentIndex())
                )
                self.sql.remove_manga_from_category(view.manga, category)
            return True
        return False

    def _refresh_button_clicked(self) -> None:
        self.update_all_manga()

    def _library_status_changed(self, manga: Manga) -> None:
        if manga.library:
            for i in range(self.manga_count):
                manga_view = self.manga_view_at(i)
                if manga_view is not None and manga_view.manga.id > manga.id:
                    view = self._manga_list.insert_manga(i, manga)
                    break
            else:
                view = self._manga_list.add_manga(manga)

            view.thumbnail_widget.priority = QNetworkRequest.Priority.HighPriority
            view.installEventFilter(self)
            if self.current_source and self.current_source != manga.source:
                view.hide()
            return view.fetch_thumbnail()

        for i in range(self.manga_count):
            view = self.manga_view_at(i)
            if view is not None and view.manga == manga:
                return view.deleteLater()

    def _category_created(self, category: Category):
        self._categories[category.name] = category
        self.tab_bar.addTab(category.name)
        self.tab_bar.show()

    def _category_deleted(self, category: Category):
        del self._categories[category.name]

        for i in range(self.tab_bar.count()):
            if self.tab_bar.tabText(i) == category.name:
                self.tab_bar.removeTab(i)
                break

        if self.tab_bar.count() == 1:
            self.tab_bar.hide()

    def _category_manga_added(self, category: Category, manga: Manga) -> None:
        if self.tab_bar.tabText(self.tab_bar.currentIndex()) == category.name:
            for i in range(self.manga_count):
                view = self.manga_view_at(i)
                if view is not None and view.manga == manga:
                    return view.show()

    def _category_manga_removed(self, category: Category, manga: Manga) -> None:
        if self.tab_bar.tabText(self.tab_bar.currentIndex()) == category.name:
            for i in range(self.manga_count):
                view = self.manga_view_at(i)
                if view is not None and view.manga == manga:
                    return view.hide()

    def _tab_changed(self, index: int) -> None:
        if index == 0:
            for i in range(self.manga_count):
                if (view := self.manga_view_at(i)) is not None:
                    view.show()
            return None

        category = self._categories[self.tab_bar.tabText(index)]
        mangas = self.sql.get_category_mangas(category)
        for i in range(self.manga_count):
            view = self.manga_view_at(i)
            if view is not None:
                view.setVisible(view.manga in mangas)

    def _set_keybinds(self, keybinds: dict[str, core_utils.Keybind]) -> None:
        for action in self.actions():
            data = keybinds.get(action.text(), {"keybinds": []})
            action.setShortcuts(data["keybinds"] if data is not None else [])

    def manga_view_at(self, index: int) -> MangaView | None:
        return self._manga_list.manga_view_at(index)

    def add_category(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Category", "Category Name:", QLineEdit.EchoMode.Normal, ""
        )
        if not name or not ok:
            return None

        self.sql.create_category(name)

    def set_source(self, source: Source | None) -> None:
        show_all = source is None
        for i in range(self.manga_count):
            if (view := self.manga_view_at(i)) is not None:
                view.setVisible(show_all or view.manga.source == source)
        self.current_source = source

    def update_all_manga(self) -> None:
        updater = self.window().app.updater
        for i in range(self.manga_count):
            if (view := self.manga_view_at(i)) is not None:
                manga = view.manga
                updater.update_manga_details(
                    manga, priority=QNetworkRequest.Priority.LowPriority
                )
                updater.update_manga_chapters(
                    manga, priority=QNetworkRequest.Priority.LowPriority
                )

    def set_current_widget(self) -> None:
        super().set_current_widget()
        window = self.window()
        window.setWindowTitle("Library")
        window.titlebar.refresh_button.pressed.connect(self._refresh_button_clicked)

    def clear_widget(self) -> None:
        super().clear_widget()
        self.window().titlebar.refresh_button.pressed.disconnect(
            self._refresh_button_clicked
        )
