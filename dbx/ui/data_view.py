"""Vista Dati di una tabella: griglia editabile, filtri, ordine, CSV (C5, C6)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.metadata import Table
from ..io.csv_io import CsvError, export_rowset
from ..runtime.rowset import Rowset, RowsetError
from . import icons


class RecordDialog(QDialog):
    """Inserimento di un nuovo record con validazione."""

    def __init__(self, table: Table, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = table
        self.setWindowTitle(f"Nuovo record — {table.display_name()}")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.editors: dict[str, QWidget] = {}
        for field in table.fields:
            if field.type == T.MEMO:
                editor: QWidget = QPlainTextEdit()
                editor.setFixedHeight(70)
            else:
                editor = QLineEdit()
                if field.type in (T.DATE, T.DATETIME):
                    editor.setPlaceholderText("AAAA-MM-GG")
                elif field.type == T.BOOLEAN:
                    editor.setPlaceholderText("Sì/No")
            if field.required:
                editor.setToolTip("Campo obbligatorio")
            self.editors[field.name] = editor
            form.addRow(field.display_name() + (" *" if field.required else ""), editor)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(460, min(680, 80 * max(1, len(table.fields)) + 80))

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field in self.table.fields:
            editor = self.editors[field.name]
            if isinstance(editor, QPlainTextEdit):
                text = editor.toPlainText()
            elif isinstance(editor, QLineEdit):
                text = editor.text()
            else:  # pragma: no cover
                text = ""
            result[field.name] = T.parse_input(text, field.type) if field.type != T.MEMO else (text or None)
        return result


class DataView(QWidget):
    """Griglia dati in stile Browse di dBASE."""

    status_changed = pyqtSignal(str)

    def __init__(self, project, table_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.table = project.require_table(table_name)
        self.rowset = Rowset(project.db, self.table)
        self._loading = False
        self._filter = ""
        self._order = ""
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        bar = QHBoxLayout()
        new = icons.make_button("Nuovo", "nuovo", self.new_record, self, "Nuovo record")
        delete = icons.make_button("Elimina", "elimina", self.delete_record, self, "Elimina il record selezionato")
        refresh = icons.make_button("Aggiorna", "aggiorna", self.refresh, self, "Rileggi i record")
        export = icons.make_button("Esporta CSV", "esporta", self.export_csv, self, "Esporta i record in CSV")
        structure = icons.make_button("Struttura…", "tabella", self.edit_structure, self, "Apri Table Structure")
        for button in (new, delete, refresh, export, structure):
            bar.addWidget(button)
        bar.addSpacing(12)
        bar.addWidget(QLabel("Cerca:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("testo in qualsiasi campo")
        self.search_edit.returnPressed.connect(self.apply_filter)
        bar.addWidget(self.search_edit, 1)
        bar.addWidget(QLabel("Ordina:"))
        self.order_combo = QComboBox()
        self.order_combo.addItem("(naturale)", "")
        for field in self.table.fields:
            self.order_combo.addItem(field.display_name(), field.name)
        self.order_combo.currentIndexChanged.connect(self.apply_filter)
        bar.addWidget(self.order_combo)
        layout.addLayout(bar)

        self.grid = QTableWidget(0, len(self.table.fields))
        self.grid.setHorizontalHeaderLabels([f.display_name() for f in self.table.fields])
        self.grid.verticalHeader().setVisible(False)
        self.grid.setAlternatingRowColors(True)
        self.grid.itemChanged.connect(self._on_item_changed)
        self.grid.doubleClicked.connect(lambda _index: self.grid.editItem(self.grid.currentItem()))
        layout.addWidget(self.grid, 1)
        self.status = QLabel("")
        layout.addWidget(self.status)

    # ------------------------------------------------------------------ query
    def _where(self) -> tuple[str, tuple[Any, ...]]:
        if not self._filter:
            return "", ()
        clauses = []
        params: list[Any] = []
        for field in self.table.fields:
            if field.type in (T.TEXT, T.MEMO):
                clauses.append(f'"{field.name}" LIKE ?')
                params.append(f"%{self._filter}%")
            else:
                clauses.append(f'CAST("{field.name}" AS TEXT) LIKE ?')
                params.append(f"%{self._filter}%")
        return "(" + " OR ".join(clauses) + ")", tuple(params)

    def edit_structure(self) -> None:
        from ..designers.table_builder import TableBuilderDialog

        dialog = TableBuilderDialog(self.project, self.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.table = self.project.require_table(self.table.name)
        self.rowset = Rowset(self.project.db, self.table)
        self.refresh()

    def refresh(self) -> None:
        self.grid.setColumnCount(len(self.table.fields))
        self.grid.setHorizontalHeaderLabels([f.display_name() for f in self.table.fields])
        where, params = self._where()
        order_field = self.order_combo.currentData() if hasattr(self, "order_combo") else ""
        order = f'"{order_field}"' if order_field else ""
        try:
            self.rowset.open(where=where, params=params, order=order)
        except RowsetError as exc:
            QMessageBox.warning(self, "Lettura non riuscita", str(exc))
            return
        self._loading = True
        self.grid.setRowCount(len(self.rowset))
        for row_index, record in enumerate(self.rowset.rows()):
            for col, field in enumerate(self.table.fields):
                value = record.get(field.name)
                item = QTableWidgetItem(T.format_value(value, field.type, field.fmt))
                item.setData(Qt.ItemDataRole.UserRole, record.get(INTERNAL_ID))
                if field.type == T.BLOB:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.grid.setItem(row_index, col, item)
        self._loading = False
        self.grid.resizeColumnsToContents()
        text = f"Record {len(self.rowset)}" + (f" — filtro: {self._filter}" if self._filter else "")
        self.status.setText(text)
        self.status_changed.emit(text)

    def apply_filter(self) -> None:
        self._filter = self.search_edit.text().strip()
        self.refresh()

    # ------------------------------------------------------------------- edit
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        row_index = item.row()
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id is None:
            return
        record = self.rowset.load(int(record_id))
        if record is None:
            return
        field = self.table.fields[item.column()]
        try:
            value = T.parse_input(item.text(), field.type)
            record[field.name] = value
            self.rowset.update(int(record_id), record)
        except (ValueError, RowsetError) as exc:
            QMessageBox.warning(self, "Modifica non valida", str(exc))
            self._loading = True
            item.setText(T.format_value(record.get(field.name), field.type, field.fmt))
            self._loading = False
            return
        self._loading = True
        item.setText(T.format_value(record.get(field.name), field.type, field.fmt))
        self._loading = False

    def new_record(self) -> None:
        dialog = RecordDialog(self.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.rowset.insert(dialog.values())
        except RowsetError as exc:
            QMessageBox.warning(self, "Inserimento non riuscito", str(exc))
            return
        self.refresh()

    def delete_record(self) -> None:
        row = self.grid.currentRow()
        if row < 0:
            return
        item = self.grid.item(row, 0)
        record_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if record_id is None:
            return
        answer = QMessageBox.question(self, "Elimina", "Eliminare il record selezionato?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.rowset.delete(int(record_id))
        except RowsetError as exc:
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self.refresh()

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Esporta CSV", f"{self.table.name}.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            export_rowset(self.rowset, path)
        except CsvError as exc:
            QMessageBox.warning(self, "Export non riuscito", str(exc))
            return
        self.status.setText(f"Esportati {len(self.rowset)} record in {path}")
