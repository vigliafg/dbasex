"""Table Builder: finestra Table Structure in stile dBASE (C1–C4)."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Callable

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core import ddl
from ..core import types as T
from ..core.metadata import (
    Field,
    ForeignKey,
    Index,
    MetadataError,
    Table,
    new_id,
    ON_DELETE_ACTIONS,
)
from ..core.project import Project, ProjectError
from ..runtime.rowset import RowsetError
from ..ui import design, icons

FIELD_COLUMNS = ["Field", "Name", "Type", "Width", "Decimal", "Index"]
COL_FIELD, COL_NAME, COL_TYPE, COL_WIDTH, COL_DECIMAL, COL_INDEX = range(6)
NO_INDEX = "(nessuno)"
_DECIMALS_RE = re.compile(r"^\.(\d+)f$")


def decimals_from_fmt(fmt: str) -> int:
    match = _DECIMALS_RE.match(fmt or "")
    return int(match.group(1)) if match else 0


def fmt_from_decimals(decimals: int) -> str:
    return f".{decimals}f" if decimals > 0 else ""


def human_size(value: int | None) -> str:
    if value is None:
        return "—"
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value / (1024 * 1024):.1f} MB"


class ChoiceDelegate(QStyledItemDelegate):
    """Delegate con combo per le colonne Type e Index."""

    def __init__(self, provider: Callable[[], list[tuple[str, str]]], parent=None) -> None:
        super().__init__(parent)
        self._provider = provider

    def createEditor(self, parent, option, index):  # noqa: N802 - API Qt
        combo = QComboBox(parent)
        for label, key in self._provider():
            combo.addItem(label, key)
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:  # noqa: N802 - API Qt
        key = index.data(Qt.ItemDataRole.UserRole)
        position = editor.findData(key)
        editor.setCurrentIndex(max(0, position))

    def setModelData(self, editor: QComboBox, model, index) -> None:  # noqa: N802 - API Qt
        model.setData(index, editor.currentText(), Qt.ItemDataRole.DisplayRole)
        model.setData(index, editor.currentData(), Qt.ItemDataRole.UserRole)


class FieldGrid(QTableWidget):
    """Griglia dei campi con trascinamento del numero di riga per riordinare."""

    row_move_requested = pyqtSignal(int, int)

    def __init__(self, rows: int, columns: int, parent: QWidget | None = None) -> None:
        super().__init__(rows, columns, parent)
        self._drag_from: int | None = None

    def mousePressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.position().toPoint())
            if index.isValid() and index.column() == COL_FIELD:
                self._drag_from = index.row()
                self.setCursor(Qt.CursorShape.SizeVerCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self._drag_from is not None:
            index = self.indexAt(event.position().toPoint())
            target = index.row() if index.isValid() else self.rowCount() - 1
            source = self._drag_from
            self._drag_from = None
            self.unsetCursor()
            if target >= 0 and target != source:
                self.row_move_requested.emit(source, target)
        super().mouseReleaseEvent(event)


class SaveTableDialog(QDialog):
    """Dialog ``Save Table``: nome e didascalia della copia."""

    def __init__(self, name: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Table")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(name)
        self.caption_edit = QLineEdit(caption)
        form.addRow("Table Name", self.name_edit)
        form.addRow("Caption", self.caption_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(360, 150)

    def values(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.caption_edit.text().strip()


class TableBuilderDialog(QDialog):
    """Editor della struttura di una tabella: griglia unica e strumenti secondari."""

    table_created = pyqtSignal(str)
    table_changed = pyqtSignal(str)

    def __init__(
        self,
        project: Project,
        table: Table | None = None,
        parent: QWidget | None = None,
        embedded: bool = False,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.embedded = embedded
        self.original = table
        self.table = table.copy() if table else Table(name="", fields=[Field("nome", T.TEXT)])
        self._meta: dict[str, dict[str, Any]] = {}
        self._original_names: dict[str, str] = {}
        self._index_touched: set[str] = set()
        self._loading = False
        self._meta_loading = False
        self._adding_field = False
        self._stats_timer = QTimer(self)
        self._stats_timer.setSingleShot(True)
        self._stats_timer.setInterval(300)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self.setWindowTitle(f"Table Structure ({table.name if table else 'Untitled'})")
        self.resize(1040, 720)
        self._build_ui()
        self._load()
        self._update_preview()
        self._refresh_stats()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QGridLayout()
        header.setHorizontalSpacing(6)
        header.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit(self.table.name)
        self.name_edit.setPlaceholderText("nome_tabella")
        self.name_edit.textChanged.connect(self._on_name_changed)
        header.addWidget(self.name_edit, 0, 1)
        header.addWidget(QLabel("Type:"), 0, 2)
        type_label = QLabel("DBASE (SQLite)")
        type_label.setObjectName("table_type")
        type_label.setToolTip("Il motore di dBX è SQLite: la struttura resta in stile dBASE")
        header.addWidget(type_label, 0, 3)
        header.addWidget(QLabel("Didascalia:"), 0, 4)
        self.caption_edit = QLineEdit(self.table.caption)
        self.caption_edit.textChanged.connect(self._update_preview)
        header.addWidget(self.caption_edit, 0, 5)
        header.setColumnStretch(1, 2)
        header.setColumnStretch(5, 2)
        layout.addLayout(header)

        meta_frame = QFrame()
        meta_frame.setObjectName("table_meta")
        meta_layout = QHBoxLayout(meta_frame)
        meta_layout.setContentsMargins(6, 3, 6, 3)
        meta_layout.setSpacing(18)
        self.updated_label = QLabel("Updated: —")
        self.bytes_label = QLabel("Bytes Used: —")
        self.records_label = QLabel("Records: —")
        self.left_label = QLabel("Bytes Left: —")
        for label in (
            self.updated_label,
            self.bytes_label,
            self.records_label,
            self.left_label,
        ):
            meta_layout.addWidget(label)
        meta_layout.addStretch(1)
        layout.addWidget(meta_frame)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(3)
        self.exclusive_button = icons.make_button(
            "Open Exclusive",
            "apri",
            self._toggle_exclusive,
            self,
            "Modifica esclusiva della struttura; deseleziona per la sola lettura",
            checkable=True,
        )
        self.exclusive_button.setChecked(True)
        toolbar.addWidget(self.exclusive_button)
        toolbar.addSpacing(6)
        for button in (
            icons.make_button("Add Records", "nuovo", self.add_records, self, "Aggiungi record vuoti"),
            icons.make_button("Save As…", "salva", self.save_as, self, "Salva la struttura come nuova tabella"),
            icons.make_button("Stampa…", "stampa", self.print_structure, self, "Stampa la struttura"),
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("table_builder_splitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._build_fields_widget())
        tools = self._build_tools_widget()
        tools.setMinimumWidth(340)
        self.splitter.addWidget(tools)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([690, 360])
        layout.addWidget(self.splitter, 1)

        buttons = QDialogButtonBox()
        self.apply_button = buttons.addButton("Applica", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Annulla", QDialogButtonBox.ButtonRole.RejectRole)
        icons.style_button_box(buttons)
        self.apply_button.setDefault(True)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self._cancel)
        layout.addWidget(buttons)

    def _build_fields_widget(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.fields_grid = FieldGrid(0, len(FIELD_COLUMNS))
        self.fields_grid.setHorizontalHeaderLabels(FIELD_COLUMNS)
        self.fields_grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.fields_grid.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.fields_grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.fields_grid.horizontalHeader().setStretchLastSection(True)
        self.fields_grid.verticalHeader().setVisible(False)
        self.fields_grid.setColumnWidth(COL_FIELD, 46)
        self.fields_grid.setColumnWidth(COL_NAME, 210)
        self.fields_grid.setColumnWidth(COL_TYPE, 170)
        self.fields_grid.setColumnWidth(COL_WIDTH, 70)
        self.fields_grid.setColumnWidth(COL_DECIMAL, 70)
        self._type_delegate = ChoiceDelegate(self._field_type_choices, self)
        self._index_delegate = ChoiceDelegate(self._index_choices, self)
        self.fields_grid.setItemDelegateForColumn(COL_TYPE, self._type_delegate)
        self.fields_grid.setItemDelegateForColumn(COL_INDEX, self._index_delegate)
        self.fields_grid.setToolTip(
            "Trascina il numero del campo per riordinare; Tab/Invio sull'ultima cella crea un nuovo campo"
        )
        self.fields_grid.itemChanged.connect(self._on_item_changed)
        self.fields_grid.currentCellChanged.connect(self._on_current_cell_changed)
        self.fields_grid.row_move_requested.connect(self._move_field_to)
        self.fields_grid.installEventFilter(self)
        self.fields_grid.itemDelegate().closeEditor.connect(self._on_editor_closed)
        self._type_delegate.closeEditor.connect(self._on_editor_closed)
        self._index_delegate.closeEditor.connect(self._on_editor_closed)
        layout.addWidget(self.fields_grid, 1)

        bar = QHBoxLayout()
        add = icons.make_button(
            "Aggiungi campo", "nuovo", lambda: self._add_field_row(Field(f"campo_{self._next_field_number()}", T.TEXT)), self
        )
        remove = icons.make_button("Rimuovi campo", "elimina", self._remove_field_row, self)
        up = icons.make_button("Sposta su", "su", lambda: self._move_field(-1), self)
        down = icons.make_button("Sposta giù", "giu", lambda: self._move_field(1), self)
        self.field_buttons = (add, remove, up, down)
        for button in self.field_buttons:
            bar.addWidget(button)
        bar.addStretch(1)
        self.grid_hint = QLabel("Trascina il numero del campo per riordinare")
        self.grid_hint.setObjectName("nav_hint")
        bar.addWidget(self.grid_hint)
        layout.addLayout(bar)
        return container

    def _build_tools_widget(self) -> QWidget:
        self.tabs = QTabWidget()
        self.index_grid = QTableWidget(0, 3)
        self.index_grid.setHorizontalHeaderLabels(["Nome", "Campi", "Univoco"])
        index_header = self.index_grid.horizontalHeader()
        index_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        index_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        index_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.index_grid.verticalHeader().setVisible(False)
        self.index_grid.setColumnWidth(0, 110)
        self.index_grid.setColumnWidth(2, 64)
        self.index_grid.itemChanged.connect(self._on_indexes_changed)
        index_page = QWidget()
        index_layout = QVBoxLayout(index_page)
        index_layout.addWidget(self.index_grid, 1)
        index_bar = QHBoxLayout()
        index_bar.addWidget(
            icons.make_button("Aggiungi indice", "nuovo", lambda: self._add_index_row(Index()), self)
        )
        index_bar.addWidget(
            icons.make_button("Rimuovi indice", "elimina", lambda: self._remove_row(self.index_grid), self)
        )
        index_bar.addStretch(1)
        index_layout.addLayout(index_bar)
        self.tabs.addTab(index_page, "Indici")

        self.relation_grid = QTableWidget(0, 4)
        self.relation_grid.setHorizontalHeaderLabels(
            ["Campo", "Tabella", "Campo rif.", "Elimina"]
        )
        relation_header = self.relation_grid.horizontalHeader()
        relation_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        relation_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        relation_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        relation_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.relation_grid.verticalHeader().setVisible(False)
        self.relation_grid.setColumnWidth(0, 80)
        self.relation_grid.setColumnWidth(2, 80)
        relation_page = QWidget()
        relation_layout = QVBoxLayout(relation_page)
        relation_layout.addWidget(self.relation_grid, 1)
        relation_bar = QHBoxLayout()
        relation_bar.addWidget(
            icons.make_button(
                "Aggiungi relazione", "nuovo", lambda: self._add_relation_row(ForeignKey()), self
            )
        )
        relation_bar.addWidget(
            icons.make_button("Rimuovi relazione", "elimina", lambda: self._remove_row(self.relation_grid), self)
        )
        relation_bar.addStretch(1)
        relation_layout.addLayout(relation_bar)
        self.tabs.addTab(relation_page, "Relazioni")

        self.tabs.addTab(self._build_properties_page(), "Proprietà")

        self.ddl_view = QPlainTextEdit()
        self.ddl_view.setReadOnly(True)
        self.ddl_view.setFont(QFont(design.CODE_FONT.family, int(design.CODE_FONT.size_pt)))
        self.tabs.addTab(self.ddl_view, "DDL")
        return self.tabs

    def _build_properties_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(6, 6, 6, 6)
        self.table_summary = QLabel("")
        self.table_summary.setObjectName("nav_hint")
        self.table_summary.setWordWrap(True)
        layout.addWidget(self.table_summary)
        self.field_summary = QLabel("Campo: —")
        self.field_summary.setObjectName("browse_header")
        layout.addWidget(self.field_summary)

        form = QFormLayout()
        self.required_check = QCheckBox("Obbligatorio")
        self.default_edit = QLineEdit()
        self.field_caption_edit = QLineEdit()
        self.fmt_edit = QLineEdit()
        self.rule_edit = QLineEdit()
        self.rule_message_edit = QLineEdit()
        self.rule_message_edit.setPlaceholderText("Messaggio mostrato se la regola è falsa")
        self.required_expr_edit = QLineEdit()
        self.required_expr_edit.setPlaceholderText("es. [attivo] = .T.")
        self.required_expr_edit.setToolTip("Se non vuota, rende il campo obbligatorio solo quando è vera")
        self.skip_expr_edit = QLineEdit()
        self.skip_expr_edit.setPlaceholderText("es. [tipo] = 'note'")
        self.skip_expr_edit.setToolTip("Se vera, il campo è saltato e non obbligatorio")
        self.lookup_edit = QLineEdit()
        self.lookup_edit.setPlaceholderText("tabella.campo")
        self.calculated_edit = QLineEdit()
        self.calculated_edit.setPlaceholderText("es. [prezzo] * [quantita]")
        self.calculated_edit.setToolTip("Espressione calcolata a ogni lettura; il campo non è salvato")
        self.auto_enter_edit = QLineEdit()
        self.auto_enter_edit.setPlaceholderText("es. TODAY() oppure [nome]")
        self.auto_enter_edit.setToolTip("Espressione valutata alla creazione se il campo è vuoto")
        self.auto_serial_check = QCheckBox("Serie automatica")
        self.auto_serial_check.setToolTip("Assegna il numero successivo alla creazione")
        self.auto_date_combo = QComboBox()
        self.auto_date_combo.addItem("(nessuna)", "")
        self.auto_date_combo.addItem("Data di creazione", "insert")
        self.auto_date_combo.addItem("Data di modifica", "update")
        self.auto_date_combo.setToolTip("Imposta la data alla creazione o a ogni modifica")
        for widget in (
            self.required_check,
            self.default_edit,
            self.field_caption_edit,
            self.fmt_edit,
            self.rule_edit,
            self.rule_message_edit,
            self.required_expr_edit,
            self.skip_expr_edit,
            self.lookup_edit,
            self.calculated_edit,
            self.auto_enter_edit,
            self.auto_serial_check,
            self.auto_date_combo,
        ):
            widget.setEnabled(False)
        form.addRow("", self.required_check)
        form.addRow("Default", self.default_edit)
        form.addRow("Didascalia", self.field_caption_edit)
        form.addRow("Formato", self.fmt_edit)
        form.addRow("Regola", self.rule_edit)
        form.addRow("Messaggio regola", self.rule_message_edit)
        form.addRow("Obbligatorio se", self.required_expr_edit)
        form.addRow("Salta se", self.skip_expr_edit)
        form.addRow("Lookup", self.lookup_edit)
        form.addRow("Calcolato", self.calculated_edit)
        form.addRow("Auto-enter", self.auto_enter_edit)
        form.addRow("", self.auto_serial_check)
        form.addRow("Data automatica", self.auto_date_combo)
        layout.addLayout(form)
        layout.addWidget(self._build_choice_group())
        layout.addStretch(1)

        self.required_check.toggled.connect(self._store_field_meta)
        self.auto_serial_check.toggled.connect(self._store_field_meta)
        self.auto_date_combo.currentIndexChanged.connect(self._store_field_meta)
        for edit in (
            self.default_edit,
            self.field_caption_edit,
            self.fmt_edit,
            self.rule_edit,
            self.rule_message_edit,
            self.required_expr_edit,
            self.skip_expr_edit,
            self.lookup_edit,
            self.calculated_edit,
            self.auto_enter_edit,
        ):
            edit.textChanged.connect(self._store_field_meta)
        return page

    def _build_choice_group(self) -> QGroupBox:
        group = QGroupBox("Valori (Scelta)")
        self.choice_group = group
        layout = QVBoxLayout(group)
        form = QFormLayout()
        self.choice_source_combo = QComboBox()
        self.choice_source_combo.addItem("Solo lista fissa", "static")
        self.choice_source_combo.addItem("Solo tabella", "table-replace")
        self.choice_source_combo.addItem("Lista + tabella", "table-append")
        form.addRow("Sorgente", self.choice_source_combo)
        self.choice_table_combo = QComboBox()
        self.choice_table_combo.setEditable(True)
        form.addRow("Tabella", self.choice_table_combo)
        self.choice_value_edit = QLineEdit()
        self.choice_value_edit.setPlaceholderText("colonna del valore")
        form.addRow("Colonna valore", self.choice_value_edit)
        self.choice_label_edit = QLineEdit()
        self.choice_label_edit.setPlaceholderText("colonna etichetta (opzionale)")
        form.addRow("Colonna etichetta", self.choice_label_edit)
        layout.addLayout(form)
        self.choice_case_check = QCheckBox("Distingui maiuscole")
        self.choice_case_check.setChecked(True)
        self.choice_blank_check = QCheckBox("Vuoto ammesso")
        self.choice_blank_check.setChecked(True)
        self.choice_other_check = QCheckBox("Testo libero ammesso (con avviso)")
        for box in (self.choice_case_check, self.choice_blank_check, self.choice_other_check):
            layout.addWidget(box)
        self.choice_values_grid = QTableWidget(0, 2)
        self.choice_values_grid.setHorizontalHeaderLabels(["Valore", "Etichetta"])
        self.choice_values_grid.verticalHeader().setVisible(False)
        self.choice_values_grid.horizontalHeader().setStretchLastSection(True)
        self.choice_values_grid.setColumnWidth(0, 120)
        layout.addWidget(self.choice_values_grid)
        bar = QHBoxLayout()
        bar.addWidget(
            icons.make_button(
                "Aggiungi valore",
                "nuovo",
                lambda: self._add_choice_row("", ""),
                self,
            )
        )
        bar.addWidget(
            icons.make_button(
                "Rimuovi valore",
                "elimina",
                lambda: self._remove_row(self.choice_values_grid),
                self,
            )
        )
        bar.addStretch(1)
        layout.addLayout(bar)
        for widget in (
            self.choice_case_check,
            self.choice_blank_check,
            self.choice_other_check,
        ):
            widget.stateChanged.connect(self._store_field_meta)
        for widget in (self.choice_source_combo, self.choice_table_combo):
            widget.currentIndexChanged.connect(self._store_field_meta)
        for edit in (self.choice_value_edit, self.choice_label_edit):
            edit.textChanged.connect(self._store_field_meta)
        self.choice_values_grid.itemChanged.connect(self._store_field_meta)
        return group

    def _add_choice_row(self, value: str, label: str) -> None:
        row = self.choice_values_grid.rowCount()
        self.choice_values_grid.insertRow(row)
        self.choice_values_grid.setItem(row, 0, QTableWidgetItem(value))
        self.choice_values_grid.setItem(row, 1, QTableWidgetItem(label))
        self._store_field_meta()

    def _choice_rows(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for row in range(self.choice_values_grid.rowCount()):
            value_item = self.choice_values_grid.item(row, 0)
            label_item = self.choice_values_grid.item(row, 1)
            value = value_item.text().strip() if value_item else ""
            if not value:
                continue
            label = label_item.text().strip() if label_item else ""
            result.append({"value": value, "label": label})
        return result

    def _fill_choice_tables(self) -> None:
        current = self.choice_table_combo.currentText()
        self.choice_table_combo.blockSignals(True)
        self.choice_table_combo.clear()
        self.choice_table_combo.addItem("")
        for name in getattr(self, "_table_names", []):
            self.choice_table_combo.addItem(name)
        position = self.choice_table_combo.findText(current)
        self.choice_table_combo.setCurrentIndex(max(0, position))
        self.choice_table_combo.blockSignals(False)

    # ---------------------------------------------------------------- caricamento
    def _load(self) -> None:
        self._loading = True
        self.name_edit.setText(self.table.name)
        self.caption_edit.setText(self.table.caption)
        self.index_grid.setRowCount(0)
        for index in self.table.indexes:
            self._add_index_row(index)
        self.relation_grid.setRowCount(0)
        for fk in self.table.foreign_keys:
            self._add_relation_row(fk)
        self._meta = {}
        self._original_names = {}
        self._index_touched.clear()
        self._table_names = list(self.project.tables()) if self.project else []
        self._reload_fields(self.table.fields)
        self._loading = False
        if self.fields_grid.rowCount():
            self.fields_grid.setCurrentCell(0, COL_NAME)

    def _meta_from_field(self, field: Field) -> dict[str, Any]:
        return {
            "required": field.required,
            "default": field.default,
            "caption": field.caption,
            "fmt": field.fmt,
            "rule": field.rule,
            "rule_message": field.rule_message,
            "required_expr": field.required_expr,
            "skip_expr": field.skip_expr,
            "lookup": field.lookup,
            "choices": [dict(item) for item in field.choices],
            "choice_source": field.choice_source,
            "choice_table": field.choice_table,
            "choice_value": field.choice_value,
            "choice_label": field.choice_label,
            "choice_combine": field.choice_combine,
            "choice_case_sensitive": field.choice_case_sensitive,
            "choice_allow_blank": field.choice_allow_blank,
            "choice_allow_other": field.choice_allow_other,
            "calculated": field.calculated,
            "auto_enter": field.auto_enter,
            "auto_serial": field.auto_serial,
            "auto_date": field.auto_date,
            "pk": field.pk,
        }

    def _reload_fields(self, fields: list[Field], selections: dict[str, str] | None = None) -> None:
        self.fields_grid.blockSignals(True)
        current = self.fields_grid.currentRow()
        self.fields_grid.setRowCount(0)
        for field in fields:
            self._meta.setdefault(field.id, self._meta_from_field(field))
            self._original_names.setdefault(field.id, field.name)
            selected = (selections or {}).get(field.id)
            self._append_field_row(field, selected)
        self.fields_grid.blockSignals(False)
        if fields:
            row = min(max(current, 0), len(fields) - 1)
            self.fields_grid.setCurrentCell(row, COL_NAME)
            self._highlight_current_row(row)
            self._load_field_meta(row)
        self._renumber()

    def _append_field_row(self, field: Field, selected_index: str | None = None) -> None:
        row = self.fields_grid.rowCount()
        self.fields_grid.insertRow(row)
        number = QTableWidgetItem(str(row + 1))
        number.setFlags(number.flags() & ~Qt.ItemFlag.ItemIsEditable)
        number.setData(Qt.ItemDataRole.UserRole, field.id)
        number.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setToolTip("Trascina per riordinare il campo")
        self.fields_grid.setItem(row, COL_FIELD, number)

        name = QTableWidgetItem(field.name)
        self.fields_grid.setItem(row, COL_NAME, name)

        type_label = T.label(field.type)
        type_item = QTableWidgetItem(type_label)
        type_item.setData(Qt.ItemDataRole.UserRole, field.type)
        self.fields_grid.setItem(row, COL_TYPE, type_item)

        self.fields_grid.setItem(
            row, COL_WIDTH, QTableWidgetItem(str(field.size) if field.size else "")
        )
        decimals = decimals_from_fmt(field.fmt)
        self.fields_grid.setItem(
            row, COL_DECIMAL, QTableWidgetItem(str(decimals) if decimals else "")
        )

        if selected_index is not None:
            key = selected_index
            label = self._index_label(key) or NO_INDEX
        else:
            key, label = self._index_for_field(field.name)
        index_item = QTableWidgetItem(label or NO_INDEX)
        index_item.setData(Qt.ItemDataRole.UserRole, key)
        self.fields_grid.setItem(row, COL_INDEX, index_item)
        self.fields_grid.setRowHeight(row, design.METRICS.row_height + 2)

    def _renumber(self) -> None:
        for row in range(self.fields_grid.rowCount()):
            item = self.fields_grid.item(row, COL_FIELD)
            if item is not None:
                item.setText(str(row + 1))

    def _highlight_current_row(self, current: int) -> None:
        for row in range(self.fields_grid.rowCount()):
            height = (
                design.METRICS.row_height * 2 + 2
                if row == current
                else design.METRICS.row_height + 2
            )
            self.fields_grid.setRowHeight(row, height)

    # ------------------------------------------------------------------ campi
    def _next_field_number(self) -> int:
        return self.fields_grid.rowCount() + 1

    def _add_field_row(self, field: Field) -> None:
        if self._adding_field:
            return
        self._adding_field = True
        try:
            self._meta[field.id] = self._meta_from_field(field)
            self._original_names[field.id] = field.name
            self._append_field_row(field)
            self._renumber()
            row = self.fields_grid.rowCount() - 1
            self.fields_grid.setCurrentCell(row, COL_NAME)
            self._highlight_current_row(row)
            self._load_field_meta(row)
            self._update_preview()
        finally:
            self._adding_field = False

    def _remove_field_row(self) -> None:
        row = self.fields_grid.currentRow()
        if row < 0:
            return
        number = self.fields_grid.item(row, COL_FIELD)
        name_item = self.fields_grid.item(row, COL_NAME)
        field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
        field_name = name_item.text().strip() if name_item else ""
        self.fields_grid.removeRow(row)
        if isinstance(field_id, str):
            self._meta.pop(field_id, None)
            self._original_names.pop(field_id, None)
            self._index_touched.discard(field_id)
        if field_name:
            self._drop_field_from_relations(field_name)
        self._renumber()
        if self.fields_grid.rowCount():
            row = min(row, self.fields_grid.rowCount() - 1)
            self.fields_grid.setCurrentCell(row, COL_NAME)
            self._load_field_meta(row)
        else:
            self._clear_field_meta()
        self._update_preview()

    def _drop_field_from_relations(self, field_name: str) -> None:
        for grid, columns in ((self.index_grid, (1,)), (self.relation_grid, (0,))):
            row = 0
            while row < grid.rowCount():
                changed = False
                for column in columns:
                    item = grid.item(row, column)
                    if item is None:
                        continue
                    parts = [part.strip() for part in item.text().split(",") if part.strip()]
                    if field_name in parts:
                        parts = [part for part in parts if part != field_name]
                        item.setText(", ".join(parts))
                        changed = True
                if changed and not (grid.item(row, 1) and grid.item(row, 1).text().strip()):
                    grid.removeRow(row)
                else:
                    row += 1

    def _move_field(self, delta: int) -> None:
        row = self.fields_grid.currentRow()
        self._move_field_to(row, row + delta)

    def _move_field_to(self, source: int, target: int) -> None:
        if source < 0 or source >= self.fields_grid.rowCount():
            return
        selections = {
            str(self.fields_grid.item(row, COL_FIELD).data(Qt.ItemDataRole.UserRole)): str(
                self.fields_grid.item(row, COL_INDEX).data(Qt.ItemDataRole.UserRole) or ""
            )
            for row in range(self.fields_grid.rowCount())
            if self.fields_grid.item(row, COL_FIELD) is not None
            and self.fields_grid.item(row, COL_INDEX) is not None
        }
        fields = self._collect_fields()
        field = fields.pop(source)
        target = max(0, min(target, len(fields)))
        fields.insert(target, field)
        self._reload_fields(fields, selections)
        self.fields_grid.setCurrentCell(target, COL_NAME)
        self._update_preview()

    def _collect_fields(self) -> list[Field]:
        fields: list[Field] = []
        for row in range(self.fields_grid.rowCount()):
            number = self.fields_grid.item(row, COL_FIELD)
            name_item = self.fields_grid.item(row, COL_NAME)
            type_item = self.fields_grid.item(row, COL_TYPE)
            field_id = str(number.data(Qt.ItemDataRole.UserRole) or new_id()) if number else new_id()
            field_type = str(type_item.data(Qt.ItemDataRole.UserRole) or T.TEXT) if type_item else T.TEXT
            try:
                size = int((self.fields_grid.item(row, COL_WIDTH).text() if self.fields_grid.item(row, COL_WIDTH) else "0") or 0)
            except ValueError:
                size = 0
            decimals = 0
            decimal_item = self.fields_grid.item(row, COL_DECIMAL)
            if decimal_item is not None:
                try:
                    decimals = max(0, int(decimal_item.text() or 0))
                except ValueError:
                    decimals = 0
            meta = self._meta.get(field_id, {})
            fmt = str(meta.get("fmt", ""))
            if field_type == T.DECIMAL and decimal_item is not None and decimal_item.text().strip():
                fmt = fmt_from_decimals(decimals)
            choice_kwargs: dict[str, Any] = {}
            if field_type == T.CHOICE:
                choice_kwargs = {
                    "choices": [
                        dict(item)
                        for item in meta.get("choices", [])
                        if isinstance(item, dict)
                    ],
                    "choice_source": str(meta.get("choice_source", "")),
                    "choice_table": str(meta.get("choice_table", "")),
                    "choice_value": str(meta.get("choice_value", "")),
                    "choice_label": str(meta.get("choice_label", "")),
                    "choice_combine": str(meta.get("choice_combine", "append")),
                    "choice_case_sensitive": bool(
                        meta.get("choice_case_sensitive", True)
                    ),
                    "choice_allow_blank": bool(meta.get("choice_allow_blank", True)),
                    "choice_allow_other": bool(meta.get("choice_allow_other", False)),
                }
            fields.append(
                Field(
                    name=(name_item.text() if name_item else "").strip(),
                    type=field_type,
                    size=size,
                    required=bool(meta.get("required", False)),
                    default=str(meta.get("default", "")),
                    caption=str(meta.get("caption", "")),
                    fmt=fmt,
                    rule=str(meta.get("rule", "")),
                    rule_message=str(meta.get("rule_message", "")),
                    required_expr=str(meta.get("required_expr", "")),
                    skip_expr=str(meta.get("skip_expr", "")),
                    lookup=str(meta.get("lookup", "")),
                    calculated=str(meta.get("calculated", "")),
                    auto_enter=str(meta.get("auto_enter", "")),
                    auto_serial=bool(meta.get("auto_serial", False)),
                    auto_date=str(meta.get("auto_date", "")),
                    pk=bool(meta.get("pk", False)),
                    id=field_id,
                    **choice_kwargs,
                )
            )
        return fields

    # ------------------------------------------------------------------ indici
    def _add_index_row(self, index: Index) -> None:
        row = self.index_grid.rowCount()
        self.index_grid.insertRow(row)
        self.index_grid.setItem(row, 0, QTableWidgetItem(index.name))
        self.index_grid.setItem(row, 1, QTableWidgetItem(", ".join(index.fields)))
        unique = QTableWidgetItem()
        unique.setFlags(unique.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        unique.setCheckState(Qt.CheckState.Checked if index.unique else Qt.CheckState.Unchecked)
        self.index_grid.setItem(row, 2, unique)

    def _collect_indexes_from_grid(self) -> list[Index]:
        indexes: list[Index] = []
        for row in range(self.index_grid.rowCount()):
            fields = [
                part.strip()
                for part in (self.index_grid.item(row, 1).text() if self.index_grid.item(row, 1) else "").split(",")
                if part.strip()
            ]
            if not fields:
                continue
            unique_item = self.index_grid.item(row, 2)
            indexes.append(
                Index(
                    name=self.index_grid.item(row, 0).text().strip() if self.index_grid.item(row, 0) else "",
                    fields=fields,
                    unique=bool(unique_item and unique_item.checkState() == Qt.CheckState.Checked),
                )
            )
        return indexes

    def _collect_indexes(self) -> list[Index]:
        table_name = self.name_edit.text().strip() or self.table.name or "tabella"
        indexes = self._collect_indexes_from_grid()
        by_key = {index.resolved_name(table_name): index for index in indexes}
        for row in range(self.fields_grid.rowCount()):
            number = self.fields_grid.item(row, COL_FIELD)
            field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
            if not isinstance(field_id, str) or field_id not in self._index_touched:
                continue
            field_name = (self.fields_grid.item(row, COL_NAME).text() if self.fields_grid.item(row, COL_NAME) else "").strip()
            if not field_name:
                continue
            index_item = self.fields_grid.item(row, COL_INDEX)
            key = str(index_item.data(Qt.ItemDataRole.UserRole) or "") if index_item else ""
            if not key:
                for index in indexes:
                    if field_name in index.fields:
                        index.fields = [name for name in index.fields if name != field_name]
                continue
            target = by_key.get(key)
            if target is None:
                continue
            for index in indexes:
                if index is not target and field_name in index.fields:
                    index.fields = [name for name in index.fields if name != field_name]
            if field_name not in target.fields:
                target.fields.append(field_name)
        return [index for index in indexes if index.fields]

    def _field_type_choices(self) -> list[tuple[str, str]]:
        return [(T.label(key), key) for key in T.ALL_TYPES]

    def _index_choices(self) -> list[tuple[str, str]]:
        table_name = self.name_edit.text().strip() or self.table.name or "tabella"
        choices = [(NO_INDEX, "")]
        for index in self._collect_indexes_from_grid():
            key = index.resolved_name(table_name)
            choices.append((index.name or key, key))
        return choices

    def _index_label(self, key: str) -> str:
        for label, candidate in self._index_choices():
            if candidate == key:
                return label
        return ""

    def _index_for_field(self, field_name: str) -> tuple[str, str]:
        table_name = self.name_edit.text().strip() or self.table.name or "tabella"
        for index in self._collect_indexes_from_grid():
            if field_name in index.fields:
                key = index.resolved_name(table_name)
                return key, index.name or key
        return "", NO_INDEX

    def _refresh_index_column(self) -> None:
        self._loading = True
        try:
            self._refresh_index_column_items()
        finally:
            self._loading = False

    def _refresh_index_column_items(self) -> None:
        for row in range(self.fields_grid.rowCount()):
            number = self.fields_grid.item(row, COL_FIELD)
            item = self.fields_grid.item(row, COL_INDEX)
            if number is None or item is None:
                continue
            field_id = number.data(Qt.ItemDataRole.UserRole)
            field_name = (self.fields_grid.item(row, COL_NAME).text() if self.fields_grid.item(row, COL_NAME) else "").strip()
            key = str(item.data(Qt.ItemDataRole.UserRole) or "")
            if isinstance(field_id, str) and field_id in self._index_touched:
                label = self._index_label(key)
                if label:
                    item.setText(label)
                else:
                    item.setText(NO_INDEX)
                    item.setData(Qt.ItemDataRole.UserRole, "")
                    self._index_touched.discard(field_id)
            else:
                key, label = self._index_for_field(field_name)
                item.setText(label)
                item.setData(Qt.ItemDataRole.UserRole, key)

    # --------------------------------------------------------------- relazioni
    def _add_relation_row(self, fk: ForeignKey) -> None:
        row = self.relation_grid.rowCount()
        self.relation_grid.insertRow(row)
        columns_item = QTableWidgetItem(", ".join(fk.columns))
        columns_item.setData(Qt.ItemDataRole.UserRole, fk.name)
        self.relation_grid.setItem(row, 0, columns_item)
        self.relation_grid.setItem(row, 1, QTableWidgetItem(fk.ref_table))
        self.relation_grid.setItem(row, 2, QTableWidgetItem(", ".join(fk.ref_columns)))
        combo = QComboBox()
        for action in ON_DELETE_ACTIONS:
            combo.addItem(action, action)
        index = combo.findData(fk.on_delete.upper())
        combo.setCurrentIndex(max(0, index))
        self.relation_grid.setCellWidget(row, 3, combo)

    def _collect_relations(self) -> list[ForeignKey]:
        relations: list[ForeignKey] = []
        for row in range(self.relation_grid.rowCount()):
            columns = [
                part.strip()
                for part in (self.relation_grid.item(row, 0).text() if self.relation_grid.item(row, 0) else "").split(",")
                if part.strip()
            ]
            ref_table = (self.relation_grid.item(row, 1).text() if self.relation_grid.item(row, 1) else "").strip()
            ref_columns = [
                part.strip()
                for part in (self.relation_grid.item(row, 2).text() if self.relation_grid.item(row, 2) else "").split(",")
                if part.strip()
            ]
            if not columns and not ref_table:
                continue
            combo = self.relation_grid.cellWidget(row, 3)
            columns_item = self.relation_grid.item(row, 0)
            relations.append(
                ForeignKey(
                    columns=columns,
                    ref_table=ref_table,
                    ref_columns=ref_columns,
                    on_delete=combo.currentData() if isinstance(combo, QComboBox) else "NO ACTION",
                    name=str(columns_item.data(Qt.ItemDataRole.UserRole) or "")
                    if columns_item is not None
                    else "",
                )
            )
        return relations

    # ------------------------------------------------------------- proprietà
    def _update_field_groups(self, row: int) -> None:
        number = self.fields_grid.item(row, COL_FIELD) if row >= 0 else None
        field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
        meta = self._meta.get(str(field_id), {}) if isinstance(field_id, str) else {}
        type_item = self.fields_grid.item(row, COL_TYPE) if row >= 0 else None
        type_name = str(type_item.data(Qt.ItemDataRole.UserRole) or T.TEXT) if type_item else T.TEXT
        editable = bool(meta) and self.exclusive_button.isChecked()
        self.choice_group.setEnabled(editable and type_name == T.CHOICE)

    def _load_field_meta(self, row: int) -> None:
        number = self.fields_grid.item(row, COL_FIELD)
        name_item = self.fields_grid.item(row, COL_NAME)
        field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
        meta = self._meta.get(str(field_id), {}) if isinstance(field_id, str) else {}
        self._meta_loading = True
        self.field_summary.setText(
            f"Campo: {name_item.text() if name_item else '—'}"
        )
        self.required_check.setChecked(bool(meta.get("required", False)))
        self.default_edit.setText(str(meta.get("default", "")))
        self.field_caption_edit.setText(str(meta.get("caption", "")))
        self.fmt_edit.setText(str(meta.get("fmt", "")))
        self.rule_edit.setText(str(meta.get("rule", "")))
        self.rule_message_edit.setText(str(meta.get("rule_message", "")))
        self.required_expr_edit.setText(str(meta.get("required_expr", "")))
        self.skip_expr_edit.setText(str(meta.get("skip_expr", "")))
        self.lookup_edit.setText(str(meta.get("lookup", "")))
        self.calculated_edit.setText(str(meta.get("calculated", "")))
        self.auto_enter_edit.setText(str(meta.get("auto_enter", "")))
        self.auto_serial_check.setChecked(bool(meta.get("auto_serial", False)))
        position = self.auto_date_combo.findData(str(meta.get("auto_date", "")))
        self.auto_date_combo.setCurrentIndex(max(0, position))
        self._fill_choice_tables()
        self.choice_table_combo.setCurrentText(str(meta.get("choice_table", "")))
        self.choice_value_edit.setText(str(meta.get("choice_value", "")))
        self.choice_label_edit.setText(str(meta.get("choice_label", "")))
        source = str(meta.get("choice_source", ""))
        if not source:
            mode = "static"
        else:
            mode = (
                "table-append"
                if str(meta.get("choice_combine", "append")) == "append"
                else "table-replace"
            )
        mode_position = self.choice_source_combo.findData(mode)
        self.choice_source_combo.setCurrentIndex(max(0, mode_position))
        self.choice_case_check.setChecked(bool(meta.get("choice_case_sensitive", True)))
        self.choice_blank_check.setChecked(bool(meta.get("choice_allow_blank", True)))
        self.choice_other_check.setChecked(bool(meta.get("choice_allow_other", False)))
        self.choice_values_grid.blockSignals(True)
        self.choice_values_grid.setRowCount(0)
        for item in meta.get("choices", []):
            if not isinstance(item, dict):
                continue
            row = self.choice_values_grid.rowCount()
            self.choice_values_grid.insertRow(row)
            self.choice_values_grid.setItem(
                row, 0, QTableWidgetItem(str(item.get("value", "")))
            )
            self.choice_values_grid.setItem(
                row, 1, QTableWidgetItem(str(item.get("label", "")))
            )
        self.choice_values_grid.blockSignals(False)
        enabled = bool(meta)
        for widget in (
            self.required_check,
            self.default_edit,
            self.field_caption_edit,
            self.fmt_edit,
            self.rule_edit,
            self.rule_message_edit,
            self.required_expr_edit,
            self.skip_expr_edit,
            self.lookup_edit,
            self.calculated_edit,
            self.auto_enter_edit,
            self.auto_serial_check,
            self.auto_date_combo,
        ):
            widget.setEnabled(enabled and self.exclusive_button.isChecked())
        self._update_field_groups(row)
        self._meta_loading = False

    def _clear_field_meta(self) -> None:
        self._meta_loading = True
        self.field_summary.setText("Campo: —")
        self.required_check.setChecked(False)
        for edit in (
            self.default_edit,
            self.field_caption_edit,
            self.fmt_edit,
            self.rule_edit,
            self.rule_message_edit,
            self.required_expr_edit,
            self.skip_expr_edit,
            self.lookup_edit,
            self.calculated_edit,
            self.auto_enter_edit,
        ):
            edit.clear()
        self.auto_serial_check.setChecked(False)
        self.auto_date_combo.setCurrentIndex(0)
        self.choice_values_grid.blockSignals(True)
        self.choice_values_grid.setRowCount(0)
        self.choice_values_grid.blockSignals(False)
        for edit in (self.choice_value_edit, self.choice_label_edit):
            edit.clear()
        self.choice_table_combo.setCurrentText("")
        self.choice_source_combo.setCurrentIndex(0)
        self.choice_case_check.setChecked(True)
        self.choice_blank_check.setChecked(True)
        self.choice_other_check.setChecked(False)
        self._update_field_groups(-1)
        self._meta_loading = False

    def _store_field_meta(self, *_args) -> None:
        if self._meta_loading:
            return
        row = self.fields_grid.currentRow()
        number = self.fields_grid.item(row, COL_FIELD) if row >= 0 else None
        field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
        if not isinstance(field_id, str):
            return
        self._meta[field_id] = {
            "required": self.required_check.isChecked(),
            "default": self.default_edit.text(),
            "caption": self.field_caption_edit.text(),
            "fmt": self.fmt_edit.text(),
            "rule": self.rule_edit.text(),
            "rule_message": self.rule_message_edit.text(),
            "required_expr": self.required_expr_edit.text(),
            "skip_expr": self.skip_expr_edit.text(),
            "lookup": self.lookup_edit.text(),
            "choices": self._choice_rows(),
            "choice_source": ""
            if str(self.choice_source_combo.currentData() or "static") == "static"
            else "table",
            "choice_table": self.choice_table_combo.currentText().strip(),
            "choice_value": self.choice_value_edit.text().strip(),
            "choice_label": self.choice_label_edit.text().strip(),
            "choice_combine": "replace"
            if str(self.choice_source_combo.currentData() or "") == "table-replace"
            else "append",
            "choice_case_sensitive": self.choice_case_check.isChecked(),
            "choice_allow_blank": self.choice_blank_check.isChecked(),
            "choice_allow_other": self.choice_other_check.isChecked(),
            "calculated": self.calculated_edit.text(),
            "auto_enter": self.auto_enter_edit.text(),
            "auto_serial": self.auto_serial_check.isChecked(),
            "auto_date": str(self.auto_date_combo.currentData() or ""),
            "pk": bool(self._meta.get(field_id, {}).get("pk", False)),
        }
        self._update_preview()

    # ------------------------------------------------------------------ eventi
    def _on_name_changed(self, _text: str) -> None:
        self.setWindowTitle(f"Table Structure ({self.name_edit.text().strip() or 'Untitled'})")
        self._update_preview()
        self._stats_timer.start()

    def _on_current_cell_changed(self, row: int, _column: int, _prev_row: int, _prev_col: int) -> None:
        if self._loading or row < 0:
            return
        self._highlight_current_row(row)
        self._load_field_meta(row)
        self._update_field_groups(row)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        row = item.row()
        number = self.fields_grid.item(row, COL_FIELD)
        field_id = number.data(Qt.ItemDataRole.UserRole) if number else None
        if item.column() == COL_INDEX and isinstance(field_id, str):
            self._index_touched.add(field_id)
        if item.column() == COL_TYPE and isinstance(field_id, str):
            self._update_field_groups(row)
        if item.column() == COL_DECIMAL and isinstance(field_id, str):
            meta = self._meta.setdefault(field_id, {})
            try:
                value = max(0, int(item.text() or 0))
            except ValueError:
                value = 0
            meta["fmt"] = fmt_from_decimals(value)
            if self.fields_grid.currentRow() == row and not self._meta_loading:
                self._meta_loading = True
                self.fmt_edit.setText(str(meta["fmt"]))
                self._meta_loading = False
        self._update_preview()

    def _on_indexes_changed(self, *_args) -> None:
        if self._loading:
            return
        self._refresh_index_column()
        self._update_preview()

    def _on_editor_closed(self, _editor, _hint) -> None:
        if self._adding_field:
            return
        row = self.fields_grid.currentRow()
        column = self.fields_grid.currentColumn()
        if row == self.fields_grid.rowCount() - 1 and column == COL_INDEX:
            QTimer.singleShot(0, self._add_field_after_last)

    def eventFilter(self, obj, event) -> bool:  # noqa: D102 - API Qt
        if obj is self.fields_grid and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.fields_grid.state() != QAbstractItemView.State.EditingState:
                    row = self.fields_grid.currentRow()
                    column = self.fields_grid.currentColumn()
                    if row == self.fields_grid.rowCount() - 1 and column == COL_INDEX:
                        self._add_field_after_last()
                        return True
        return super().eventFilter(obj, event)

    def _add_field_after_last(self) -> None:
        if self._adding_field:
            return
        if self.fields_grid.currentRow() != self.fields_grid.rowCount() - 1:
            return
        self._add_field_row(Field(f"campo_{self._next_field_number()}", T.TEXT))
        self.fields_grid.setCurrentCell(self.fields_grid.rowCount() - 1, COL_NAME)
        self.fields_grid.editItem(self.fields_grid.currentItem())

    def _show_tool(self, index: int) -> None:
        self.tabs.setCurrentIndex(index)

    def _toggle_exclusive(self, checked: bool) -> None:
        editable = QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        self.fields_grid.setEditTriggers(editable if checked else QAbstractItemView.EditTrigger.NoEditTriggers)
        self.index_grid.setEnabled(checked)
        self.relation_grid.setEnabled(checked)
        self.apply_button.setEnabled(checked)
        for button in getattr(self, "field_buttons", ()):
            button.setEnabled(checked)
        row = self.fields_grid.currentRow()
        if row >= 0:
            self._load_field_meta(row)
            self._update_field_groups(row)
        self.grid_hint.setText(
            "Modifica esclusiva attiva" if checked else "Sola lettura: struttura bloccata"
        )

    # ---------------------------------------------------------------- corrente
    def current_table(self) -> Table:
        fields = self._collect_fields()
        renames = {
            self._original_names.get(field.id, field.name): field.name
            for field in fields
            if field.id in self._original_names and self._original_names[field.id] != field.name
        }
        indexes = self._collect_indexes()
        for index in indexes:
            if renames:
                index.fields = [renames.get(name, name) for name in index.fields]
        relations = [
            ForeignKey(
                columns=[renames.get(name, name) for name in fk.columns],
                ref_table=fk.ref_table,
                ref_columns=list(fk.ref_columns),
                on_delete=fk.on_delete,
                name=fk.name,
            )
            for fk in self._collect_relations()
        ]
        return Table(
            name=self.name_edit.text().strip(),
            caption=self.caption_edit.text().strip(),
            fields=fields,
            indexes=indexes,
            foreign_keys=relations,
            id=self.original.id if self.original else self.table.id,
        )

    def _update_preview(self) -> None:
        try:
            table = self.current_table()
        except Exception as exc:  # pragma: no cover - difensivo
            self.ddl_view.setPlainText(str(exc))
            return
        try:
            old = self.project.table(table.name) if self.project else None
            plan = ddl.plan_migration(old if old else None, table)
        except (MetadataError, Exception) as exc:
            self.ddl_view.setPlainText(f"-- Struttura non valida:\n{exc}")
            self.table_summary.setText(f"{table.name or 'Nuova tabella'} · struttura non valida")
            return
        lines = ["-- Modifiche pianificate:"] + [f"-- {d}" for d in plan.descriptions] + ["", plan.sql or "-- nessuna modifica"]
        self.ddl_view.setPlainText("\n".join(lines))
        self.table_summary.setText(
            f"{table.name or 'Nuova tabella'} · {len(table.fields)} campi · "
            f"{len(table.indexes)} indici · {len(table.foreign_keys)} relazioni"
        )

    def _refresh_stats(self) -> None:
        name = self.name_edit.text().strip()
        exists = bool(name) and self.project is not None and self.project.table(name) is not None
        if not exists:
            self.updated_label.setText("Updated: —")
            self.bytes_label.setText("Bytes Used: —")
            self.records_label.setText("Records: 0")
            self.left_label.setText("Bytes Left: —")
            return
        artifact = self.project.objects_path / "tables" / f"{name}.table.json"
        updated = "—"
        if artifact.exists():
            updated = datetime.fromtimestamp(artifact.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        records = 0
        used = 0
        try:
            table = self.project.require_table(name)
            expressions = [
                f"COALESCE(LENGTH(CAST({ddl.quote(field.name)} AS TEXT)), 0)"
                for field in table.stored_fields
            ]
            row = self.project.db.query(
                f"SELECT COUNT(*) AS n, SUM({'+'.join(expressions)}) AS bytes "
                f"FROM {ddl.quote(name)}"
            )[0]
            records = int(row["n"] or 0)
            used = int(row["bytes"] or 0)
        except Exception:  # pragma: no cover - difensivo
            pass
        free = 0
        try:
            page_size = int(self.project.db.scalar("PRAGMA page_size") or 0)
            free_pages = int(self.project.db.scalar("PRAGMA freelist_count") or 0)
            free = page_size * free_pages
        except Exception:  # pragma: no cover - difensivo
            free = 0
        self.updated_label.setText(f"Updated: {updated}")
        self.bytes_label.setText(f"Bytes Used: {human_size(used)}")
        self.records_label.setText(f"Records: {records}")
        self.left_label.setText(f"Bytes Left: {human_size(free)}")

    # ------------------------------------------------------------------ azioni
    def add_records(self, count: int | None = None) -> int:
        name = self.name_edit.text().strip()
        table = self.project.table(name) if name else None
        if table is None:
            QMessageBox.information(self, "Add Records", "Applica prima la struttura della tabella.")
            return 0
        if count is None:
            count, ok = QInputDialog.getInt(
                self, "Add Records", "Record da aggiungere:", 1, 1, 1000
            )
            if not ok:
                return 0
        from ..runtime.rowset import Rowset

        rowset = Rowset(self.project.db, table)
        numeric_keys: dict[str, int] = {}
        for field in table.fields:
            if field.pk and field.type == T.INTEGER:
                numeric_keys[field.name] = int(
                    self.project.db.scalar(
                        f"SELECT COALESCE(MAX({ddl.quote(field.name)}), 0) "
                        f"FROM {ddl.quote(table.name)}"
                    )
                    or 0
                )
        added = 0
        for index in range(count):
            values = table.new_record()
            for field in table.fields:
                if field.pk and field.name in numeric_keys:
                    values[field.name] = numeric_keys[field.name] + index + 1
                    continue
                if not field.required:
                    continue
                value = values.get(field.name)
                if value not in (None, "") and not field.pk:
                    continue
                if field.type in (T.INTEGER, T.DECIMAL, T.BOOLEAN):
                    values[field.name] = index + 1
                elif field.type in (T.DATE, T.DATETIME):
                    values[field.name] = datetime.now().strftime(
                        "%Y-%m-%d" if field.type == T.DATE else "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    values[field.name] = f"nuovo_{rowset.count() + index + 1}"
            try:
                rowset.insert(values)
            except RowsetError as exc:
                QMessageBox.warning(self, "Add Records", str(exc))
                break
            added += 1
        if added:
            self._refresh_stats()
            self._update_preview()
        return added

    def save_as(self, name: str | None = None, caption: str | None = None) -> Table | None:
        table = self.current_table()
        if name is None:
            dialog = SaveTableDialog(
                f"{table.name or 'tabella'}_copia",
                table.caption,
                self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return None
            name, caption = dialog.values()
        table.name = name.strip()
        if caption is not None:
            table.caption = caption
        if not table.name:
            QMessageBox.warning(self, "Save Table", "Il nome della tabella è obbligatorio.")
            return None
        table.id = new_id()
        try:
            table.validate()
        except MetadataError as exc:
            QMessageBox.warning(self, "Save Table", str(exc))
            return None
        if self.project.table(table.name) is not None:
            QMessageBox.warning(self, "Save Table", f"La tabella {table.name} esiste già.")
            return None
        try:
            self.project.apply_table(table)
        except (ProjectError, MetadataError) as exc:
            QMessageBox.critical(self, "Save Table", str(exc))
            return None
        self.table_created.emit(table.name)
        return table

    def print_structure(self) -> None:
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        if QPrintDialog(printer, self).exec() != QDialog.DialogCode.Accepted:
            return
        document = QTextDocument()
        document.setPlainText(self.ddl_view.toPlainText())
        document.print(printer)

    def _cancel(self) -> None:
        if not self.embedded:
            self.reject()
            return
        if self.original is not None:
            reloaded = self.project.table(self.original.name)
            if reloaded is not None:
                self.table = reloaded.copy()
                self.original = reloaded
                self._original_names = {field.id: field.name for field in self.table.fields}
                self._index_touched.clear()
                self._load()
                self._update_preview()
                self._refresh_stats()

    def _apply(self) -> None:
        table = self.current_table()
        try:
            table.validate()
        except MetadataError as exc:
            QMessageBox.warning(self, "Struttura non valida", str(exc))
            return
        if self.original is not None and table.name.lower() != self.original.name.lower():
            from ..core.refactor import rename_table

            try:
                rename_table(self.project, self.original.name, table.name)
            except (ProjectError, MetadataError) as exc:
                QMessageBox.warning(self, "Rinomina non riuscita", str(exc))
                return
            self.original = self.project.require_table(table.name)
        old = self.project.table(table.name) if self.project else None
        try:
            plan = ddl.plan_migration(old, table)
        except MetadataError as exc:
            QMessageBox.warning(self, "Struttura non valida", str(exc))
            return
        if self.original is not None and (plan.destructive or plan.kind == "rebuild"):
            details = "\n".join(plan.descriptions) or "La struttura verrà ricostruita."
            answer = QMessageBox.question(
                self,
                "Migrazione distruttiva",
                f"{details}\n\nVerrà creato un backup prima della migrazione. Continuare?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.project.apply_table(table)
        except (ProjectError, MetadataError) as exc:
            QMessageBox.critical(self, "Migrazione non riuscita", str(exc))
            return
        self.table = table
        self.original = table
        self._original_names = {field.id: field.name for field in table.fields}
        self._index_touched.clear()
        self._refresh_stats()
        self.table_changed.emit(table.name)
        if not self.embedded:
            self.accept()
