"""Dati e impaginazione delle etichette (0.8 O7).

Il modulo riusa il modello di pagina dei report ma non il layout a bande: le
etichette sono disposte su una griglia regolare e ogni record produce una
etichetta. La sorgente può essere una tabella (anche con campi calcolati) o una
query già aggregata; filtro e ordinamento selezionano i record del mail merge.
"""

from __future__ import annotations

import re
from math import ceil
from typing import Any, Iterable

from ..core.expressions import Expression, ExpressionError
from ..core.label_model import LabelSpec
from ..core.query_engine import QueryError, engine_for, run_query
from ..core.query_model import QuerySpec
from .query_rowset import sort_rows
from .report_engine import Op, Page, _format_value, text_height, wrap_text
from .rowset import Rowset, RowsetError

_TOKEN = re.compile(r"\[([^\[\]]+)\]")
_EXPR_TOKEN = re.compile(r"\{\{([^{}]+)\}\}")


def label_field_choices(project, spec: LabelSpec) -> list[tuple[str, str]]:
    """Coppie ``(nome, didascalia)`` dei campi disponibili nella sorgente."""
    try:
        if spec.source_type == "query":
            query = QuerySpec.from_project(project, spec.query)
            if query is None:
                return []
            columns = engine_for(project).columns(query)
            return [(column.key, column.label) for column in columns]
        table = project.table(spec.table)
        if table is None:
            return []
        return [(field.name, field.display_name()) for field in table.fields]
    except (QueryError, ValueError):
        return []


def load_label_rows(project, spec: LabelSpec) -> list[dict[str, Any]]:
    """Record del mail merge, filtrati e ordinati come richiesto."""
    if spec.source_type == "query":
        query = QuerySpec.from_project(project, spec.query)
        if query is None:
            raise ValueError(f"Query dell'etichetta inesistente: {spec.query}")
        try:
            rows = list(run_query(project, query).rows)
        except QueryError as exc:
            raise ValueError(f"Query dell'etichetta non valida: {exc}") from exc
        if spec.filter:
            try:
                expression = Expression(spec.filter)
                rows = [
                    row
                    for row in rows
                    if expression.evaluate(row, {}, spec.query)
                ]
            except ExpressionError as exc:
                raise ValueError(f"Filtro dell'etichetta non valido: {exc}") from exc
        return sort_rows(rows, spec.order)

    table = project.table(spec.table)
    if table is None:
        raise ValueError(f"Tabella dell'etichetta inesistente: {spec.table}")
    try:
        return Rowset(project.db, table).open(
            where=spec.filter or "", order=spec.order or ""
        ).rows()
    except RowsetError as exc:
        raise ValueError(f"Filtro dell'etichetta non valido: {exc}") from exc


def _value_of(source: str, record: dict[str, Any] | None, table: str) -> Any:
    source = str(source or "").strip()
    if not source or record is None:
        return None
    if "[" not in source and "(" not in source:
        return record.get(source)
    try:
        return Expression(source).evaluate(record, table=table or None)
    except ExpressionError:
        return record.get(source)


def label_text(spec: LabelSpec, record: dict[str, Any] | None) -> str:
    """Sostituisce ``[campo]`` e ``{{espressione}}`` con i valori del record."""
    if not spec.template:
        return ""
    table = spec.table if spec.source_type == "table" else ""
    if record is None:
        # Anteprima senza dati: lascia visibili solo i testi fissi.
        return _TOKEN.sub("", _EXPR_TOKEN.sub("", spec.template))

    def replace_expr(match: re.Match[str]) -> str:
        try:
            value = Expression(match.group(1).strip()).evaluate(
                record, table=table or None
            )
        except ExpressionError:
            value = None
        return _format_value(value)

    def replace(match: re.Match[str]) -> str:
        value = _value_of(match.group(1), record, table)
        return _format_value(value)

    text = _EXPR_TOKEN.sub(replace_expr, spec.template)
    return _TOKEN.sub(replace, text)


def render_labels(
    spec: LabelSpec,
    rows: Iterable[dict[str, Any]],
) -> list[Page]:
    """Genera le pagine del foglio di etichette, una per foglio."""
    errors = spec.validate()
    if errors:
        raise ValueError("; ".join(errors))
    records: list[dict[str, Any] | None] = list(rows)
    if not records:
        records = [None]
    page_width, page_height = spec.page_dimensions()
    per_page = spec.labels_per_page
    total_slots = spec.start_offset + len(records)
    page_count = max(1, ceil(total_slots / per_page))
    pages = [
        Page(index=index, width=page_width, height=page_height)
        for index in range(page_count)
    ]
    inner_width = max(1.0, spec.label_width - 2 * spec.padding)
    for index, record in enumerate(records):
        slot = spec.start_offset + index
        page = pages[slot // per_page]
        row, column = divmod(slot % per_page, max(1, spec.columns))
        x = spec.margin("left") + column * (spec.label_width + spec.gutter_x)
        y = spec.margin("top") + row * (spec.label_height + spec.gutter_y)
        if spec.border:
            page.ops.append(
                Op(
                    kind="rect",
                    x=x,
                    y=y,
                    w=spec.label_width,
                    h=spec.label_height,
                    color=spec.color,
                )
            )
        text = label_text(spec, record)
        lines = wrap_text(text, inner_width, spec.font_size, spec.bold)
        page.ops.append(
            Op(
                kind="text",
                x=x + spec.padding,
                y=y + spec.padding,
                w=inner_width,
                h=max(0.0, min(spec.label_height - 2 * spec.padding, text_height(lines, spec.font_size))),
                text=text,
                lines=lines,
                font_size=spec.font_size,
                bold=spec.bold,
                align=spec.align,
                color=spec.color,
            )
        )
    return pages


def render_labels_for_project(project, spec: LabelSpec) -> list[Page]:
    """Scorciatoia usata da anteprima, stampa e test."""
    return render_labels(spec, load_label_rows(project, spec))


__all__ = [
    "label_field_choices",
    "label_text",
    "load_label_rows",
    "render_labels",
    "render_labels_for_project",
]
