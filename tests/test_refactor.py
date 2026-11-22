"""Test di rinomina, duplicazione e manutenzione (0.6)."""

from __future__ import annotations

import pytest

from dbx.core.form_model import FormSpec
from dbx.core.project import ProjectError
from dbx.core.query_model import QuerySpec
from dbx.core.refactor import (
    check_database,
    compact_database,
    duplicate_object,
    rename_table,
)


def test_rename_table_updates_database_and_references(demo_project):
    rename_table(demo_project, "clienti", "anagrafica")
    assert demo_project.db.has_table("anagrafica")
    assert not demo_project.db.has_table("clienti")
    assert demo_project.table("anagrafica") is not None
    assert demo_project.table("clienti") is None

    fatture = demo_project.require_table("fatture")
    assert fatture.foreign_keys[0].ref_table == "anagrafica"

    query = QuerySpec.from_dict(demo_project.artifact("queries", "clienti_attivi"))
    assert query.base == "anagrafica"
    assert all(item.table == "anagrafica" for item in query.fields)
    assert query.filters[0].field == "anagrafica.attivo"

    joined = QuerySpec.from_dict(demo_project.artifact("queries", "fatture_clienti"))
    assert joined.joins[0].table == "anagrafica"
    assert joined.joins[0].right == "anagrafica.codice"
    assert any(item.table == "anagrafica" for item in joined.fields)

    form = FormSpec.from_dict(demo_project.artifact("forms", "form_clienti"))
    assert form.table == "anagrafica"

    diagram = demo_project.artifact("diagrams", "schema")
    assert any(node["table"] == "anagrafica" for node in diagram["nodes"])

    # La tabella rinominata resta interrogabile.
    assert demo_project.db.scalar('SELECT COUNT(*) FROM "anagrafica"') == 3


def test_rename_rejects_collisions_and_invalid_names(demo_project):
    with pytest.raises(ProjectError):
        rename_table(demo_project, "clienti", "fatture")
    with pytest.raises(Exception):
        rename_table(demo_project, "clienti", "nome con spazi")


def test_duplicate_table_copies_structure_and_data(demo_project):
    name = duplicate_object(demo_project, "tables", "clienti")
    assert name == "clienti_copia"
    copied = demo_project.require_table(name)
    assert copied.field_names == demo_project.require_table("clienti").field_names
    assert demo_project.db.scalar(f'SELECT COUNT(*) FROM "{name}"') == 3
    again = duplicate_object(demo_project, "tables", "clienti")
    assert again == "clienti_copia_2"


def test_duplicate_query_and_form(demo_project):
    query_name = duplicate_object(demo_project, "queries", "clienti_attivi", "clienti_copia")
    assert query_name == "clienti_copia"
    artifact = demo_project.artifact("queries", query_name)
    assert artifact["name"] == query_name
    form_name = duplicate_object(demo_project, "forms", "form_clienti")
    assert form_name == "form_clienti_copia"
    assert demo_project.artifact("forms", form_name)["name"] == form_name


def test_compact_and_integrity(demo_project):
    assert check_database(demo_project) == "ok"
    backup = compact_database(demo_project)
    assert backup is not None
    assert check_database(demo_project) == "ok"
