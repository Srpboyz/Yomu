import os
from datetime import datetime
from logging import getLogger
from typing import TYPE_CHECKING

from PyQt6.QtSql import QSqlDatabase, QSqlQuery

from yomu.source import Chapter as SourceChapter, Manga as SourceManga, Source

from .models import Manga, Chapter, Category
from .utils import app_data_path

if TYPE_CHECKING:
    from .app import YomuApp

logger = getLogger(__name__)


class Sql:
    def __init__(self, app: YomuApp) -> None:
        self.app = app

        self._conn = QSqlDatabase("QSQLITE")
        self._conn.setDatabaseName(os.path.join(app_data_path(), "yomu.db"))
        if not self._conn.open():
            raise FileNotFoundError("Failed to open sql file")

        self._create_tables()

    def _create_tables(self) -> None:
        query = self.create_query()
        query.exec(
            """CREATE TABLE IF NOT EXISTS mangas (id INTEGER PRIMARY KEY,
                                                  source INTEGER NOT NULL,
                                                  title TEXT NOT NULL,
                                                  description TEXT,
                                                  author TEXT,
                                                  artist TEXT,
                                                  thumbnail TEXT,
                                                  url TEXT NOT NULL,
                                                  library BOOLEAN NOT NULL DEFAULT FALSE,
                                                  initialized BOOLEAN NOT NULL DEFAULT FALSE,
                                                  UNIQUE(source, url));"""
        )
        query.exec("CREATE INDEX IF NOT EXISTS mangas_url_index ON mangas(url);")

        query.exec(
            """CREATE TABLE IF NOT EXISTS chapters (id INTEGER PRIMARY KEY,
                                                    manga_id INTEGER NOT NULL,
                                                    number INTEGER NOT NULL,
                                                    title TEXT NOT NULL,
                                                    url TEXT NOT NULL,
                                                    uploaded INTEGER NOT NULL,
                                                    downloaded BOOLEAN NOT NULL DEFAULT FALSE,
                                                    read BOOLEAN NOT NULL DEFAULT FALSE,
                                                    FOREIGN KEY(manga_id) REFERENCES mangas(id) ON DELETE CASCADE,
                                                    UNIQUE(manga_id, url));"""
        )
        query.exec("CREATE INDEX IF NOT EXISTS chapters_id_index ON chapters(id);")
        query.exec(
            "CREATE INDEX IF NOT EXISTS chapters_manga_id_index ON chapters(manga_id);"
        )

        query.exec(
            """CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY,
                                                      name TEXT NOT NULL);"""
        )
        query.exec(
            """CREATE TABLE IF NOT EXISTS category_mangas (category_id INTEGER NOT NULL,
                                                           manga_id INTEGER NOT NULL,
                                                           PRIMARY KEY (category_id, manga_id),
                                                           FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                                                           FOREIGN KEY (manga_id) REFERENCES mangas(id) ON DELETE CASCADE);"""
        )
        query.exec(
            """CREATE TRIGGER IF NOT EXISTS category_manga_library_update
               AFTER UPDATE ON mangas WHEN NEW.library = FALSE
               BEGIN
                   DELETE FROM category_mangas WHERE manga_id = NEW.id;
               END;
            """
        )

    def create_query(self) -> QSqlQuery:
        query = QSqlQuery(self._conn)
        query.exec("PRAGMA foreign_keys=ON;")
        query.exec("PRAGMA journal_mode=WAL;")
        query.exec("PRAGMA synchronous=NORMAL;")
        return query

    def get_categories(self) -> list[Category]:
        query = self.create_query()
        query.setForwardOnly(True)

        categories: list[Category] = []
        if query.exec("SELECT * FROM categories;"):
            while query.next():
                categories.append(Category(query.value("id"), query.value("name")))
        return categories

    def create_category(self, name: str) -> Category | None:
        query = self.create_query()
        query.prepare("INSERT INTO categories(name) VALUES (:name) RETURNING id;")
        query.bindValue(":name", name)
        if not query.exec():
            return logger.error(
                f"Failed to create category - {query.lastError().text()}"
            )

        query.first()
        category = Category(query.value("id"), name)
        self.app.category_created.emit(category)
        return category

    def delete_category(self, category: Category) -> bool:
        query = self.create_query()
        query.prepare("DELETE FROM categories WHERE id = :category_id;")
        query.bindValue(":category_id", category.id)

        if ret := query.exec():
            self.app.category_deleted.emit(category)
        else:
            logger.error(f"Failed to delete category - {query.lastError().text()}")
        return ret

    def get_category_mangas(self, category: Category) -> list[Manga]:
        query = self.create_query()
        query.prepare(
            """
            SELECT mangas.*
            FROM category_mangas
            INNER JOIN mangas
            ON mangas.id = category_mangas.manga_id
            WHERE category_mangas.category_id = :category_id;
            """
        )
        query.bindValue(":category_id", category.id)
        if not query.exec():
            logger.error(f"Failed to get category mangas - {query.lastError().text()}")
            return []

        source_manager = self.app.source_manager

        mangas = []
        while query.next():
            source = source_manager.get_source(query.value("source"))
            if source is None:
                continue

            manga = Manga(
                id=query.value("id"),
                source=source,
                title=query.value("title"),
                description=query.value("description"),
                author=query.value("author"),
                artist=query.value("artist"),
                thumbnail=query.value("thumbnail"),
                url=query.value("url"),
                library=True,
                initialized=bool(query.value("initialized")),
            )
            mangas.append(manga)
        return mangas

    def add_manga_to_category(self, manga: Manga, category: Category) -> bool:
        query = self.create_query()
        query.prepare("INSERT INTO category_mangas VALUES (:category_id, :manga_id);")
        query.bindValue(":category_id", category.id)
        query.bindValue(":manga_id", manga.id)
        if not (ret := query.exec()):
            logger.error(
                f"Failed to add manga to category - {query.lastError().text()}"
            )
        else:
            self.app.category_manga_added.emit(category, manga)
        return ret

    def remove_manga_from_category(self, manga: Manga, category: Category) -> bool:
        query = self.create_query()
        query.prepare(
            "DELETE FROM category_mangas WHERE manga_id = :manga_id AND category_id = :category_id;"
        )
        query.bindValue(":manga_id", manga.id)
        query.bindValue(":category_id", category.id)
        if not (ret := query.exec()):
            logger.error(
                f"Failed to delete category manga - {query.lastError().text()}"
            )
        else:
            self.app.category_manga_removed.emit(category, manga)
        return ret

    def get_library(self) -> list[Manga]:
        source_manager = self.app.source_manager

        query = self.create_query()
        query.setForwardOnly(True)
        if not query.exec("SELECT * FROM mangas WHERE library = TRUE;"):
            logger.error(f"Failed to get the library - {query.lastError().text()}")

        mangas: list[Manga] = []
        while query.next():
            source = source_manager.get_source(query.value("source"))
            if source is None:
                continue

            manga = Manga(
                id=query.value("id"),
                source=source,
                title=query.value("title"),
                description=query.value("description"),
                author=query.value("author"),
                artist=query.value("artist"),
                thumbnail=query.value("thumbnail"),
                url=query.value("url"),
                library=True,
                initialized=bool(query.value("initialized")),
            )
            mangas.append(manga)

        return mangas

    def set_library(self, manga: Manga, *, library: bool) -> bool:
        query = self.create_query()
        query.prepare("UPDATE mangas SET library = :library WHERE id = :id;")
        query.bindValue(":library", library)
        query.bindValue(":id", manga.id)

        if ret := query.exec():
            manga.library = library
            self.app.manga_library_status_changed.emit(manga)
        else:
            logger.error(
                f"Failed to add manga ({manga.title}) to library - {query.lastError().text()}"
            )
        return ret

    def get_manga_by_id(self, id: int) -> Manga | None:
        query = self.create_query()
        query.prepare("SELECT * FROM mangas WHERE id = :id")
        query.bindValue(":id", id)
        if query.exec() and query.first():
            source = self.app.source_manager.get_source(query.value("source"))
            return Manga(
                id=query.value("id"),
                source=source,
                title=query.value("title"),
                description=query.value("description"),
                author=query.value("author"),
                artist=query.value("artist"),
                thumbnail=query.value("thumbnail"),
                url=query.value("url"),
                library=query.value("library"),
                initialized=bool(query.value("initialized")),
            )

        return None

    def add_and_get_mangas(
        self, source: Source, smangas: list[SourceManga]
    ) -> list[Manga]:
        query = self.create_query()

        query.prepare(
            """INSERT INTO mangas (source, title, thumbnail, url)
               VALUES (:source, :title, :thumbnail, :url)
               ON CONFLICT(source, url) DO UPDATE
               SET title = COALESCE(EXCLUDED.title, title)
               RETURNING *;"""
        )

        mangas: list[Manga] = []
        for smanga in smangas:
            query.bindValue(":source", source.id)
            query.bindValue(":title", smanga.title)
            query.bindValue(":thumbnail", smanga.thumbnail)
            query.bindValue(":url", smanga.url)

            if not query.exec() or not query.first():
                continue

            manga = Manga(
                id=query.value("id"),
                source=source,
                title=query.value("title"),
                description=query.value("description"),
                author=query.value("author"),
                artist=query.value("artist"),
                thumbnail=query.value("thumbnail"),
                url=query.value("url"),
                library=bool(query.value("library")),
                initialized=bool(query.value("initialized")),
            )

            mangas.append(manga)

        return mangas

    def get_manga_info(self, smanga: SourceManga) -> Manga | None:
        query = self.create_query()
        query.setForwardOnly(True)
        query.prepare("SELECT * FROM mangas WHERE url = :url;")

        query.bindValue(":url", smanga.url)
        if not query.exec() or not query.first():
            return None

        source = self.app.source_manager.get_source(query.value("source"))
        if source is None:
            return None

        return Manga(
            id=query.value("id"),
            source=source,
            title=query.value("title"),
            description=query.value("description"),
            author=query.value("author"),
            artist=query.value("artist"),
            thumbnail=query.value("thumbnail"),
            url=query.value("url"),
            library=bool(query.value("library")),
            initialized=bool(query.value("initialized")),
        )

    def update_manga_info(
        self,
        id: int,
        title: str,
        description: str,
        author: str,
        artist: str,
        thumbnail: str,
    ) -> bool:
        query = self.create_query()
        query.prepare(
            """UPDATE mangas
               SET title = COALESCE(:title, title),
                   description = COALESCE(:description, description),
                   author = COALESCE(:author, author),
                   artist = COALESCE(:artist, artist),
                   thumbnail = COALESCE(:thumbnail, thumbnail),
                   initialized = TRUE
               WHERE id = :id
               RETURNING *;"""
        )

        query.bindValue(":title", title)
        query.bindValue(":description", description)
        query.bindValue(":author", author)
        query.bindValue(":artist", artist)
        query.bindValue(":thumbnail", thumbnail)
        query.bindValue(":id", id)

        if not (ret := query.exec()):
            logger.error(
                f"Failed to get update manga ({id}) - {query.lastError().text()}"
            )

        return ret

    def get_chapters(self, manga: Manga) -> list[Chapter]:
        query = self.create_query()
        query.prepare(
            "SELECT * FROM chapters WHERE manga_id = :manga_id ORDER BY number, uploaded;"
        )
        query.bindValue(":manga_id", manga.id)
        if not query.exec():
            logger.error(
                f"Failed to get get chapters for {manga.title} - {query.lastError().text()}"
            )

        chapters = []
        while query.next():
            id = query.value("id")
            number = query.value("number")
            title = query.value("title")
            uploaded = datetime.fromtimestamp(query.value("uploaded"))
            url = query.value("url")
            downloaded = bool(query.value("downloaded"))
            read = bool(query.value("read"))

            chapters.append(
                Chapter(
                    id=id,
                    number=number,
                    manga=manga,
                    title=title,
                    uploaded=uploaded,
                    url=url,
                    downloaded=downloaded,
                    read=read,
                )
            )

        return chapters

    def get_chapter_by_id(self, chapter_id: int) -> Chapter | None:
        query = self.create_query()
        query.prepare(
            "SELECT * FROM chapters INNER JOIN mangas ON mangas.id = chapters.manga_id WHERE chapters.id = :chapter_id;"
        )
        query.bindValue(":chapter_id", chapter_id)

        if not query.exec():
            return logger.error(
                f"Failed to get chapter with id {chapter_id} - {query.lastError().text()}"
            )

        if not query.first():
            return None

        source = source = self.app.source_manager.get_source(
            query.value("mangas.source")
        )
        if source is None:
            return None

        manga = Manga(
            id=query.value("mangas.id"),
            source=source,
            title=query.value("mangas.title"),
            description=query.value("mangas.description"),
            author=query.value("mangas.author"),
            artist=query.value("mangas.artist"),
            thumbnail=query.value("mangas.thumbnail"),
            url=query.value("mangas.url"),
            library=bool(query.value("mangas.library")),
            initialized=bool(query.value("mangas.initialized")),
        )

        return Chapter(
            id=query.value("chapters.id"),
            number=query.value("chapters.number"),
            manga=manga,
            title=query.value("chapters.title"),
            uploaded=datetime.fromtimestamp(query.value("chapters.uploaded")),
            url=query.value("chapters.url"),
            downloaded=bool(query.value("chapters.downloaded")),
            read=bool(query.value("chapters.read")),
        )

    def update_chapters(self, manga: Manga, chapters: list[SourceChapter]) -> bool:
        query = self.create_query()
        query.prepare("SELECT * FROM chapters WHERE manga_id = ?;")
        query.addBindValue(manga.id)
        if not query.exec():
            return False

        saved_chapters: set[Chapter] = set()
        while query.next():
            saved_chapters.add(
                SourceChapter(
                    number=query.value("number"),
                    title=query.value("title"),
                    url=query.value("url"),
                    uploaded=datetime.fromtimestamp(query.value("uploaded")),
                )
            )

        def compare_chapters(
            source_chapter: SourceChapter, saved_chapter: SourceChapter
        ):
            return (
                source_chapter.number != saved_chapter.number
                or source_chapter.title != saved_chapter.title
                or (
                    source_chapter.uploaded.timestamp()
                    != saved_chapter.uploaded.timestamp()
                )
            )

        chapters_to_remove = sorted(
            saved_chapters.difference(chapters), key=lambda chapter: chapter.number
        )
        chapters_to_add = sorted(
            set(chapters).difference(saved_chapters), key=lambda chapter: chapter.number
        )

        chapters_to_update = set()
        for source_chapter in chapters:
            try:
                saved_chapter = next(
                    ch for ch in saved_chapters if ch.url == source_chapter.url
                )
            except StopIteration:
                continue
            if compare_chapters(source_chapter, saved_chapter):
                chapters_to_update.add(source_chapter)

        chapters_to_update: list[Chapter] = sorted(
            chapters_to_update, key=lambda chapter: chapter.number
        )

        if chapters_to_remove:
            query.prepare(
                "DELETE FROM chapters WHERE manga_id = ? AND url = ? AND downloaded = FALSE;"
            )
            query.addBindValue([manga.id] * len(chapters_to_remove))
            query.addBindValue([chapter.url for chapter in chapters_to_remove])
            chapters_removed = query.execBatch()
        else:
            chapters_removed = False

        if chapters_to_add:
            query.prepare(
                """
                INSERT INTO chapters (manga_id, number, title, uploaded, url)
                VALUES (:manga_id, :number, :title, :uploaded, :url)
                ON CONFLICT DO NOTHING;
                """
            )
            query.addBindValue([manga.id] * len(chapters_to_add))
            query.addBindValue([chapter.number for chapter in chapters_to_add])
            query.addBindValue([chapter.title for chapter in chapters_to_add])
            query.addBindValue(
                [chapter.uploaded.timestamp() for chapter in chapters_to_add],
            )
            query.addBindValue([chapter.url for chapter in chapters_to_add])
            chapters_added = query.execBatch()
        else:
            chapters_added = True

        if chapters_to_update:
            query.prepare(
                """
                UPDATE chapters
                SET title = COALESCE(?, title), number = COALESCE(?, number), uploaded = COALESCE(?, uploaded)
                WHERE manga_id = ? AND url = ?;
                """
            )
            query.addBindValue([chapter.title for chapter in chapters_to_update])
            query.addBindValue([chapter.number for chapter in chapters_to_update])
            query.addBindValue(
                [chapter.uploaded.timestamp() for chapter in chapters_to_update],
            )
            query.addBindValue([manga.id] * len(chapters_to_update))
            query.addBindValue([chapter.url for chapter in chapters_to_update])
            chapters_updated = query.execBatch()
        else:
            chapters_updated = False

        if changed := (chapters_added or chapters_removed or chapters_updated):
            self.app.chapter_list_updated.emit(manga)
        return changed

    def mark_chapters_read_status(self, chapters: list[Chapter], *, read: bool) -> None:
        query = self.create_query()
        query.prepare("UPDATE chapters SET read = :read WHERE id = :id;")

        for chapter in filter(lambda chapter: chapter.read != read, chapters):
            query.bindValue(":id", chapter.id)
            query.bindValue(":read", read)

            if query.exec():
                chapter.read = read
                self.app.chapter_read_status_changed.emit(chapter)
            else:
                logger.error(
                    f"Failed to mark chapter ({chapter.title}) as read - {query.lastError().text()}"
                )

    def mark_chapters_download_status(
        self, chapter: Chapter, *, downloaded: bool
    ) -> bool:
        query = self.create_query()
        query.prepare("UPDATE chapters SET downloaded = :downloaded WHERE id = :id;")

        query.bindValue(":id", chapter.id)
        query.bindValue(":downloaded", downloaded)

        if ret := query.exec():
            chapter.downloaded = downloaded
            self.app.chapter_download_status_changed.emit(chapter)
        else:
            logger.error(
                f"Failed mark chapter ({chapter.title}) as downloaded - {query.lastError().text()}"
            )
        return ret

    def commit(self) -> None:
        self._conn.commit()
