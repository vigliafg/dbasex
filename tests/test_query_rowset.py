"""Test del cursore read-only sulle query."""

from __future__ import annotations

import pytest

from dbx.core.query_engine import run_query
from dbx.core.query_model import QuerySpec
from dbx.runtime.query_rowset import QueryRowset, sort_rows
from dbx.runtime.rowset import RowsetError


def _result(demo_project):
    spec = QuerySpec.from_project(demo_project, "fatture_clienti")
    assert spec is not None
    return run_query(demo_project, spec), spec


def test_navigation_and_status(demo_project) -> None:
    result, spec = _result(demo_project)
    rowset = QueryRowset(result, order="numero desc")
    assert len(rowset) == 5
    assert rowset.count() == 5
    assert rowset.index == 0
    assert rowset.current["numero"] == 5
    assert rowset.is_first is True
    assert rowset.next()["numero"] == 4
    assert rowset.index == 1
    assert rowset.last()["numero"] == 1
    assert rowset.is_last is True
    assert rowset.previous()["numero"] == 2
    assert rowset.goto(1)["numero"] == 4
    assert rowset.first()["numero"] == 5
    assert rowset.columns[:3] == ["numero", "data", "cliente_nome"]


def test_read_only_operations_raise(demo_project) -> None:
    result, _spec = _result(demo_project)
    rowset = QueryRowset(result)
    assert set(rowset.new_record()) == set(result.names())
    with pytest.raises(RowsetError, match="sola lettura"):
        rowset.save({})
    with pytest.raises(RowsetError, match="sola lettura"):
        rowset.delete()


def test_sort_rows_is_stable_and_handles_nulls() -> None:
    rows = [
        {"nome": "b", "n": 2},
        {"nome": "a", "n": None},
        {"nome": "a", "n": 1},
    ]
    ordered = sort_rows(rows, "nome asc, n desc")
    assert [(row["nome"], row["n"]) for row in ordered] == [("a", 1), ("a", None), ("b", 2)]
    assert sort_rows(rows, "") == rows
