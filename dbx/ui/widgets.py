"""Widget condivisi: editor di proprietà dell'Object Inspector (D4)."""

from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class PropertyEditor(QWidget):
    """Editor generico chiave/valore con widget per tipo."""

    changed = pyqtSignal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row = QVBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._form: QFormLayout | None = None
        self._widgets: dict[str, QWidget] = {}
        self._types: dict[str, str] = {}
        self._order: list[str] = []
        self._loading = False

    def clear(self) -> None:
        while self._row.count():
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._widgets = {}
        self._types = {}
        self._order = []
        self._form = None

    def set_properties(self, specs: Iterable[tuple[str, str, str, Any, Any]]) -> None:
        """specs: (chiave, etichetta, tipo, valore, opzioni extra)."""
        self.clear()
        self._loading = True
        container = QWidget(self)
        form = QFormLayout(container)
        form.setContentsMargins(6, 6, 6, 6)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self._form = form
        self._row.addWidget(container)
        for key, label, kind, value, extra in specs:
            self._types[key] = kind
            self._order.append(key)
            widget = self._build(kind, value, extra)
            self._widgets[key] = widget
            form.addRow(QLabel(label), widget)
        self._loading = False

    def _build(self, kind: str, value: Any, extra: Any) -> QWidget:
        key_placeholder = None
        if kind == "text":
            widget = QLineEdit(str(value or ""))
            widget.textEdited.connect(lambda text, w=widget: self._emit(w, text))
            return widget
        if kind == "multiline":
            widget = QPlainTextEdit(str(value or ""))
            widget.setFixedHeight(max(60, extra if isinstance(extra, int) else 90))
            widget.textChanged.connect(lambda w=widget: self._emit(w, w.toPlainText()))
            return widget
        if kind == "int":
            widget = QSpinBox()
            widget.setRange(-1_000_000, 10_000_000)
            widget.setValue(int(value or 0))
            widget.valueChanged.connect(lambda v, w=widget: self._emit(w, v))
            return widget
        if kind == "float":
            widget = QDoubleSpinBox()
            widget.setRange(-1_000_000, 10_000_000)
            widget.setDecimals(2)
            widget.setValue(float(value or 0))
            widget.valueChanged.connect(lambda v, w=widget: self._emit(w, v))
            return widget
        if kind == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.toggled.connect(lambda v, w=widget: self._emit(w, v))
            return widget
        if kind == "choice":
            widget = QComboBox()
            options = list(extra or [])
            for option in options:
                if isinstance(option, tuple):
                    widget.addItem(str(option[1]), option[0])
                else:
                    widget.addItem(str(option), option)
            index = widget.findData(value)
            if index < 0:
                index = widget.findText(str(value or ""))
            widget.setCurrentIndex(max(0, index))
            widget.currentIndexChanged.connect(lambda _i, w=widget: self._emit(w, w.currentData()))
            return widget
        if kind == "color":
            widget = QLineEdit(str(value or ""))
            widget.setPlaceholderText("#rrggbb")
            widget.textEdited.connect(lambda text, w=widget: self._emit(w, text))
            return widget
        assert key_placeholder is None
        widget = QLineEdit(str(value or ""))
        widget.textEdited.connect(lambda text, w=widget: self._emit(w, text))
        return widget

    def _emit(self, widget: QWidget, value: Any) -> None:
        if self._loading:
            return
        for key, candidate in self._widgets.items():
            if candidate is widget:
                self.changed.emit(key, value)
                return

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in self._order:
            widget = self._widgets[key]
            if isinstance(widget, QLineEdit):
                result[key] = widget.text()
            elif isinstance(widget, QPlainTextEdit):
                result[key] = widget.toPlainText()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                result[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                result[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentData()
        return result

    def value(self, key: str) -> Any:
        return self.values().get(key)

