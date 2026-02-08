from __future__ import annotations

import importlib
import json
import os
import sys
from logging import getLogger
from typing import TYPE_CHECKING, overload

from yomu.source import Source
from .utils import app_data_path

if TYPE_CHECKING:
    from .app import YomuApp

logger = getLogger(__name__)


class SourceManager:
    def __init__(self, app: YomuApp) -> None:
        self.app = app
        self._sources: dict[int, Source] = {}

    @property
    def sources(self) -> tuple[Source]:
        return tuple(self._sources.values())

    def _load_source_filters(self) -> dict:
        """Get the saved source filters"""
        path = os.path.join(app_data_path(), "source_filters.json")
        if not os.path.exists(path):
            return {}

        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_source_filters(self, filters: dict) -> None:
        """Write the updated source filters to file"""
        path = os.path.join(app_data_path(), "source_filters.json")
        with open(path, "w") as f:
            json.dump(filters, f, indent=4)

    def load_source(self, cls: type[Source]) -> Source | None:
        """Load source from class"""
        try:
            source = cls(self.app.network)
        except Exception as e:
            logger.error(
                f"Failed to load source {getattr(cls, 'name', cls.__name__)}",
                exc_info=e,
            )
            return None

        if source.id in self._sources:
            logger.error(f"Error adding {source.name} - {source.id} in use")
            return None

        self._sources[source.id] = source
        self.app.downloader.handle_source_icon(source)
        return source

    def _load_sources(self) -> None:
        from _sources import _default_sources

        appdata = app_data_path()
        sys.path.append(appdata)

        source_folder = os.path.join(appdata, "sources")
        os.makedirs(source_folder, exist_ok=True)

        source_cls = _default_sources()
        for source_dir in os.listdir(source_folder):
            try:
                mod = importlib.import_module(f".{source_dir}", package="sources")  # fmt:skip
            except Exception as e:
                logger.error(
                    f"Failed to load source directory {source_dir}", exc_info=e
                )
                continue

            for obj_name in dir(mod):
                cls = getattr(mod, obj_name)
                if (
                    isinstance(cls, type)
                    and cls is not Source
                    and issubclass(cls, Source)
                ):
                    source_cls.append(cls)

        source_filters = self._load_source_filters()
        for cls in source_cls:
            try:
                source = self.load_source(cls)
            except Exception as e:
                logger.error(f"Failed to load source", exc_info=e)
                continue

            if source is None or str(source.id) not in source_filters:
                continue

            self.update_source_filters(
                source, source_filters[str(source.id)], update_file=False
            )

        sys.path.remove(appdata)

    def get_source(self, id: int) -> Source | None:
        return self._sources.get(id)

    @overload
    def update_source_filters(
        self, source: int, new_filters: dict, *, update_file: bool = True
    ) -> None: ...

    @overload
    def update_source_filters(
        self, source: Source, new_filters: dict, *, update_file: bool = True
    ) -> None: ...

    def update_source_filters(
        self, source: Source | int, new_filters: dict, *, update_file: bool = True
    ) -> None:
        if isinstance(source, int) and (source := self.get_source(source)) is None:
            return

        try:
            if not bool(source.update_filters(new_filters)):
                return
        except Exception as e:
            logger.error(f"Failed to update filters for {source.name}", exc_info=e)
            return

        if update_file:
            source_filters = self._load_source_filters()
            source_filters[str(source.id)] = new_filters
            self._save_source_filters(source_filters)

        self.app.source_filters_updated.emit(source, new_filters)
