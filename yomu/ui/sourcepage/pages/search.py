from __future__ import annotations

from logging import getLogger

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QNetworkRequest
from PyQt6.QtWidgets import QLineEdit

from yomu.core.network import Response
from yomu.source import MangaList

from .base import BasePage

logger = getLogger(__name__)


class SearchWidget(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.current_text = ""

        self.line_edit = QLineEdit(self)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setPlaceholderText("Search")
        self.line_edit.returnPressed.connect(self.search)

        layout = self.layout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.insertWidget(0, self.line_edit)

    def search(self) -> None:
        window = self.window()
        self._cancel_request.emit()

        self.current_text = query = self.line_edit.text()
        if not query:
            return self.clear_widget()

        try:
            request = self.source.search_for_manga(self.line_edit.text())
        except Exception:
            return window.display_message("Error while searching for manga")

        request.setPriority(QNetworkRequest.Priority.HighPriority)
        response = window.network.handle_request(request)
        response.finished.connect(self._parse_search_results)
        self._cancel_request.connect(response.abort)

        self._loading_icon.movie().start()
        self._loading_icon.show()
        self.manga_list.hide()

    def _parse_search_results(self) -> None:
        response: Response = self.sender()
        self._loading_icon.movie().stop()
        self._loading_icon.hide()
        self.manga_list.show()

        window = self.window()

        if window.current_widget != self.parent():
            return None

        error = response.error()
        if error == Response.Error.OperationCanceledError:
            return None

        if error != Response.Error.NoError:
            self.source.search_request_error(response, self.current_text)
            return window.display_message("Error while searching for manga")

        try:
            manga_list = self.source.parse_search_results(response, self.current_text)
        except Exception as e:
            logger.exception(
                f"Failed to parse search results for {self.source.name}", exc_info=e
            )
            return window.display_message("Error while searching for manga")

        if not isinstance(manga_list, MangaList):
            logger.error(
                f"{self.source.name} returned a {type(manga_list).__name__} instead of a MangaList for the search parse"
            )
            return window.display_message("Error while searching for manga")

        self.manga_list.clear()
        self.insert_mangas(manga_list.mangas)

    def clear_widget(self) -> None:
        self.line_edit.clear()
        self._cancel_request.emit()
        super().clear_widget()
