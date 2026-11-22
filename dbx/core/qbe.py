"""Grammatica delle celle QBE (0.4/O4).

Il modulo è puro e indipendente dalla UI: traduce il testo scritto in una
cella della *query image* in una condizione ``QueryFilter`` e viceversa.
La sintassi è un sottoinsieme esplicito e documentato del QBE di Paradox:

- valore nudo = uguaglianza;
- ``=``, ``<>``, ``>``, ``>=``, ``<``, ``<=``;
- ``a..b`` = intervallo inclusivo per numeri e date;
- ``blank`` / ``not blank`` (anche ``vuoto`` / ``non vuoto``);
- ``*`` e ``?`` come jolly per il testo;
- ``_nome`` = example element.

Le celle non valide sollevano :class:`QbeError`; la UI le evidenzia e non le
applica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import types as T
from .query_model import type_family

EXAMPLE_RE = re.compile(r"^_[A-Za-z_][A-Za-z0-9_]*$")
_WILDCARD_RE = re.compile(r"[*?]")
_COMPARISONS = (
    ("<=", "le"),
    (">=", "ge"),
    ("<>", "ne"),
    ("!=", "ne"),
    ("=", "eq"),
    (">", "gt"),
    ("<", "lt"),
)
_BLANK = ("blank", "vuoto", "null")
_NOT_BLANK = ("not blank", "non vuoto", "not null")
_RANGE_TYPES = ("number", "date")


class QbeError(ValueError):
    """Testo di cella QBE non interpretabile o non adatto al tipo del campo."""


@dataclass(frozen=True)
class QbeCell:
    """Condizione estratta da una cella QBE."""

    op: str
    value: str = ""
    value2: str = ""


def is_example_element(text: str) -> bool:
    return bool(EXAMPLE_RE.match(str(text or "").strip()))


def example_name(text: str) -> str:
    raw = str(text or "").strip()
    return raw[1:] if is_example_element(raw) else ""


def _has_wildcard(value: str) -> bool:
    return bool(_WILDCARD_RE.search(value))


def _check_range(value: str, value2: str, type_name: str) -> None:
    if not value or not value2:
        raise QbeError("intervallo incompleto: usa a..b")
    if type_family(type_name) not in _RANGE_TYPES:
        raise QbeError("l'intervallo a..b è ammesso solo per numeri e date")
    try:
        T.to_storage(value, type_name)
        T.to_storage(value2, type_name)
    except (TypeError, ValueError) as exc:
        raise QbeError(str(exc)) from exc


def parse_cell(text: str, type_name: str = T.TEXT) -> QbeCell | None:
    """Interpreta una cella QBE. Restituisce ``None`` se la cella è vuota."""
    raw = str(text or "").strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in _BLANK:
        return QbeCell("null")
    if lowered in _NOT_BLANK:
        return QbeCell("notnull")
    if is_example_element(raw):
        raise QbeError("un example element non è una condizione")

    for prefix, op in _COMPARISONS:
        if not raw.startswith(prefix):
            continue
        value = raw[len(prefix):].strip()
        if not value:
            raise QbeError(f"valore mancante dopo {prefix}")
        if ".." in value:
            if op != "eq":
                raise QbeError("usa a..b senza operatore di confronto")
            left, right = value.split("..", 1)
            left, right = left.strip(), right.strip()
            _check_range(left, right, type_name)
            return QbeCell("between", left, right)
        if op == "eq" and _has_wildcard(value):
            if type_family(type_name) != "text":
                raise QbeError("i jolly * e ? sono ammessi solo per il testo")
            return QbeCell("like", value)
        return QbeCell(op, value)

    if ".." in raw:
        left, right = raw.split("..", 1)
        left, right = left.strip(), right.strip()
        _check_range(left, right, type_name)
        return QbeCell("between", left, right)

    if _has_wildcard(raw):
        if type_family(type_name) != "text":
            raise QbeError("i jolly * e ? sono ammessi solo per il testo")
        return QbeCell("like", raw)

    return QbeCell("eq", raw)


def format_cell(cell: QbeCell | None) -> str:
    """Testo reversibile per una cella QBE."""
    if cell is None:
        return ""
    op = cell.op
    if op == "null":
        return "blank"
    if op == "notnull":
        return "not blank"
    if op == "between":
        return f"{cell.value}..{cell.value2}"
    if op == "eq":
        return cell.value
    if op == "like":
        return cell.value
    prefixes = {"ne": "<>", "gt": ">", "ge": ">=", "lt": "<", "le": "<="}
    return f"{prefixes.get(op, '')}{cell.value}"


__all__ = [
    "QbeCell",
    "QbeError",
    "EXAMPLE_RE",
    "example_name",
    "format_cell",
    "is_example_element",
    "parse_cell",
]
