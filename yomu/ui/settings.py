from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from .window import ReaderWindow


class BoolOption(QCheckBox):
    value_changed = pyqtSignal((str, object))

    def __init__(self, name: str, value: bool) -> None:
        super().__init__()
        self.setText(name)
        self.setChecked(value)
        self.checkStateChanged.connect(self._check_state_changed)

    def _check_state_changed(self, state: Qt.CheckState) -> None:
        self.value_changed.emit(self.text(), state == Qt.CheckState.Checked)


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

        widget = QFrame()

        general_settings = QGroupBox(self)
        general_settings.setTitle(QWidget.tr("General"))
        general_layout = QVBoxLayout(general_settings)

        offline_settings = BoolOption(
            "Offline Mode", self.settings.value("offline_mode", False, bool)
        )
        offline_settings.value_changed.connect(self._option_changed)

        delete_after_read = BoolOption(
            "Autodelete chapter after read",
            self.settings.value("autodelete_chapter_after_read", False, bool),
        )
        delete_after_read.value_changed.connect(self._option_changed)

        delete_after_read_label = QLabel()
        delete_after_read_label.setWordWrap(True)
        delete_after_read_label.setText(
            "Automatically delete a chapter after its been marked as read"
        )

        general_layout.addWidget(offline_settings)
        general_layout.addSpacing(10)
        general_layout.addWidget(delete_after_read)
        general_layout.addWidget(delete_after_read_label)

        reader_settings = QGroupBox(self)
        reader_settings.setTitle(QWidget.tr("Reader"))
        reader_layout = QVBoxLayout(reader_settings)

        from .reader import Reader

        view_list = QComboBox()
        view_list.currentTextChanged.connect(window.reader.set_view)
        window.reader.view_changed.connect(view_list.setCurrentText)
        view_list.addItems(Reader.views.keys())
        view_list.setCurrentText("Webtoon")

        view_list_label = QLabel()
        view_list_label.setText("Set this window's current reader mode")

        reader_layout.addWidget(view_list)
        reader_layout.addWidget(view_list_label)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(general_settings)
        layout.addWidget(reader_settings)
        widget.setLayout(layout)

        keybinds_Table = Keybinds(self)
        window.app.keybinds_changed.connect(keybinds_Table.set_keybindings)

        tab_view = QTabWidget(self)
        tab_view.setContentsMargins(0, 0, 0, 0)
        tab_view.addTab(widget, "Settings")
        tab_view.addTab(keybinds_Table, "Keybinds")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(tab_view)
        self.setLayout(layout)

        self.resize(338, 250)

    def _option_changed(self, name: str, newValue: bool) -> None:
        self.settings.setValue(name.replace(" ", "_").lower(), newValue)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.hide()
        a0.ignore()
