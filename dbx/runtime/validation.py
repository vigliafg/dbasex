"""Validazione strutturata dei record: issue, report ed errori (piano validazione).

Il modulo è indipendente dalla UI e dal database: contiene solo i tipi condivisi
tra `Rowset`, griglia, form, import e script. Le funzioni di risoluzione delle
scelte e del dominio numerico vivono qui perché sono regole del dato, non
dell'editor.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any


class RowsetError(RuntimeError):
    """Errore di lettura/scrittura o di validazione."""


@dataclass(frozen=True)
class ValidationIssue:
    """Singolo problema di validazione, collegato a un campo."""

    field: str
    message: str
    code: str  # type | required | choice | choice_source | choice_other
    #           | domain | rule | unique | record
    severity: str = "error"  # "error" | "warning"

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def text(self) -> str:
        return self.message


class ValidationError(RowsetError):
    """Errore di validazione con l'elenco strutturato delle issue."""

    def __init__(self, issues: list[ValidationIssue] | ValidationIssue) -> None:
        if isinstance(issues, ValidationIssue):
            issues = [issues]
        self.issues = list(issues)
        super().__init__("\n".join(issue.text() for issue in self.issues))


@dataclass
class ValidationReport:
    """Esito di una validazione: valori pronti, errori e avvisi."""

    values: dict[str, Any] = dc_field(default_factory=dict)
    issues: list[ValidationIssue] = dc_field(default_factory=list)

    def add(
        self,
        field: str,
        message: str,
        code: str,
        severity: str = "error",
    ) -> ValidationIssue:
        issue = ValidationIssue(field=field, message=message, code=code, severity=severity)
        self.issues.append(issue)
        return issue

    def extend(self, issues: list[ValidationIssue]) -> None:
        self.issues.extend(issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.is_error]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if not issue.is_error]

    @property
    def ok(self) -> bool:
        return not self.errors

    def messages(self, severity: str = "") -> list[str]:
        return [
            issue.text()
            for issue in self.issues
            if not severity or issue.severity == severity
        ]

    def raise_if_errors(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


# --------------------------------------------------------------- Scelta (choice)
@dataclass(frozen=True)
class ChoiceOption:
    """Voce di un campo Scelta: valore memorizzato ed etichetta mostrata."""

    value: str
    label: str


class ChoiceSourceError(ValueError):
    """Sorgente della Scelta mancante o non leggibile."""


MAX_CHOICE_VALUES = 1000
_CHOICE_CACHE: dict[tuple[Any, ...], tuple[int, list[ChoiceOption]]] = {}
_CHOICE_VERSION: dict[str, int] = {}


def touch_choices(table_name: str = "") -> None:
    """Invalida la cache delle Scelte dopo una scrittura sulla tabella."""
    if table_name:
        key = table_name.lower()
        _CHOICE_VERSION[key] = _CHOICE_VERSION.get(key, 0) + 1
    else:
        _CHOICE_CACHE.clear()


def _static_options(field) -> list[ChoiceOption]:
    result: list[ChoiceOption] = []
    seen: set[str] = set()
    for item in getattr(field, "choices", []) or []:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", ""))
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(ChoiceOption(value=value, label=str(item.get("label") or value)))
    return result


def _dynamic_options(field, db) -> list[ChoiceOption]:
    if db is None:
        raise ChoiceSourceError(
            f"La sorgente della Scelta {field.name} non è disponibile"
        )
    table = str(getattr(field, "choice_table", "") or "")
    value_column = str(getattr(field, "choice_value", "") or "")
    if not table or not value_column:
        raise ChoiceSourceError(
            f"La sorgente della Scelta {field.name} è incompleta"
        )
    label_column = str(getattr(field, "choice_label", "") or "") or value_column
    quote = lambda name: '"' + str(name).replace('"', '""') + '"'
    sql = (
        f"SELECT {quote(value_column)} AS value, {quote(label_column)} AS label "
        f"FROM {quote(table)} ORDER BY {quote(label_column)} LIMIT {MAX_CHOICE_VALUES + 1}"
    )
    try:
        rows = db.query(sql)
    except Exception as exc:
        raise ChoiceSourceError(
            f"Sorgente della Scelta {field.name} non leggibile: {exc}"
        ) from exc
    if len(rows) > MAX_CHOICE_VALUES:
        raise ChoiceSourceError(
            f"La lista supera {MAX_CHOICE_VALUES} valori"
        )
    result: list[ChoiceOption] = []
    seen: set[str] = set()
    for row in rows:
        value = row["value"]
        if value is None:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        label = row["label"]
        result.append(ChoiceOption(value=text, label=str(label) if label is not None else text))
    return result


def resolve_choices(field, db=None) -> list[ChoiceOption]:
    """Risolve la lista statica e/o dinamica del campo, con cache.

    ``append`` mette gli statici in testa e aggiunge i dinamici assenti;
    ``replace`` usa i dinamici e ricade sugli statici solo se vuoti.
    """
    source = str(getattr(field, "choice_source", "") or "")
    key = (
        id(db),
        str(getattr(field, "id", "") or field.name),
        source,
        str(getattr(field, "choice_table", "") or ""),
        str(getattr(field, "choice_value", "") or ""),
        str(getattr(field, "choice_label", "") or ""),
        str(getattr(field, "choice_combine", "append")),
        tuple((str(item.get("value", "")), str(item.get("label", ""))) for item in getattr(field, "choices", []) or [] if isinstance(item, dict)),
        _CHOICE_VERSION.get(str(getattr(field, "choice_table", "") or "").lower(), 0),
    )
    cached = _CHOICE_CACHE.get(key)
    if cached is not None:
        return list(cached[1])
    static = _static_options(field)
    dynamic: list[ChoiceOption] = []
    if source == "table":
        dynamic = _dynamic_options(field, db)
    combine = str(getattr(field, "choice_combine", "append") or "append")
    if source != "table" or combine == "append":
        result = list(static)
        seen = {option.value for option in static}
        for option in dynamic:
            if option.value not in seen:
                result.append(option)
                seen.add(option.value)
    else:
        result = list(dynamic) if dynamic else list(static)
    _CHOICE_CACHE[key] = (0, result)
    return list(result)


def match_choice(field, value: str, options: list[ChoiceOption]) -> ChoiceOption | None:
    """Trova la voce corrispondente, esatta o case-insensitive secondo il campo."""
    if getattr(field, "choice_case_sensitive", True):
        for option in options:
            if option.value == value:
                return option
        return None
    folded = value.casefold()
    for option in options:
        if option.value.casefold() == folded:
            return option
    return None


__all__ = [
    "RowsetError",
    "ValidationIssue",
    "ValidationError",
    "ValidationReport",
    "ChoiceOption",
    "ChoiceSourceError",
    "MAX_CHOICE_VALUES",
    "resolve_choices",
    "match_choice",
    "touch_choices",
]
