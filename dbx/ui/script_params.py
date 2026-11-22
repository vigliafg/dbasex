"""Dialoghi per i parametri degli script (0.9 O10).

``ScriptParametersDialog`` modifica la dichiarazione dei parametri (nome,
etichetta, valore predefinito) salvata nell'oggetto script. ``ScriptArgumentsDialog``
chiede i valori quando lo script viene eseguito dal Navigator, dal menu o dal
Project Runner. Entrambi producono soltanto dati: l'esecuzione resta nel motore.
"""

from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..runtime.script_engine import ScriptError, script_parameters


class ScriptParametersDialog(QDialog):
    """Editor della dichiarazione dei parametri di uno script."""

    def __init__(
        self,
        parameters: Iterable[dict[str, str]] = (),
        parent: QWidget | None = None,
        name: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Parametri script — {name}" if name else "Parametri script")
        layout = QVBoxLayout(self)
        hint = QLabel(
            "I parametri diventano variabili locali dello script (:nome) e possono "
            "essere usati nelle espressioni, nei messaggi e nei filtri."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nome", "Etichetta", "Predefinito"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 190)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        buttons_row = QHBoxLayout()
        add = QPushButton("Aggiungi")
        add.clicked.connect(lambda: self.add_row())
        remove = QPushButton("Rimuovi")
        remove.clicked.connect(self.remove_row)
        buttons_row.addWidget(add)
        buttons_row.addWidget(remove)
        buttons_row.addStretch(1)
        layout.addLayout(buttons_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        for entry in parameters:
            self.add_row(
                str(entry.get("name", "")),
                str(entry.get("label", "")),
                str(entry.get("default", "")),
            )
        if self.table.rowCount() == 0:
            self.add_row()
        self.resize(560, 340)

    # ------------------------------------------------------------------ righe
    def add_row(self, name: str = "", label: str = "", default: str = "") -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate((name, label, default)):
            self.table.setItem(row, column, QTableWidgetItem(value))
        self.table.setCurrentCell(row, 0)

    def remove_row(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def parameters(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for row in range(self.table.rowCount()):
            name = self._text(row, 0)
            label = self._text(row, 1)
            default = self._text(row, 2)
            if not name and not label and not default:
                continue
            result.append(
                {"name": name or label, "label": label or name, "default": default}
            )
        return result

    def _text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    # ------------------------------------------------------------------ esito
    def accept(self) -> None:
        try:
            script_parameters({"params": self.parameters()})
        except ScriptError as exc:
            QMessageBox.warning(self, "Parametri non validi", str(exc))
            return
        super().accept()


class ScriptArgumentsDialog(QDialog):
    """Chiede i valori dei parametri prima di eseguire uno script."""

    def __init__(
        self,
        parameters: Iterable[dict[str, str]],
        parent: QWidget | None = None,
        name: str = "",
        overrides: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Esegui script — {name}" if name else "Esegui script")
        self._entries = list(parameters)
        self._edits: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        values = dict(overrides or {})
        for entry in self._entries:
            key = str(entry.get("name", ""))
            edit = QLineEdit(str(values.get(key, entry.get("default", ""))))
            edit.setPlaceholderText("valore")
            self._edits[key] = edit
            form.addRow(str(entry.get("label") or key), edit)
        layout.addLayout(form)
        hint = QLabel(
            "I valori precompilati sono i predefiniti e diventano variabili :nome "
            "per questa esecuzione."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Esegui")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(460, 220)

    def values(self) -> dict[str, str]:
        return {name: edit.text() for name, edit in self._edits.items()}


__all__ = ["ScriptArgumentsDialog", "ScriptParametersDialog"]
