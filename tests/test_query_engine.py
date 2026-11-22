"""Test del motore delle query statiche."""

from __future__ import annotations

from datetime import date

import pytest

from dbx.core.query_engine import QueryEngine, QueryError, engine_for, preview_sql, run_query
from dbx.core.query_model import (
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
)
from dbx.runtime.rowset import Rowset


def _join_query() -> QuerySpec:
    return QuerySpec(
        name="fatture_clienti",
        caption="Fatture per cliente",
        base="fatture",
        fields=[
            QueryField("fatture", "numero"),
            QueryField("fatture", "data"),
            QueryField("clienti", "nome", alias="cliente_nome"),
            QueryField("fatture", "importo"),
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
    )


def test_run_filter_sort_and_types(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[
            QueryField("fatture", "numero"),
            QueryField("fatture", "data"),
            QueryField("fatture", "importo"),
            QueryField("fatture", "pagata"),
        ],
        filters=[QueryFilter("fatture.importo", "gt", "1000")],
        sorts=[QuerySort("fatture.importo", "desc")],
    )
    result = run_query(demo_project, spec)
    assert result.names() == ["numero", "data", "importo", "pagata"]
    assert [row["numero"] for row in result.rows] == [3, 1]
    assert result.rows[0]["importo"] == pytest.approx(3200.0)
    assert isinstance(result.rows[0]["importo"], float)
    assert isinstance(result.rows[0]["data"], date)
    assert isinstance(result.rows[0]["pagata"], bool)
    assert "ORDER BY" in result.sql
    assert "?" in result.sql
    assert result.params == (1000.0,)


def test_inner_join_and_alias(demo_project) -> None:
    result = run_query(demo_project, _join_query())
    assert len(result) == 5
    assert result.names() == ["numero", "data", "cliente_nome", "importo", "pagata"]
    assert result.column("CLIENTE_NOME").caption == "Nome"
    assert result.rows[0]["cliente_nome"] in {"Alfa Srl", "Beta Studio", "Gamma snc"}
    assert "INNER JOIN" in result.sql
    assert result.headers()[2] == "Nome"


def test_left_join_keeps_rows_without_match(demo_project) -> None:
    clienti = demo_project.require_table("clienti")
    Rowset(demo_project.db, clienti).insert(
        {"codice": "C004", "nome": "Delta", "citta": "Bari", "attivo": True}
    )
    spec = QuerySpec(
        name="clienti_fatture",
        base="clienti",
        fields=[
            QueryField("clienti", "codice"),
            QueryField("clienti", "nome"),
            QueryField("fatture", "numero"),
        ],
        joins=[
            QueryJoin(
                kind="left",
                table="fatture",
                left="clienti.codice",
                right="fatture.cliente",
            )
        ],
        sorts=[QuerySort("clienti.codice", "asc"), QuerySort("fatture.numero", "asc")],
    )
    result = run_query(demo_project, spec)
    assert len(result) == 6
    assert [row["numero"] for row in result.rows if row["codice"] == "C004"] == [None]
    assert "LEFT JOIN" in result.sql


def test_contains_and_boolean_filters(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero"), QueryField("fatture", "descrizione")],
        filters=[QueryFilter("fatture.descrizione", "contains", "consul")],
    )
    assert [row["numero"] for row in run_query(demo_project, spec).rows] == [1]

    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.pagata", "eq", "no")],
        sorts=[QuerySort("fatture.numero")],
    )
    assert [row["numero"] for row in run_query(demo_project, spec).rows] == [2, 3, 5]


def test_like_escapes_wildcards(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.descrizione", "contains", "%")],
    )
    result = run_query(demo_project, spec)
    assert result.rows == []
    assert "ESCAPE" in result.sql


def test_distinct_and_null_operators(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        distinct=True,
        fields=[QueryField("fatture", "cliente")],
        sorts=[QuerySort("fatture.cliente")],
    )
    result = run_query(demo_project, spec)
    assert [row["cliente"] for row in result.rows] == ["C001", "C002", "C003"]
    assert result.sql.startswith("SELECT DISTINCT")

    empty = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.data", "null")],
    )
    result = run_query(demo_project, empty)
    assert result.rows == []
    assert "IS NULL" in result.sql


def test_values_are_bound_not_interpolated(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.descrizione", "eq", "x' OR '1'='1")],
    )
    result = run_query(demo_project, spec)
    assert result.rows == []
    assert "OR '1'" not in result.sql
    assert result.params == ("x' OR '1'='1",)


def test_invalid_query_raises(demo_project) -> None:
    spec = QuerySpec(name="q", base="fatture", fields=[QueryField("fatture", "sconosciuto")])
    with pytest.raises(QueryError, match="Campo inesistente"):
        run_query(demo_project, spec)


def test_preview_sql_lists_params(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.numero", "ge", "2")],
    )
    text = preview_sql(demo_project, spec)
    assert "SELECT" in text
    assert "parametri: (2,)" in text


def test_engine_requires_database(demo_project) -> None:
    spec = QuerySpec(name="q", base="fatture", fields=[QueryField("fatture", "numero")])
    with pytest.raises(QueryError, match="database"):
        QueryEngine(demo_project.tables()).run(spec)


def test_engine_for_project(demo_project) -> None:
    spec = _join_query()
    result = engine_for(demo_project).run(spec.to_dict())
    assert len(result) == 5
    assert result.first()["numero"] == 1


def test_query_category_persists(demo_project) -> None:
    spec = QuerySpec(
        name="fatture_aperte",
        caption="Fatture aperte",
        base="fatture",
        fields=[QueryField("fatture", "numero"), QueryField("fatture", "importo")],
        filters=[QueryFilter("fatture.pagata", "eq", "no")],
    )
    demo_project.add_object("queries", spec.to_dict())
    demo_project.save()
    assert demo_project.names("queries") == ["fatture_aperte"]
    loaded = QuerySpec.from_project(demo_project, "fatture_aperte")
    assert loaded is not None
    assert loaded.to_dict() == spec.to_dict()
    assert (demo_project.objects_path / "queries" / "fatture_aperte.query.json").exists()
