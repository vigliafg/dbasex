"""Finestra Crosstab read-only per i risultati di query (0.7 O6)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.crosstab import CrosstabError, CrosstabResult, build_crosstab
from ..core.query_engine import QueryResult
from ..core import types as T


class CrosstabDialog(QDialog):
    """Sceglie righe, colonne e valore numerico e mostra la matrice."""

    def __init__(
        self,
        result: QueryResult,
        title: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.result = result
        self.crosstab: CrosstabResult | None = None
        self.setWindowTitle(f"Crosstab — {title}" if title else "Crosstab")
        self.resize(940, 620)

        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        self.row_combo = QComboBox()
        self.column_combo = QComboBox()
        self.value_combo = QComboBox()
        for column in result.columns:
            self.row_combo.addItem(column.label, column.key)
            self.column_combo.addItem(column.label, column.key)
        numeric = [
            column
            for column in result.columns
            if column.type in (T.INTEGER, T.DECIMAL)
        ]
        for column in numeric:
            self.value_combo.addItem(column.label, column.key)
        for label, combo in (
            ("Righe:", self.row_combo),
            ("Colonne:", self.column_combo),
            ("Valore:", self.value_combo),
        ):
            form.addWidget(QLabel(label))
            form.addWidget(combo, 1)
        layout.addLayout(form)

        self.summary = QLabel("")
        self.summary.setObjectName("nav_hint")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAccessibleName("Tabella incrociata in sola lettura")
        layout.addWidget(self.table, 1)

        hint = QLabel(
            "Matrice in sola lettura: i valori sono sommati per ogni incrocio; "
            "l'ultima colonna e l'ultima riga mostrano i totali."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        self.export_button = buttons.addButton(
            "Esporta CSV…", QDialogButtonBox.ButtonRole.ActionRole
        )
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.export_button.clicked.connect(self.export_csv)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.row_combo.currentIndexChanged.connect(self.rebuild)
        self.column_combo.currentIndexChanged.connect(self.rebuild)
        self.value_combo.currentIndexChanged.connect(self.rebuild)
        self._choose_defaults()
        self.rebuild()

    def _choose_defaults(self) -> None:
        keys = [column.key for column in self.result.columns]
        if len(keys) >= 2:
            self.row_combo.setCurrentIndex(0)
            self.column_combo.setCurrentIndex(1)
        elif keys:
            self.column_combo.setCurrentIndex(0)
        if self.value_combo.count():
            self.value_combo.setCurrentIndex(self.value_combo.count() - 1)

    def rebuild(self) -> bool:
        row_key = str(self.row_combo.currentData() or "")
        column_key = str(self.column_combo.currentData() or "")
        value_key = str(self.value_combo.currentData() or "")
        try:
            self.crosstab = build_crosstab(
                self.result, row_key, column_key, value_key
            )
        except CrosstabError as exc:
            self.crosstab = None
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.summary.setText(str(exc))
            self.export_button.setEnabled(False)
            return False
        self._fill(self.crosstab)
        self.export_button.setEnabled(True)
        return True

    def _fill(self, crosstab: CrosstabResult) -> None:
        rows = crosstab.rows()
        headers = rows[0]
        body = rows[1:]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(body))
        for row_index, values in enumerate(body):
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column_index > 0:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if row_index == len(body) - 1 or column_index == len(headers) - 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(row_index, column_index, item)
        self.table.resizeColumnsToContents()
        self.summary.setText(
            f"{len(crosstab.row_values)} righe · {len(crosstab.column_values)} colonne · "
            f"{crosstab.source_rows} record di origine · sola lettura"
        )

    def export_csv(self) -> Path | None:
        if self.crosstab is None:
            return None
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta crosstab CSV", "crosstab.csv", "CSV (*.csv)"
        )
        if not path:
            return None
        try:
            target = self.crosstab.to_csv(path)
        except CrosstabError as exc:
            QMessageBox.warning(self, "Export non riuscito", str(exc))
            return None
        return target


__all__ = ["CrosstabDialog"]
