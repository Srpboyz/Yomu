from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QMouseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidgetItem,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from yomu.core import utils
from .reader import Reader

if TYPE_CHECKING:
    from yomu.core.extensionmanager import ExtensionInfo, ExtensionManager
    from yomu.source import Source
    from .window import ReaderWindow


class BoolOption(QCheckBox):
    value_changed = pyqtSignal((str, object))

    def __init__(self, key: str, name: str, value: bool) -> None:
        super().__init__()
        self.key = key
        self.setText(name)
        self.setChecked(value)
        self.checkStateChanged.connect(self._check_state_changed)

    def _check_state_changed(self, state: Qt.CheckState) -> None:
        self.value_changed.emit(self.key, state == Qt.CheckState.Checked)


class Keybinds(QTableWidget):
    def __init__(self, parent: Settings) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setColumnCount(2)

        self.verticalHeader().hide()
        self.setHorizontalHeaderLabels(("Name", "Keybind"))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)

        self.set_keybindings(utils.get_keybinds())

    def mousePressEvent(self, e: QMouseEvent | None) -> None: ...

    def set_keybindings(self, keybinds: dict[str, utils.Keybind]) -> None:
        self.setRowCount(sum(len(data["keybinds"]) for data in keybinds.values()))

        row = 0
        for name, data in keybinds.items():
            item = QTableWidgetItem(name)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setToolTip(data["description"])
            self.setItem(row, 0, item)

            for keybind in data["keybinds"]:
                item = QTableWidgetItem(keybind)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.setItem(row, 1, item)
                row += 1


class Settings(QDialog):
    def __init__(self, window: ReaderWindow) -> None:
        super().__init__(window)
        self.setWindowTitle("Settings")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.settings = window.app.settings
        self.setContentsMargins(0, 0, 0, 0)

        tab_view = QTabWidget(self)
        tab_view.setContentsMargins(0, 0, 0, 0)

        widget = QFrame(tab_view)
        layout = QVBoxLayout(widget)
        layout.addWidget(self._create_general_settings())
        layout.addWidget(
            self._create_library_settings(window.app.source_manager.sources)
        )
        layout.addWidget(self._create_reader_settings(window))
        widget.setLayout(layout)
        tab_view.addTab(widget, "Settings")

        extension_settings = QFrame(self)
        layout = QVBoxLayout(extension_settings)
        for ext_settings in self._create_extension_settings(
            window.app.extension_manager
        ):
            layout.addWidget(ext_settings)
        tab_view.addTab(extension_settings, "Extensions")

        keybinds_table = Keybinds(self)
        window.app.keybinds_changed.connect(keybinds_table.set_keybindings)
        tab_view.addTab(keybinds_table, "Keybinds")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(tab_view)
        self.setLayout(layout)

        self.resize(340, 350)

    parent: Callable[[], ReaderWindow]

    def _create_general_settings(self) -> QGroupBox:
        general_settings_group = QGroupBox(QWidget.tr("General"), self)
        general_group_layout = QVBoxLayout(general_settings_group)

        key = "offline_mode"
        offline_settings = BoolOption(
            key, "Offline Mode", self.settings.value(key, False, bool)
        )
        offline_settings.value_changed.connect(self._option_changed)

        key = "autodelete_chapter"
        delete_after_read = BoolOption(
            key, "Autodelete Chapter after Read", self.settings.value(key, False, bool)
        )
        delete_after_read.value_changed.connect(self._option_changed)

        delete_after_read_label = QLabel()
        delete_after_read_label.setWordWrap(True)
        delete_after_read_label.setText(
            "Automatically delete a chapter after its been marked as read"
        )

        general_group_layout.addWidget(offline_settings)
        general_group_layout.addSpacing(10)
        general_group_layout.addWidget(delete_after_read)
        general_group_layout.addWidget(delete_after_read_label)
        return general_settings_group

    def _library_source_changed(self, index: int) -> None:
        combo_box: QComboBox = self.sender()
        source: Source | None = combo_box.itemData(index)
        self.parent().library.set_source(source)

    def _create_library_settings(self, sources: list[Source]) -> QGroupBox:
        library_settings_group = QGroupBox(QWidget.tr("Library"), self)
        library_group_layout = QVBoxLayout(library_settings_group)

        combo_box = QComboBox()
        combo_box.addItem("All", None)
        for source in sources:
            combo_box.addItem(source.name, source)
        combo_box.setCurrentText("All")
        combo_box.currentIndexChanged.connect(self._library_source_changed)

        combo_box_label = QLabel()
        combo_box_label.setText(
            "Sets the visible manga to a specific source for the library"
        )

        library_group_layout.addWidget(combo_box)
        library_group_layout.addWidget(combo_box_label)
        return library_settings_group

    def _create_reader_settings(self, window: ReaderWindow) -> QGroupBox:
        reader_settings_group = QGroupBox(QWidget.tr("Reader"), self)
        reader_group_layout = QVBoxLayout(reader_settings_group)

        combo_box = QComboBox()
        combo_box.currentTextChanged.connect(window.reader.set_view)
        window.reader.view_changed.connect(combo_box.setCurrentText)
        combo_box.addItems(Reader.views.keys())
        combo_box.setCurrentText("Webtoon")

        combo_box_label = QLabel()
        combo_box_label.setText("Set this window's current reader mode")

        reader_group_layout.addWidget(combo_box)
        reader_group_layout.addWidget(combo_box_label)
        return reader_settings_group

    def _create_extension_settings(
        self, extension_manager: ExtensionManager
    ) -> list[QGroupBox]:
        def create_checkbox(extension: ExtensionInfo) -> QCheckBox:
            def set_enabled(state: Qt.CheckState):
                if state == Qt.CheckState.Checked:
                    extension_manager.enable_extension(extension.id)
                else:
                    extension_manager.disable_extension(extension.id)

            checkbox = QCheckBox("Enabled")
            checkbox.setChecked(extension.enabled)
            checkbox.checkStateChanged.connect(set_enabled)
            return checkbox

        settings = []
        for ext in extension_manager.extensions:
            ext_settings_group = QGroupBox(QWidget.tr(ext.name), self)
            ext_group_layout = QVBoxLayout(ext_settings_group)
            ext_group_layout.addWidget(create_checkbox(ext))
            settings.append(ext_settings_group)

            try:
                settings_widget = extension_manager.get_extension_settings(ext.id)
            except Exception as e:
                continue

            if settings_widget is None:
                continue

            ext_group_layout.addWidget(settings_widget)

        return settings

    def _option_changed(self, key: str, new_value: bool) -> None:
        self.settings.setValue(key, new_value)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.hide()
        a0.ignore()
