from __future__ import annotations

from logging import Logger
from copy import copy
from collections.abc import Sequence
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QNetworkRequest

from yomu.source.models import Manga as SourceManga, Chapter as SourceChapter

from .models import Manga
from .network import Response

if TYPE_CHECKING:
    from .app import YomuApp


class BaseUpdate(QObject):
    failed = pyqtSignal(Manga)

    def __init__(
        self, parent: Updater, manga: Manga, response: Response, logger: Logger = None
    ):
        super().__init__(parent)
        self.manga = manga
        self.logger = logger

        response.finished.connect(self._request_finished)

    def _request_finished(self) -> None: ...


class MangaUpdate(BaseUpdate):
    success = pyqtSignal((Manga, SourceManga))

    def _request_finished(self):
        response: Response = self.sender()
        if response.error() == Response.Error.NoError:
            try:
                smanga = self.manga.source.parse_manga_info(
                    response, self.manga.to_source_manga()
                )
            except Exception as e:
                if self.logger is not None:
                    self.logger.error("Failled to parse manga info", exc_info=e)
                self.failed.emit(self.manga)
            else:
                if isinstance(smanga, SourceManga):
                    self.success.emit(self.manga, smanga)
                else:
                    self.failed.emit(self.manga)
        else:
            self.manga.source.manga_info_request_error(
                response, self.manga.to_source_manga()
            )

        self.deleteLater()


class ChaptersUpdate(BaseUpdate):
    success = pyqtSignal((Manga, list))

    def _request_finished(self):
        response: Response = self.sender()
        if response.error() == Response.Error.NoError:
            try:
                chapters = self.manga.source.parse_chapters(
                    response, self.manga.to_source_manga()
                )
            except Exception as e:
                if self.logger is not None:
                    self.logger.error("Failed to parse chapters", exc_info=e)
                self.failed.emit(self.manga)
            else:
                if isinstance(chapters, Sequence) and all(
                    isinstance(chapter, SourceChapter) for chapter in chapters
                ):
                    self.success.emit(self.manga, list(chapters))
                else:
                    self.failed.emit(self.manga)
        else:
            self.manga.source.chapter_request_error(
                response, self.manga.to_source_manga()
            )
            self.failed.emit(self.manga)

        self.deleteLater()


class Updater(QObject):
    manga_update_finished = pyqtSignal((Manga, bool))
    chapter_update_finished = pyqtSignal((Manga, bool))

    def __init__(self, app: YomuApp):
        super().__init__(app)
        self.app = app

    def _manga_updated(self, manga: Manga, smanga: SourceManga) -> None:
        if not self.app.sql.update_manga_info(
            id=manga.id,
            title=smanga.title,
            description=smanga.description,
            author=smanga.author,
            artist=smanga.artist,
            thumbnail=smanga.thumbnail,
        ):
            return None

        if manga.thumbnail != smanga.thumbnail:
            manga.thumbnail = smanga.thumbnail

            if manga.library:
                self.app.downloader.download_thumbnail(manga)

            self.app.manga_thumbnail_changed.emit(copy(manga))

        if (
            manga.title != smanga.title
            or manga.description != smanga.description
            or manga.author != smanga.author
            or manga.artist != smanga.artist
        ):
            manga.title = smanga.title
            manga.description = smanga.description
            manga.author = smanga.author
            manga.artist = smanga.artist

            self.app.manga_details_updated.emit(copy(manga))

        self.manga_update_finished.emit(manga, True)

    def _manga_failed(self, manga: Manga) -> None:
        self.manga_update_finished.emit(manga, False)

    def update_manga_details(
        self,
        manga: Manga,
        *,
        priority: QNetworkRequest.Priority = QNetworkRequest.Priority.NormalPriority,
    ) -> MangaUpdate:
        for child in self.findChildren(MangaUpdate):
            if child.manga == manga:
                return child

        try:
            request = manga.get_manga_info()
        except Exception:
            return None

        request.setPriority(priority)
        manga_response = self.app.network.handle_request(request)
        update = MangaUpdate(self, copy(manga), manga_response)
        update.success.connect(self._manga_updated)
        update.failed.connect(self._manga_failed)

        return update

    def _chapter_list_updated(
        self, manga: Manga, chapters: Sequence[SourceChapter]
    ) -> None:
        self.app.sql.update_chapters(manga, chapters)
        self.chapter_update_finished.emit(manga, True)

    def _chapter_list_failed(self, manga: Manga) -> None:
        self.chapter_update_finished.emit(manga, False)

    def update_manga_chapters(
        self,
        manga: Manga,
        *,
        priority: QNetworkRequest.Priority = QNetworkRequest.Priority.NormalPriority,
    ) -> ChaptersUpdate:
        for child in self.findChildren(ChaptersUpdate):
            if child.manga == manga:
                return child

        try:
            request = manga.get_chapters()
        except Exception:
            return None

        request.setPriority(priority)
        manga_response = self.app.network.handle_request(request)

        update = ChaptersUpdate(self, copy(manga), manga_response)
        update.success.connect(self._chapter_list_updated)
        update.failed.connect(self._chapter_list_failed)

        return update
