"""Widget condivisi: editor di proprietà e Object Inspector ad albero (D4)."""

from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QStyledItemDelegate,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

TRUE_TEXT = ".T."
FALSE_TEXT = ".F."


def parse_bool(text: str, default: bool = False) -> bool:
    """Interpreta ``.T.``/``.F.`` e le forme testuali comuni."""
    lowered = str(text).strip().lower()
    if lowered in (".t.", "t", "true", "sì", "si", "yes", "1", "on"):
        return True
    if lowered in (".f.", "f", "false", "no", "0", "off"):
        return False
    return default


def format_bool(value: Any) -> str:
    return TRUE_TEXT if bool(value) else FALSE_TEXT


class _InspectorDelegate(QStyledItemDelegate):
    """Combo in-cell per valori enumerati e booleani in stile dBASE."""

    def __init__(self, inspector: "PropertyInspector") -> None:
        super().__init__(inspector)
        self.inspector = inspector

    def createEditor(self, parent, option, index):  # noqa: N802 - API Qt
        item = self.inspector.tree.itemFromIndex(index)
        if item is None:
            return super().createEditor(parent, option, index)
        kind = str(item.data(0, Qt.ItemDataRole.UserRole) or "text")
        if kind not in ("choice", "bool"):
            return super().createEditor(parent, option, index)
        combo = QComboBox(parent)
        if kind == "bool":
            combo.addItem(TRUE_TEXT, True)
            combo.addItem(FALSE_TEXT, False)
        else:
            key = str(item.data(0, Qt.ItemDataRole.UserRole + 1) or "")
            for candidate in self.inspector._options.get(key, []):
                if isinstance(candidate, tuple):
                    combo.addItem(str(candidate[1]), candidate[0])
                else:
                    combo.addItem(str(candidate), candidate)
        return combo

    def setEditorData(self, editor, index) -> None:  # noqa: N802 - API Qt
        if not isinstance(editor, QComboBox):
            return super().setEditorData(editor, index)
        data = index.data(Qt.ItemDataRole.UserRole + 2)
        position = editor.findData(data)
        if position < 0:
            position = editor.findText(str(index.text()))
        editor.setCurrentIndex(max(0, position))

    def setModelData(self, editor, model, index) -> None:  # noqa: N802 - API Qt
        if not isinstance(editor, QComboBox):
            return super().setModelData(editor, model, index)
        model.setData(index, editor.currentText(), Qt.ItemDataRole.DisplayRole)


class PropertyInspector(QWidget):
    """Object Inspector a tre schede: Properties, Events, Methods."""

    property_changed = pyqtSignal(str, object)
    event_changed = pyqtSignal(str, str)
    method_changed = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Quick Filter:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("filtra le proprietà")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self.apply_filter)
        filter_row.addWidget(self.filter_edit, 1)
        layout.addLayout(filter_row)

        self.tabs = QTabWidget()
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Property", "Value"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(False)
        self.tree.header().setStretchLastSection(True)
        self.tree.setColumnWidth(0, 104)
        self.tree.itemChanged.connect(self._on_item_changed)
        self._delegate = _InspectorDelegate(self)
        self.tree.setItemDelegateForColumn(1, self._delegate)
        self.tabs.addTab(self.tree, "Proprietà")

        self.events = QTableWidget(0, 2)
        self.events.setHorizontalHeaderLabels(["Evento", "Azione"])
        self.events.horizontalHeader().setStretchLastSection(True)
        self.events.verticalHeader().setVisible(False)
        self.events.setColumnWidth(0, 104)
        self.events.itemChanged.connect(self._on_event_changed)
        events_page = QWidget()
        events_layout = QVBoxLayout(events_page)
        events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_hint = QLabel(
            "Azione singola: save · new · delete · next · close · script:nome · report:nome · message:testo"
        )
        self.events_hint.setObjectName("nav_hint")
        self.events_hint.setWordWrap(True)
        events_layout.addWidget(self.events, 1)
        events_layout.addWidget(self.events_hint)
        self.tabs.addTab(events_page, "Eventi")

        self.methods = QTableWidget(0, 2)
        self.methods.setHorizontalHeaderLabels(["Metodo", "Corpo"])
        self.methods.horizontalHeader().setStretchLastSection(True)
        self.methods.verticalHeader().setVisible(False)
        self.methods.setColumnWidth(0, 104)
        self.methods.itemChanged.connect(self._on_method_changed)
        methods_page = QWidget()
        methods_layout = QVBoxLayout(methods_page)
        methods_layout.setContentsMargins(0, 0, 0, 0)
        self.methods_hint = QLabel(
            "I corpi dei metodi sono testo descrittivo: il runtime non esegue un linguaggio di scripting."
        )
        self.methods_hint.setObjectName("nav_hint")
        self.methods_hint.setWordWrap(True)
        methods_layout.addWidget(self.methods, 1)
        methods_layout.addWidget(self.methods_hint)
        self.tabs.addTab(methods_page, "Metodi")

        layout.addWidget(self.tabs, 1)
        self._loading = False
        self._options: dict[str, list[tuple[str, Any]]] = {}
        self._groups: dict[str, QTreeWidgetItem] = {}

    # -------------------------------------------------------------- proprietà
    def set_properties(self, groups: Iterable[tuple[str, Iterable[tuple]]]) -> None:
        """groups: (titolo gruppo, [(chiave, etichetta, tipo, valore, opzioni)])."""
        self._loading = True
        self.tree.clear()
        self._groups = {}
        self._options = {}
        for group_title, rows in groups:
            group_item = QTreeWidgetItem(self.tree, [group_title, ""])
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            group_item.setExpanded(True)
            self._groups[group_title] = group_item
            for key, label, kind, value, extra in rows:
                child = QTreeWidgetItem(group_item, [label, ""])
                child.setData(0, Qt.ItemDataRole.UserRole, kind)
                child.setData(0, Qt.ItemDataRole.UserRole + 1, key)
                child.setData(0, Qt.ItemDataRole.UserRole + 2, value)
                flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                if kind == "ro":
                    child.setText(1, self._format("text", value))
                    child.setFlags(flags)
                elif kind == "choice":
                    options = list(extra or [])
                    self._options[key] = options
                    child.setText(1, self._choice_label(options, value))
                    child.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                elif kind == "bool":
                    child.setText(1, format_bool(value))
                    child.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
                else:
                    child.setText(1, self._format(kind, value))
                    child.setFlags(flags | Qt.ItemFlag.ItemIsEditable)
        self._loading = False
        self.apply_filter(self.filter_edit.text())

    @staticmethod
    def _format(kind: str, value: Any) -> str:
        if kind == "bool":
            return format_bool(value)
        if kind in ("int", "float"):
            return str(value)
        return "" if value is None else str(value)

    @staticmethod
    def _choice_label(options: list[Any], value: Any) -> str:
        for option in options:
            if isinstance(option, tuple):
                if option[0] == value:
                    return str(option[1])
            elif option == value:
                return str(option)
        return str(value if value is not None else "")

    @staticmethod
    def _choice_value(options: list[Any], text: str) -> Any:
        for option in options:
            if isinstance(option, tuple):
                if str(option[1]) == text:
                    return option[0]
            elif str(option) == text:
                return option
        return text

    def _on_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._loading:
            return
        key = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not key:
            return
        kind = str(item.data(0, Qt.ItemDataRole.UserRole) or "text")
        if kind == "ro":
            return
        previous = item.data(0, Qt.ItemDataRole.UserRole + 2)
        text = item.text(1)
        if kind == "int":
            try:
                value: Any = int(float(text.strip() or 0))
            except ValueError:
                value = previous
                text = self._format(kind, previous)
        elif kind == "float":
            try:
                value = float(text.strip().replace(",", ".") or 0)
            except ValueError:
                value = previous
                text = self._format(kind, previous)
        elif kind == "bool":
            value = parse_bool(text, bool(previous))
            text = format_bool(value)
        elif kind == "choice":
            value = self._choice_value(self._options.get(str(key), []), text)
        else:
            value = text
        self._loading = True
        item.setText(1, text)
        item.setData(0, Qt.ItemDataRole.UserRole + 2, value)
        self._loading = False
        self.property_changed.emit(str(key), value)

    def items(self) -> list[QTreeWidgetItem]:
        result: list[QTreeWidgetItem] = []
        for index in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(index)
            for child_index in range(group.childCount()):
                result.append(group.child(child_index))
        return result

    def item(self, key: str) -> QTreeWidgetItem | None:
        for child in self.items():
            if child.data(0, Qt.ItemDataRole.UserRole + 1) == key:
                return child
        for child in self.items():
            if child.text(0) == key:
                return child
        return None

    def apply_filter(self, text: str) -> None:
        needle = str(text or "").strip().lower()
        for index in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(index)
            visible_children = 0
            for child_index in range(group.childCount()):
                child = group.child(child_index)
                match = not needle or needle in child.text(0).lower() or needle in child.text(1).lower()
                child.setHidden(not match)
                visible_children += 1 if match else 0
            group.setHidden(visible_children == 0)
            if needle and visible_children:
                group.setExpanded(True)

    # ----------------------------------------------------------------- eventi
    def set_events(self, rows: Iterable[tuple[str, str, str]]) -> None:
        """rows: (nome evento, descrizione, azione)."""
        self._loading = True
        self.events.setRowCount(0)
        for name, description, action in rows:
            row = self.events.rowCount()
            self.events.insertRow(row)
            label = QTableWidgetItem(f"{name} — {description}")
            label.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            label.setData(Qt.ItemDataRole.UserRole, name)
            self.events.setItem(row, 0, label)
            value = QTableWidgetItem(str(action or ""))
            value.setData(Qt.ItemDataRole.UserRole, name)
            self.events.setItem(row, 1, value)
        self._loading = False

    def _on_event_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if name:
            self.event_changed.emit(name, item.text())

    # ---------------------------------------------------------------- metodi
    def set_methods(self, rows: Iterable[tuple[str, str, str]]) -> None:
        """rows: (nome metodo, descrizione, corpo)."""
        self._loading = True
        self.methods.setRowCount(0)
        for name, description, body in rows:
            row = self.methods.rowCount()
            self.methods.insertRow(row)
            label = QTableWidgetItem(f"{name} — {description}")
            label.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            label.setData(Qt.ItemDataRole.UserRole, name)
            self.methods.setItem(row, 0, label)
            value = QTableWidgetItem(str(body or ""))
            value.setData(Qt.ItemDataRole.UserRole, name)
            self.methods.setItem(row, 1, value)
        self._loading = False

    def _on_method_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if name:
            self.method_changed.emit(name, item.text())


class PropertyEditor(QWidget):
    """Editor generico chiave/valore con widget per tipo (report designer)."""

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

