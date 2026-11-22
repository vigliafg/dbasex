"""Componenti condivisi delle procedure guidate (esperti) di dBX.

Gli esperti producono artefatti normali del progetto: non introducono formati
speciali e non duplicano i modelli dati. Questo modulo contiene solo lo shell
comune e i widget riusabili; la logica di ogni esperto resta nel proprio file.
"""

from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import QRegularExpression, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QWizard,
)

from ..core import types as T
from ..core.metadata import Field, new_id
from ..ui import icons

COL_NAME, COL_TYPE, COL_SIZE, COL_DECIMALS, COL_CAPTION, COL_PK = range(6)
FIELD_HEADERS = ["Nome", "Tipo", "Lunghezza", "Decimali", "Didascalia", "Chiave"]
IDENT_PATTERN = r"[A-Za-z_][A-Za-z0-9_]*"


def decimals_from_fmt(fmt: str) -> int:
    """Legge il numero di decimali da un formato ``.2f``; 0 se assente."""
    text = str(fmt or "")
    if text.startswith(".") and text.endswith("f"):
        try:
            return max(0, int(text[1:-1]))
        except ValueError:
            return 0
    return 0


def fmt_from_decimals(decimals: int) -> str:
    return f".{int(decimals)}f" if int(decimals) > 0 else ""


class ExpertWizard(QWizard):
    """Shell coerente per gli esperti: pulsanti, aiuto e stile."""

    def __init__(self, parent: QWidget | None = None, title: str = "Esperto") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setButtonText(QWizard.WizardButton.NextButton, "Avanti >")
        self.setButtonText(QWizard.WizardButton.BackButton, "< Indietro")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Crea")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Annulla")
        self.setButtonText(QWizard.WizardButton.HelpButton, "Aiuto")
        self.setOption(QWizard.WizardOption.HaveHelpButton, True)
        self.helpRequested.connect(self._show_help)

    def help_text(self) -> str:
        """Testo mostrato dal pulsante Aiuto; le sottoclassi lo specializzano."""
        return "Compila i passi e premi Crea per generare l'oggetto."

    def _show_help(self) -> None:
        QMessageBox.information(self, self.windowTitle(), self.help_text())

    def set_finish_text(self, text: str) -> None:
        self.setButtonText(QWizard.WizardButton.FinishButton, text)


class FieldEditor(QWidget):
    """Editor tabellare dei campi usato dagli esperti.

    Le celle hanno widget reali (combo, spin, checkbox) per evitare delegati
    diversi tra Table Expert e gli esperti successivi.
    """

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.table = QTableWidget(0, len(FIELD_HEADERS))
        self.table.setHorizontalHeaderLabels(FIELD_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_DECIMALS, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(COL_CAPTION, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_PK, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        self.add_button = icons.make_button(
            "Aggiungi campo", "nuovo", self.add_field, self, "Aggiunge una riga campo"
        )
        self.remove_button = icons.make_button(
            "Rimuovi", "elimina", self.remove_selected, self, "Rimuove il campo selezionato"
        )
        self.up_button = icons.make_button(
            "Sposta su", "su", lambda: self.move_selected(-1), self, "Sposta il campo prima"
        )
        self.down_button = icons.make_button(
            "Sposta giù", "giu", lambda: self.move_selected(1), self, "Sposta il campo dopo"
        )
        for button in (self.add_button, self.remove_button, self.up_button, self.down_button):
            bar.addWidget(button)
        bar.addStretch(1)
        hint = QLabel("I nomi usano lettere, cifre e underscore.")
        hint.setObjectName("nav_hint")
        bar.addWidget(hint)
        layout.addLayout(bar)

    # ------------------------------------------------------------------ dati
    def set_fields(self, fields: Iterable[Field]) -> None:
        self._loading = True
        try:
            self.table.setRowCount(0)
            for field in fields:
                self._append_row(field)
            if self.table.rowCount() == 0:
                self._append_row(Field(name="", type=T.TEXT, size=50))
        finally:
            self._loading = False
        self.changed.emit()

    def fields(self) -> list[Field]:
        return self._read_fields(include_empty=False)

    def _read_fields(self, include_empty: bool = False) -> list[Field]:
        result: list[Field] = []
        for row in range(self.table.rowCount()):
            name_edit = self.table.cellWidget(row, COL_NAME)
            type_combo = self.table.cellWidget(row, COL_TYPE)
            size_spin = self.table.cellWidget(row, COL_SIZE)
            decimals_spin = self.table.cellWidget(row, COL_DECIMALS)
            caption_edit = self.table.cellWidget(row, COL_CAPTION)
            pk_check = self.table.cellWidget(row, COL_PK)
            if not isinstance(name_edit, QLineEdit) or not isinstance(type_combo, QComboBox):
                continue
            name = name_edit.text().strip()
            if not name and not include_empty:
                continue
            type_name = str(type_combo.currentData() or T.TEXT)
            size = int(size_spin.value()) if isinstance(size_spin, QSpinBox) else 0
            decimals = (
                int(decimals_spin.value()) if isinstance(decimals_spin, QSpinBox) else 0
            )
            if type_name not in (T.TEXT, T.MEMO):
                size = 0
            result.append(
                Field(
                    id=new_id(),
                    name=name,
                    type=type_name,
                    size=size,
                    caption=(
                        caption_edit.text().strip()
                        if isinstance(caption_edit, QLineEdit)
                        else ""
                    ),
                    fmt=fmt_from_decimals(decimals),
                    pk=bool(pk_check.isChecked()) if isinstance(pk_check, QCheckBox) else False,
                )
            )
        return result

    # ------------------------------------------------------------------ righe
    def _append_row(self, field: Field) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_edit = QLineEdit(field.name)
        name_edit.setValidator(QRegularExpressionValidator(QRegularExpression(IDENT_PATTERN)))
        name_edit.setPlaceholderText("nome_campo")
        name_edit.textChanged.connect(self._on_changed)
        self.table.setCellWidget(row, COL_NAME, name_edit)

        type_combo = QComboBox()
        for type_name in T.ALL_TYPES:
            type_combo.addItem(T.label(type_name), type_name)
        position = type_combo.findData(field.type)
        type_combo.setCurrentIndex(max(0, position))
        type_combo.currentIndexChanged.connect(self._on_changed)
        type_combo.currentIndexChanged.connect(
            lambda _index, combo=type_combo, r=row: self._sync_row_controls(r, combo)
        )
        self.table.setCellWidget(row, COL_TYPE, type_combo)

        size_spin = QSpinBox()
        size_spin.setRange(0, 10000)
        size_spin.setValue(max(0, int(field.size)))
        size_spin.valueChanged.connect(self._on_changed)
        self.table.setCellWidget(row, COL_SIZE, size_spin)

        decimals_spin = QSpinBox()
        decimals_spin.setRange(0, 9)
        decimals_spin.setValue(decimals_from_fmt(field.fmt))
        decimals_spin.valueChanged.connect(self._on_changed)
        self.table.setCellWidget(row, COL_DECIMALS, decimals_spin)

        caption_edit = QLineEdit(field.caption)
        caption_edit.setPlaceholderText("Etichetta mostrata")
        caption_edit.textChanged.connect(self._on_changed)
        self.table.setCellWidget(row, COL_CAPTION, caption_edit)

        pk_check = QCheckBox()
        pk_check.setChecked(bool(field.pk))
        pk_check.stateChanged.connect(self._on_changed)
        self.table.setCellWidget(row, COL_PK, pk_check)

        self._sync_row_controls(row, type_combo)

    def _sync_row_controls(self, row: int, combo: QComboBox) -> None:
        type_name = str(combo.currentData() or T.TEXT)
        size_spin = self.table.cellWidget(row, COL_SIZE)
        decimals_spin = self.table.cellWidget(row, COL_DECIMALS)
        if isinstance(size_spin, QSpinBox):
            size_spin.setEnabled(type_name in (T.TEXT, T.MEMO))
        if isinstance(decimals_spin, QSpinBox):
            decimals_spin.setEnabled(type_name in (T.DECIMAL,))

    def _on_changed(self, *_args) -> None:
        if not self._loading:
            self.changed.emit()

    def add_field(self) -> None:
        self._append_row(Field(name="", type=T.TEXT, size=50))
        self.table.setCurrentCell(self.table.rowCount() - 1, COL_NAME)
        self.changed.emit()

    def remove_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        self.table.removeRow(row)
        if self.table.rowCount() == 0:
            self._append_row(Field(name="", type=T.TEXT, size=50))
        self.changed.emit()

    def move_selected(self, delta: int) -> None:
        row = self.table.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= self.table.rowCount():
            return
        fields = self._read_fields(include_empty=True)
        if row >= len(fields) or target >= len(fields):
            return
        fields[row], fields[target] = fields[target], fields[row]
        self.set_fields(fields)
        self.table.setCurrentCell(target, COL_NAME)

    def selected_name(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        edit = self.table.cellWidget(row, COL_NAME)
        return edit.text().strip() if isinstance(edit, QLineEdit) else ""


__all__ = [
    "ExpertWizard",
    "FieldEditor",
    "decimals_from_fmt",
    "fmt_from_decimals",
]
