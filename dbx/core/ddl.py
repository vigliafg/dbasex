"""Generazione DDL e migrazioni sicure per SQLite (B3, B4).

SQLite non supporta la modifica distruttiva delle colonne: quando una modifica
non è puramente additiva si ricostruisce la tabella (create + copy + rename)
dentro una transazione, con backup del file .sqlite richiesto dal chiamante.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field as dc_field

from . import types as T
from .metadata import Field, Table

INTERNAL_ID = "_id"


def quote(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (bytes, bytearray)):
        return "X'" + bytes(value).hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


def default_literal(field: Field) -> str:
    if field.default != "":
        try:
            return _sql_literal(T.to_storage(field.default, field.type))
        except ValueError:
            return "NULL"
    if field.required:
        if field.type in (T.INTEGER, T.BOOLEAN):
            return "0"
        if field.type == T.DECIMAL:
            return "0"
        if field.type in (T.DATE, T.DATETIME, T.BLOB):
            return "NULL"
        return "''"
    return "NULL"


def column_sql(field: Field) -> str:
    parts = [quote(field.name), T.sql_type(field.type)]
    if field.required:
        parts.append("NOT NULL")
    if field.pk:
        parts.append("UNIQUE")
    if field.default != "":
        parts.append("DEFAULT " + default_literal(field))
    return " ".join(parts)


def create_table_sql(table: Table, name: str | None = None) -> str:
    target = name or table.name
    lines = [f"  {quote(INTERNAL_ID)} INTEGER PRIMARY KEY AUTOINCREMENT"]
    for f in table.fields:
        lines.append("  " + column_sql(f))
    for fk in table.foreign_keys:
        cols = ", ".join(quote(c) for c in fk.columns)
        refs = ", ".join(quote(c) for c in fk.ref_columns)
        lines.append(
            f"  CONSTRAINT {quote(fk.resolved_name(table.name))} FOREIGN KEY ({cols}) "
            f"REFERENCES {quote(fk.ref_table)} ({refs}) ON DELETE {fk.on_delete.upper()}"
        )
    body = ",\n".join(lines)
    return f"CREATE TABLE {quote(target)} (\n{body}\n)"


def index_sql(table: Table, index, name: str | None = None) -> str:
    unique = "UNIQUE " if index.unique else ""
    cols = ", ".join(quote(c) for c in index.fields)
    idx_name = name or index.resolved_name(table.name)
    return f"CREATE {unique}INDEX {quote(idx_name)} ON {quote(table.name)} ({cols})"


def create_indexes_sql(table: Table) -> list[str]:
    return [index_sql(table, idx) for idx in table.indexes]


@dataclass
class MigrationPlan:
    kind: str = "none"  # none | create | alter | rebuild
    statements: list[str] = dc_field(default_factory=list)
    descriptions: list[str] = dc_field(default_factory=list)
    destructive: bool = False

    def __bool__(self) -> bool:
        return self.kind != "none"

    @property
    def sql(self) -> str:
        return ";\n".join(self.statements) + (";" if self.statements else "")


def _field_signature(field: Field) -> tuple:
    return (
        field.name.lower(),
        field.type,
        field.size,
        field.required,
        field.default,
        field.pk,
    )


def _index_signature(table: Table, index) -> tuple:
    return (
        index.resolved_name(table.name).lower(),
        tuple(c.lower() for c in index.fields),
        index.unique,
    )


def _fk_signature(table: Table, fk) -> tuple:
    return (
        fk.resolved_name(table.name).lower(),
        tuple(c.lower() for c in fk.columns),
        fk.ref_table.lower(),
        tuple(c.lower() for c in fk.ref_columns),
        fk.on_delete.upper(),
    )


def _find_source(new_field: Field, old_table: Table | None) -> str | None:
    if old_table is None:
        return None
    for f in old_table.fields:
        if f.id == new_field.id:
            return f.name
    for f in old_table.fields:
        if f.name.lower() == new_field.name.lower():
            return f.name
    return None


def _copy_expression(new_field: Field, old_table: Table | None) -> str:
    source = _find_source(new_field, old_table)
    if source is not None:
        if new_field.type in (T.TEXT, T.MEMO, T.BLOB):
            return quote(source)
        return f"CAST({quote(source)} AS {T.affinity(new_field.type)})"
    return default_literal(new_field)


def plan_migration(old: Table | None, new: Table) -> MigrationPlan:
    """Confronta due versioni di tabella e produce il piano SQL."""
    new.validate()
    if old is None:
        statements = [create_table_sql(new)] + create_indexes_sql(new)
        return MigrationPlan("create", statements, [f"Crea la tabella {new.name}"])

    old_ids = {f.id for f in old.fields}
    old_names = {f.name.lower() for f in old.fields}
    new_ids = {f.id for f in new.fields}
    new_names = {f.name.lower() for f in new.fields}

    added = [f for f in new.fields if f.id not in old_ids]
    removed = [f for f in old.fields if f.id not in new_ids]
    renamed = [
        (old_f, new_f)
        for new_f in new.fields
        for old_f in old.fields
        if new_f.id == old_f.id and new_f.name.lower() != old_f.name.lower()
    ]
    modified = [
        (old_f, new_f)
        for old_f in old.fields
        for new_f in new.fields
        if old_f.id == new_f.id and _field_signature(old_f) != _field_signature(new_f)
    ]

    old_indexes = {_index_signature(old, i) for i in old.indexes}
    new_indexes = {_index_signature(new, i) for i in new.indexes}
    old_fks = {_fk_signature(old, fk) for fk in old.foreign_keys}
    new_fks = {_fk_signature(new, fk) for fk in new.foreign_keys}

    descriptions: list[str] = []
    for f in added:
        descriptions.append(f"Aggiunge il campo {f.name}")
    for f in removed:
        descriptions.append(f"Elimina il campo {f.name}")
    for old_f, new_f in renamed:
        descriptions.append(f"Rinomina {old_f.name} in {new_f.name}")
    for old_f, new_f in modified:
        if old_f.type != new_f.type:
            descriptions.append(
                f"Cambia tipo di {new_f.name}: {T.label(old_f.type)} -> {T.label(new_f.type)}"
            )
        elif old_f.required != new_f.required:
            descriptions.append(
                f"{'Rende obbligatorio' if new_f.required else 'Rende facoltativo'} {new_f.name}"
            )
        else:
            descriptions.append(f"Modifica il campo {new_f.name}")

    additions_without_default = [f for f in added if f.required and f.default == ""]
    can_alter = (
        not removed
        and not renamed
        and not modified
        and old_fks == new_fks
        and not additions_without_default
        and old_indexes.issubset(new_indexes)
        and all("_id" not in f.name for f in added)
    )

    if not descriptions and old_fks == new_fks and old_indexes == new_indexes:
        return MigrationPlan("none", [], ["Nessuna modifica"])

    if can_alter:
        statements = [f"ALTER TABLE {quote(new.name)} ADD COLUMN {column_sql(f)}" for f in added]
        for idx in new.indexes:
            if _index_signature(new, idx) not in old_indexes:
                statements.append(index_sql(new, idx))
        if not statements:
            statements = []
        return MigrationPlan("alter", statements, descriptions)

    # Ricostruzione completa della tabella.
    temp_name = f"__dbx_new_{new.name}"
    statements = [f"DROP TABLE IF EXISTS {quote(temp_name)}", create_table_sql(new, temp_name)]
    sources = [quote(INTERNAL_ID)]
    targets = [quote(INTERNAL_ID)]
    for f in new.fields:
        targets.append(quote(f.name))
        sources.append(_copy_expression(f, old))
    statements.append(
        f"INSERT INTO {quote(temp_name)} ({', '.join(targets)}) "
        f"SELECT {', '.join(sources)} FROM {quote(old.name)}"
    )
    statements.append(f"DROP TABLE {quote(old.name)}")
    statements.append(f"ALTER TABLE {quote(temp_name)} RENAME TO {quote(new.name)}")
    statements.extend(create_indexes_sql(new))
    return MigrationPlan(
        "rebuild", statements, descriptions or ["Ricostruisce la tabella"], destructive=True
    )


def apply_migration(con: sqlite3.Connection, new: Table, old: Table | None = None) -> MigrationPlan:
    """Applica il piano in transazione, con foreign key sospese durante il rebuild."""
    plan = plan_migration(old, new)
    if not plan:
        return plan
    foreign_keys_on = False
    try:
        row = con.execute("PRAGMA foreign_keys").fetchone()
        foreign_keys_on = bool(row and row[0])
    except sqlite3.Error:  # pragma: no cover - pragma non disponibile
        foreign_keys_on = False
    if foreign_keys_on:
        con.execute("PRAGMA foreign_keys=OFF")
    try:
        con.execute("BEGIN")
        try:
            for statement in plan.statements:
                con.execute(statement)
        except Exception:
            con.execute("ROLLBACK")
            raise
        con.execute("COMMIT")
    finally:
        if foreign_keys_on:
            con.execute("PRAGMA foreign_keys=ON")
    if foreign_keys_on:
        problems = con.execute("PRAGMA foreign_key_check").fetchall()
        if problems:
            raise sqlite3.IntegrityError(f"Violazioni di integrità referenziale: {problems[:3]}")
    return plan
