"""Test del modello e del motore QBE (0.4/O3)."""

from __future__ import annotations

import pytest

from dbx.core.query_engine import QueryError, engine_for
from dbx.core.query_model import (
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
)


def test_filter_roundtrip_with_group_and_value2() -> None:
    item = QueryFilter(
        field="fatture.importo",
        op="between",
        value="100",
        value2="500",
        group=2,
    )
    clone = QueryFilter.from_dict(item.to_dict())
    assert clone == item
    assert item.to_dict()["value2"] == "500"
    assert item.to_dict()["group"] == 2


def test_filter_old_json_defaults() -> None:
    item = QueryFilter.from_dict({"field": "fatture.importo", "op": "gt", "value": "10"})
    assert item.value2 == ""
    assert item.group == 0


def test_validate_between_and_group(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[
            QueryFilter("fatture.importo", "between", "100"),
            QueryFilter("fatture.numero", "eq", "1", group=-1),
        ],
    )
    errors = spec.validate(demo_project.tables())
    assert any("intervallo incompleto" in error for error in errors)
    assert any("Gruppo di filtro non valido" in error for error in errors)


def test_validate_ref_type_compatibility(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero"), QueryField("clienti", "codice")],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        filters=[QueryFilter("fatture.cliente", "ref", "clienti.codice")],
    )
    assert spec.validate(demo_project.tables()) == []

    spec.filters = [QueryFilter("fatture.cliente", "ref", "fatture.importo")]
    errors = spec.validate(demo_project.tables())
    assert any("tipi incompatibili" in error for error in errors)


def test_engine_between(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero"), QueryField("fatture", "importo")],
        filters=[QueryFilter("fatture.importo", "between", "500", "1300")],
        sorts=[QuerySort("fatture.numero", "asc")],
    )
    result = engine_for(demo_project).run(spec)
    assert [row["numero"] for row in result.rows] == [1, 4]
    assert "BETWEEN ? AND ?" in result.sql
    assert result.params == (500.0, 1300.0)


def test_engine_like_wildcards(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="clienti",
        fields=[QueryField("clienti", "nome")],
        filters=[QueryFilter("clienti.nome", "like", "Al*")],
    )
    result = engine_for(demo_project).run(spec)
    assert [row["nome"] for row in result.rows] == ["Alfa Srl"]

    spec.filters = [QueryFilter("clienti.nome", "like", "*ta*")]
    result = engine_for(demo_project).run(spec)
    assert [row["nome"] for row in result.rows] == ["Beta Studio"]


def test_engine_like_literal_percent(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "descrizione")],
        filters=[QueryFilter("fatture.descrizione", "like", "100%")],
    )
    result = engine_for(demo_project).run(spec)
    assert result.rows == []
    assert "LIKE ? ESCAPE" in result.sql


def test_engine_or_groups(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="clienti",
        fields=[QueryField("clienti", "nome")],
        filters=[
            QueryFilter("clienti.citta", "eq", "Milano", group=0),
            QueryFilter("clienti.citta", "eq", "Roma", group=1),
        ],
        sorts=[QuerySort("clienti.nome", "asc")],
    )
    result = engine_for(demo_project).run(spec)
    assert [row["nome"] for row in result.rows] == ["Alfa Srl", "Gamma snc"]
    assert " OR " in result.sql
    assert result.params == ("Milano", "Roma")


def test_engine_ref_example_element(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        filters=[QueryFilter("fatture.cliente", "ref", "clienti.codice")],
    )
    result = engine_for(demo_project).run(spec)
    assert len(result.rows) == 5
    assert result.params == ()
    assert '"fatture"."cliente" = "clienti"."codice"' in result.sql


def test_engine_rejects_invalid_ref(demo_project) -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        filters=[QueryFilter("fatture.cliente", "ref", "clienti.codice")],
    )
    with pytest.raises(QueryError):
        engine_for(demo_project).run(spec)
