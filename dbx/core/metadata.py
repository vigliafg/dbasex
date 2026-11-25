"""Modello logico del progetto: tabelle, campi, indici, relazioni (B1).

Gli artefatti sono serializzati in JSON e versionabili; il DB fisico viene
generato da `ddl.py`. Ogni campo porta un `id` stabile per riconoscere i
rinomina durante le migrazioni.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field as dc_field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from . import types as T
from .input_rules import CASE_MODES, MASK_CHARS

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TABLE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?: [A-Za-z0-9_]+)*$")
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


def check_table_name(name: str, what: str = "nome tabella") -> None:
    """Valida un nome di tabella: come gli identificatori, ma con spazi interni."""
    if not name or not isinstance(name, str):
        raise MetadataError(f"{what.capitalize()} mancante")
    if not TABLE_IDENT_RE.match(name):
        raise MetadataError(
            f"{what.capitalize()} non valido: {name!r} "
            "(lettere, cifre, underscore e spazi interni, non iniziare con cifra)"
        )
    if name.lower() in RESERVED_NAMES:
        raise MetadataError(f"{what.capitalize()} riservato: {name}")


def _check_expression(source: str, what: str) -> None:
    from .expressions import Expression, ExpressionError

    try:
        Expression(source)
    except ExpressionError as exc:
        raise MetadataError(f"Espressione non valida per {what}: {exc}") from exc


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
    choices: list[dict[str, Any]] = dc_field(default_factory=list)
    choice_source: str = ""
    choice_table: str = ""
    choice_value: str = ""
    choice_label: str = ""
    choice_combine: str = "append"
    choice_case_sensitive: bool = True
    choice_allow_blank: bool = True
    choice_allow_other: bool = False
    case_mode: str = ""
    mask: str = ""
    domain_min: str = ""
    domain_max: str = ""
    domain_ranges: list[list[str]] = dc_field(default_factory=list)
    domain_message: str = ""
    rule: str = ""
    rule_message: str = ""
    required_expr: str = ""
    skip_expr: str = ""
    calculated: str = ""
    auto_enter: str = ""
    increment: str = ""
    auto_date: str = ""
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
        if self.auto_date not in ("", "insert", "update"):
            raise MetadataError(
                f"Momento automatico non valido per {self.name}: {self.auto_date!r}"
            )
        if self.increment not in ("", "records", "updates"):
            raise MetadataError(
                f"Incremento non valido per {self.name}: {self.increment!r}"
            )
        for source, label in (
            (self.required_expr, "obbligatorietà condizionale"),
            (self.skip_expr, "condizione di salto"),
        ):
            if str(source).strip():
                _check_expression(str(source), f"{label} di {self.name}")
        mechanisms = [
            bool(self.calculated.strip()),
            bool(self.auto_enter.strip()),
            bool(self.increment),
            bool(self.auto_date),
        ]
        if sum(mechanisms) > 1:
            raise MetadataError(
                f"Il campo {self.name} può avere un solo meccanismo automatico "
                "(calcolato, auto-enter, incremento o data)"
            )
        if self.calculated:
            if self.pk or self.required:
                raise MetadataError(
                    f"Il campo calcolato {self.name} non può essere chiave o obbligatorio"
                )
            if self.lookup:
                raise MetadataError(f"Il campo calcolato {self.name} non può avere un lookup")
            _check_expression(self.calculated, f"calcolo di {self.name}")
        if self.auto_enter:
            _check_expression(self.auto_enter, f"auto-enter di {self.name}")
        if self.increment and self.type != T.INTEGER:
            raise MetadataError(
                f"L'incremento di {self.name} richiede il tipo Intero"
            )
        if self.auto_date and self.type not in (T.DATE, T.DATETIME):
            raise MetadataError(
                f"La data automatica di {self.name} richiede il tipo Data o Data/ora"
            )
        if self.rule and self.calculated:
            raise MetadataError(
                f"Il campo calcolato {self.name} non può avere una regola di validazione"
            )
        self._validate_choice()
        self._validate_input()
        self._validate_domain()

    def _validate_choice(self) -> None:
        configured = bool(
            self.choices
            or self.choice_source
            or self.choice_table
            or self.choice_value
            or self.choice_label
        )
        if configured and self.type != T.CHOICE:
            raise MetadataError(
                f"Il campo {self.name} ha una configurazione Scelta ma il tipo non è Scelta"
            )
        if self.type != T.CHOICE:
            return
        if self.calculated:
            raise MetadataError(f"Il campo Scelta {self.name} non può essere calcolato")
        if self.choice_source not in ("", "table"):
            raise MetadataError(
                f"Sorgente Scelta non valida per {self.name}: {self.choice_source!r}"
            )
        if self.choice_source == "table":
            if not self.choice_table or not self.choice_value:
                raise MetadataError(
                    f"La Scelta {self.name} richiede tabella e colonna del valore"
                )
            check_table_name(self.choice_table, "tabella della Scelta")
            check_identifier(self.choice_value, "colonna della Scelta")
            if self.choice_label:
                check_identifier(self.choice_label, "colonna etichetta della Scelta")
        if self.choice_combine not in ("append", "replace"):
            raise MetadataError(
                f"Combinazione Scelta non valida per {self.name}: {self.choice_combine!r}"
            )
        seen: set[str] = set()
        for item in self.choices:
            if not isinstance(item, dict):
                raise MetadataError(
                    f"Voce Scelta non valida per {self.name}: atteso un oggetto valore/etichetta"
                )
            value = str(item.get("value", ""))
            if value == "":
                raise MetadataError(f"Voce Scelta senza valore per {self.name}")
            if value in seen:
                raise MetadataError(f"Voce Scelta duplicata per {self.name}: {value}")
            seen.add(value)

    def _validate_input(self) -> None:
        if self.case_mode not in CASE_MODES:
            raise MetadataError(
                f"Modalità maiuscole non valida per {self.name}: {self.case_mode!r}"
            )
        if not self.mask:
            return
        if self.type != T.TEXT:
            raise MetadataError(
                f"La maschera di {self.name} richiede il tipo Testo"
            )
        if self.calculated:
            raise MetadataError(
                f"Il campo calcolato {self.name} non può avere una maschera"
            )
        invalid = sorted(set(self.mask) - MASK_CHARS)
        if invalid:
            raise MetadataError(
                f"Maschera non valida per {self.name}: caratteri ammessi 9, A, a e spazio "
                f"(trovati {''.join(invalid)!r})"
            )

    @staticmethod
    def _parse_domain_value(value: Any, what: str, field_name: str) -> Decimal | None:
        text = str(value if value is not None else "").strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError) as exc:
            raise MetadataError(
                f"Estremo del dominio non valido per {field_name} ({what}): {text!r}"
            ) from exc

    def _validate_domain(self) -> None:
        configured = bool(
            self.domain_min
            or self.domain_max
            or self.domain_ranges
            or self.domain_message
        )
        if not configured:
            return
        if not T.is_numeric(self.type):
            raise MetadataError(
                f"Il dominio numerico di {self.name} richiede il tipo Intero o Decimale"
            )
        if self.calculated:
            raise MetadataError(
                f"Il campo calcolato {self.name} non può avere un dominio numerico"
            )
        low = self._parse_domain_value(self.domain_min, "minimo", self.name)
        high = self._parse_domain_value(self.domain_max, "massimo", self.name)
        if low is not None and high is not None and low > high:
            raise MetadataError(
                f"Dominio non valido per {self.name}: il minimo supera il massimo"
            )
        for position, item in enumerate(self.domain_ranges, start=1):
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise MetadataError(
                    f"Intervallo {position} non valido per {self.name}: "
                    "sono richiesti minimo e massimo"
                )
            interval_low = self._parse_domain_value(
                item[0], f"intervallo {position} minimo", self.name
            )
            interval_high = self._parse_domain_value(
                item[1], f"intervallo {position} massimo", self.name
            )
            if (
                interval_low is not None
                and interval_high is not None
                and interval_low > interval_high
            ):
                raise MetadataError(
                    f"Intervallo {position} non valido per {self.name}: "
                    "il minimo supera il massimo"
                )

    @property
    def stored(self) -> bool:
        """Il campo ha una colonna fisica; i calcolati sono solo virtuali."""
        return not bool(self.calculated)

    @property
    def not_null(self) -> bool:
        """Obbligatorietà incondizionata: la colonna può essere NOT NULL."""
        return bool(self.required and not self.required_expr and not self.skip_expr)

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
            "choices": [dict(item) for item in self.choices],
            "choice_source": self.choice_source,
            "choice_table": self.choice_table,
            "choice_value": self.choice_value,
            "choice_label": self.choice_label,
            "choice_combine": self.choice_combine,
            "choice_case_sensitive": self.choice_case_sensitive,
            "choice_allow_blank": self.choice_allow_blank,
            "choice_allow_other": self.choice_allow_other,
            "case_mode": self.case_mode,
            "mask": self.mask,
            "domain_min": self.domain_min,
            "domain_max": self.domain_max,
            "domain_ranges": [list(item) for item in self.domain_ranges],
            "domain_message": self.domain_message,
            "rule": self.rule,
            "rule_message": self.rule_message,
            "required_expr": self.required_expr,
            "skip_expr": self.skip_expr,
            "calculated": self.calculated,
            "auto_enter": self.auto_enter,
            "increment": self.increment,
            "auto_date": self.auto_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Field":
        type_name = str(data.get("type", T.TEXT))
        lookup = str(data.get("lookup", ""))
        choice_source = str(data.get("choice_source", ""))
        choice_table = str(data.get("choice_table", ""))
        choice_value = str(data.get("choice_value", ""))
        choice_combine = str(data.get("choice_combine", "append"))
        choice_allow_other = bool(data.get("choice_allow_other", False))
        increment = str(data.get("increment", "") or "")
        # Migrazione trasparente del vecchio auto_serial in increment.
        if not increment and bool(data.get("auto_serial", False)):
            increment = "records"
        # Migrazione trasparente del vecchio lookup testuale in Scelta.
        if (
            type_name == T.TEXT
            and lookup
            and "." in lookup
            and not choice_source
        ):
            table_part, field_part = (part.strip() for part in lookup.split(".", 1))
            if table_part and field_part:
                type_name = T.CHOICE
                choice_source = "table"
                choice_table = table_part
                choice_value = field_part
                choice_combine = "replace"
                choice_allow_other = True
                lookup = ""
        return cls(
            name=str(data.get("name", "")),
            type=type_name,
            size=int(data.get("size", 0) or 0),
            required=bool(data.get("required", False)),
            default=str(data.get("default", "")),
            caption=str(data.get("caption", "")),
            fmt=str(data.get("fmt", "")),
            pk=bool(data.get("pk", False)),
            lookup=lookup,
            choices=[
                dict(item) for item in data.get("choices", []) if isinstance(item, dict)
            ],
            choice_source=choice_source,
            choice_table=choice_table,
            choice_value=choice_value,
            choice_label=str(data.get("choice_label", "")),
            choice_combine=choice_combine,
            choice_case_sensitive=bool(data.get("choice_case_sensitive", True)),
            choice_allow_blank=bool(data.get("choice_allow_blank", True)),
            choice_allow_other=choice_allow_other,
            case_mode=str(data.get("case_mode", "")),
            mask=str(data.get("mask", "")),
            domain_min=str(data.get("domain_min", "")),
            domain_max=str(data.get("domain_max", "")),
            domain_ranges=[
                [str(item[0]), str(item[1])]
                for item in data.get("domain_ranges", []) or []
                if isinstance(item, (list, tuple)) and len(item) == 2
            ],
            domain_message=str(data.get("domain_message", "")),
            rule=str(data.get("rule", "")),
            rule_message=str(data.get("rule_message", "")),
            required_expr=str(data.get("required_expr", "")),
            skip_expr=str(data.get("skip_expr", "")),
            calculated=str(data.get("calculated", "")),
            auto_enter=str(data.get("auto_enter", "")),
            increment=increment,
            auto_date=str(data.get("auto_date", "")),
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
        check_table_name(self.ref_table, "tabella di riferimento")
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

    @property
    def stored_fields(self) -> list[Field]:
        """Campi con una colonna fisica: esclude i calcolati."""
        return [f for f in self.fields if f.stored]

    @property
    def calculated_fields(self) -> list[Field]:
        return [f for f in self.fields if not f.stored]

    @property
    def stored_field_names(self) -> list[str]:
        return [f.name for f in self.stored_fields]

    def display_name(self) -> str:
        return self.caption or self.name

    def validate(self) -> None:
        check_table_name(self.name, "nome tabella")
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
            if any(
                (field := self.field(name)) is not None and not field.stored
                for name in index.fields
            ):
                raise MetadataError(f"Indice su campo calcolato: {index.resolved_name(self.name)}")
            resolved = index.resolved_name(self.name)
            if resolved.lower() in index_names:
                raise MetadataError(f"Indice duplicato: {resolved}")
            index_names.add(resolved.lower())
        fk_names: set[str] = set()
        for fk in self.foreign_keys:
            fk.validate(self)
            if any(
                (field := self.field(name)) is not None and not field.stored
                for name in fk.columns
            ):
                raise MetadataError(f"Relazione su campo calcolato: {fk.resolved_name(self.name)}")
            resolved = fk.resolved_name(self.name)
            if resolved.lower() in fk_names:
                raise MetadataError(f"Relazione duplicata: {resolved}")
            fk_names.add(resolved.lower())

    def new_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {}
        for f in self.fields:
            if not f.stored or f.increment or f.auto_date:
                # I calcolati e i campi automatici partono vuoti: li risolve il Rowset.
                record[f.name] = None if f.stored else T.default_value(f.type)
                continue
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
