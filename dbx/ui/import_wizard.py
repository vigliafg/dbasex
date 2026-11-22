"""Importazione CSV guidata con anteprima e mappatura delle colonne (0.6)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.metadata import Table
from ..io.csv_io import (
    DELIMITERS,
    ENCODINGS,
    CsvError,
    read_table,
    records_from_table,
    suggest_mapping,
)
from ..runtime.rowset import Rowset, RowsetError
from . import icons

PREVIEW_LIMIT = 50


class ImportCsvDialog(QDialog):
    """Wizard minimo: file, opzioni, anteprima, mappatura e importazione."""

    def __init__(self, project, table_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.table: Table = project.require_table(table_name)
        self.imported = 0
        self._rows: list[list[str]] = []
        self._mapping: list[str | None] = []
        self._headers: list[str] = []
        self.setWindowTitle(f"Importa CSV — {self.table.display_name()}")
        self.resize(900, 680)

        layout = QVBoxLayout(self)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("File CSV:"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Scegli un file .csv o .txt")
        self.path_edit.textChanged.connect(self._file_changed)
        file_row.addWidget(self.path_edit, 1)
        file_row.addWidget(
            icons.make_button("Sfoglia…", "apri", self.browse, self, "Scegli il file da importare")
        )
        layout.addLayout(file_row)

        options = QGroupBox("Opzioni di lettura")
        grid = QGridLayout(options)
        self.encoding_combo = QComboBox()
        for key, label in ENCODINGS.items():
            self.encoding_combo.addItem(label, key)
        self.delimiter_combo = QComboBox()
        for key, label in DELIMITERS.items():
            self.delimiter_combo.addItem(label, key)
        self.header_box = QCheckBox("La prima riga contiene i nomi delle colonne")
        self.header_box.setChecked(True)
        self.clear_box = QCheckBox("Svuota la tabella prima di importare")
        self.clear_box.setToolTip("Operazione irreversibile: viene creato un backup solo su richiesta.")
        for widget in (self.encoding_combo, self.delimiter_combo):
            widget.currentIndexChanged.connect(self.reload_preview)
        self.header_box.stateChanged.connect(self.reload_preview)
        grid.addWidget(QLabel("Codifica:"), 0, 0)
        grid.addWidget(self.encoding_combo, 0, 1)
        grid.addWidget(QLabel("Delimitatore:"), 0, 2)
        grid.addWidget(self.delimiter_combo, 0, 3)
        grid.addWidget(self.header_box, 1, 0, 1, 2)
        grid.addWidget(self.clear_box, 1, 2, 1, 2)
        layout.addWidget(options)

        preview_box = QGroupBox("Anteprima")
        preview_layout = QVBoxLayout(preview_box)
        self.summary = QLabel("Scegli un file per vedere l'anteprima.")
        preview_layout.addWidget(self.summary)
        self.preview = QTableWidget(0, 0)
        self.preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.preview.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview.setMaximumHeight(190)
        self.preview.verticalHeader().setVisible(False)
        preview_layout.addWidget(self.preview)
        layout.addWidget(preview_box)

        mapping_box = QGroupBox("Mappatura colonne → campi")
        mapping_layout = QVBoxLayout(mapping_box)
        self.mapping_table = QTableWidget(0, 2)
        self.mapping_table.setHorizontalHeaderLabels(["Colonna CSV", "Campo dBX"])
        self.mapping_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mapping_table.verticalHeader().setVisible(False)
        self.mapping_table.setColumnWidth(0, 320)
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        mapping_layout.addWidget(self.mapping_table)
        layout.addWidget(mapping_box, 1)

        buttons = QDialogButtonBox()
        self.import_button = buttons.addButton(
            "Importa", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.import_button.setEnabled(False)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.run_import)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ file
    def browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importa CSV", "", "CSV e testo (*.csv *.txt *.tsv);;Tutti i file (*)"
        )
        if path:
            self.path_edit.setText(path)

    def _file_changed(self) -> None:
        self.reload_preview()

    def reload_preview(self) -> None:
        path = self.path_edit.text().strip()
        if not path:
            self._rows = []
            self._headers = []
            self.preview.setRowCount(0)
            self.preview.setColumnCount(0)
            self.mapping_table.setRowCount(0)
            self.summary.setText("Scegli un file per vedere l'anteprima.")
            self.import_button.setEnabled(False)
            return
        try:
            _delim, _encoding, rows = read_table(
                path,
                str(self.delimiter_combo.currentData() or "auto"),
                str(self.encoding_combo.currentData() or "auto"),
            )
        except CsvError as exc:
            self._rows = []
            self._headers = []
            self.preview.setRowCount(0)
            self.preview.setColumnCount(0)
            self.mapping_table.setRowCount(0)
            self.summary.setText(str(exc))
            self.import_button.setEnabled(False)
            return
        self._rows = rows
        has_header = self.header_box.isChecked()
        if has_header and rows:
            self._headers = [str(cell).strip() or f"Colonna {index + 1}" for index, cell in enumerate(rows[0])]
            data = rows[1:]
        else:
            width = max((len(row) for row in rows), default=0)
            self._headers = [f"Colonna {index + 1}" for index in range(width)]
            data = rows
        self._build_preview(data)
        self._build_mapping()
        self.summary.setText(
            f"{len(data)} righe di dati · {len(self._headers)} colonne · "
            f"delimitatore {_delim!r} · codifica {_encoding}"
        )
        self.import_button.setEnabled(bool(data) and bool(self._headers))

    def _build_preview(self, data: list[list[str]]) -> None:
        visible = data[:PREVIEW_LIMIT]
        self.preview.setColumnCount(len(self._headers))
        self.preview.setHorizontalHeaderLabels(self._headers)
        self.preview.setRowCount(len(visible))
        for row_index, row in enumerate(visible):
            for column, value in enumerate(row[: len(self._headers)]):
                self.preview.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.preview.resizeColumnsToContents()

    def _build_mapping(self) -> None:
        previous = list(self._mapping)
        suggested = suggest_mapping(self._headers, self.table)
        self.mapping_table.setRowCount(len(self._headers))
        self._mapping = []
        for column, header in enumerate(self._headers):
            label = QTableWidgetItem(str(header))
            label.setFlags(label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mapping_table.setItem(column, 0, label)
            combo = QComboBox()
            combo.addItem("(ignora)", "")
            for field in self.table.fields:
                combo.addItem(field.display_name(), field.name)
            choice = None
            if column < len(previous) and previous[column]:
                choice = previous[column]
            elif suggested[column]:
                choice = suggested[column]
            position = combo.findData(choice)
            combo.setCurrentIndex(max(0, position))
            combo.currentIndexChanged.connect(
                lambda _index, col=column, widget=combo: self._set_mapping(col, widget)
            )
            self.mapping_table.setCellWidget(column, 1, combo)
            self._mapping.append(str(combo.currentData() or "") or None)
        self.mapping_table.resizeColumnsToContents()
        self.mapping_table.setColumnWidth(0, 320)

    def _set_mapping(self, column: int, combo: QComboBox) -> None:
        while len(self._mapping) <= column:
            self._mapping.append(None)
        self._mapping[column] = str(combo.currentData() or "") or None

    def current_mapping(self) -> list[str | None]:
        mapping: list[str | None] = []
        for column in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(column, 1)
            mapping.append(
                str(combo.currentData() or "") or None if isinstance(combo, QComboBox) else None
            )
        return mapping

    # --------------------------------------------------------------- importa
    def run_import(self) -> None:
        mapping = self.current_mapping()
        if not any(mapping):
            QMessageBox.warning(
                self, "Importa CSV", "Associa almeno una colonna a un campo della tabella."
            )
            return
        targets = [name for name in mapping if name]
        if len(targets) != len(set(targets)):
            QMessageBox.warning(
                self, "Importa CSV", "Ogni campo può ricevere una sola colonna del file."
            )
            return
        if self.clear_box.isChecked():
            answer = QMessageBox.question(
                self,
                "Importa CSV",
                f"Svuotare «{self.table.display_name()}» prima di importare? "
                "I record esistenti saranno eliminati.",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.project.backup("import-csv")
        try:
            records = records_from_table(
                self._rows,
                self.table,
                mapping,
                self.header_box.isChecked(),
            )
            if not records:
                QMessageBox.information(self, "Importa CSV", "Nessuna riga da importare.")
                return
            count = self._insert_records(records, self.clear_box.isChecked())
        except (CsvError, RowsetError) as exc:
            QMessageBox.warning(self, "Importazione non riuscita", str(exc))
            return
        self.imported = count
        QMessageBox.information(
            self, "Importa CSV", f"Importati {count} record in «{self.table.display_name()}»."
        )
        self.accept()

    def _insert_records(self, records: list[dict], clear: bool) -> int:
        rowset = Rowset(self.project.db, self.table)
        count = 0
        try:
            with self.project.db.transaction():
                if clear:
                    self.project.db.execute(f'DELETE FROM "{self.table.name}"')
                for index, record in enumerate(records):
                    try:
                        rowset.insert(record)
                    except RowsetError as exc:
                        raise CsvError(f"Riga {index + 2}: {exc}") from exc
                    count += 1
        except Exception:
            # Il rowset in memoria è solo di lavoro: il rollback ripristina il database.
            raise
        return count


__all__ = ["ImportCsvDialog"]
