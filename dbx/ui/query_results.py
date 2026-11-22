"""Query Results: griglia in sola lettura del risultato di una query (0.3).

La finestra esegue la query salvata, mostra le colonne con la formattazione dei
tipi dBX e consente l'export CSV. Non modifica i dati e non duplica la logica
del Query Designer: usa lo stesso ``query_engine``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import types as T
from ..core.project import Project
from ..core.query_engine import QueryError, run_query
from ..core.query_model import QuerySpec
from ..io.csv_io import CsvError, export_rows
from ..ui import icons


class QueryResultsWidget(QWidget):
    """Risultato read-only di una query, con aggiornamento ed export CSV."""

    def __init__(
        self,
        project: Project,
        query: QuerySpec | str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("query_results")
        self.project = project
        if isinstance(query, QuerySpec):
            self.spec = query
        else:
            spec = QuerySpec.from_project(project, str(query))
            if spec is None:
                raise ValueError(f"Query sconosciuta: {query}")
            self.spec = spec
        self.result = None
        self.setWindowTitle(f"Query Results — {self.spec.caption or self.spec.name}")
        self.resize(1000, 620)
        self._build_ui()
        self.refresh()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)
        self.refresh_button = icons.make_button(
            "Aggiorna", "aggiorna", self.refresh, self, "Riesegue la query"
        )
        self.export_button = icons.make_button(
            "Esporta CSV", "esporta", self.export_csv, self, "Esporta il risultato in CSV"
        )
        self.crosstab_button = icons.make_button(
            "Crosstab…", "tabella", self.open_crosstab, self,
            "Dispone il risultato in una tabella incrociata in sola lettura",
        )
        toolbar.addWidget(self.refresh_button)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.crosstab_button)
        toolbar.addStretch(1)
        self.info_label = QLabel("")
        self.info_label.setObjectName("nav_hint")
        toolbar.addWidget(self.info_label)
        layout.addLayout(toolbar)

        header = QLabel(self.spec.caption or self.spec.name)
        header.setObjectName("browse_header")
        layout.addWidget(header)

        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAccessibleName("Risultato della query, sola lettura")
        layout.addWidget(self.table, 1)

        hint = QLabel(
            "Risultato in sola lettura. Per modificare i dati apri la tabella di origine; "
            "per cambiare campi, join o filtri usa il Query Designer."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    # ------------------------------------------------------------------ dati
    def refresh(self) -> bool:
        try:
            self.result = run_query(self.project, self.spec)
        except QueryError as exc:
            self.result = None
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.info_label.setText(f"Query non valida: {exc}")
            return False
        self._fill(self.result)
        return True

    def _fill(self, result) -> None:
        headers = result.headers()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(result.rows))
        for row_index, row in enumerate(result.rows):
            for column_index, column in enumerate(result.columns):
                value = row.get(column.key)
                text = T.format_value(value, column.type, column.fmt)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column.type in (T.INTEGER, T.DECIMAL):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, column_index, item)
        self.table.resizeColumnsToContents()
        self.info_label.setText(
            f"{len(result.rows)} righe · {len(result.columns)} colonne · sola lettura"
        )

    def open_crosstab(self) -> None:
        if self.result is None and not self.refresh():
            return
        assert self.result is not None
        if len(self.result.columns) < 2:
            QMessageBox.information(
                self,
                "Crosstab",
                "Servono almeno due colonne: una per le righe e una per le colonne.",
            )
            return
        from .crosstab_dialog import CrosstabDialog

        dialog = CrosstabDialog(
            self.result, self.spec.caption or self.spec.name, self
        )
        dialog.exec()

    def export_csv(self) -> Path | None:
        if self.result is None and not self.refresh():
            return None
        assert self.result is not None
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta risultato CSV", f"{self.spec.name}.csv", "CSV (*.csv)"
        )
        if not path:
            return None
        if not Path(path).suffix:
            path += ".csv"
        try:
            export_rows(
                path,
                self.result.names(),
                self.result.rows,
                table=self.result.as_table(
                    self.spec.name, self.spec.caption or self.spec.name
                ),
            )
        except CsvError as exc:
            QMessageBox.warning(self, "Export non riuscito", str(exc))
            return None
        return Path(path)

    def row_values(self, row: int) -> dict[str, Any]:
        """Valori di una riga, utili a test e integrazioni."""
        if self.result is None or not (0 <= row < len(self.result.rows)):
            return {}
        return dict(self.result.rows[row])
