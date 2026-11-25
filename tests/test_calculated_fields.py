"""Test dei campi calcolati e delle compilazioni automatiche (0.7 O4)."""

from __future__ import annotations

from datetime import date

import pytest

from dbx.core import types as T
from dbx.core.db import Database
from dbx.core.ddl import apply_migration, plan_migration
from dbx.core.metadata import Field, Index, MetadataError, Table
from dbx.core.query_engine import QueryEngine
from dbx.core.query_model import QueryField, QuerySpec
from dbx.core.search import SearchCriterion, SearchRequest, SearchError, build_where
from dbx.runtime.rowset import Rowset, RowsetError


def _table() -> Table:
    return Table(
        name="righe",
        fields=[
            Field("qta", T.INTEGER, required=True),
            Field("prezzo", T.DECIMAL, required=True),
            Field("totale", T.DECIMAL, calculated="[qta] * [prezzo]"),
            Field("codice", T.INTEGER, increment="records"),
            Field("creato", T.DATE, auto_date="insert"),
            Field("etichetta", T.TEXT, auto_enter="CONCAT([qta], ' x')"),
        ],
    )


@pytest.fixture()
def database():
    db = Database(":memory:")
    table = _table()
    apply_migration(db.con, table, None)
    return db, table


def test_calculated_fields_are_virtual(database):
    db, table = database
    columns = [row["name"] for row in db.query("PRAGMA table_info('righe')")]
    assert "totale" in table.field_names
    assert "totale" not in columns
    assert table.field("totale").stored is False
    assert "totale" not in table.stored_field_names


def test_insert_and_update_compute_calculated_fields(database):
    db, table = database
    rowset = Rowset(db, table)
    record_id = rowset.insert({"qta": 2, "prezzo": 3.5})
    assert rowset.current["totale"] == 7.0
    assert rowset.current["codice"] == 1
    assert rowset.current["creato"] == date.today()
    assert rowset.current["etichetta"] == "2 x"

    rowset.update(record_id, {"qta": 3, "prezzo": 2, "codice": 1, "creato": date.today()})
    assert rowset.current["totale"] == 6.0

    rowset.open()
    assert [row["totale"] for row in rowset.rows()] == [6.0]
    assert rowset.load(record_id)["totale"] == 6.0


def test_serial_increments_and_auto_enter_only_on_insert(database):
    db, table = database
    rowset = Rowset(db, table)
    rowset.insert({"qta": 1, "prezzo": 1})
    second = rowset.insert({"qta": 5, "prezzo": 2})
    assert rowset.load(second)["codice"] == 2
    assert rowset.load(second)["etichetta"] == "5 x"

    # Una modifica non ripete l'auto-enter e conserva il numero di serie.
    rowset.update(second, {"qta": 9, "prezzo": 2, "codice": 2, "creato": date.today()})
    assert rowset.load(second)["codice"] == 2
    assert rowset.load(second)["etichetta"] == "5 x"


def test_calculated_chain_and_validation_rule(database):
    db, table = database
    table.fields[2].calculated = "[imponibile] * 1.22"
    table.fields.insert(2, Field("imponibile", T.DECIMAL, calculated="[qta] * [prezzo]"))
    table.fields[0].rule = "[totale] > 0"
    apply_migration(db.con, table, Table.from_dict(table.to_dict()))
    rowset = Rowset(db, table)
    rowset.insert({"qta": 2, "prezzo": 10})
    assert rowset.current["imponibile"] == 20
    assert rowset.current["totale"] == pytest.approx(24.4)

    fields = list(table.fields)
    bad = Table.from_dict(table.to_dict())
    bad.fields[0].rule = "[totale] < 0"
    apply_migration(db.con, bad, table)
    with pytest.raises(RowsetError):
        Rowset(db, bad).insert({"qta": 1, "prezzo": 1})
    assert fields


def test_auto_value_supplied_is_preserved(database):
    db, table = database
    rowset = Rowset(db, table)
    rowset.insert({"qta": 1, "prezzo": 1, "codice": 42, "etichetta": "manuale"})
    assert rowset.current["codice"] == 42
    assert rowset.current["etichetta"] == "manuale"


def test_invalid_mechanisms_are_rejected():
    with pytest.raises(MetadataError):
        Table(
            name="t",
            fields=[
                Field(
                    "x",
                    T.INTEGER,
                    calculated="1",
                    increment="records",
                )
            ],
        ).validate()
    with pytest.raises(MetadataError):
        Table(name="t", fields=[Field("x", T.TEXT, increment="records")]).validate()
    with pytest.raises(MetadataError):
        Table(name="t", fields=[Field("x", T.TEXT, auto_date="insert")]).validate()
    with pytest.raises(MetadataError):
        Table(name="t", fields=[Field("x", T.INTEGER, calculated="[inesistente] +")]).validate()
    with pytest.raises(MetadataError):
        Table(
            name="t",
            fields=[Field("x", T.INTEGER, calculated="1")],
            indexes=[Index(fields=["x"])],
        ).validate()


def test_calculated_fields_round_trip():
    table = _table()
    clone = Table.from_dict(table.to_dict())
    field = clone.field("totale")
    assert field.calculated == "[qta] * [prezzo]"
    assert clone.field("codice").increment == "records"
    assert clone.field("creato").auto_date == "insert"
    assert clone.field("etichetta").auto_enter == "CONCAT([qta], ' x')"
    assert clone.to_dict() == table.to_dict()


def test_migration_adds_only_stored_columns():
    old = Table(name="t", fields=[Field("a", T.INTEGER)])
    new = Table(
        name="t",
        fields=[
            Field("a", T.INTEGER),
            Field("calc", T.INTEGER, calculated="[a] + 1"),
            Field("serie", T.INTEGER, increment="records"),
        ],
    )
    plan = plan_migration(old, new)
    statements = " ".join(plan.statements)
    assert '"serie"' in statements
    assert '"calc"' not in statements


def test_query_and_search_reject_calculated_fields(database):
    db, table = database
    engine = QueryEngine({table.name: table}, db)
    spec = QuerySpec(
        name="q",
        base="righe",
        fields=[QueryField("righe", "totale")],
    )
    with pytest.raises(Exception) as query_error:
        engine.compile(spec)
    assert "calcolato" in str(query_error.value).lower()

    with pytest.raises(SearchError):
        build_where(table, SearchRequest([SearchCriterion("totale", "gt", "1")]))


def test_rules_reference_calculated_values(database):
    db, table = database
    table.fields[0].rule = "[totale] >= 10"
    apply_migration(db.con, table, Table.from_dict(table.to_dict()))
    rowset = Rowset(db, table)
    with pytest.raises(RowsetError):
        rowset.insert({"qta": 1, "prezzo": 2})
    rowset.insert({"qta": 5, "prezzo": 2})
    assert rowset.current["totale"] == 10.0


def test_rename_rewrites_calculated_and_auto_enter_references(demo_project):
    from dbx.core.refactor import rename_table

    table = demo_project.require_table("clienti")
    table.fields.append(
        Field("saluto", T.TEXT, calculated="'Ciao ' + [clienti.nome]")
    )
    table.fields.append(
        Field("copia", T.TEXT, auto_enter="[clienti.nome]")
    )
    demo_project.apply_table(table)
    rename_table(demo_project, "clienti", "anagrafica")
    renamed = demo_project.require_table("anagrafica")
    assert renamed.field("saluto").calculated == "'Ciao ' + [anagrafica.nome]"
    assert renamed.field("copia").auto_enter == "[anagrafica.nome]"
