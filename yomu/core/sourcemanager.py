from __future__ import annotations

import importlib
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

    def _load_source(self, cls: type[Source]) -> None:
        try:
            source = cls(self.app.network)
        except Exception as e:
            logger.error(
                f"Failed to load source {getattr(cls, 'name', cls.__name__)}",
                exc_info=e,
            )
            return None

        if source.id in self._sources:
            logger.error(
                f"Duplicate source id between {self._sources[source.id].name} and {source.name}"
            )
            return None

        self._sources[source.id] = source

    def _load_sources(self) -> None:
        from _sources import _default_sources

        for cls in _default_sources():
            self._load_source(cls)

        appdata = app_data_path()
        sys.path.append(appdata)

        source_folder = os.path.join(appdata, "sources")
        if not os.path.exists(source_folder):
            os.makedirs(source_folder)

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
                    self._load_source(cls)

        sys.path.remove(appdata)

    def get_source(self, id: int) -> Source | None:
        return self._sources.get(id)

    @overload
    def update_source_filters(self, source: int, new_filters: dict) -> None: ...

    @overload
    def update_source_filters(self, source: Source, new_filters: dict) -> None: ...

    def update_source_filters(self, source: Source | int, new_filters: dict) -> None:
        if isinstance(source, int) and (source := self.get_source(source)) is None:
            return

        try:
            if bool(source.update_filters(new_filters)):
                self.app.source_filters_updated.emit(source, new_filters)
        except Exception:
            pass
