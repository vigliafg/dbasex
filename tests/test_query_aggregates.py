"""Test degli aggregati e di GROUP BY nelle query (0.7 O5)."""

from __future__ import annotations

import pytest

from dbx.core.query_engine import engine_for
from dbx.core.query_model import (
    QueryAggregate,
    QueryError,
    QueryField,
    QueryJoin,
    QuerySort,
    QuerySpec,
)


def _global_aggregates() -> QuerySpec:
    return QuerySpec(
        name="riepilogo",
        base="fatture",
        fields=[],
        aggregates=[
            QueryAggregate("count", "fatture"),
            QueryAggregate("sum", "fatture", "importo", "totale"),
            QueryAggregate("avg", "fatture", "importo", "media"),
            QueryAggregate("min", "fatture", "importo", "minimo"),
            QueryAggregate("max", "fatture", "importo", "massimo"),
        ],
    )


def test_global_aggregates(demo_project):
    result = engine_for(demo_project).run(_global_aggregates())
    assert len(result) == 1
    row = result.rows[0]
    assert row["count_record"] == 5
    assert row["totale"] == pytest.approx(5900.5)
    assert row["media"] == pytest.approx(1180.1)
    assert row["minimo"] == pytest.approx(250.5)
    assert row["massimo"] == pytest.approx(3200.0)
    types = {column.key: column.type for column in result.columns}
    assert types["count_record"] == "integer"
    assert types["totale"] == "decimal"


def test_group_by_with_count_and_sum(demo_project):
    spec = QuerySpec(
        name="per_pagata",
        base="fatture",
        fields=[QueryField("fatture", "pagata")],
        group_by=["fatture.pagata"],
        aggregates=[
            QueryAggregate("count", "fatture", alias="numero_fatture"),
            QueryAggregate("sum", "fatture", "importo", "totale"),
        ],
        sorts=[QuerySort("pagata", "asc")],
    )
    result = engine_for(demo_project).run(spec)
    assert len(result) == 2
    assert [bool(row["pagata"]) for row in result.rows] == [False, True]
    non_pagate = result.rows[0]
    pagate = result.rows[1]
    assert non_pagate["numero_fatture"] == 3
    assert non_pagate["totale"] == pytest.approx(3900.5)
    assert pagate["numero_fatture"] == 2
    assert pagate["totale"] == pytest.approx(2000.0)


def test_group_by_join_and_sort_by_aggregate_alias(demo_project):
    spec = QuerySpec(
        name="per_cliente",
        base="fatture",
        fields=[QueryField("clienti", "nome", alias="cliente")],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        group_by=["clienti.nome"],
        aggregates=[QueryAggregate("sum", "fatture", "importo", "totale")],
        sorts=[QuerySort("totale", "desc")],
    )
    result = engine_for(demo_project).run(spec)
    assert len(result) == 3
    assert result.rows[0]["cliente"] == "Beta Studio"
    assert result.rows[0]["totale"] == pytest.approx(3450.5)
    assert result.rows[1]["totale"] == pytest.approx(1650.0)


def test_count_field_ignores_nulls(demo_project):
    spec = QuerySpec(
        name="conteggio",
        base="fatture",
        aggregates=[QueryAggregate("count", "fatture", "pagata", "con_pagata")],
    )
    result = engine_for(demo_project).run(spec)
    assert result.rows[0]["con_pagata"] == 5


def test_grouped_query_validation(demo_project):
    spec = QuerySpec(
        name="non_valida",
        base="fatture",
        fields=[QueryField("fatture", "numero")],
        group_by=["fatture.pagata"],
        aggregates=[QueryAggregate("sum", "fatture", "importo")],
    )
    errors = spec.validate(demo_project.tables())
    assert any("non raggruppato" in error for error in errors)

    bad = QuerySpec(
        name="bad",
        base="fatture",
        fields=[QueryField("fatture", "pagata")],
        group_by=["fatture.pagata"],
        aggregates=[QueryAggregate("sum", "fatture", "numero", "totale")],
    )
    # Il campo esiste, ma l'aggregato su un testo è accettato dal modello:
    # il limite è semantico e SQLite restituisce 0. Verifichiamo invece i casi bloccanti.
    assert bad.validate(demo_project.tables()) == []

    missing = QuerySpec(
        name="missing",
        base="fatture",
        aggregates=[QueryAggregate("sum", "fatture", "inesistente")],
    )
    assert any("inesistente" in error for error in missing.validate(demo_project.tables()))

    wrong_function = QuerySpec(
        name="wrong",
        base="fatture",
        aggregates=[QueryAggregate("median", "fatture", "importo")],
    )
    assert any("Funzione" in error for error in wrong_function.validate(demo_project.tables()))


def test_aggregate_round_trip():
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "pagata")],
        group_by=["fatture.pagata"],
        aggregates=[QueryAggregate("sum", "fatture", "importo", "totale")],
    )
    restored = QuerySpec.from_dict(spec.to_dict())
    assert restored.group_by == ["fatture.pagata"]
    assert restored.aggregates[0].function == "sum"
    assert restored.aggregates[0].alias == "totale"
    assert restored.output_names() == ["pagata", "totale"]


def test_aggregate_excludes_calculated_fields(demo_project):
    from dbx.core import types as T
    from dbx.core.metadata import Field

    table = demo_project.require_table("fatture")
    table.fields.append(Field("doppio", T.DECIMAL, calculated="[importo] * 2"))
    demo_project.apply_table(table)
    spec = QuerySpec(
        name="calc",
        base="fatture",
        aggregates=[QueryAggregate("sum", "fatture", "doppio")],
    )
    errors = spec.validate(demo_project.tables())
    assert any("calcolato" in error.lower() for error in errors)


def test_query_error_when_group_field_order_invalid(demo_project):
    spec = QuerySpec(
        name="sort_errata",
        base="fatture",
        fields=[QueryField("fatture", "pagata")],
        group_by=["fatture.pagata"],
        aggregates=[QueryAggregate("count", "fatture", alias="n")],
        sorts=[QuerySort("inesistente", "asc")],
    )
    with pytest.raises(QueryError):
        engine_for(demo_project).compile(spec)
