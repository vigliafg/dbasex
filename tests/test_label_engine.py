"""Test di dati e impaginazione delle etichette (0.8 O7)."""

from __future__ import annotations

from datetime import date

import pytest

from dbx.core import types as T
from dbx.core.label_model import LabelSpec
from dbx.core.metadata import Field
from dbx.runtime.label_engine import (
    label_field_choices,
    label_text,
    load_label_rows,
    render_labels,
    render_labels_for_project,
)


def _spec(**changes) -> LabelSpec:
    spec = LabelSpec.create("et", "clienti", ["codice", "nome", "citta"])
    spec.border = True
    for key, value in changes.items():
        setattr(spec, key, value)
    return spec


def test_load_rows_from_table_with_filter_and_order(demo_project):
    spec = _spec(filter="attivo = 1", order="nome")
    rows = load_label_rows(demo_project, spec)
    assert [row["nome"] for row in rows] == ["Alfa Srl", "Beta Studio"]


def test_load_rows_from_query(demo_project):
    spec = LabelSpec.create_for_query(
        "et_query", "clienti_attivi", ["codice", "nome", "citta"]
    )
    rows = load_label_rows(demo_project, spec)
    assert [row["nome"] for row in rows] == ["Alfa Srl", "Beta Studio"]
    assert label_field_choices(demo_project, spec)[0] == ("codice", "Codice")


def test_load_rows_reports_invalid_source(demo_project):
    spec = _spec(table="inesistente")
    with pytest.raises(ValueError):
        load_label_rows(demo_project, spec)
    spec = LabelSpec.create_for_query("et", "query_inesistente", ["nome"])
    with pytest.raises(ValueError):
        load_label_rows(demo_project, spec)


def test_render_labels_grid_positions():
    spec = _spec(template="[nome]")
    pages = render_labels(spec, [{"nome": f"R{index}"} for index in range(4)])
    assert len(pages) == 1
    text_ops = [op for op in pages[0].ops if op.kind == "text"]
    assert [op.text for op in text_ops] == ["R0", "R1", "R2", "R3"]
    assert [(round(op.x, 1), round(op.y, 1)) for op in text_ops] == [
        (2.0, 2.0),
        (72.0, 2.0),
        (142.0, 2.0),
        (2.0, 39.0),
    ]
    assert len([op for op in pages[0].ops if op.kind == "rect"]) == 4


def test_render_labels_paginates_and_skips_used_labels():
    spec = _spec(template="[nome]", columns=3, rows=2)
    pages = render_labels(spec, [{"nome": f"R{index}"} for index in range(5)])
    assert len(pages) == 1
    spec.start_offset = 4
    pages = render_labels(spec, [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}])
    assert len(pages) == 2
    first = [op for op in pages[0].ops if op.kind == "text"]
    assert [(round(op.x, 1), round(op.y, 1)) for op in first] == [
        (72.0, 39.0),
        (142.0, 39.0),
    ]
    second = [op for op in pages[1].ops if op.kind == "text"]
    assert [(round(op.x, 1), round(op.y, 1)) for op in second] == [(2.0, 2.0)]


def test_label_text_formats_dates_numbers_and_expressions():
    spec = _spec(template="[data] · [importo] · {{[qta] * 2}}")
    text = label_text(
        spec,
        {"data": date(2026, 1, 15), "importo": 1200.0, "qta": 3},
    )
    assert text == "15/01/2026 · 1.200 · 6"


def test_empty_rows_render_one_blank_label_with_literals():
    spec = _spec(template="Solo testo fisso")
    pages = render_labels(spec, [])
    assert len(pages) == 1
    text = [op.text for op in pages[0].ops if op.kind == "text"]
    assert text == ["Solo testo fisso"]


def test_invalid_geometry_raises_value_error():
    spec = _spec(label_width=120)
    with pytest.raises(ValueError):
        render_labels(spec, [{"nome": "A"}])


def test_calculated_fields_are_available_in_labels(demo_project):
    table = demo_project.require_table("clienti")
    table.fields.append(
        Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])")
    )
    demo_project.apply_table(table)
    spec = _spec(template="[nome_maiuscolo]")
    rows = load_label_rows(demo_project, spec)
    pages = render_labels_for_project(demo_project, spec)
    text = " ".join(op.text for page in pages for op in page.ops)
    assert "ALFA SRL" in text
    assert rows[0]["nome_maiuscolo"] == "ALFA SRL"


def test_rename_rewrites_label_source_and_qualified_tokens(demo_project):
    from dbx.core.refactor import rename_table

    spec = _spec(
        template="[clienti.nome]",
        filter="[clienti.attivo] = 1",
    )
    demo_project.put_object("labels", spec.to_dict())
    rename_table(demo_project, "clienti", "anagrafica")
    artifact = demo_project.artifact("labels", "et")
    assert artifact is not None
    assert artifact["table"] == "anagrafica"
    assert artifact["template"] == "[anagrafica.nome]"
    assert artifact["filter"] == "[anagrafica.attivo] = 1"
