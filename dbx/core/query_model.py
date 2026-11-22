"""Modello delle query statiche del progetto (0.3).

Una query è una vista in sola lettura: ``SELECT`` su una tabella base, con
eventuali ``INNER``/``LEFT JOIN``, filtri a valore letterale e ordinamento.
Non contiene parametri interattivi e non modifica il database; il motore la
traduce in SQL con parametri ``?`` per non concatenare mai i valori.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable

from . import types as T
from .metadata import Table, slugify

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

JOIN_KINDS = ("inner", "left")
JOIN_LABELS = {"inner": "INNER JOIN", "left": "LEFT JOIN"}
SORT_DIRECTIONS = ("asc", "desc")

# Operatore logico -> frammento SQL. Gli operatori "like" usano un pattern.
OPERATORS = {
    "eq": "=",
    "ne": "<>",
    "gt": ">",
    "ge": ">=",
    "lt": "<",
    "le": "<=",
}
LIKE_OPERATORS = ("contains", "starts", "ends")
QBE_LIKE_OPERATORS = ("like",)
REF_OPERATORS = ("ref",)
NULL_OPERATORS = ("null", "notnull")
OPERATOR_LABELS = {
    "eq": "uguale a",
    "ne": "diverso da",
    "gt": "maggiore di",
    "ge": "maggiore o uguale a",
    "lt": "minore di",
    "le": "minore o uguale a",
    "contains": "contiene",
    "starts": "inizia con",
    "ends": "finisce con",
    "like": "simile a (* e ?)",
    "between": "compreso tra",
    "ref": "uguale al campo",
    "null": "è vuoto",
    "notnull": "non è vuoto",
}
ALL_OPERATORS = tuple(OPERATOR_LABELS)


def type_family(type_name: str) -> str:
    """Famiglia usata per verificare la compatibilità degli example elements."""
    if type_name in (T.INTEGER, T.DECIMAL, T.BOOLEAN):
        return "number"
    if type_name in (T.DATE, T.DATETIME):
        return "date"
    if type_name in (T.TEXT, T.MEMO):
        return "text"
    return type_name



class QueryError(ValueError):
    """Query non valida o non eseguibile."""


def parse_ref(ref: str) -> tuple[str, str]:
    """Divide ``tabella.campo`` in due nomi; solleva ``QueryError`` se invalido."""
    raw = str(ref or "").strip()
    if raw.count(".") != 1:
        raise QueryError(f"Riferimento non valido: {ref!r} (usa tabella.campo)")
    table, field = (part.strip() for part in raw.split(".", 1))
    if not table or not field:
        raise QueryError(f"Riferimento non valido: {ref!r} (usa tabella.campo)")
    return table, field


def _index_tables(tables: dict[str, Table] | Iterable[Table]) -> dict[str, Table]:
    if isinstance(tables, dict):
        values = tables.values()
    else:
        values = tables
    return {table.name.lower(): table for table in values}


def _field_of(table: Table | None, name: str):
    return table.field(name) if table is not None else None


@dataclass
class QueryField:
    """Campo selezionato dalla query, con eventuale alias di output."""

    table: str
    field: str
    alias: str = ""

    @property
    def ref(self) -> str:
        return f"{self.table}.{self.field}"

    def to_dict(self) -> dict[str, Any]:
        return {"table": self.table, "field": self.field, "alias": self.alias}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryField":
        return cls(
            table=str(data.get("table", "")),
            field=str(data.get("field", "")),
            alias=str(data.get("alias", "")),
        )


@dataclass
class QueryJoin:
    """Join verso una tabella aggiuntiva, con condizione ``left = right``."""

    kind: str = "inner"
    table: str = ""
    left: str = ""
    right: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "table": self.table,
            "left": self.left,
            "right": self.right,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryJoin":
        kind = str(data.get("kind", "inner")).lower()
        return cls(
            kind=kind if kind in JOIN_KINDS else "inner",
            table=str(data.get("table", "")),
            left=str(data.get("left", "")),
            right=str(data.get("right", "")),
        )


@dataclass
class QueryFilter:
    """Condizione ``campo operatore valore``.

    ``group`` distingue le righe QBE: lo stesso gruppo è combinato in AND,
    gruppi diversi in OR. ``value2`` è il secondo estremo di ``between``.
    """

    field: str = ""
    op: str = "eq"
    value: str = ""
    value2: str = ""
    group: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "op": self.op,
            "value": self.value,
            "value2": self.value2,
            "group": int(self.group),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryFilter":
        op = str(data.get("op", "eq")).lower()
        try:
            group = int(data.get("group", 0) or 0)
        except (TypeError, ValueError):
            group = 0
        return cls(
            field=str(data.get("field", "")),
            op=op if op in ALL_OPERATORS else "eq",
            value=str(data.get("value", "")),
            value2=str(data.get("value2", "")),
            group=max(0, group),
        )


@dataclass
class QuerySort:
    """Voce di ordinamento, applicata nell'ordine dell'elenco."""

    field: str = ""
    direction: str = "asc"

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "direction": self.direction}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuerySort":
        direction = str(data.get("direction", "asc")).lower()
        return cls(
            field=str(data.get("field", "")),
            direction=direction if direction in SORT_DIRECTIONS else "asc",
        )


@dataclass
class QuerySpec:
    """Definizione serializzabile di una query statica."""

    name: str
    caption: str = ""
    base: str = ""
    distinct: bool = False
    fields: list[QueryField] = dc_field(default_factory=list)
    joins: list[QueryJoin] = dc_field(default_factory=list)
    filters: list[QueryFilter] = dc_field(default_factory=list)
    sorts: list[QuerySort] = dc_field(default_factory=list)

    # ------------------------------------------------------------------ crea
    @classmethod
    def create(cls, table: Table, name: str | None = None, caption: str = "") -> "QuerySpec":
        return cls(
            name=name or f"query_{slugify(table.name)}",
            caption=caption or f"Query {table.display_name()}",
            base=table.name,
            fields=[QueryField(table.name, field.name) for field in table.stored_fields],
        )

    @classmethod
    def from_project(cls, project, name: str) -> "QuerySpec | None":
        artifact = project.artifact("queries", name)
        return cls.from_dict(artifact) if artifact else None

    # --------------------------------------------------------------- nomi output
    def output_names(self) -> list[str]:
        """Nomi di colonna stabili e unici, rispettando gli alias."""
        counts: dict[str, int] = {}
        for item in self.fields:
            key = item.field.lower()
            counts[key] = counts.get(key, 0) + 1
        used: set[str] = set()
        names: list[str] = []
        for item in self.fields:
            if item.alias:
                base = item.alias
            elif counts.get(item.field.lower(), 0) > 1:
                base = f"{item.table}_{item.field}"
            else:
                base = item.field
            candidate = base
            index = 2
            while candidate.lower() in used:
                candidate = f"{base}_{index}"
                index += 1
            used.add(candidate.lower())
            names.append(candidate)
        return names

    def refs(self) -> list[str]:
        return [item.ref for item in self.fields]

    # -------------------------------------------------------------- validazione
    def validate(self, tables: dict[str, Table] | Iterable[Table]) -> list[str]:
        by_name = _index_tables(tables)
        errors: list[str] = []
        if not str(self.name).strip():
            errors.append("La query non ha un nome")
        base = by_name.get(str(self.base).lower())
        if base is None:
            errors.append(f"Tabella base inesistente: {self.base or '(nessuna)'}")
            return errors
        available = {base.name.lower()}
        if not self.fields:
            errors.append("La query non seleziona alcun campo")
        if self.distinct is not True and self.distinct is not False:
            errors.append("Il flag DISTINCT deve essere vero o falso")

        for join in self.joins:
            if join.kind not in JOIN_KINDS:
                errors.append(f"Tipo di join non valido: {join.kind}")
            join_table = by_name.get(join.table.lower())
            if join_table is None:
                errors.append(f"Join verso tabella inesistente: {join.table or '(nessuna)'}")
                continue
            if join.table.lower() in available:
                errors.append(f"Tabella già presente nella query: {join.table}")
            try:
                left_table, left_field = parse_ref(join.left)
                right_table, right_field = parse_ref(join.right)
            except QueryError as exc:
                errors.append(str(exc))
                continue
            if left_table.lower() not in available or by_name.get(left_table.lower()) is None:
                errors.append(f"Join {join.table}: tabella sinistra non disponibile: {left_table}")
            elif by_name[left_table.lower()].field(left_field) is None:
                errors.append(f"Join {join.table}: campo sinistro inesistente: {join.left}")
            elif not by_name[left_table.lower()].field(left_field).stored:
                errors.append(f"Join {join.table}: campo calcolato non disponibile: {join.left}")
            if right_table.lower() != join.table.lower():
                errors.append(
                    f"Join {join.table}: la condizione destra deve appartenere a {join.table}"
                )
            elif join_table.field(right_field) is None:
                errors.append(f"Join {join.table}: campo destro inesistente: {join.right}")
            elif not join_table.field(right_field).stored:
                errors.append(f"Join {join.table}: campo calcolato non disponibile: {join.right}")
            available.add(join.table.lower())

        for item in self.fields:
            table = by_name.get(item.table.lower())
            if table is None:
                errors.append(f"Campo {item.ref}: tabella inesistente {item.table}")
                continue
            if item.table.lower() not in available:
                errors.append(f"Campo {item.ref}: la tabella non è nella query")
            if table.field(item.field) is None:
                errors.append(f"Campo inesistente: {item.ref}")
            elif not table.field(item.field).stored:
                errors.append(f"Campo calcolato non disponibile nelle query: {item.ref}")
            if item.alias and not IDENT_RE.match(item.alias):
                errors.append(f"Alias non valido: {item.alias}")

        for item in self.filters:
            try:
                table_name, field_name = parse_ref(item.field)
            except QueryError as exc:
                errors.append(str(exc))
                continue
            table = by_name.get(table_name.lower())
            source_field = None
            if table is None:
                errors.append(f"Filtro su tabella inesistente: {table_name}")
            elif table_name.lower() not in available:
                errors.append(f"Filtro su tabella non presente nella query: {table_name}")
            elif table.field(field_name) is None:
                errors.append(f"Filtro su campo inesistente: {item.field}")
            else:
                source_field = table.field(field_name)
                if not source_field.stored:
                    errors.append(
                        f"Filtro su campo calcolato non disponibile: {item.field}"
                    )
            if item.op not in ALL_OPERATORS:
                errors.append(f"Operatore di filtro non valido: {item.op}")
                continue
            if not isinstance(item.group, int) or item.group < 0:
                errors.append(f"Gruppo di filtro non valido: {item.group!r}")
            if item.op == "between":
                if not str(item.value).strip() or not str(item.value2).strip():
                    errors.append(f"Filtro {item.field}: intervallo incompleto")
            elif item.op == "like":
                if not str(item.value).strip():
                    errors.append(f"Filtro {item.field}: valore mancante")
            elif item.op == "ref":
                try:
                    target_table_name, target_field_name = parse_ref(item.value)
                except QueryError as exc:
                    errors.append(f"Filtro {item.field}: {exc}")
                    continue
                target_table = by_name.get(target_table_name.lower())
                if target_table is None or target_table_name.lower() not in available:
                    errors.append(
                        f"Filtro {item.field}: tabella di riferimento non presente: {target_table_name}"
                    )
                    continue
                target_field = target_table.field(target_field_name)
                if target_field is None:
                    errors.append(
                        f"Filtro {item.field}: campo di riferimento inesistente: {item.value}"
                    )
                    continue
                if (
                    source_field is not None
                    and type_family(source_field.type) != type_family(target_field.type)
                ):
                    errors.append(
                        f"Filtro {item.field}: tipi incompatibili con {item.value}"
                    )
            elif item.op not in NULL_OPERATORS and str(item.value).strip() == "":
                errors.append(f"Filtro {item.field or '(nessun campo)'}: valore mancante")

        for item in self.sorts:
            try:
                table_name, field_name = parse_ref(item.field)
            except QueryError as exc:
                errors.append(str(exc))
                continue
            table = by_name.get(table_name.lower())
            if table is None:
                errors.append(f"Ordinamento su tabella inesistente: {table_name}")
            elif table_name.lower() not in available:
                errors.append(f"Ordinamento su tabella non presente nella query: {table_name}")
            elif table.field(field_name) is None:
                errors.append(f"Ordinamento su campo inesistente: {item.field}")
            elif not table.field(field_name).stored:
                errors.append(f"Ordinamento su campo calcolato non disponibile: {item.field}")
            if item.direction not in SORT_DIRECTIONS:
                errors.append(f"Direzione di ordinamento non valida: {item.direction}")

        return errors

    def table_names(self) -> list[str]:
        """Tabelle coinvolte, nell'ordine base + join."""
        names = [self.base]
        names.extend(join.table for join in self.joins)
        return [name for name in names if name]

    def field_items(self) -> list[tuple[str, str, str]]:
        """Coppie ``(tabella, campo, nome output)`` per colonne e griglie."""
        return [
            (item.table, item.field, name)
            for item, name in zip(self.fields, self.output_names())
        ]

    # -------------------------------------------------------------------- JSON
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "caption": self.caption,
            "base": self.base,
            "distinct": bool(self.distinct),
            "fields": [item.to_dict() for item in self.fields],
            "joins": [item.to_dict() for item in self.joins],
            "filters": [item.to_dict() for item in self.filters],
            "sorts": [item.to_dict() for item in self.sorts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuerySpec":
        return cls(
            name=str(data.get("name", "")),
            caption=str(data.get("caption", "")),
            base=str(data.get("base", "")),
            distinct=bool(data.get("distinct", False)),
            fields=[QueryField.from_dict(item) for item in data.get("fields", []) if isinstance(item, dict)],
            joins=[QueryJoin.from_dict(item) for item in data.get("joins", []) if isinstance(item, dict)],
            filters=[QueryFilter.from_dict(item) for item in data.get("filters", []) if isinstance(item, dict)],
            sorts=[QuerySort.from_dict(item) for item in data.get("sorts", []) if isinstance(item, dict)],
        )
