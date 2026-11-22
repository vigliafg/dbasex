"""Test headless del Table Expert (0.4/O1)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, MetadataError, Table
from dbx.designers.table_expert import (
    TEMPLATES,
    TableExpert,
    template_fields,
)


def test_template_fields_are_valid() -> None:
    assert TEMPLATES
    for template in TEMPLATES:
        fields = template_fields(template.key)
        if not fields:
            continue
        table = Table(name=f"t_{template.key}", fields=fields)
        table.validate()
        assert template.label
        assert template.description


def test_template_fields_get_new_ids() -> None:
    first = template_fields("contatti")
    second = template_fields("contatti")
    assert first and second
    assert [field.id for field in first] != [field.id for field in second]


def test_table_expert_contatti(qapp, demo_project) -> None:
    wizard = TableExpert(demo_project, suggested_name="rubrica")
    try:
        wizard.template_combo.setCurrentIndex(
            [template.key for template in TEMPLATES].index("contatti")
        )
        wizard.name_edit.setText("Rubrica Clienti")
        wizard.caption_edit.setText("Rubrica")
        table = wizard.build_table()
        assert table.name == "rubrica_clienti"
        assert table.caption == "Rubrica"
        assert [field.name for field in table.fields] == [
            "nome",
            "cognome",
            "email",
            "telefono",
            "note",
        ]
        assert table.field("note").type == T.MEMO
        assert {index.fields[0] for index in table.indexes} >= {"cognome", "email"}
        table.validate()
    finally:
        wizard.close()


def test_table_expert_custom_fields(qapp, demo_project) -> None:
    wizard = TableExpert(demo_project, suggested_name="custom")
    try:
        wizard.template_combo.setCurrentIndex(0)
        wizard.field_editor.set_fields(
            [
                Field(name="codice", type=T.TEXT, size=20, caption="Codice"),
                Field(name="valore", type=T.DECIMAL, size=10, fmt=".2f", caption="Valore"),
            ]
        )
        table = wizard.build_table()
        assert [field.name for field in table.fields] == ["codice", "valore"]
        assert table.field("valore").fmt == ".2f"
        assert table.indexes == []
    finally:
        wizard.close()


def test_table_expert_requires_fields(qapp, demo_project) -> None:
    wizard = TableExpert(demo_project, suggested_name="vuota")
    try:
        wizard.field_editor.set_fields([])
        with pytest.raises(MetadataError):
            wizard.build_table()
    finally:
        wizard.close()


def test_table_expert_summary(qapp, demo_project) -> None:
    wizard = TableExpert(demo_project, suggested_name="fatture")
    try:
        wizard.template_combo.setCurrentIndex(
            [template.key for template in TEMPLATES].index("fatture")
        )
        wizard._refresh_indexes()
        wizard._refresh_summary()
        text = wizard.summary_view.toPlainText()
        assert "CREATE TABLE" in text
        assert "fatture" in text
    finally:
        wizard.close()
