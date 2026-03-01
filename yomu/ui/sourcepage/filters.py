from typing import TYPE_CHECKING

from PyQt6.QtCore import QSizeF, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from yomu.source import FilterOption, FilterType

if TYPE_CHECKING:
    from .core import SourcePage


class CheckBox(QCheckBox):
    def __init__(self, parent: FilterDialog, key: str, name: str, value: bool) -> None:
        super().__init__(name, parent)
        self.setChecked(value)
        self.key = key

    def get_new_value(self) -> bool:
        return self.isChecked()


class ListOptions(QWidget):
    def __init__(
        self,
        parent: FilterDialog,
        key: str,
        name: str,
        values: list[str],
        options: list[str],
    ) -> None:
        super().__init__(parent)
        self.key = key

        self.list_widget = QListWidget(self)
        self.list_widget.addItems((option.capitalize() for option in options))

        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text().lower() in values:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(QLabel(name, self))
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def get_new_value(self) -> bool:
        return [
            item.text().lower()
            for i in range(self.list_widget.count())
            if (item := self.list_widget.item(i)).checkState() == Qt.CheckState.Checked
        ]


class FilterDialog(QDialog):
    def __init__(self, source_page: SourcePage) -> None:
        super().__init__(source_page)
        self.source_page = source_page
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.WindowModal)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setContentsMargins(0, 0, 0, 0)

        self.widget = QWidget(scroll_area)
        layout = QVBoxLayout(self.widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self.widget.setLayout(layout)
        scroll_area.setWidget(self.widget)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        layout.addWidget(QLabel("Filters", self))
        layout.addWidget(scroll_area)
        layout.addWidget(buttonbox)
        self.setLayout(layout)

    def accept(self) -> None:
        new_filters = {}

        layout = self.widget.layout()
        for _ in range(layout.count()):
            widget: CheckBox | ListOptions = layout.takeAt(0).widget()
            new_filters[widget.key] = widget.get_new_value()
            widget.deleteLater()

        self.source_page._source_filters_updated(new_filters)
        return super().accept()

    def reject(self):
        layout = self.widget.layout()
        for _ in range(layout.count()):
            layout.takeAt(0).widget().deleteLater()
        return super().reject()

    def exec(self, filters: dict[str, FilterOption]) -> None:
        layout: QVBoxLayout = self.widget.layout()
        for _ in range(layout.count()):
            layout.takeAt(0).widget().deleteLater()

        for key, filter in filters.items():
            name = filter.get("display_name", key)
            value = filter.get("value", False)
            if filter["type"] == FilterType.CHECKBOX:
                layout.addWidget(CheckBox(self, key, name, value))
            elif filter["type"] == FilterType.LIST:
                options = filter.get("options", [])
                layout.addWidget(ListOptions(self, key, name, value, options))

        width, height = 356, 200
        if (self.source_page.width() * 0.75) < 356:
            width = self.source_page.width() * 0.75
        if (self.source_page.height() * 0.75) < 200:
            height = self.source_page.height() * 0.75
        self.setFixedSize(QSizeF(width, height).toSize())

        window = self.source_page.window()
        pos = window.pos()
        pos.setX(int((window.width() - self.width()) / 2) + pos.x())
        pos.setY(int((window.height() - self.height()) / 2) + pos.y())
        self.show()
