"""Modello logico del progetto: tabelle, campi, indici, relazioni (B1).

Gli artefatti sono serializzati in JSON e versionabili; il DB fisico viene
generato da `ddl.py`. Ogni campo porta un `id` stabile per riconoscere i
rinomina durante le migrazioni.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable

from . import types as T

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RESERVED_NAMES = {"_id", "rowid", "oid", "sqlite_master"}
ON_DELETE_ACTIONS = ("NO ACTION", "CASCADE", "SET NULL", "RESTRICT")


class MetadataError(ValueError):
    """Metadati non validi (nome, tipo, indice o relazione incoerente)."""


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9_]+", "_", str(text).strip().lower()).strip("_")
    return slug or "oggetto"


def check_identifier(name: str, what: str = "nome") -> None:
    if not name or not isinstance(name, str):
        raise MetadataError(f"{what.capitalize()} mancante")
    if not IDENT_RE.match(name):
        raise MetadataError(
            f"{what.capitalize()} non valido: {name!r} (lettere, cifre e underscore, non iniziare con cifra)"
        )
    if name.lower() in RESERVED_NAMES:
        raise MetadataError(f"{what.capitalize()} riservato: {name}")


@dataclass
class Field:
    name: str
    type: str = T.TEXT
    size: int = 0
    required: bool = False
    default: str = ""
    caption: str = ""
    fmt: str = ""
    pk: bool = False
    lookup: str = ""
    rule: str = ""
    id: str = dc_field(default_factory=new_id)

    def validate(self) -> None:
        check_identifier(self.name, "nome campo")
        if self.type not in T.ALL_TYPES:
            raise MetadataError(f"Tipo sconosciuto per il campo {self.name}: {self.type}")
        if self.size < 0:
            raise MetadataError(f"Dimensione negativa per il campo {self.name}")
        if self.lookup:
            if "." not in self.lookup:
                raise MetadataError(
                    f"Lookup del campo {self.name} non valido: usa 'tabella.campo'"
                )

    def display_name(self) -> str:
        return self.caption or self.name.replace("_", " ").capitalize()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "size": self.size,
            "required": self.required,
            "default": self.default,
            "caption": self.caption,
            "fmt": self.fmt,
            "pk": self.pk,
            "lookup": self.lookup,
            "rule": self.rule,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Field":
        return cls(
            name=str(data.get("name", "")),
            type=str(data.get("type", T.TEXT)),
            size=int(data.get("size", 0) or 0),
            required=bool(data.get("required", False)),
            default=str(data.get("default", "")),
            caption=str(data.get("caption", "")),
            fmt=str(data.get("fmt", "")),
            pk=bool(data.get("pk", False)),
            lookup=str(data.get("lookup", "")),
            rule=str(data.get("rule", "")),
            id=str(data.get("id") or new_id()),
        )


@dataclass
class Index:
    fields: list[str] = dc_field(default_factory=list)
    unique: bool = False
    name: str = ""

    def resolved_name(self, table_name: str) -> str:
        if self.name:
            return self.name
        return "idx_" + slugify(table_name) + "_" + "_".join(slugify(f) for f in self.fields)

    def validate(self, table: "Table") -> None:
        if not self.fields:
            raise MetadataError("Un indice deve avere almeno un campo")
        for name in self.fields:
            if table.field(name) is None:
                raise MetadataError(f"Indice su campo inesistente: {name}")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "fields": list(self.fields), "unique": self.unique}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Index":
        return cls(
            fields=[str(f) for f in data.get("fields", [])],
            unique=bool(data.get("unique", False)),
            name=str(data.get("name", "")),
        )


@dataclass
class ForeignKey:
    columns: list[str] = dc_field(default_factory=list)
    ref_table: str = ""
    ref_columns: list[str] = dc_field(default_factory=list)
    on_delete: str = "NO ACTION"
    name: str = ""

    def resolved_name(self, table_name: str) -> str:
        if self.name:
            return self.name
        return "fk_" + slugify(table_name) + "_" + "_".join(slugify(c) for c in self.columns)

    def validate(self, table: "Table") -> None:
        if not self.columns:
            raise MetadataError("Relazione senza colonne")
        check_identifier(self.ref_table, "tabella di riferimento")
        if not self.ref_columns:
            raise MetadataError(f"Relazione {self.ref_table}: campo di riferimento mancante")
        if len(self.columns) != len(self.ref_columns):
            raise MetadataError(f"Relazione {self.ref_table}: colonne e riferimenti non allineati")
        for name in self.columns:
            if table.field(name) is None:
                raise MetadataError(f"Relazione su campo inesistente: {name}")
        if self.on_delete.upper() not in ON_DELETE_ACTIONS:
            raise MetadataError(f"Azione ON DELETE non valida: {self.on_delete}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": list(self.columns),
            "ref_table": self.ref_table,
            "ref_columns": list(self.ref_columns),
            "on_delete": self.on_delete,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForeignKey":
        return cls(
            columns=[str(c) for c in data.get("columns", [])],
            ref_table=str(data.get("ref_table", "")),
            ref_columns=[str(c) for c in data.get("ref_columns", [])],
            on_delete=str(data.get("on_delete", "NO ACTION")),
            name=str(data.get("name", "")),
        )


@dataclass
class Table:
    name: str
    caption: str = ""
    fields: list[Field] = dc_field(default_factory=list)
    indexes: list[Index] = dc_field(default_factory=list)
    foreign_keys: list[ForeignKey] = dc_field(default_factory=list)
    id: str = dc_field(default_factory=new_id)

    # ------------------------------------------------------------------ API
    def field(self, name: str) -> Field | None:
        lowered = str(name).lower()
        for f in self.fields:
            if f.name.lower() == lowered:
                return f
        return None

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]

    def display_name(self) -> str:
        return self.caption or self.name

    def validate(self) -> None:
        check_identifier(self.name, "nome tabella")
        if not self.fields:
            raise MetadataError(f"La tabella {self.name} non ha campi")
        seen: set[str] = set()
        for f in self.fields:
            f.validate()
            if f.name.lower() in seen:
                raise MetadataError(f"Campo duplicato in {self.name}: {f.name}")
            seen.add(f.name.lower())
        index_names: set[str] = set()
        for index in self.indexes:
            index.validate(self)
            resolved = index.resolved_name(self.name)
            if resolved.lower() in index_names:
                raise MetadataError(f"Indice duplicato: {resolved}")
            index_names.add(resolved.lower())
        fk_names: set[str] = set()
        for fk in self.foreign_keys:
            fk.validate(self)
            resolved = fk.resolved_name(self.name)
            if resolved.lower() in fk_names:
                raise MetadataError(f"Relazione duplicata: {resolved}")
            fk_names.add(resolved.lower())

    def new_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for f in self.fields:
            if f.default != "":
                try:
                    record[f.name] = T.to_storage(f.default, f.type)
                except ValueError:
                    record[f.name] = T.default_value(f.type)
            else:
                record[f.name] = T.default_value(f.type)
        return record

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "caption": self.caption,
            "fields": [f.to_dict() for f in self.fields],
            "indexes": [i.to_dict() for i in self.indexes],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Table":
        return cls(
            name=str(data.get("name", "")),
            caption=str(data.get("caption", "")),
            fields=[Field.from_dict(f) for f in data.get("fields", [])],
            indexes=[Index.from_dict(i) for i in data.get("indexes", [])],
            foreign_keys=[ForeignKey.from_dict(f) for f in data.get("foreign_keys", [])],
            id=str(data.get("id") or new_id()),
        )

    def copy(self) -> "Table":
        return Table.from_dict(self.to_dict())


def validate_project_tables(tables: Iterable[Table]) -> list[str]:
    """Valida le tabelle e i riferimenti incrociati; restituisce gli errori."""
    errors: list[str] = []
    by_name: dict[str, Table] = {}
    for table in tables:
        try:
            table.validate()
        except MetadataError as exc:
            errors.append(str(exc))
        by_name[table.name.lower()] = table
    for table in tables:
        for fk in table.foreign_keys:
            target = by_name.get(fk.ref_table.lower())
            if target is None:
                errors.append(f"{table.name}: relazione verso tabella inesistente {fk.ref_table}")
                continue
            for ref in fk.ref_columns:
                if target.field(ref) is None:
                    errors.append(
                        f"{table.name}: relazione verso campo inesistente {fk.ref_table}.{ref}"
                    )
    return errors
