"""Tipi logici dBX: mapping verso SQLite, conversione e formattazione valori.

I tipi logici sono quelli di un personal database in stile dBASE (Character,
Numeric, Date, Logical, Memo) ma mappati sulle affinity SQLite.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

TEXT = "text"
INTEGER = "integer"
DECIMAL = "decimal"
DATE = "date"
DATETIME = "datetime"
BOOLEAN = "boolean"
MEMO = "memo"
BLOB = "blob"

ALL_TYPES = (TEXT, INTEGER, DECIMAL, DATE, DATETIME, BOOLEAN, MEMO, BLOB)

TYPE_LABELS = {
    TEXT: "Testo",
    INTEGER: "Intero",
    DECIMAL: "Decimale",
    DATE: "Data",
    DATETIME: "Data/ora",
    BOOLEAN: "Logico (Sì/No)",
    MEMO: "Memo",
    BLOB: "Allegato",
}

TYPE_HINTS = {
    TEXT: "Fino a 254 caratteri (in SQLite nessun limite pratico)",
    INTEGER: "Numero intero con segno",
    DECIMAL: "Numero con decimali",
    DATE: "Data (AAAA-MM-GG su disco)",
    DATETIME: "Data e ora",
    BOOLEAN: "Vero/Falso memorizzato come 0/1",
    MEMO: "Testo lungo",
    BLOB: "Dati binari (immagini, allegati)",
}

_SQL_TYPES = {
    TEXT: "TEXT",
    INTEGER: "INTEGER",
    DECIMAL: "REAL",
    DATE: "TEXT",
    DATETIME: "TEXT",
    BOOLEAN: "INTEGER",
    MEMO: "TEXT",
    BLOB: "BLOB",
}

DEFAULT_FORMATS = {
    DATE: "DD/MM/YYYY",
    DATETIME: "DD/MM/YYYY HH:MM",
}

_TRUE_TOKENS = {"1", "t", "true", "y", "yes", "s", "si", "sì", "x", "v", "*"}

# Traduzione dei token di formato in stile dBASE verso strftime.
_FORMAT_TOKENS = (
    ("YYYY", "%Y"),
    ("YY", "%y"),
    ("DD", "%d"),
    ("MM", "%m"),
    ("HH", "%H"),
    ("NN", "%M"),
    ("SS", "%S"),
)


def sql_type(type_name: str) -> str:
    """Restituisce il tipo SQL SQLite per un tipo logico."""
    return _SQL_TYPES.get(type_name, "TEXT")


def affinity(type_name: str) -> str:
    """Affinity SQLite usata nelle migrazioni (CAST)."""
    sql = sql_type(type_name)
    return {"TEXT": "TEXT", "INTEGER": "INTEGER", "REAL": "REAL", "BLOB": "BLOB"}[sql]


def label(type_name: str) -> str:
    return TYPE_LABELS.get(type_name, str(type_name))


def is_numeric(type_name: str) -> bool:
    return type_name in (INTEGER, DECIMAL)


def is_date_like(type_name: str) -> bool:
    return type_name in (DATE, DATETIME)


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Data vuota")
    # Tronca l'eventuale parte oraria prima di interpretare.
    head = text.replace("T", " ").split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data non valida: {value!r}")


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).strip()
    if not text:
        raise ValueError("Data/ora vuota")
    normalized = text.replace("T", " ")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    # Fallback: solo la parte data.
    day = _parse_date(text)
    return datetime(day.year, day.month, day.day)


def to_storage(value: Any, type_name: str) -> Any:
    """Converte un valore Python/UI nella rappresentazione memorizzata su SQLite."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "" and type_name not in (TEXT, MEMO):
        return None
    if type_name == INTEGER:
        if isinstance(value, bool):
            return int(value)
        try:
            return int(float(str(value).replace(",", ".")))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valore intero non valido: {value!r}") from exc
    if type_name == DECIMAL:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valore numerico non valido: {value!r}") from exc
    if type_name == BOOLEAN:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, (int, float)):
            return 1 if value else 0
        return 1 if str(value).strip().lower() in _TRUE_TOKENS else 0
    if type_name == DATE:
        try:
            return _parse_date(value).isoformat()
        except ValueError as exc:
            raise ValueError(f"Data non valida: {value!r}") from exc
    if type_name == DATETIME:
        try:
            return _parse_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(f"Data/ora non valida: {value!r}") from exc
    if type_name == BLOB:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def from_storage(value: Any, type_name: str) -> Any:
    """Converte il valore memorizzato in un valore Python naturale per la UI."""
    if value is None:
        return None
    if type_name == INTEGER:
        return int(value)
    if type_name == DECIMAL:
        return float(value)
    if type_name == BOOLEAN:
        return bool(value)
    if type_name == DATE:
        try:
            return _parse_date(value)
        except ValueError:
            return None
    if type_name == DATETIME:
        try:
            return _parse_datetime(value)
        except ValueError:
            return None
    if type_name == BLOB:
        return bytes(value) if not isinstance(value, bytes) else value
    return str(value)


def python_format(fmt: str, type_name: str) -> str:
    """Traduce un formato dBASE (DD/MM/YYYY) in formato strftime."""
    result = fmt or DEFAULT_FORMATS.get(type_name, "")
    if not result:
        return ""
    for token, repl in _FORMAT_TOKENS:
        result = result.replace(token, repl)
    return result


def format_value(value: Any, type_name: str, fmt: str = "") -> str:
    """Formatta un valore per la visualizzazione (griglie, report, form)."""
    if value is None:
        return ""
    if type_name == BOOLEAN:
        return "Sì" if bool(value) else "No"
    if type_name == DATE:
        parsed = from_storage(value, DATE) if not isinstance(value, date) else value
        if parsed is None:
            return ""
        return parsed.strftime(python_format(fmt, DATE))
    if type_name == DATETIME:
        parsed = from_storage(value, DATETIME) if not isinstance(value, datetime) else value
        if parsed is None:
            return ""
        return parsed.strftime(python_format(fmt, DATETIME))
    if type_name == DECIMAL:
        if fmt:
            try:
                return format(float(value), fmt)
            except (ValueError, TypeError):
                pass
        number = float(value)
        return str(int(number)) if number.is_integer() else f"{number:.2f}".rstrip("0").rstrip(".")
    if type_name == INTEGER:
        return str(int(value))
    if type_name == BLOB:
        return f"<{len(value)} byte>" if isinstance(value, (bytes, bytearray)) else ""
    return str(value)


def parse_input(text: str, type_name: str) -> Any:
    """Interpreta il testo digitato dall'utente secondo il tipo logico."""
    text = "" if text is None else str(text)
    if text.strip() == "":
        return None
    if type_name == TEXT or type_name == MEMO:
        return text
    return to_storage(text, type_name)


def default_value(type_name: str) -> Any:
    if type_name in (INTEGER,):
        return 0
    if type_name == DECIMAL:
        return 0.0
    if type_name == BOOLEAN:
        return 0
    if type_name == BLOB:
        return None
    if type_name in (DATE, DATETIME):
        return None
    return ""
