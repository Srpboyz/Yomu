from __future__ import annotations

import copy
import importlib
import json
import os
import sys
from dataclasses import dataclass
from hashlib import md5
from logging import getLogger
from typing import Self, TYPE_CHECKING

from PyQt6.QtWidgets import QWidget

from yomu.extension import YomuExtension
from .utils import app_data_path

if TYPE_CHECKING:
    from typing import TypedDict
    from yomu.ui import ReaderWindow
    from .app import YomuApp

    class BaseInfo(TypedDict):
        name: str
        icon: str | None
        enabled: bool

    class ExtenstionModule:
        @staticmethod
        def setup(app: YomuApp) -> YomuExtension: ...


logger = getLogger(__name__)


@dataclass(kw_only=True, slots=True)
class ExtensionInfo:
    id: int
    name: str
    icon: str | None
    enabled: bool
    path: str

    def to_dict(self) -> BaseInfo:
        return {"name": self.name, "icon": self.icon, "enabled": self.enabled}


@dataclass(kw_only=True)
class ExtensionWrapper:
    ext: YomuExtension | None
    info: ExtensionInfo


class DependencyHandler:
    def __init__(self, path: str):
        dependency_path = os.path.join(path, "dependencies")

        self.dependency_path = (
            dependency_path if os.path.exists(dependency_path) else None
        )
        self._modules = set(sys.modules)

    def __enter__(self) -> Self:
        if self.dependency_path is not None:
            sys.path.append(self.dependency_path)
        return self

    def __exit__(self, *_, **__) -> None:
        if self.dependency_path is not None:
            sys.path.pop()

        new_mods = set(sys.modules) - self._modules
        for mod in new_mods:
            sys.modules.pop(mod, None)


class ExtensionManager:
    def __init__(self, app: YomuApp) -> None:
        self.app = app
        self._extensions: dict[int, ExtensionWrapper] = {}

    def handle_dependency(self, path: str) -> DependencyHandler:
        return DependencyHandler(path)

    def _load_extensions(self) -> None:
        appdata = app_data_path()
        sys.path.append(appdata)

        extensions_folder = os.path.join(appdata, "extensions")
        if not os.path.exists(extensions_folder):
            os.makedirs(extensions_folder)

        for extension_dir in os.listdir(extensions_folder):
            path = os.path.join(extensions_folder, extension_dir)

            ext_data = os.path.join(path, "extension.json")
            if not os.path.exists(ext_data):
                continue

            try:
                with open(ext_data, encoding="utf-8") as f:
                    ext_info: BaseInfo = json.load(f)
            except Exception:
                continue

            enabled = ext_info.get("enabled", False)
            if not isinstance(enabled, bool):
                enabled = False

            name = ext_info.get("name", extension_dir)
            if not isinstance(name, str):
                name = extension_dir

            icon = ext_info.get("icon")
            if icon is not None and not isinstance(icon, str):
                icon = None

            ext_id = int(str(int(md5(extension_dir.encode()).hexdigest(), 16))[:12])
            if enabled:
                with self.handle_dependency(path):
                    try:
                        mod: ExtenstionModule = importlib.import_module(f".{extension_dir}", package="extensions")  # fmt:skip
                    except Exception as e:
                        logger.error(
                            f"Failed to import: {e.__class__.__name__} - {e}",
                            exc_info=e,
                        )
                        mod = None

                    if mod is not None:
                        try:
                            extension = mod.setup(app=self.app)
                        except Exception as e:
                            enabled, extension = False, None
                            logger.error(
                                f"Failed to initialize: {e.__class__.__name__} - {e}",
                                exc_info=e,
                            )
                        else:
                            if not isinstance(extension, YomuExtension):
                                enabled, extension = False, None
                    else:
                        enabled, extension = False, None
            else:
                extension = None

            ext_info = ExtensionInfo(
                id=ext_id, name=name, icon=icon, enabled=enabled, path=path
            )
            self._extensions[ext_id] = ExtensionWrapper(ext=extension, info=ext_info)

        sys.path.remove(appdata)

    @property
    def extensions(self) -> tuple[ExtensionInfo]:
        return tuple(copy.copy(wrapper.info) for wrapper in self._extensions.values())

    def enable_extension(self, ext_id: int) -> None:
        if (wrapper := self._extensions.get(ext_id)) is None:
            return

        ext_info = wrapper.info
        if ext_info.enabled:
            return
        ext_info.enabled = True

        path = os.path.join(ext_info.path, "extension.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ext_info.to_dict(), f, indent=4)

        self.app.display_message("You must restart the app to reload the extension.")

    def disable_extension(self, ext_id: int) -> None:
        if (wrapper := self._extensions.get(ext_id)) is None:
            return

        extension = wrapper.ext
        if extension is not None:
            try:
                extension.unload()
            except Exception:
                ...
            extension.deleteLater()
            wrapper.ext = None

        ext_info = wrapper.info
        if not ext_info.enabled:
            return
        ext_info.enabled = False

        path = os.path.join(ext_info.path, "extension.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ext_info.to_dict(), f, indent=4)

        self.app.extension_disabled.emit(ext_info)

    def get_extension_settings(self, ext_id: int) -> QWidget | None:
        wrapper = self._extensions.get(ext_id)
        if wrapper is None:
            return

        if not wrapper.info.enabled:
            return

        widget = wrapper.ext.settings_widget()
        if widget is not None:
            wrapper.ext.destroyed.connect(widget.deleteLater)
        return widget
