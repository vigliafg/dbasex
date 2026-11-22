"""Import/export CSV per tabelle dBX (C6)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.metadata import Table


class CsvError(RuntimeError):
    """Errore di import/export CSV."""


def export_rows(
    path: str | Path,
    fields: Sequence[str],
    rows: Iterable[dict[str, Any]],
    table: Table | None = None,
    include_id: bool = False,
    delimiter: str = ";",
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    headers = list(fields)
    if include_id:
        headers = [INTERNAL_ID] + headers
    try:
        with target.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=delimiter)
            writer.writerow(headers)
            for row in rows:
                values = []
                if include_id:
                    values.append(row.get(INTERNAL_ID, ""))
                for name in fields:
                    value = row.get(name)
                    field = table.field(name) if table else None
                    if value is None:
                        values.append("")
                    elif field is not None:
                        values.append(T.format_value(value, field.type, field.fmt))
                    else:
                        values.append(str(value))
                writer.writerow(values)
    except OSError as exc:
        raise CsvError(f"Export CSV non riuscito: {exc}") from exc
    return target


def export_rowset(rowset, path: str | Path, include_id: bool = False) -> Path:
    return export_rows(
        path,
        rowset.table.field_names,
        rowset.rows(),
        table=rowset.table,
        include_id=include_id,
    )


def read_csv(path: str | Path, delimiter: str | None = None) -> tuple[list[str], list[list[str]]]:
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise CsvError(f"Lettura CSV non riuscita: {exc}") from exc
    if delimiter is None:
        first_line = text.splitlines()[0] if text.splitlines() else ""
        delimiter = ";" if first_line.count(";") >= first_line.count(",") else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if not rows:
        raise CsvError("Il file CSV è vuoto")
    return rows[0], rows[1:]


def import_rows(
    path: str | Path,
    table: Table,
    delimiter: str | None = None,
    has_header: bool = True,
) -> list[dict[str, Any]]:
    headers, rows = read_csv(path, delimiter)
    result: list[dict[str, Any]] = []
    if has_header:
        mapping = []
        for header in headers:
            field = table.field(header.strip())
            mapping.append(field.name if field else None)
    else:
        mapping = [f.name for f in table.fields]
        rows = [headers] + rows
    for raw in rows:
        if not any(cell.strip() for cell in raw):
            continue
        record: dict[str, Any] = {}
        for index, cell in enumerate(raw):
            if index >= len(mapping):
                break
            name = mapping[index]
            if not name:
                continue
            field = table.field(name)
            text = cell.strip()
            if text == "":
                record[name] = None
                continue
            try:
                record[name] = T.to_storage(text, field.type) if field else text
            except ValueError as exc:
                raise CsvError(f"Riga {len(result) + 2}, colonna {headers[index]}: {exc}") from exc
        result.append(record)
    return result
