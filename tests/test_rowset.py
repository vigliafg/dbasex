import pytest

from dbx.core import types as T
from dbx.core.db import Database
from dbx.core.ddl import apply_migration
from dbx.core.metadata import Field, Index, Table
from dbx.runtime.rowset import Rowset, RowsetError


@pytest.fixture()
def rowset():
    db = Database(":memory:")
    table = Table(
        name="contatti",
        fields=[
            Field("nome", T.TEXT, required=True),
            Field("email", T.TEXT),
            Field("anni", T.INTEGER),
            Field("attivo", T.BOOLEAN),
            Field("nato", T.DATE),
            Field("voto", T.DECIMAL),
            Field("codice", T.TEXT, rule="LEN([codice]) >= 3"),
        ],
        indexes=[Index(fields=["email"], unique=True)],
    )
    apply_migration(db.con, table, None)
    return Rowset(db, table)


def test_insert_navigation_and_count(rowset):
    first = rowset.insert({"nome": "Ada", "anni": 36, "codice": "ABC"})
    rowset.insert({"nome": "Bob", "anni": 40, "codice": "DEF"})
    assert rowset.count() == 2
    assert len(rowset) == 2
    assert rowset.current["nome"] == "Bob"
    rowset.first()
    assert rowset.current["nome"] == "Ada"
    assert rowset.is_first and not rowset.is_last
    rowset.next()
    assert rowset.current["nome"] == "Bob"
    assert rowset.is_last
    rowset.previous()
    assert rowset.index == 0
    rowset.goto(1)
    assert rowset.current["nome"] == "Bob"
    assert rowset.load(first)["nome"] == "Ada"


def test_type_conversion_on_write_and_read(rowset):
    rowset.insert(
        {
            "nome": "Ada",
            "anni": "36",
            "attivo": "Sì",
            "nato": "10/12/1815",
            "voto": "8,5",
            "codice": "ABC",
        }
    )
    record = rowset.current
    assert record["anni"] == 36
    assert record["attivo"] is True
    assert str(record["nato"]) == "1815-12-10"
    assert record["voto"] == 8.5


def test_required_field_is_enforced(rowset):
    with pytest.raises(RowsetError) as exc:
        rowset.insert({"nome": "  ", "codice": "ABC"})
    assert "obbligatorio" in str(exc.value)


def test_unique_index_is_enforced(rowset):
    rowset.insert({"nome": "Ada", "email": "a@example.com", "codice": "ABC"})
    with pytest.raises(RowsetError) as exc:
        rowset.insert({"nome": "Altro", "email": "a@example.com", "codice": "XYZ"})
    assert "univoco" in str(exc.value)


def test_validation_rule_expression(rowset):
    with pytest.raises(RowsetError) as exc:
        rowset.insert({"nome": "Ada", "codice": "AB"})
    assert "regola" in str(exc.value)


def test_update_and_delete(rowset):
    record_id = rowset.insert({"nome": "Ada", "codice": "ABC"})
    rowset.update(record_id, {"nome": "Ada Lovelace", "anni": 37, "codice": "ABC"})
    assert rowset.load(record_id)["nome"] == "Ada Lovelace"
    rowset.delete(record_id)
    assert rowset.count() == 0
    assert rowset.current is None


def test_filter_and_order(rowset):
    rowset.insert({"nome": "Carla", "anni": 20, "codice": "CCC"})
    rowset.insert({"nome": "Anna", "anni": 30, "codice": "AAA"})
    rowset.insert({"nome": "Bruno", "anni": 40, "codice": "BBB"})
    rowset.open(where="anni >= ?", params=(30,), order="nome")
    assert [r["nome"] for r in rowset.rows()] == ["Anna", "Bruno"]
    assert rowset.count() == 2
