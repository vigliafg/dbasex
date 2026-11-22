"""Test headless del Query Expert (0.4/O2)."""

from __future__ import annotations

import pytest
from PyQt6.QtCore import Qt

from dbx.core.query_model import QueryError
from dbx.designers.query_expert import QueryExpert, relation_candidates


def test_relation_candidates_from_foreign_key(demo_project) -> None:
    candidates = relation_candidates(demo_project, "clienti")
    assert any(item.table == "fatture" for item in candidates)
    fatture = next(item for item in candidates if item.table == "fatture")
    assert fatture.left == "clienti.codice"
    assert fatture.right == "fatture.cliente"


def test_query_expert_defaults(qapp, demo_project) -> None:
    wizard = QueryExpert(demo_project, suggested_name="clienti_query")
    try:
        assert wizard.base_table_name() == "clienti"
        spec = wizard.build_spec()
        assert spec.name == "clienti_query"
        assert spec.base == "clienti"
        assert [field.field for field in spec.fields] == [
            "codice",
            "nome",
            "citta",
            "email",
            "telefono",
            "attivo",
            "note",
        ]
        assert spec.joins == []
        assert spec.validate(demo_project.tables()) == []
    finally:
        wizard.close()


def test_query_expert_join_criteria_and_sort(qapp, demo_project) -> None:
    wizard = QueryExpert(demo_project, suggested_name="clienti_fatture")
    try:
        assert wizard.relations_table.rowCount() >= 1
        wizard.relations_table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        wizard._refresh_fields()
        wizard.add_criterion()
        value_edit = wizard.criteria_table.cellWidget(0, 2)
        value_edit.setText("Roma")
        wizard.add_sort()
        spec = wizard.build_spec()
        assert len(spec.joins) == 1
        assert spec.joins[0].table == "fatture"
        assert len(spec.filters) == 1
        assert spec.filters[0].value == "Roma"
        assert len(spec.sorts) == 1
        assert spec.validate(demo_project.tables()) == []
    finally:
        wizard.close()


def test_query_expert_rejects_empty_criterion(qapp, demo_project) -> None:
    wizard = QueryExpert(demo_project, suggested_name="vuota")
    try:
        wizard.add_criterion()
        with pytest.raises(QueryError):
            wizard.build_spec()
    finally:
        wizard.close()


def test_query_expert_summary_shows_sql(qapp, demo_project) -> None:
    wizard = QueryExpert(demo_project, suggested_name="sql")
    try:
        wizard._refresh_summary()
        text = wizard.summary_view.toPlainText()
        assert "SELECT" in text
        assert '"clienti"' in text
    finally:
        wizard.close()
