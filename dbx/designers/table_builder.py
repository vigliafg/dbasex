"""Table Builder: struttura, indici, relazioni e applicazione (C1–C4)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import ddl
from ..core import types as T
from ..core.metadata import Field, ForeignKey, Index, MetadataError, Table, new_id, ON_DELETE_ACTIONS
from ..core.project import Project, ProjectError
from ..ui import icons

FIELD_COLUMNS = ["Nome", "Tipo", "Dim.", "Obbligatorio", "Default", "Didascalia", "Formato", "Regola", "Lookup"]


class TableBuilderDialog(QDialog):
    """Editor della struttura di una tabella, con anteprima DDL."""

    def __init__(self, project: Project, table: Table | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.original = table
        self.table = table.copy() if table else Table(name="", fields=[Field("nome", T.TEXT)])
        self.setWindowTitle(f"Table Structure — {table.name if table else '(Untitled)'}")
        self.resize(1040, 720)
        self._build_ui()
        self._load()
        self._update_preview()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Tabella:"))
        from PyQt6.QtWidgets import QLineEdit

        self.name_edit = QLineEdit(self.table.name)
        self.name_edit.setPlaceholderText("nome_tabella")
        self.name_edit.textChanged.connect(self._update_preview)
        header.addWidget(self.name_edit, 1)
        header.addWidget(QLabel("Type:"))
        type_label = QLabel("DBASE (SQLite)")
        type_label.setToolTip("Il motore di dBX è SQLite: la struttura resta in stile dBASE")
        header.addWidget(type_label)
        header.addWidget(QLabel("Didascalia:"))
        self.caption_edit = QLineEdit(self.table.caption)
        self.caption_edit.textChanged.connect(self._update_preview)
        header.addWidget(self.caption_edit, 1)
        layout.addLayout(header)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet("color: palette(mid);")
        layout.addWidget(self.meta_label)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._build_fields_tab()
        self._build_indexes_tab()
        self._build_relations_tab()
        self.ddl_view = QPlainTextEdit()
        self.ddl_view.setReadOnly(True)
        self.ddl_view.setStyleSheet("font-family: monospace;")
        self.tabs.addTab(self.ddl_view, "Anteprima DDL")

        buttons = QDialogButtonBox()
        self.apply_button = buttons.addButton("Applica", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Annulla", QDialogButtonBox.ButtonRole.RejectRole)
        icons.style_button_box(buttons)
        self.apply_button.setDefault(True)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_fields_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.fields_grid = QTableWidget(0, len(FIELD_COLUMNS))
        self.fields_grid.setHorizontalHeaderLabels(FIELD_COLUMNS)
        self.fields_grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.fields_grid.horizontalHeader().setStretchLastSection(True)
        self.fields_grid.verticalHeader().setVisible(True)
        self.fields_grid.verticalHeader().setFixedWidth(28)
        self.fields_grid.setToolTip("La colonna a sinistra numera i campi come Field in Table Structure")
        layout.addWidget(self.fields_grid, 1)
        bar = QHBoxLayout()
        add = icons.make_button("Aggiungi campo", "nuovo", lambda: self._add_field_row(Field("nuovo_campo", T.TEXT)), self)
        remove = icons.make_button("Rimuovi campo", "elimina", self._remove_field_row, self)
        up = icons.make_button("Sposta su", "su", lambda: self._move_field(-1), self)
        down = icons.make_button("Sposta giù", "giu", lambda: self._move_field(1), self)
        for button in (add, remove, up, down):
            bar.addWidget(button)
        bar.addStretch(1)
        layout.addLayout(bar)
        self.tabs.addTab(container, "Campi")

    def _build_indexes_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.index_grid = QTableWidget(0, 3)
        self.index_grid.setHorizontalHeaderLabels(["Nome", "Campi (separati da virgola)", "Univoco"])
        self.index_grid.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.index_grid, 1)
        bar = QHBoxLayout()
        add = icons.make_button("Aggiungi indice", "nuovo", lambda: self._add_index_row(Index()), self)
        remove = icons.make_button("Rimuovi indice", "elimina", lambda: self._remove_row(self.index_grid), self)
        bar.addWidget(add)
        bar.addWidget(remove)
        bar.addStretch(1)
        layout.addLayout(bar)
        self.tabs.addTab(container, "Indici")

    def _build_relations_tab(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.relation_grid = QTableWidget(0, 4)
        self.relation_grid.setHorizontalHeaderLabels(["Campo", "Tabella riferita", "Campo riferito", "Su eliminazione"])
        self.relation_grid.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.relation_grid, 1)
        bar = QHBoxLayout()
        add = icons.make_button("Aggiungi relazione", "nuovo", lambda: self._add_relation_row(ForeignKey()), self)
        remove = icons.make_button("Rimuovi relazione", "elimina", lambda: self._remove_row(self.relation_grid), self)
        bar.addWidget(add)
        bar.addWidget(remove)
        bar.addStretch(1)
        layout.addLayout(bar)
        self.tabs.addTab(container, "Relazioni")

    # ---------------------------------------------------------------- caricamento
    def _load(self) -> None:
        self.name_edit.setText(self.table.name)
        self.caption_edit.setText(self.table.caption)
        self.fields_grid.setRowCount(0)
        for field in self.table.fields:
            self._add_field_row(field)
        self.index_grid.setRowCount(0)
        for index in self.table.indexes:
            self._add_index_row(index)
        self.relation_grid.setRowCount(0)
        for fk in self.table.foreign_keys:
            self._add_relation_row(fk)

    # ------------------------------------------------------------------ campi
    def _add_field_row(self, field: Field) -> None:
        row = self.fields_grid.rowCount()
        self.fields_grid.insertRow(row)
        name = QTableWidgetItem(field.name)
        name.setData(Qt.ItemDataRole.UserRole, field.id)
        self.fields_grid.setItem(row, 0, name)
        combo = QComboBox()
        for key in T.ALL_TYPES:
            combo.addItem(T.label(key), key)
        index = combo.findData(field.type)
        combo.setCurrentIndex(max(0, index))
        self.fields_grid.setCellWidget(row, 1, combo)

        def text_item(value: str = "") -> QTableWidgetItem:
            return QTableWidgetItem(str(value))

        self.fields_grid.setItem(row, 2, text_item(str(field.size or "")))
        required = QTableWidgetItem()
        required.setFlags(required.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        required.setCheckState(Qt.CheckState.Checked if field.required else Qt.CheckState.Unchecked)
        self.fields_grid.setItem(row, 3, required)
        self.fields_grid.setItem(row, 4, text_item(field.default))
        self.fields_grid.setItem(row, 5, text_item(field.caption))
        self.fields_grid.setItem(row, 6, text_item(field.fmt))
        self.fields_grid.setItem(row, 7, text_item(field.rule))
        self.fields_grid.setItem(row, 8, text_item(field.lookup))
        self.fields_grid.resizeColumnsToContents()
        self._update_preview()

    def _remove_field_row(self) -> None:
        self._remove_row(self.fields_grid)

    def _move_field(self, delta: int) -> None:
        row = self.fields_grid.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.fields_grid.rowCount():
            return
        fields = self._collect_fields()
        fields[row], fields[target] = fields[target], fields[row]
        self.fields_grid.setRowCount(0)
        self.table.fields = fields
        for field in fields:
            self._add_field_row(field)
        self.fields_grid.setCurrentCell(target, 0)

    def _remove_row(self, grid: QTableWidget) -> None:
        row = grid.currentRow()
        if row >= 0:
            grid.removeRow(row)
            self._update_preview()

    def _collect_fields(self) -> list[Field]:
        fields: list[Field] = []
        for row in range(self.fields_grid.rowCount()):
            name_item = self.fields_grid.item(row, 0)
            name = (name_item.text() if name_item else "").strip()
            combo = self.fields_grid.cellWidget(row, 1)
            field_type = combo.currentData() if isinstance(combo, QComboBox) else T.TEXT
            try:
                size = int((self.fields_grid.item(row, 2).text() if self.fields_grid.item(row, 2) else "0") or 0)
            except ValueError:
                size = 0
            required_item = self.fields_grid.item(row, 3)
            required = bool(required_item and required_item.checkState() == Qt.CheckState.Checked)
            fields.append(
                Field(
                    name=name,
                    type=field_type,
                    size=size,
                    required=required,
                    default=self.fields_grid.item(row, 4).text() if self.fields_grid.item(row, 4) else "",
                    caption=self.fields_grid.item(row, 5).text() if self.fields_grid.item(row, 5) else "",
                    fmt=self.fields_grid.item(row, 6).text() if self.fields_grid.item(row, 6) else "",
                    rule=self.fields_grid.item(row, 7).text() if self.fields_grid.item(row, 7) else "",
                    lookup=self.fields_grid.item(row, 8).text() if self.fields_grid.item(row, 8) else "",
                    id=(name_item.data(Qt.ItemDataRole.UserRole) if name_item and name_item.data(Qt.ItemDataRole.UserRole) else new_id()),
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
        self.index_grid.resizeColumnsToContents()

    def _collect_indexes(self) -> list[Index]:
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

    # --------------------------------------------------------------- relazioni
    def _add_relation_row(self, fk: ForeignKey) -> None:
        row = self.relation_grid.rowCount()
        self.relation_grid.insertRow(row)
        self.relation_grid.setItem(row, 0, QTableWidgetItem(", ".join(fk.columns)))
        self.relation_grid.setItem(row, 1, QTableWidgetItem(fk.ref_table))
        self.relation_grid.setItem(row, 2, QTableWidgetItem(", ".join(fk.ref_columns)))
        combo = QComboBox()
        for action in ON_DELETE_ACTIONS:
            combo.addItem(action, action)
        index = combo.findData(fk.on_delete.upper())
        combo.setCurrentIndex(max(0, index))
        self.relation_grid.setCellWidget(row, 3, combo)
        self.relation_grid.resizeColumnsToContents()

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
            relations.append(
                ForeignKey(
                    columns=columns,
                    ref_table=ref_table,
                    ref_columns=ref_columns,
                    on_delete=combo.currentData() if isinstance(combo, QComboBox) else "NO ACTION",
                )
            )
        return relations

    # ---------------------------------------------------------------- corrente
    def current_table(self) -> Table:
        table = Table(
            name=self.name_edit.text().strip(),
            caption=self.caption_edit.text().strip(),
            fields=self._collect_fields(),
            indexes=self._collect_indexes(),
            foreign_keys=self._collect_relations(),
            id=self.original.id if self.original else self.table.id,
        )
        return table

    def _update_preview(self) -> None:
        records = "—"
        name = self.name_edit.text().strip() if hasattr(self, "meta_label") else ""
        if name and self.project is not None and self.project.table(name) is not None:
            try:
                rows = self.project.db.query(f'SELECT COUNT(*) AS n FROM "{name}"')
                records = str(rows[0]["n"]) if rows else "0"
            except Exception:  # pragma: no cover - tabella appena rinominata
                records = "—"
        if hasattr(self, "meta_label"):
            self.meta_label.setText(
                f"Campi: {self.fields_grid.rowCount()} · Indici: {self.index_grid.rowCount()} · "
                f"Relazioni: {self.relation_grid.rowCount()} · Record: {records}"
            )
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
            return
        lines = ["-- Modifiche pianificate:"] + [f"-- {d}" for d in plan.descriptions] + ["", plan.sql or "-- nessuna modifica"]
        self.ddl_view.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ azioni
    def _apply(self) -> None:
        table = self.current_table()
        try:
            table.validate()
        except MetadataError as exc:
            QMessageBox.warning(self, "Struttura non valida", str(exc))
            return
        try:
            self.project.apply_table(table)
        except (ProjectError, MetadataError) as exc:
            QMessageBox.critical(self, "Migrazione non riuscita", str(exc))
            return
        self.table = table
        self.original = table
        self.accept()
