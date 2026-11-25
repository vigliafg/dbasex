"""Ricerca guidata in stile Find mode (0.6).

Il modulo è volutamente puro: produce frammenti SQL parametrizzati per il
``Rowset`` e non tocca la UI. Una richiesta è un elenco di criteri combinati in
AND oppure OR; ogni criterio può essere marcato ``omit`` per escludere le righe
che lo soddisfano, come il comando “Ometti” di FileMaker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any

from . import types as T
from .ddl import INTERNAL_ID
from .metadata import Table


class SearchError(ValueError):
    """Ricerca non valida o non eseguibile."""


# Operatore -> etichetta italiana mostrata nel dialogo.
SEARCH_OPERATORS: dict[str, str] = {
    "contains": "contiene",
    "eq": "uguale a",
    "ne": "diverso da",
    "starts": "inizia con",
    "ends": "finisce con",
    "gt": "maggiore di",
    "ge": "maggiore o uguale a",
    "lt": "minore di",
    "le": "minore o uguale a",
    "blank": "è vuoto",
    "notblank": "non è vuoto",
}

TEXT_OPERATORS = ("contains", "starts", "ends")
COMPARISON_OPERATORS = ("eq", "ne", "gt", "ge", "lt", "le")
NULL_OPERATORS = ("blank", "notblank")
MATCH_MODES = {"all": "Tutti i criteri (AND)", "any": "Almeno un criterio (OR)"}


@dataclass
class SearchCriterion:
    """Un confronto su un campo della tabella."""

    field: str = ""
    op: str = "contains"
    value: str = ""
    omit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "op": self.op,
            "value": self.value,
            "omit": bool(self.omit),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchCriterion":
        op = str(data.get("op", "contains")).lower()
        return cls(
            field=str(data.get("field", "")),
            op=op if op in SEARCH_OPERATORS else "contains",
            value=str(data.get("value", "")),
            omit=bool(data.get("omit", False)),
        )


@dataclass
class SearchRequest:
    """Criteri combinati in AND (``all``) oppure OR (``any``)."""

    criteria: list[SearchCriterion] = dc_field(default_factory=list)
    match: str = "all"

    # ------------------------------------------------------------------ stato
    def is_empty(self) -> bool:
        return not any(self._active(criterion) for criterion in self.criteria)

    @staticmethod
    def _active(criterion: SearchCriterion) -> bool:
        if not criterion.field:
            return False
        if criterion.op in NULL_OPERATORS:
            return True
        return bool(str(criterion.value).strip())

    def __bool__(self) -> bool:
        return not self.is_empty()

    # ------------------------------------------------------------ serializzazione
    def to_dict(self) -> dict[str, Any]:
        return {
            "match": self.match if self.match in MATCH_MODES else "all",
            "criteria": [criterion.to_dict() for criterion in self.criteria],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchRequest":
        match = str(data.get("match", "all")).lower()
        criteria = [
            SearchCriterion.from_dict(item)
            for item in data.get("criteria", [])
            if isinstance(item, dict)
        ]
        return cls(criteria=criteria, match=match if match in MATCH_MODES else "all")


def _quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _escape_like(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _condition(table: Table, criterion: SearchCriterion) -> tuple[str, tuple[Any, ...]] | None:
    field = table.field(criterion.field)
    if field is None:
        raise SearchError(f"Campo inesistente: {criterion.field or '(nessuno)'}")
    if not field.stored:
        raise SearchError(
            f"Il campo calcolato {field.display_name()} non è ricercabile"
        )
    op = criterion.op if criterion.op in SEARCH_OPERATORS else "contains"
    column = _quote(field.name)
    if op in NULL_OPERATORS:
        sql = f"({column} IS NULL OR CAST({column} AS TEXT) = '')"
        return (f"NOT {sql}" if op == "notblank" else sql), ()
    value = str(criterion.value)
    if value.strip() == "":
        return None
    if op in TEXT_OPERATORS:
        pattern = {
            "contains": f"%{_escape_like(value)}%",
            "starts": f"{_escape_like(value)}%",
            "ends": f"%{_escape_like(value)}",
        }[op]
        return f"CAST({column} AS TEXT) LIKE ? ESCAPE '\\'", (pattern,)
    try:
        stored = T.to_storage(value, field.type)
    except ValueError as exc:
        raise SearchError(f"{field.display_name()}: {exc}") from exc
    operator = {
        "eq": "=",
        "ne": "<>",
        "gt": ">",
        "ge": ">=",
        "lt": "<",
        "le": "<=",
    }[op]
    return f"{column} {operator} ?", (stored,)


def validate_request(table: Table, request: SearchRequest) -> list[str]:
    """Errori bloccanti della richiesta, senza eseguire SQL."""
    errors: list[str] = []
    if request.match not in MATCH_MODES:
        errors.append(f"Combinazione non valida: {request.match}")
    for index, criterion in enumerate(request.criteria, start=1):
        if not criterion.field and criterion.op not in NULL_OPERATORS:
            continue
        if table.field(criterion.field) is None:
            errors.append(f"Criterio {index}: campo inesistente {criterion.field!r}")
            continue
        if criterion.op not in SEARCH_OPERATORS:
            errors.append(f"Criterio {index}: operatore non valido {criterion.op!r}")
            continue
        if criterion.op in NULL_OPERATORS:
            continue
        if str(criterion.value).strip() == "":
            continue
        try:
            _condition(table, criterion)
        except SearchError as exc:
            errors.append(f"Criterio {index}: {exc}")
    return errors


def build_where(table: Table, request: SearchRequest) -> tuple[str, tuple[Any, ...]]:
    """Traduce la richiesta in ``WHERE`` parametrizzato; vuoto se inattiva."""
    errors = validate_request(table, request)
    if errors:
        raise SearchError("\n".join(errors))
    clauses: list[str] = []
    params: list[Any] = []
    for criterion in request.criteria:
        if not SearchRequest._active(criterion):
            continue
        built = _condition(table, criterion)
        if built is None:
            continue
        sql, values = built
        if criterion.omit:
            sql = f"NOT ({sql})"
        clauses.append(f"({sql})")
        params.extend(values)
    if not clauses:
        return "", ()
    joiner = " OR " if request.match == "any" else " AND "
    return joiner.join(clauses), tuple(params)


def count_matches(db, table: Table, request: SearchRequest) -> int:
    where, params = build_where(table, request)
    sql = f"SELECT COUNT(*) FROM {_quote(table.name)}"
    if where:
        sql += f" WHERE {where}"
    return int(db.scalar(sql, params) or 0)


# ---------------------------------------------------------------- sostituzione
def replace_text(
    value: Any,
    find: str,
    replace: str,
    match_case: bool = False,
    whole_word: bool = False,
) -> str:
    """Sostituisce ``find`` in un valore testuale, senza regex fornite dall'utente."""
    text = "" if value is None else str(value)
    if not find:
        return text
    flags = 0 if match_case else re.IGNORECASE
    pattern = re.escape(find)
    if whole_word:
        pattern = rf"\b{pattern}\b"
    return re.sub(pattern, lambda _match: replace, text, flags=flags)


def replaceable_fields(table: Table, field: str = "") -> list:
    if field:
        candidate = table.field(field)
        if candidate is None:
            raise SearchError(f"Campo inesistente: {field}")
        if not candidate.stored:
            raise SearchError(f"Il campo {candidate.display_name()} è calcolato e non modificabile")
        if not T.is_text_like(candidate.type):
            raise SearchError(f"Il campo {candidate.display_name()} non è testuale")
        return [candidate]
    return [
        item
        for item in table.fields
        if item.stored and T.is_text_like(item.type)
    ]


def replace_in_rowset(
    rowset,
    find: str,
    replace: str,
    field: str = "",
    match_case: bool = False,
    whole_word: bool = False,
    limit: int | None = None,
) -> int:
    """Sostituisce nei record correnti del rowset e restituisce il numero di celle."""
    if not find:
        return 0
    fields = replaceable_fields(rowset.table, field)
    changed = 0
    for record in list(rowset.rows()):
        values = dict(record)
        touched = False
        for item in fields:
            before = values.get(item.name)
            after = replace_text(before, find, replace, match_case, whole_word)
            if after != ("" if before is None else str(before)):
                values[item.name] = after
                touched = True
                changed += 1
        if touched:
            rowset.update(int(record[INTERNAL_ID]), values)
            if limit is not None and changed >= limit:
                break
    return changed


# --------------------------------------------------------------- ricerche salvate
def saved_finds(project, table_name: str) -> dict[str, dict[str, Any]]:
    stored = project.settings.get("saved_finds")
    if not isinstance(stored, dict):
        return {}
    table_map = stored.get(table_name)
    if not isinstance(table_map, dict):
        return {}
    return {
        str(name): dict(value)
        for name, value in table_map.items()
        if isinstance(value, dict)
    }


def save_find(project, table_name: str, name: str, request: SearchRequest) -> None:
    name = str(name).strip()
    if not name:
        raise SearchError("La ricerca salvata deve avere un nome")
    stored = project.settings.setdefault("saved_finds", {})
    if not isinstance(stored, dict):
        stored = {}
        project.settings["saved_finds"] = stored
    table_map = stored.setdefault(table_name, {})
    if not isinstance(table_map, dict):
        table_map = {}
        stored[table_name] = table_map
    table_map[name] = request.to_dict()
    project.save()


def delete_find(project, table_name: str, name: str) -> bool:
    stored = project.settings.get("saved_finds")
    if not isinstance(stored, dict):
        return False
    table_map = stored.get(table_name)
    if not isinstance(table_map, dict) or name not in table_map:
        return False
    del table_map[name]
    project.save()
    return True
