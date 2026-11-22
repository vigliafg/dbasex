"""Import/export CSV per tabelle dBX (C6, 0.6)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.metadata import Table


class CsvError(RuntimeError):
    """Errore di import/export CSV."""


ENCODINGS = {
    "auto": "Rilevamento automatico",
    "utf-8-sig": "UTF-8 (con BOM)",
    "utf-8": "UTF-8",
    "latin-1": "Windows-1252 / Latin-1",
}

DELIMITERS = {
    "auto": "Rilevamento automatico",
    ";": "Punto e virgola (;)",
    ",": "Virgola (,)",
    "\t": "Tabulazione",
    "|": "Barra verticale (|)",
}


def detect_delimiter(line: str) -> str:
    """Sceglie il delimitatore più probabile dalla prima riga utile."""
    counts = {candidate: line.count(candidate) for candidate in (";", ",", "\t", "|")}
    best = max(counts, key=lambda key: counts[key])
    return best if counts[best] else ","


def decode_csv(path: str | Path, encoding: str = "auto") -> tuple[str, str]:
    """Legge il file e restituisce testo e codifica effettivamente usata."""
    target = Path(path)
    candidates = ["utf-8-sig"] if encoding in ("auto", "") else [encoding]
    if encoding in ("auto", ""):
        candidates.append("latin-1")
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return target.read_text(encoding=candidate), candidate
        except UnicodeDecodeError as exc:
            last_error = exc
        except OSError as exc:
            raise CsvError(f"Lettura CSV non riuscita: {exc}") from exc
    raise CsvError(f"Codifica non riconosciuta: {last_error}")


def read_table(
    path: str | Path,
    delimiter: str | None = None,
    encoding: str = "auto",
) -> tuple[str, str, list[list[str]]]:
    """Legge tutte le righe grezze; restituisce delimitatore, codifica e righe."""
    try:
        text, used_encoding = decode_csv(path, encoding)
    except OSError as exc:
        raise CsvError(f"Lettura CSV non riuscita: {exc}") from exc
    if not text.strip():
        raise CsvError("Il file CSV è vuoto")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    used_delimiter = detect_delimiter(first_line) if delimiter in (None, "", "auto") else delimiter
    try:
        rows = list(csv.reader(text.splitlines(), delimiter=used_delimiter))
    except csv.Error as exc:
        raise CsvError(f"CSV non valido: {exc}") from exc
    return used_delimiter, used_encoding, rows


def read_csv(
    path: str | Path,
    delimiter: str | None = None,
    encoding: str = "auto",
) -> tuple[list[str], list[list[str]]]:
    _delimiter, _encoding, rows = read_table(path, delimiter, encoding)
    if not rows:
        raise CsvError("Il file CSV è vuoto")
    return rows[0], rows[1:]


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


def _convert_cell(text: str, field, line: int, column: str) -> Any:
    if text == "":
        return None
    try:
        return T.to_storage(text, field.type)
    except ValueError as exc:
        raise CsvError(f"Riga {line}, colonna {column}: {exc}") from exc


def import_rows(
    path: str | Path,
    table: Table,
    delimiter: str | None = None,
    has_header: bool = True,
    encoding: str = "auto",
) -> list[dict[str, Any]]:
    headers, rows = read_csv(path, delimiter, encoding)
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
            if field is None:
                continue
            record[name] = _convert_cell(cell.strip(), field, len(result) + 2, headers[index])
        result.append(record)
    return result


def records_from_table(
    rows: Sequence[Sequence[str]],
    table: Table,
    mapping: Sequence[str | None],
    has_header: bool,
    first_data_line: int = 2,
) -> list[dict[str, Any]]:
    """Converte righe grezze in record secondo la mappatura colonna → campo."""
    result: list[dict[str, Any]] = []
    source = rows[1:] if has_header else rows
    for offset, raw in enumerate(source):
        if not any(str(cell).strip() for cell in raw):
            continue
        record: dict[str, Any] = {}
        for index, cell in enumerate(raw):
            if index >= len(mapping):
                break
            name = mapping[index]
            if not name:
                continue
            field = table.field(name)
            if field is None:
                continue
            record[name] = _convert_cell(
                str(cell).strip(), field, first_data_line + offset, name
            )
        result.append(record)
    return result


def _normalize(text: str) -> str:
    return "".join(char for char in str(text).lower() if char.isalnum())


def suggest_mapping(headers: Sequence[str], table: Table) -> list[str | None]:
    """Associa per nome le colonne del file ai campi della tabella."""
    by_name = {_normalize(field.name): field.name for field in table.fields}
    by_caption = {
        _normalize(field.caption): field.name for field in table.fields if field.caption
    }
    mapping: list[str | None] = []
    for header in headers:
        key = _normalize(header)
        mapping.append(by_name.get(key) or by_caption.get(key))
    return mapping
