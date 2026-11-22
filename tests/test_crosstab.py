"""Test della tabella incrociata read-only (0.7 O6)."""

from __future__ import annotations

import csv

import pytest

from dbx.core.crosstab import CrosstabError, build_crosstab, numeric_columns
from dbx.core.query_engine import engine_for
from dbx.core.query_model import (
    QueryAggregate,
    QueryField,
    QueryJoin,
    QuerySpec,
)


def _pivot_spec() -> QuerySpec:
    return QuerySpec(
        name="pivot_fatture",
        base="fatture",
        fields=[
            QueryField("clienti", "nome", alias="cliente"),
            QueryField("fatture", "pagata"),
        ],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        group_by=["clienti.nome", "fatture.pagata"],
        aggregates=[QueryAggregate("sum", "fatture", "importo", "totale")],
    )


def _crosstab(demo_project):
    result = engine_for(demo_project).run(_pivot_spec())
    return result, build_crosstab(result, "cliente", "pagata", "totale")


def test_crosstab_pivots_rows_and_columns(demo_project):
    result, crosstab = _crosstab(demo_project)
    assert len(result) == 4
    assert crosstab.row_values == ["Alfa Srl", "Beta Studio", "Gamma snc"]
    assert crosstab.column_values == [False, True]
    assert crosstab.cell("Alfa Srl", True) == pytest.approx(1200.0)
    assert crosstab.cell("Alfa Srl", False) == pytest.approx(450.0)
    assert crosstab.cell("Beta Studio", False) == pytest.approx(3450.5)
    assert crosstab.cell("Beta Studio", True) is None
    assert crosstab.cell("Gamma snc", True) == pytest.approx(800.0)


def test_crosstab_totals(demo_project):
    _result, crosstab = _crosstab(demo_project)
    assert crosstab.row_totals["Alfa Srl"] == pytest.approx(1650.0)
    assert crosstab.row_totals["Beta Studio"] == pytest.approx(3450.5)
    assert crosstab.row_totals["Gamma snc"] == pytest.approx(800.0)
    assert crosstab.column_totals[False] == pytest.approx(3900.5)
    assert crosstab.column_totals[True] == pytest.approx(2000.0)
    assert crosstab.grand_total == pytest.approx(5900.5)
    assert crosstab.source_rows == 4


def test_crosstab_rows_and_csv(demo_project, tmp_path):
    _result, crosstab = _crosstab(demo_project)
    rows = crosstab.rows()
    assert rows[0][0] == "Nome \\ Pagata"
    assert rows[0][-1] == "Totale"
    assert rows[-1][0] == "Totale"
    assert rows[1][0] == "Alfa Srl"
    assert rows[-1][-1] == "5900,5" or rows[-1][-1] == "5900.5"

    path = crosstab.to_csv(tmp_path / "pivot")
    assert path.suffix == ".csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        loaded = list(csv.reader(handle, delimiter=";"))
    assert loaded[0] == rows[0]
    assert loaded[-1][-1] == rows[-1][-1]


def test_crosstab_rejects_invalid_columns(demo_project):
    result = engine_for(demo_project).run(_pivot_spec())
    with pytest.raises(CrosstabError):
        build_crosstab(result, "inesistente", "pagata", "totale")
    with pytest.raises(CrosstabError):
        build_crosstab(result, "cliente", "pagata", "cliente")
    with pytest.raises(CrosstabError):
        build_crosstab(result, "cliente", "pagata", "pagata")


def test_numeric_columns_are_listed(demo_project):
    result = engine_for(demo_project).run(_pivot_spec())
    keys = [column.key for column in numeric_columns(result)]
    assert keys == ["totale"]
