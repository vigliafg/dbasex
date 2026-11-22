"""Vista Dati di una tabella: griglia editabile, filtri, ordine, CSV (C5, C6)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import load_config, save_config
from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.metadata import Table
from ..core.search import SearchError, SearchRequest, build_where, replace_in_rowset
from ..io.csv_io import CsvError, export_rowset
from ..runtime.rowset import Rowset, RowsetError
from . import design, icons
from .find_dialog import FindDialog, ReplaceDialog
from .import_wizard import ImportCsvDialog

DEFAULT_OPTIONS = {
    "alternate": True,
    "record_numbers": True,
    "confirm_delete": True,
}


class RecordDialog(QDialog):
    """Inserimento di un nuovo record con validazione."""

    def __init__(self, table: Table, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = table
        self.setWindowTitle(f"Nuovo record — {table.display_name()}")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.editors: dict[str, QWidget] = {}
        for field in table.stored_fields:
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
        self.resize(460, min(680, 80 * max(1, len(table.stored_fields)) + 80))

    def values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for field in self.table.stored_fields:
            editor = self.editors[field.name]
            if isinstance(editor, QPlainTextEdit):
                text = editor.toPlainText()
            elif isinstance(editor, QLineEdit):
                text = editor.text()
            else:  # pragma: no cover
                text = ""
            result[field.name] = T.parse_input(text, field.type) if field.type != T.MEMO else (text or None)
        return result


class EditingOptionsDialog(QDialog):
    """Opzioni minime di visualizzazione della Browse."""

    def __init__(self, options: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editing Options")
        layout = QVBoxLayout(self)
        self.alternate = QCheckBox("Righe alternate")
        self.alternate.setChecked(bool(options.get("alternate", True)))
        self.record_numbers = QCheckBox("Colonna selettore record")
        self.record_numbers.setChecked(bool(options.get("record_numbers", True)))
        self.confirm_delete = QCheckBox("Conferma prima di eliminare")
        self.confirm_delete.setChecked(bool(options.get("confirm_delete", True)))
        for box in (self.alternate, self.record_numbers, self.confirm_delete):
            layout.addWidget(box)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(360, 170)

    def options(self) -> dict[str, bool]:
        return {
            "alternate": self.alternate.isChecked(),
            "record_numbers": self.record_numbers.isChecked(),
            "confirm_delete": self.confirm_delete.isChecked(),
        }


class DataView(QWidget):
    """Griglia dati in stile Browse di dBASE."""

    status_changed = pyqtSignal(str)
    structure_requested = pyqtSignal(str)

    def __init__(self, project, table_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("data_view")
        self.project = project
        self.table = project.require_table(table_name)
        self.rowset = Rowset(project.db, self.table)
        self._loading = False
        self._restoring = False
        self._filter = ""
        self._search = SearchRequest()
        config = load_config()
        self.options = dict(DEFAULT_OPTIONS)
        stored_options = config.get("browse_options")
        if isinstance(stored_options, dict):
            self.options.update(
                {key: bool(value) for key, value in stored_options.items() if key in DEFAULT_OPTIONS}
            )
        self._column_key = f"{project.path}::{table_name}"
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.setInterval(400)
        self._width_timer.timeout.connect(self._persist_columns)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        self.first_button = self._nav_button("primo", "Primo record", self.first_record)
        self.prev_button = self._nav_button("precedente", "Record precedente", self.previous_record)
        self.next_button = self._nav_button("successivo", "Record successivo", self.next_record)
        self.last_button = self._nav_button("ultimo", "Ultimo record", self.last_record)
        for button in (self.first_button, self.prev_button, self.next_button, self.last_button):
            bar.addWidget(button)
        bar.addSpacing(8)
        for button in (
            icons.make_button("Nuovo", "nuovo", self.new_record, self, "Nuovo record"),
            icons.make_button(
                "Elimina", "elimina", self.delete_record, self, "Elimina il record selezionato"
            ),
            icons.make_button("Aggiorna", "aggiorna", self.refresh, self, "Rileggi i record"),
        ):
            bar.addWidget(button)
        bar.addSpacing(8)
        for button in (
            icons.make_button("Trova…", "cerca", self.open_find, self, "Ricerca guidata con più criteri"),
            icons.make_button("Sostituisci…", "modifica", self.open_replace, self, "Sostituisci testo nei record visibili"),
        ):
            bar.addWidget(button)
        bar.addStretch(1)
        for button in (
            icons.make_button("Importa CSV…", "importa", self.import_csv, self, "Importa un file CSV con anteprima e mappatura"),
            icons.make_button("Esporta CSV", "esporta", self.export_csv, self, "Esporta i record in CSV"),
            icons.make_button("Struttura…", "tabella", self.edit_structure, self, "Apri Table Structure"),
            icons.make_button("Opzioni…", "impostazioni", self.edit_options, self, "Editing Options"),
        ):
            bar.addWidget(button)
        layout.addLayout(bar)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Cerca:"))
        self.search_edit = QLineEdit()
        self.search_edit.setAccessibleName("Cerca nei record")
        self.search_edit.setPlaceholderText("Cerca rapido in qualsiasi campo")
        self.search_edit.returnPressed.connect(self.apply_filter)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(QLabel("Ordina:"))
        self.order_combo = QComboBox()
        self.order_combo.addItem("(naturale)", "")
        for field in self.table.stored_fields:
            self.order_combo.addItem(field.display_name(), field.name)
        self.order_combo.currentIndexChanged.connect(self.apply_filter)
        filter_row.addWidget(self.order_combo)
        layout.addLayout(filter_row)

        self.table_header = QLabel("")
        self.table_header.setObjectName("browse_header")
        layout.addWidget(self.table_header)

        self.grid = QTableWidget(0, len(self.table.fields))
        self.grid.setAccessibleName("Griglia dei record")
        self.grid.setHorizontalHeaderLabels([f.display_name() for f in self.table.fields])
        self.grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.grid.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.grid.setAlternatingRowColors(self.options["alternate"])
        self.grid.verticalHeader().setVisible(self.options["record_numbers"])
        self.grid.verticalHeader().setFixedWidth(30)
        self.grid.verticalHeader().setDefaultSectionSize(design.METRICS.row_height + 2)
        self.grid.horizontalHeader().setStretchLastSection(True)
        self.grid.itemChanged.connect(self._on_item_changed)
        self.grid.currentCellChanged.connect(self._on_current_cell_changed)
        self.grid.horizontalHeader().sectionResized.connect(self._on_section_resized)
        layout.addWidget(self.grid, 1)

        self.status = QLabel("")
        layout.addWidget(self.status)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self.open_find)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.open_replace)

    def _nav_button(self, glyph: str, tooltip: str, slot):
        button = icons.make_button("", glyph, slot, self, tooltip)
        button.setFixedWidth(30)
        return button

    def _apply_options(self) -> None:
        self.grid.setAlternatingRowColors(bool(self.options.get("alternate", True)))
        self.grid.verticalHeader().setVisible(bool(self.options.get("record_numbers", True)))

    # ------------------------------------------------------------------ query
    def _where(self) -> tuple[str, tuple[Any, ...]]:
        clauses: list[str] = []
        params: list[Any] = []
        if self._filter:
            quick = []
            for field in self.table.stored_fields:
                quick.append(f'CAST("{field.name}" AS TEXT) LIKE ?')
                params.append(f"%{self._filter}%")
            clauses.append("(" + " OR ".join(quick) + ")")
        if self._search:
            try:
                where, search_params = build_where(self.table, self._search)
            except SearchError as exc:
                QMessageBox.warning(self, "Ricerca non valida", str(exc))
                where, search_params = "", ()
            if where:
                clauses.append(f"({where})")
                params.extend(search_params)
        return " AND ".join(clauses), tuple(params)

    def _order_field(self) -> str:
        return str(self.order_combo.currentData() or "")

    def edit_structure(self) -> None:
        self.structure_requested.emit(self.table.name)

    def reload_structure(self) -> None:
        """Ricarica la tabella dopo una modifica applicata da Table Structure."""
        previous_order = self._order_field()
        self.table = self.project.require_table(self.table.name)
        self.rowset = Rowset(self.project.db, self.table)
        self.order_combo.blockSignals(True)
        self.order_combo.clear()
        self.order_combo.addItem("(naturale)", "")
        for field in self.table.stored_fields:
            self.order_combo.addItem(field.display_name(), field.name)
        position = self.order_combo.findData(previous_order)
        self.order_combo.setCurrentIndex(max(0, position))
        self.order_combo.blockSignals(False)
        self.refresh()

    def edit_options(self) -> None:
        dialog = EditingOptionsDialog(self.options, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.options = dialog.options()
        config = load_config()
        config["browse_options"] = dict(self.options)
        save_config(config)
        self._apply_options()

    def refresh(self) -> None:
        self.grid.setColumnCount(len(self.table.fields))
        self.grid.setHorizontalHeaderLabels([f.display_name() for f in self.table.fields])
        caption = self.table.display_name()
        title = self.table.name if caption == self.table.name else f"{self.table.name} — {caption}"
        self.table_header.setText(f"{title}  ·  {len(self.table.fields)} campi")
        current_id = self.rowset.current.get(INTERNAL_ID) if self.rowset.current else None
        where, params = self._where()
        order_field = self._order_field()
        order = f'"{order_field}"' if order_field else ""
        try:
            self.rowset.open(where=where, params=params, order=order)
        except RowsetError as exc:
            QMessageBox.warning(self, "Lettura non riuscita", str(exc))
            return
        if current_id is not None:
            self.rowset.find(INTERNAL_ID, current_id)
        self._loading = True
        self.grid.setRowCount(len(self.rowset))
        for row_index, record in enumerate(self.rowset.rows()):
            for col, field in enumerate(self.table.fields):
                value = record.get(field.name)
                item = QTableWidgetItem(T.format_value(value, field.type, field.fmt))
                item.setData(Qt.ItemDataRole.UserRole, record.get(INTERNAL_ID))
                if field.type == T.BLOB:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if not field.stored:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setToolTip(f"Campo calcolato: {field.calculated}")
                self.grid.setItem(row_index, col, item)
        self._loading = False
        self._restoring = True
        if not self._restore_columns():
            self.grid.resizeColumnsToContents()
        self._restoring = False
        self._sync_selection()
        self._update_status()

    def apply_filter(self) -> None:
        self._filter = self.search_edit.text().strip()
        self.refresh()

    def _restore_columns(self) -> bool:
        config = load_config()
        widths = config.get("browse_columns", {}).get(self._column_key)
        if not isinstance(widths, dict):
            return False
        applied = False
        for col, field in enumerate(self.table.fields):
            width = widths.get(field.name)
            if isinstance(width, int) and width > 20:
                self.grid.setColumnWidth(col, width)
                applied = True
        return applied

    def _on_section_resized(self, *_args: int) -> None:
        if self._loading or self._restoring:
            return
        self._width_timer.start()

    def _persist_columns(self) -> None:
        widths = {
            field.name: self.grid.columnWidth(col)
            for col, field in enumerate(self.table.fields)
        }
        config = load_config()
        columns = config.setdefault("browse_columns", {})
        if not isinstance(columns, dict):
            columns = {}
            config["browse_columns"] = columns
        columns[self._column_key] = widths
        save_config(config)

    # ------------------------------------------------------------- navigazione
    def _sync_selection(self) -> None:
        index = self.rowset.index
        if index < 0 or index >= self.grid.rowCount():
            return
        column = max(0, self.grid.currentColumn())
        self._loading = True
        self.grid.setCurrentCell(index, column)
        self.grid.selectRow(index)
        item = self.grid.item(index, 0)
        if item is not None:
            self.grid.scrollToItem(item)
        self._loading = False
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        index = self.rowset.index
        total = len(self.rowset)
        self.first_button.setEnabled(index > 0)
        self.prev_button.setEnabled(index > 0)
        self.next_button.setEnabled(0 <= index < total - 1)
        self.last_button.setEnabled(0 <= index < total - 1)

    def _update_status(self) -> None:
        position = self.rowset.index + 1 if self.rowset.current else 0
        parts = [f"Record {position} di {len(self.rowset)}"]
        if self._filter:
            parts.append(f"filtro: {self._filter}")
        if self._search:
            parts.append(f"ricerca: {len(self._search.criteria)} criteri ({self._search.match.upper()})")
        if self._order_field():
            parts.append(f"ordine: {self.order_combo.currentText()}")
        text = " · ".join(parts)
        self.status.setText(text)
        self.status_changed.emit(text)

    def _on_current_cell_changed(self, row: int, _column: int, _prev_row: int, _prev_col: int) -> None:
        if self._loading:
            return
        if 0 <= row < len(self.rowset) and row != self.rowset.index:
            self.rowset.goto(row)
            self._update_nav_buttons()
            self._update_status()

    def goto_record(self, index: int) -> None:
        self.rowset.goto(index)
        self._sync_selection()
        self._update_status()

    def first_record(self) -> None:
        self.rowset.first()
        self._sync_selection()
        self._update_status()

    def previous_record(self) -> None:
        self.rowset.previous()
        self._sync_selection()
        self._update_status()

    def next_record(self) -> None:
        self.rowset.next()
        self._sync_selection()
        self._update_status()

    def last_record(self) -> None:
        self.rowset.last()
        self._sync_selection()
        self._update_status()

    # ------------------------------------------------------------------- edit
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        record_id = item.data(Qt.ItemDataRole.UserRole)
        if record_id is None:
            return
        record = self.rowset.load(int(record_id))
        if record is None:
            return
        field = self.table.fields[item.column()]
        if not field.stored:
            return
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
        self._update_status()

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
        if self.options.get("confirm_delete", True):
            answer = QMessageBox.question(self, "Elimina", "Eliminare il record selezionato?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.rowset.delete(int(record_id))
        except RowsetError as exc:
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self.refresh()

    # ------------------------------------------------------------------ find
    def open_find(self) -> None:
        dialog = FindDialog(self.project, self.table, self._search, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._search = SearchRequest() if dialog.was_cleared() else dialog.request()
        self.refresh()
        if self._search:
            self.status.setText(f"{len(self.rowset)} record trovati")
        else:
            self.status.setText(f"Ricerca azzerata · {len(self.rowset)} record")

    def clear_find(self) -> None:
        self._search = SearchRequest()
        self.refresh()

    def open_replace(self) -> None:
        dialog = ReplaceDialog(self.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        total = len(self.rowset)
        if total == 0:
            QMessageBox.information(self, "Sostituisci", "Nessun record visibile su cui operare.")
            return
        answer = QMessageBox.question(
            self,
            "Sostituisci",
            f"Sostituire «{values['find']}» con «{values['replace']}» "
            f"nei {total} record visibili?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            changed = replace_in_rowset(
                self.rowset,
                values["find"],
                values["replace"],
                field=values["field"],
                match_case=values["match_case"],
                whole_word=values["whole_word"],
            )
        except (SearchError, RowsetError) as exc:
            QMessageBox.warning(self, "Sostituzione non riuscita", str(exc))
            return
        self.refresh()
        self.status.setText(f"Sostituite {changed} celle in {total} record")
        QMessageBox.information(self, "Sostituisci", f"Sostituite {changed} celle.")

    def import_csv(self) -> None:
        dialog = ImportCsvDialog(self.project, self.table.name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.reload_structure()
        self.status.setText(f"Importati {dialog.imported} record da CSV")

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
