"""Cursore read-only su un ``QueryResult``.

Il runtime dei form e le anteprime usano la stessa interfaccia minima del
``Rowset``; questo adapter evita di duplicare la navigazione e rende esplicito
che una sorgente query non è modificabile.
"""

from __future__ import annotations

from typing import Any

from ..core.query_engine import QueryResult
from .rowset import RowsetError


def _sort_value(value: Any) -> tuple[int, Any]:
    if value is None or value == "":
        return (3, "")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (0, float(value))
    return (1, str(value).casefold())


def sort_rows(rows: list[dict[str, Any]], order: str) -> list[dict[str, Any]]:
    """Applica un ordine in stile SQL ``campo [ASC|DESC], ...`` alle righe."""
    result = list(rows)
    terms = [term.strip() for term in str(order or "").split(",") if term.strip()]
    for term in reversed(terms):
        parts = term.split()
        field = parts[0]
        reverse = len(parts) > 1 and parts[1].lower().startswith("desc")
        missing = [
            row for row in result if row.get(field) is None or row.get(field) == ""
        ]
        present = [
            row for row in result if row.get(field) is not None and row.get(field) != ""
        ]
        present.sort(key=lambda row, f=field: _sort_value(row.get(f)), reverse=reverse)
        result = present + missing
    return result


class QueryRowset:
    """Vista sequenziale in sola lettura sulle righe di una query."""

    def __init__(self, result: QueryResult, order: str = "") -> None:
        self.result = result
        self.table_name = result.as_table().name
        self._rows = sort_rows(result.rows, order)
        self._position = 0 if self._rows else -1

    def __len__(self) -> int:
        return len(self._rows)

    @property
    def columns(self) -> list[str]:
        return self.result.names()

    def rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def count(self) -> int:
        return len(self._rows)

    @property
    def index(self) -> int:
        return self._position

    @property
    def current(self) -> dict[str, Any] | None:
        if 0 <= self._position < len(self._rows):
            return self._rows[self._position]
        return None

    @property
    def is_first(self) -> bool:
        return self._position <= 0

    @property
    def is_last(self) -> bool:
        return self._position >= len(self._rows) - 1

    def goto(self, index: int) -> dict[str, Any] | None:
        if self._rows:
            self._position = max(0, min(len(self._rows) - 1, int(index)))
        else:
            self._position = -1
        return self.current

    def first(self) -> dict[str, Any] | None:
        self._position = 0 if self._rows else -1
        return self.current

    def last(self) -> dict[str, Any] | None:
        self._position = len(self._rows) - 1
        return self.current

    def next(self) -> dict[str, Any] | None:
        if self._position + 1 < len(self._rows):
            self._position += 1
        return self.current

    def previous(self) -> dict[str, Any] | None:
        if self._position > 0:
            self._position -= 1
        return self.current

    def new_record(self) -> dict[str, Any]:
        return {name: None for name in self.result.names()}

    def save(self, _values: dict[str, Any] | None = None) -> int:
        raise RowsetError("La query è in sola lettura: apri la tabella per modificare i dati")

    def delete(self) -> None:
        raise RowsetError("La query è in sola lettura: apri la tabella per eliminare i record")
