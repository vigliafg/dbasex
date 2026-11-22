"""Tabella incrociata (crosstab) read-only da un risultato di query (0.7 O6).

Il modulo non esegue SQL: riceve un ``QueryResult`` già calcolato e dispone i
valori su due dimensioni. Serve a leggere in modo immediato i risultati di una
query con ``GROUP BY`` senza introdurre un nuovo linguaggio o un nuovo oggetto
di progetto.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from . import types as T
from .query_engine import QueryColumn, QueryResult


class CrosstabError(ValueError):
    """Crosstab non costruibile dalla query indicata."""


def _sort_key(value: Any) -> tuple[int, Any]:
    if value is None:
        return (3, "")
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, (int, float)):
        return (0, float(value))
    if isinstance(value, (date, datetime)):
        return (1, value.isoformat())
    return (2, str(value).lower())


@dataclass
class CrosstabResult:
    """Matrice righe × colonne con totali di riga, colonna e generale."""

    row_key: str
    column_key: str
    value_key: str
    row_label: str
    column_label: str
    value_label: str
    value_type: str = T.DECIMAL
    fmt: str = ""
    row_values: list[Any] = dc_field(default_factory=list)
    column_values: list[Any] = dc_field(default_factory=list)
    cells: dict[tuple[Any, Any], float] = dc_field(default_factory=dict)
    row_totals: dict[Any, float] = dc_field(default_factory=dict)
    column_totals: dict[Any, float] = dc_field(default_factory=dict)
    grand_total: float = 0.0
    source_rows: int = 0

    def cell(self, row: Any, column: Any) -> float | None:
        return self.cells.get((row, column))

    def formatted(self, value: Any) -> str:
        if value is None:
            return ""
        return T.format_value(value, self.value_type, self.fmt)

    def headers(self) -> list[str]:
        return [f"{self.row_label} \\ {self.column_label}"] + [
            self._label(value) for value in self.column_values
        ] + ["Totale"]

    def _label(self, value: Any) -> str:
        if value is None:
            return "(vuoto)"
        if isinstance(value, bool):
            return "Sì" if value else "No"
        if isinstance(value, (date, datetime)):
            return T.format_value(value, T.DATE)
        return str(value)

    def rows(self) -> list[list[str]]:
        """Righe già formattate per griglia o CSV: intestazione inclusa."""
        result = [self.headers()]
        for row in self.row_values:
            current = [self._label(row)]
            for column in self.column_values:
                current.append(self.formatted(self.cell(row, column)))
            current.append(self.formatted(self.row_totals.get(row, 0.0)))
            result.append(current)
        total_row = ["Totale"]
        total_row.extend(
            self.formatted(self.column_totals.get(column, 0.0))
            for column in self.column_values
        )
        total_row.append(self.formatted(self.grand_total))
        result.append(total_row)
        return result

    def to_csv(self, path: str | Path) -> Path:
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix(".csv")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerows(self.rows())
        except OSError as exc:
            raise CrosstabError(f"Export CSV non riuscito: {exc}") from exc
        return target


def _column(result: QueryResult, key: str, role: str) -> QueryColumn:
    for column in result.columns:
        if column.key == key:
            return column
    raise CrosstabError(f"Colonna {role} inesistente: {key}")


def numeric_columns(result: QueryResult) -> list[QueryColumn]:
    return [
        column
        for column in result.columns
        if column.type in (T.INTEGER, T.DECIMAL) or column.key.startswith("count_")
    ]


def build_crosstab(
    result: QueryResult,
    row_key: str,
    column_key: str,
    value_key: str,
) -> CrosstabResult:
    """Dispone i valori numerici di ``result`` su righe e colonne indicate."""
    row_column = _column(result, row_key, "riga")
    column_column = _column(result, column_key, "colonna")
    value_column = _column(result, value_key, "valore")
    if value_column.type not in (T.INTEGER, T.DECIMAL):
        raise CrosstabError(
            f"La colonna valore {value_column.key} non è numerica: usa un aggregato"
        )
    row_values = sorted(
        {row.get(row_key) for row in result.rows}, key=_sort_key
    )
    column_values = sorted(
        {row.get(column_key) for row in result.rows}, key=_sort_key
    )
    cells: dict[tuple[Any, Any], float] = {}
    for row in result.rows:
        row_value = row.get(row_key)
        column_value = row.get(column_key)
        value = row.get(value_key)
        try:
            number = float(value or 0)
        except (TypeError, ValueError) as exc:
            raise CrosstabError(
                f"Valore non numerico in {value_key}: {value!r}"
            ) from exc
        cells[(row_value, column_value)] = (
            cells.get((row_value, column_value), 0.0) + number
        )
    row_totals = {
        row: sum(cells.get((row, column), 0.0) for column in column_values)
        for row in row_values
    }
    column_totals = {
        column: sum(cells.get((row, column), 0.0) for row in row_values)
        for column in column_values
    }
    return CrosstabResult(
        row_key=row_key,
        column_key=column_key,
        value_key=value_key,
        row_label=row_column.label,
        column_label=column_column.label,
        value_label=value_column.label,
        value_type=value_column.type,
        fmt=value_column.fmt,
        row_values=row_values,
        column_values=column_values,
        cells=cells,
        row_totals=row_totals,
        column_totals=column_totals,
        grand_total=sum(row_totals.values()),
        source_rows=len(result.rows),
    )


__all__ = [
    "CrosstabError",
    "CrosstabResult",
    "build_crosstab",
    "numeric_columns",
]
