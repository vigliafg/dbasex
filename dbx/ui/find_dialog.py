"""Dialoghi di ricerca guidata, sostituzione e ricerche salvate (0.6)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.metadata import Table
from ..core.search import (
    MATCH_MODES,
    SEARCH_OPERATORS,
    SearchCriterion,
    SearchError,
    SearchRequest,
    delete_find,
    replaceable_fields,
    save_find,
    saved_finds,
    validate_request,
)
from . import icons

VALUE_HINT = {
    "blank": "nessun valore",
    "notblank": "nessun valore",
}


class FindDialog(QDialog):
    """Find mode: più criteri in AND/OR, con “Ometti” e ricerche salvate."""

    def __init__(
        self,
        project,
        table: Table,
        request: SearchRequest | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.table = table
        self._cleared = False
        self.setWindowTitle(f"Trova — {table.display_name()}")
        self.setMinimumSize(720, 420)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Combina i criteri come in Find mode: AND cerca record che soddisfano tutti i "
            "criteri, OR almeno uno. “Ometti” esclude i record che corrispondono."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        options = QHBoxLayout()
        options.addWidget(QLabel("Combinazione:"))
        self.match_combo = QComboBox()
        for key, label in MATCH_MODES.items():
            self.match_combo.addItem(label, key)
        options.addWidget(self.match_combo)
        options.addStretch(1)
        self.add_button = icons.make_button(
            "Aggiungi criterio", "nuovo", self.add_criterion, self, "Aggiungi una riga di ricerca"
        )
        self.remove_button = icons.make_button(
            "Rimuovi", "elimina", self.remove_criterion, self, "Rimuovi il criterio selezionato"
        )
        options.addWidget(self.add_button)
        options.addWidget(self.remove_button)
        layout.addLayout(options)

        self.grid = QTableWidget(0, 4)
        self.grid.setHorizontalHeaderLabels(["Campo", "Operatore", "Valore", "Ometti"])
        self.grid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.grid.verticalHeader().setVisible(False)
        self.grid.horizontalHeader().setStretchLastSection(False)
        self.grid.setColumnWidth(0, 180)
        self.grid.setColumnWidth(1, 170)
        self.grid.setColumnWidth(2, 260)
        self.grid.setColumnWidth(3, 70)
        layout.addWidget(self.grid, 1)

        saved_row = QHBoxLayout()
        saved_row.addWidget(QLabel("Ricerche salvate:"))
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(200)
        saved_row.addWidget(self.saved_combo, 1)
        self.load_button = icons.make_button(
            "Carica", "apri", self.load_saved, self, "Applica la ricerca salvata"
        )
        self.save_button = icons.make_button(
            "Salva…", "salva", self.save_current, self, "Salva i criteri correnti con un nome"
        )
        self.delete_button = icons.make_button(
            "Elimina", "elimina", self.delete_saved, self, "Elimina la ricerca salvata"
        )
        for button in (self.load_button, self.save_button, self.delete_button):
            saved_row.addWidget(button)
        layout.addLayout(saved_row)

        buttons = QDialogButtonBox()
        self.find_button = buttons.addButton("Trova", QDialogButtonBox.ButtonRole.AcceptRole)
        self.clear_button = buttons.addButton(
            "Trova tutto", QDialogButtonBox.ButtonRole.ResetRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.find_button.setDefault(True)
        buttons.accepted.connect(self._accept_find)
        buttons.rejected.connect(self.reject)
        self.clear_button.clicked.connect(self._clear_all)
        layout.addWidget(buttons)

        self.set_request(request or SearchRequest())
        self._reload_saved()

    # ---------------------------------------------------------------- criteri
    def _field_combo(self, selected: str = "") -> QComboBox:
        combo = QComboBox()
        for field in self.table.fields:
            combo.addItem(field.display_name(), field.name)
        position = combo.findData(selected)
        combo.setCurrentIndex(max(0, position))
        return combo

    def _op_combo(self, selected: str = "contains") -> QComboBox:
        combo = QComboBox()
        for key, label in SEARCH_OPERATORS.items():
            combo.addItem(label, key)
        position = combo.findData(selected)
        combo.setCurrentIndex(max(0, position))
        return combo

    def add_criterion(self, criterion: SearchCriterion | None = None) -> None:
        criterion = criterion or SearchCriterion(
            field=self.table.fields[0].name if self.table.fields else "",
            op="contains",
            value="",
        )
        row = self.grid.rowCount()
        self.grid.insertRow(row)
        field_combo = self._field_combo(criterion.field)
        op_combo = self._op_combo(criterion.op)
        value_edit = QLineEdit(criterion.value)
        value_edit.setPlaceholderText("valore da cercare")
        omit = QCheckBox()
        omit.setChecked(bool(criterion.omit))
        omit.setToolTip("Ometti i record che corrispondono a questo criterio")
        omit.setAccessibleName("Ometti criterio")
        self.grid.setCellWidget(row, 0, field_combo)
        self.grid.setCellWidget(row, 1, op_combo)
        self.grid.setCellWidget(row, 2, value_edit)
        omit_wrap = QWidget()
        omit_layout = QHBoxLayout(omit_wrap)
        omit_layout.setContentsMargins(0, 0, 0, 0)
        omit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        omit_layout.addWidget(omit)
        self.grid.setCellWidget(row, 3, omit_wrap)
        op_combo.currentIndexChanged.connect(
            lambda _index, edit=value_edit, op=op_combo: self._sync_value_hint(edit, op)
        )
        self._sync_value_hint(value_edit, op_combo)

    @staticmethod
    def _sync_value_hint(edit: QLineEdit, op_combo: QComboBox) -> None:
        op = str(op_combo.currentData() or "")
        hint = VALUE_HINT.get(op, "valore da cercare")
        edit.setPlaceholderText(hint)
        edit.setEnabled(op not in VALUE_HINT)

    def remove_criterion(self) -> None:
        row = self.grid.currentRow()
        if row < 0 and self.grid.rowCount():
            row = self.grid.rowCount() - 1
        if row >= 0:
            self.grid.removeRow(row)

    def set_request(self, request: SearchRequest) -> None:
        self.grid.setRowCount(0)
        position = self.match_combo.findData(request.match)
        self.match_combo.setCurrentIndex(max(0, position))
        for criterion in request.criteria:
            self.add_criterion(criterion)
        if not request.criteria:
            self.add_criterion()

    def request(self) -> SearchRequest:
        criteria: list[SearchCriterion] = []
        for row in range(self.grid.rowCount()):
            field_combo = self.grid.cellWidget(row, 0)
            op_combo = self.grid.cellWidget(row, 1)
            value_edit = self.grid.cellWidget(row, 2)
            omit_wrap = self.grid.cellWidget(row, 3)
            if not isinstance(field_combo, QComboBox) or not isinstance(op_combo, QComboBox):
                continue
            value = value_edit.text() if isinstance(value_edit, QLineEdit) else ""
            omit = False
            if omit_wrap is not None:
                box = omit_wrap.findChild(QCheckBox)
                omit = bool(box and box.isChecked())
            criteria.append(
                SearchCriterion(
                    field=str(field_combo.currentData() or ""),
                    op=str(op_combo.currentData() or "contains"),
                    value=value,
                    omit=omit,
                )
            )
        return SearchRequest(
            criteria=criteria,
            match=str(self.match_combo.currentData() or "all"),
        )

    def _accept_find(self) -> None:
        errors = validate_request(self.table, self.request())
        if errors:
            QMessageBox.warning(self, "Ricerca non valida", "\n".join(errors))
            return
        self.accept()

    def _clear_all(self) -> None:
        self._cleared = True
        self.set_request(SearchRequest())
        self.accept()

    def was_cleared(self) -> bool:
        return self._cleared

    # --------------------------------------------------------- ricerche salvate
    def _reload_saved(self) -> None:
        current = self.saved_combo.currentText()
        self.saved_combo.clear()
        for name in sorted(saved_finds(self.project, self.table.name)):
            self.saved_combo.addItem(name)
        position = self.saved_combo.findText(current)
        if position >= 0:
            self.saved_combo.setCurrentIndex(position)
        enabled = self.saved_combo.count() > 0
        self.load_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def load_saved(self) -> None:
        name = self.saved_combo.currentText()
        if not name:
            return
        stored = saved_finds(self.project, self.table.name).get(name)
        if stored is None:
            return
        self.set_request(SearchRequest.from_dict(stored))

    def save_current(self) -> None:
        name, ok = QInputDialog.getText(self, "Salva ricerca", "Nome della ricerca:")
        if not ok or not name.strip():
            return
        try:
            save_find(self.project, self.table.name, name.strip(), self.request())
        except SearchError as exc:
            QMessageBox.warning(self, "Salva ricerca", str(exc))
            return
        self._reload_saved()
        position = self.saved_combo.findText(name.strip())
        if position >= 0:
            self.saved_combo.setCurrentIndex(position)

    def delete_saved(self) -> None:
        name = self.saved_combo.currentText()
        if not name:
            return
        answer = QMessageBox.question(
            self, "Elimina ricerca", f"Eliminare la ricerca salvata «{name}»?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        delete_find(self.project, self.table.name, name)
        self._reload_saved()


class ReplaceDialog(QDialog):
    """Sostituzione testuale sui record correnti, con ambito e opzioni."""

    def __init__(self, table: Table, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = table
        self.setWindowTitle(f"Sostituisci — {table.display_name()}")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("testo da cercare")
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText("nuovo testo")
        self.field_combo = QComboBox()
        self.field_combo.addItem("Tutti i campi testuali", "")
        for field in replaceable_fields(table):
            self.field_combo.addItem(field.display_name(), field.name)
        self.case_box = QCheckBox("Distingui maiuscole e minuscole")
        self.word_box = QCheckBox("Solo parole intere")
        form.addRow("Cerca:", self.find_edit)
        form.addRow("Sostituisci con:", self.replace_edit)
        form.addRow("Ambito:", self.field_combo)
        form.addRow("", self.case_box)
        form.addRow("", self.word_box)
        layout.addLayout(form)
        hint = QLabel("La sostituzione agisce sui record attualmente visibili nella Browse.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(480, 260)

    def _accept(self) -> None:
        if not self.find_edit.text():
            QMessageBox.warning(self, "Sostituisci", "Indica il testo da cercare.")
            return
        self.accept()

    def values(self) -> dict[str, Any]:
        return {
            "find": self.find_edit.text(),
            "replace": self.replace_edit.text(),
            "field": str(self.field_combo.currentData() or ""),
            "match_case": self.case_box.isChecked(),
            "whole_word": self.word_box.isChecked(),
        }


__all__ = ["FindDialog", "ReplaceDialog"]
