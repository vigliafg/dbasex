"""Runtime dei dati: navigazione, CRUD e validazione (B6)."""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from ..core import types as T
from ..core.db import Database
from ..core.ddl import INTERNAL_ID
from ..core.expressions import Expression, ExpressionError
from ..core.metadata import Table
from .validation import (
    ChoiceSourceError,
    RowsetError,
    ValidationError,
    ValidationIssue,
    ValidationReport,
    domain_error,
    match_choice,
    resolve_choices,
    touch_choices,
)


class Rowset:
    """Insieme di record di una tabella, con cursore in stile dBASE."""

    def __init__(self, db: Database, table: Table) -> None:
        self.db = db
        self.table = table
        self.last_warnings: list[ValidationIssue] = []
        self._rows: list[dict[str, Any]] = []
        self._position = -1
        self._where = ""
        self._params: tuple[Any, ...] = ()
        self._order = ""
        self._limit: int | None = None
        self._calculated: list[tuple[str, Expression]] = []
        for field in table.calculated_fields:
            try:
                self._calculated.append((field.name, Expression(field.calculated)))
            except ExpressionError as exc:
                raise RowsetError(
                    f"Calcolo non valido per {field.name}: {exc}"
                ) from exc

    # ------------------------------------------------------------------ query
    @property
    def columns(self) -> list[str]:
        return [INTERNAL_ID] + self.table.stored_field_names

    def _select_sql(self) -> str:
        cols = ", ".join(f'"{c}"' for c in self.columns)
        sql = f'SELECT {cols} FROM "{self.table.name}"'
        if self._where:
            sql += f" WHERE {self._where}"
        if self._order:
            sql += f" ORDER BY {self._order}"
        if self._limit:
            sql += f" LIMIT {int(self._limit)}"
        return sql

    def open(
        self,
        where: str = "",
        params: Sequence[Any] = (),
        order: str = "",
        limit: int | None = None,
    ) -> "Rowset":
        self._where = where or ""
        self._params = tuple(params or ())
        self._order = order or ""
        self._limit = limit
        try:
            rows = self.db.query(self._select_sql(), self._params)
        except Exception as exc:
            raise RowsetError(f"Lettura di {self.table.name} non riuscita: {exc}") from exc
        self._rows = [
            self._with_calculated(
                {key: T.from_storage(row[key], self._type_of(key)) for key in row.keys()}
            )
            for row in rows
        ]
        self._position = 0 if self._rows else -1
        return self

    def refresh(self) -> None:
        current_id = self.current.get(INTERNAL_ID) if self.current else None
        self.open(self._where, self._params, self._order, self._limit)
        if current_id is not None:
            for index, row in enumerate(self._rows):
                if row.get(INTERNAL_ID) == current_id:
                    self._position = index
                    break

    def _type_of(self, column: str) -> str:
        if column == INTERNAL_ID:
            return T.INTEGER
        field = self.table.field(column)
        return field.type if field else T.TEXT

    # ---------------------------------------------------------- campi calcolati
    def _with_calculated(self, record: dict[str, Any]) -> dict[str, Any]:
        """Aggiunge i valori dei campi calcolati, nell'ordine dei campi."""
        if not self._calculated:
            return record
        result = dict(record)
        for name, expression in self._calculated:
            try:
                result[name] = expression.evaluate(result, table=self.table.name)
            except ExpressionError as exc:
                raise RowsetError(f"Calcolo di {name} non riuscito: {exc}") from exc
        return result

    @staticmethod
    def _empty(value: Any) -> bool:
        return value is None or (isinstance(value, str) and value.strip() == "")

    def _next_serial(self, field) -> int:
        current = self.db.scalar(
            f'SELECT COALESCE(MAX("{field.name}"), 0) FROM "{self.table.name}"'
        )
        return int(current or 0) + 1

    def _apply_auto_enter(self, values: dict[str, Any], creating: bool) -> dict[str, Any]:
        """Risolve serie, date automatiche ed espressioni auto-enter."""
        result = dict(values)
        base = self.table.new_record()
        base.update(result)
        # Prima serie e date, così le espressioni auto-enter possono leggerle.
        for field in self.table.stored_fields:
            if field.auto_serial and creating and self._empty(result.get(field.name)):
                result[field.name] = self._next_serial(field)
                base[field.name] = result[field.name]
            if field.auto_date:
                if creating and field.auto_date == "insert":
                    result[field.name] = self._auto_date(field)
                    base[field.name] = result[field.name]
                elif not creating and field.auto_date == "update":
                    result[field.name] = self._auto_date(field)
                    base[field.name] = result[field.name]
        if creating:
            for field in self.table.stored_fields:
                if not field.auto_enter or not self._empty(result.get(field.name)):
                    continue
                try:
                    value = Expression(field.auto_enter).evaluate(
                        base, table=self.table.name
                    )
                except ExpressionError as exc:
                    raise RowsetError(
                        f"Auto-enter di {field.name} non riuscito: {exc}"
                    ) from exc
                result[field.name] = value
                base[field.name] = value
        return result

    @staticmethod
    def _auto_date(field) -> Any:
        from datetime import date, datetime

        return datetime.now() if field.type == T.DATETIME else date.today()

    # -------------------------------------------------------------- navigazione
    def __len__(self) -> int:
        return len(self._rows)

    @property
    def index(self) -> int:
        return self._position

    @property
    def current(self) -> dict[str, Any] | None:
        if 0 <= self._position < len(self._rows):
            return self._rows[self._position]
        return None

    @property
    def is_first(self) -> bool:
        return self._position <= 0

    @property
    def is_last(self) -> bool:
        return self._position >= len(self._rows) - 1

    def first(self) -> dict[str, Any] | None:
        self._position = 0 if self._rows else -1
        return self.current

    def last(self) -> dict[str, Any] | None:
        self._position = len(self._rows) - 1
        return self.current

    def next(self) -> dict[str, Any] | None:
        if self._position + 1 < len(self._rows):
            self._position += 1
        return self.current

    def previous(self) -> dict[str, Any] | None:
        if self._position > 0:
            self._position -= 1
        return self.current

    def goto(self, index: int) -> dict[str, Any] | None:
        if 0 <= index < len(self._rows):
            self._position = index
        return self.current

    def find(self, column: str, value: Any) -> dict[str, Any] | None:
        for index, row in enumerate(self._rows):
            if row.get(column) == value:
                self._position = index
                return row
        return None

    def rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def count(self) -> int:
        sql = f'SELECT COUNT(*) FROM "{self.table.name}"'
        if self._where:
            sql += f" WHERE {self._where}"
        return int(self.db.scalar(sql, self._params) or 0)

    # ------------------------------------------------------------------- CRUD
    def new_record(self) -> dict[str, Any]:
        record = self.table.new_record()
        record[INTERNAL_ID] = None
        return record

    def load(self, record_id: int) -> dict[str, Any] | None:
        columns = ", ".join(f'"{c}"' for c in self.columns)
        row = self.db.con.execute(
            f'SELECT {columns} FROM "{self.table.name}" WHERE "{INTERNAL_ID}" = ?',
            (record_id,),
        ).fetchone()
        if row is None:
            return None
        return self._with_calculated(
            {key: T.from_storage(row[key], self._type_of(key)) for key in row.keys()}
        )

    # --------------------------------------------------------------- validazione
    def _is_skipped(self, field, record: dict[str, Any]) -> bool:
        """Il campo è escluso dall'obbligatorietà (``skip_expr`` vera)."""
        source = str(getattr(field, "skip_expr", "") or "")
        if not source:
            return False
        return Expression(source).truth(record, table=self.table.name)

    def _is_required(self, field, record: dict[str, Any]) -> bool:
        """Obbligatorietà booleana o condizionale (``required_expr`` vince)."""
        source = str(getattr(field, "required_expr", "") or "")
        if not source:
            return bool(field.required)
        return Expression(source).truth(record, table=self.table.name)

    def _check_value(
        self,
        report: ValidationReport,
        field,
        stored: Any,
    ) -> Any:
        """Controlla Scelta e Dominio; restituisce il valore canonico o None."""
        if field.type == T.CHOICE:
            return self._check_choice(report, field, stored)
        if T.is_numeric(field.type):
            issue = domain_error(field, stored)
            if issue is not None:
                report.issues.append(issue)
        return None

    def _check_choice(
        self,
        report: ValidationReport,
        field,
        stored: Any,
    ) -> Any:
        empty = self._empty(stored)
        if empty:
            if not bool(getattr(field, "choice_allow_blank", True)):
                report.add(
                    field.name,
                    f"{field.display_name()}: valore vuoto non ammesso",
                    "choice",
                )
            return None
        try:
            options = resolve_choices(field, self.db)
        except ChoiceSourceError as exc:
            report.add(
                field.name,
                f"{field.display_name()}: {exc}",
                "choice_source",
            )
            return None
        option = match_choice(field, str(stored), options)
        if option is not None:
            return option.value
        if bool(getattr(field, "choice_allow_other", False)):
            report.add(
                field.name,
                f"{field.display_name()}: valore fuori elenco",
                "choice_other",
                severity="warning",
            )
            return None
        report.add(
            field.name,
            f"{field.display_name()}: valore non ammesso ({stored})",
            "choice",
        )
        return None

    def validate_report(
        self,
        values: dict[str, Any],
        *,
        only: set[str] | None = None,
    ) -> ValidationReport:
        """Converte e valida i valori, restituendo valori pronti e issue.

        ``only=None`` valida tutto il record; un insieme di nomi limita
        obbligatorietà, Scelta, Dominio e regole ai campi indicati, ma converte
        comunque tutti i campi perché le espressioni li possono leggere.
        """
        report = ValidationReport()
        prepared: dict[str, Any] = {}
        record = dict(values)
        for field in self.table.stored_fields:
            raw = values.get(field.name)
            try:
                stored = T.to_storage(raw, field.type)
            except ValueError as exc:
                report.add(field.name, f"{field.display_name()}: {exc}", "type")
                continue
            prepared[field.name] = stored
            record[field.name] = T.from_storage(stored, field.type)
        targets = (
            {field.name for field in self.table.stored_fields}
            if only is None
            else set(only)
        )
        skipped: dict[str, bool] = {}
        for field in self.table.stored_fields:
            if field.name not in prepared or field.name not in targets:
                continue
            try:
                skip = self._is_skipped(field, record)
                skipped[field.name] = skip
                if skip:
                    continue
                required = self._is_required(field, record)
            except ExpressionError as exc:
                report.add(
                    field.name,
                    f"{field.display_name()}: condizione non valida ({exc})",
                    "rule",
                )
                continue
            if required and self._empty(prepared[field.name]):
                report.add(
                    field.name,
                    f"{field.display_name()} è obbligatorio",
                    "required",
                )
        if not report.errors:
            for field in self.table.stored_fields:
                if (
                    field.name in prepared
                    and field.name in targets
                    and not skipped.get(field.name)
                ):
                    canonical = self._check_value(report, field, prepared[field.name])
                    if canonical is not None:
                        prepared[field.name] = canonical
                        record[field.name] = T.from_storage(canonical, field.type)
        if not report.errors:
            for name, expression in self._calculated:
                try:
                    record[name] = expression.evaluate(record, table=self.table.name)
                except ExpressionError as exc:
                    report.add(name, f"Calcolo di {name} non valido: {exc}", "rule")
        if not report.errors:
            for field in self.table.fields:
                if not field.rule or field.name not in targets:
                    continue
                try:
                    if not Expression(field.rule).truth(record, table=self.table.name):
                        message = str(getattr(field, "rule_message", "") or "").strip()
                        if not message:
                            message = (
                                f"{field.display_name()}: regola di validazione "
                                f"non soddisfatta ({field.rule})"
                            )
                        report.add(field.name, message, "rule")
                except ExpressionError as exc:
                    report.add(
                        field.name,
                        f"{field.display_name()}: regola non valida ({exc})",
                        "rule",
                    )
        report.values = prepared
        return report

    def validate(
        self,
        values: dict[str, Any],
        *,
        only: set[str] | None = None,
    ) -> dict[str, Any]:
        """Valida i valori e restituisce i dati pronti per lo storage."""
        report = self.validate_report(values, only=only)
        self.last_warnings = list(report.warnings)
        report.raise_if_errors()
        return report.values

    def _prepare(self, values: dict[str, Any]) -> dict[str, Any]:
        """Conversione senza controlli, per le scritture esplicitamente fidate."""
        prepared: dict[str, Any] = {}
        for field in self.table.stored_fields:
            try:
                prepared[field.name] = T.to_storage(values.get(field.name), field.type)
            except ValueError as exc:
                raise RowsetError(f"{field.display_name()}: {exc}") from exc
        return prepared

    def check_insert(self, values: dict[str, Any]) -> dict[str, Any]:
        """Simula un inserimento (auto-enter incluso) senza scrivere."""
        values = self._apply_auto_enter(values, creating=True)
        return self.validate(values)

    def validate_field(
        self,
        record_id: int,
        field_name: str,
        value: Any,
    ) -> dict[str, Any]:
        """Valida un solo campo di un record esistente, senza scrivere.

        È la primitiva della griglia: converte tutto il record ma applica
        obbligatorietà, Scelta, Dominio e regole al solo campo indicato.
        """
        if self.table.field(field_name) is None:
            raise RowsetError(f"Campo inesistente: {field_name}")
        record = self.load(record_id)
        if record is None:
            raise RowsetError(f"Record {record_id} inesistente")
        record[field_name] = value
        return self.validate(record, only={field_name})


    def _check_unique(self, prepared: dict[str, Any], record_id: int | None) -> None:
        issues: list[ValidationIssue] = []
        for index in self.table.indexes:
            if not index.unique:
                continue
            values = [prepared.get(name) for name in index.fields]
            if any(v is None for v in values):
                continue
            condition = " AND ".join(f'"{name}" = ?' for name in index.fields)
            params: list[Any] = list(values)
            if record_id is not None:
                condition += f' AND "{INTERNAL_ID}" <> ?'
                params.append(record_id)
            try:
                existing = self.db.scalar(
                    f'SELECT COUNT(*) FROM "{self.table.name}" WHERE {condition}', params
                )
            except Exception as exc:
                raise RowsetError(f"Controllo di unicità non riuscito: {exc}") from exc
            if existing:
                issues.append(
                    ValidationIssue(
                        field=index.fields[0],
                        message=(
                            "Valori duplicati per l'indice univoco %s su %s"
                            % (index.resolved_name(self.table.name), ", ".join(index.fields))
                        ),
                        code="unique",
                    )
                )
        if issues:
            raise ValidationError(issues)

    def insert(
        self,
        values: dict[str, Any],
        *,
        validate: bool = True,
    ) -> int:
        values = self._apply_auto_enter(values, creating=True)
        prepared = self.validate(values) if validate else self._prepare(values)
        self._check_unique(prepared, None)
        names = self.table.stored_field_names
        placeholders = ", ".join("?" for _ in names)
        sql = (
            f'INSERT INTO "{self.table.name}" ({", ".join(f"{chr(34)}{n}{chr(34)}" for n in names)}) '
            f"VALUES ({placeholders})"
        )
        try:
            cursor = self.db.execute(sql, [prepared[name] for name in names])
        except Exception as exc:
            raise RowsetError(f"Inserimento non riuscito: {exc}") from exc
        record_id = int(cursor.lastrowid)
        touch_choices(self.table.name)
        record = {INTERNAL_ID: record_id}
        for field in self.table.stored_fields:
            record[field.name] = T.from_storage(prepared[field.name], field.type)
        record = self._with_calculated(record)
        self._rows.append(record)
        self._position = len(self._rows) - 1
        return record_id

    def update(
        self,
        record_id: int,
        values: dict[str, Any],
        *,
        only: set[str] | None = None,
        validate: bool = True,
    ) -> int:
        # Le modifiche parziali non azzerano i campi non indicati.
        columns = ", ".join(f'"{c}"' for c in self.columns)
        existing = self.db.con.execute(
            f'SELECT {columns} FROM "{self.table.name}" WHERE "{INTERNAL_ID}" = ?',
            (record_id,),
        ).fetchone()
        if existing is not None:
            merged = {
                key: T.from_storage(existing[key], self._type_of(key))
                for key in existing.keys()
            }
            merged.update(values)
            values = merged
        values = self._apply_auto_enter(values, creating=False)
        prepared = self.validate(values, only=only) if validate else self._prepare(values)
        self._check_unique(prepared, record_id)
        names = self.table.stored_field_names
        assignments = ", ".join(f'"{name}" = ?' for name in names)
        sql = f'UPDATE "{self.table.name}" SET {assignments} WHERE "{INTERNAL_ID}" = ?'
        try:
            self.db.execute(sql, [prepared[name] for name in names] + [record_id])
        except Exception as exc:
            raise RowsetError(f"Aggiornamento non riuscito: {exc}") from exc
        touch_choices(self.table.name)
        record = {INTERNAL_ID: record_id}
        for field in self.table.stored_fields:
            record[field.name] = T.from_storage(prepared[field.name], field.type)
        record = self._with_calculated(record)
        for index, row in enumerate(self._rows):
            if row.get(INTERNAL_ID) == record_id:
                self._rows[index] = record
                self._position = index
                break
        else:
            self._rows.append(record)
            self._position = len(self._rows) - 1
        return record_id

    def save(self, values: dict[str, Any]) -> int:
        record_id = values.get(INTERNAL_ID)
        if record_id in (None, "", 0):
            return self.insert(values)
        return self.update(int(record_id), values)

    def delete(self, record_id: int | None = None) -> None:
        if record_id is None:
            current = self.current
            if current is None:
                raise RowsetError("Nessun record corrente da eliminare")
            record_id = current[INTERNAL_ID]
        try:
            self.db.execute(f'DELETE FROM "{self.table.name}" WHERE "{INTERNAL_ID}" = ?', (record_id,))
        except Exception as exc:
            raise RowsetError(f"Eliminazione non riuscita: {exc}") from exc
        touch_choices(self.table.name)
        self._rows = [row for row in self._rows if row.get(INTERNAL_ID) != record_id]
        if not self._rows:
            self._position = -1
        else:
            self._position = min(self._position, len(self._rows) - 1)

    def export_dicts(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]

    def bulk_insert(self, records: Iterable[dict[str, Any]]) -> int:
        count = 0
        for record in records:
            self.insert(record)
            count += 1
        return count
