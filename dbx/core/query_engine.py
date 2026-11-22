"""Motore delle query statiche: SQL parametrizzato e risultato tipizzato.

Il motore non conosce la UI. Riceve le tabelle reali del progetto, valida la
``QuerySpec``, costruisce una ``SELECT`` con parametri ``?`` e restituisce un
``QueryResult`` con colonne tipizzate. Lo usano Query Designer (anteprima),
Query Results, form e report.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable

from . import types as T
from .metadata import Table
from .query_model import (
    LIKE_OPERATORS,
    OPERATORS,
    QueryError,
    QueryFilter,
    QuerySpec,
    parse_ref,
)


def _quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _ref_sql(table: str, field: str) -> str:
    return f"{_quote(table)}.{_quote(field)}"


def _index_tables(tables: dict[str, Table] | Iterable[Table]) -> dict[str, Table]:
    values = tables.values() if isinstance(tables, dict) else tables
    return {table.name.lower(): table for table in values}


def _pattern(value: str, op: str) -> str:
    text = str(value)
    for char in ("\\", "%", "_"):
        text = text.replace(char, "\\" + char)
    if op == "contains":
        return f"%{text}%"
    if op == "starts":
        return f"{text}%"
    return f"%{text}"


def _filter_sql(item: QueryFilter, by_name: dict[str, Table]) -> tuple[str, list[Any]]:
    table_name, field_name = parse_ref(item.field)
    column = _ref_sql(table_name, field_name)
    if item.op == "null":
        return f"{column} IS NULL", []
    if item.op == "notnull":
        return f"{column} IS NOT NULL", []
    if item.op in LIKE_OPERATORS:
        return f"{column} LIKE ? ESCAPE '\\'", [_pattern(item.value, item.op)]
    operator = OPERATORS.get(item.op)
    if operator is None:
        raise QueryError(f"Operatore di filtro non valido: {item.op}")
    table = by_name.get(table_name.lower())
    field = table.field(field_name) if table is not None else None
    if field is None:
        raise QueryError(f"Filtro su campo inesistente: {item.field}")
    try:
        value = T.to_storage(item.value, field.type)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"Filtro {item.field}: {exc}") from exc
    return f"{column} {operator} ?", [value]


@dataclass(frozen=True)
class QueryColumn:
    """Colonna del risultato, collegata al campo reale che la origina."""

    key: str
    table: str
    field: str
    caption: str = ""
    type: str = T.TEXT
    size: int = 0
    fmt: str = ""

    @property
    def label(self) -> str:
        return self.caption or self.field or self.key


@dataclass
class QueryResult:
    """Insieme di righe read-only con colonne tipizzate."""

    columns: list[QueryColumn] = dc_field(default_factory=list)
    rows: list[dict[str, Any]] = dc_field(default_factory=list)
    sql: str = ""
    params: tuple[Any, ...] = ()

    def __len__(self) -> int:
        return len(self.rows)

    def names(self) -> list[str]:
        return [column.key for column in self.columns]

    def headers(self) -> list[str]:
        return [column.label for column in self.columns]

    def column(self, key: str) -> QueryColumn | None:
        target = str(key).lower()
        for column in self.columns:
            if column.key.lower() == target:
                return column
        return None

    def first(self) -> dict[str, Any] | None:
        return self.rows[0] if self.rows else None

    def to_dicts(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.rows]


class QueryEngine:
    """Compila ed esegue query statiche sulle tabelle di un progetto."""

    def __init__(
        self,
        tables: dict[str, Table] | Iterable[Table],
        db: Any = None,
    ) -> None:
        self.tables = _index_tables(tables)
        self.db = db

    # ------------------------------------------------------------------- SQL
    def columns(self, spec: QuerySpec) -> list[QueryColumn]:
        result: list[QueryColumn] = []
        for item, name in zip(spec.fields, spec.output_names()):
            table = self.tables.get(item.table.lower())
            field = table.field(item.field) if table is not None else None
            result.append(
                QueryColumn(
                    key=name,
                    table=table.name if table is not None else item.table,
                    field=field.name if field is not None else item.field,
                    caption=(field.caption or field.name) if field is not None else item.field,
                    type=field.type if field is not None else T.TEXT,
                    size=field.size if field is not None else 0,
                    fmt=field.fmt if field is not None else "",
                )
            )
        return result

    def compile(self, spec: QuerySpec) -> tuple[str, tuple[Any, ...]]:
        """Restituisce ``(sql, params)`` senza eseguire nulla."""
        errors = spec.validate(self.tables)
        if errors:
            raise QueryError("; ".join(errors))
        names = spec.output_names()
        select = ", ".join(
            f"{_ref_sql(item.table, item.field)} AS {_quote(name)}"
            for item, name in zip(spec.fields, names)
        )
        prefix = "SELECT DISTINCT " if spec.distinct else "SELECT "
        sql = f"{prefix}{select} FROM {_quote(spec.base)}"
        for join in spec.joins:
            left_table, left_field = parse_ref(join.left)
            right_table, right_field = parse_ref(join.right)
            keyword = "INNER JOIN" if join.kind == "inner" else "LEFT JOIN"
            sql += (
                f" {keyword} {_quote(join.table)}"
                f" ON {_ref_sql(left_table, left_field)} = {_ref_sql(right_table, right_field)}"
            )
        conditions: list[str] = []
        params: list[Any] = []
        for item in spec.filters:
            condition, values = _filter_sql(item, self.tables)
            conditions.append(condition)
            params.extend(values)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        if spec.sorts:
            terms = []
            for item in spec.sorts:
                table_name, field_name = parse_ref(item.field)
                terms.append(f"{_ref_sql(table_name, field_name)} {item.direction.upper()}")
            sql += " ORDER BY " + ", ".join(terms)
        return sql, tuple(params)

    # -------------------------------------------------------------- esecuzione
    def run(self, spec: QuerySpec | dict[str, Any]) -> QueryResult:
        if not isinstance(spec, QuerySpec):
            spec = QuerySpec.from_dict(dict(spec))
        sql, params = self.compile(spec)
        if self.db is None:
            raise QueryError("Nessun database collegato al motore di query")
        try:
            raw_rows = self.db.query(sql, params)
        except Exception as exc:
            raise QueryError(f"Esecuzione della query non riuscita: {exc}") from exc
        columns = self.columns(spec)
        rows: list[dict[str, Any]] = []
        for raw in raw_rows:
            row: dict[str, Any] = {}
            for column in columns:
                try:
                    row[column.key] = T.from_storage(raw[column.key], column.type)
                except (TypeError, ValueError):
                    row[column.key] = raw[column.key]
            rows.append(row)
        return QueryResult(columns=columns, rows=rows, sql=sql, params=params)


def engine_for(project) -> QueryEngine:
    """Motore collegato alle tabelle e al database di un progetto."""
    return QueryEngine(project.tables(), project.db)


def run_query(project, spec: QuerySpec | dict[str, Any]) -> QueryResult:
    """Scorciatoia: esegue una query sul progetto dato."""
    return engine_for(project).run(spec)


def preview_sql(project, spec: QuerySpec) -> str:
    """SQL leggibile per l'anteprima del Query Designer (parametri inclusi)."""
    sql, params = engine_for(project).compile(spec)
    if not params:
        return sql
    return f"{sql}\n-- parametri: {params!r}"
