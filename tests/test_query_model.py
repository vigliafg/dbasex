"""Test del modello delle query statiche."""

from __future__ import annotations

from dbx.core import types as T
from dbx.core.metadata import Field, ForeignKey, Table
from dbx.core.query_model import (
    ALL_OPERATORS,
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
    parse_ref,
)


def _tables() -> dict[str, Table]:
    clienti = Table(
        name="clienti",
        caption="Clienti",
        fields=[
            Field("codice", T.TEXT, size=8, pk=True, caption="Codice"),
            Field("nome", T.TEXT, size=40),
            Field("citta", T.TEXT, size=30),
        ],
    )
    fatture = Table(
        name="fatture",
        caption="Fatture",
        fields=[
            Field("numero", T.INTEGER, pk=True),
            Field("cliente", T.TEXT, size=8),
            Field("importo", T.DECIMAL),
        ],
        foreign_keys=[
            ForeignKey(columns=["cliente"], ref_table="clienti", ref_columns=["codice"])
        ],
    )
    return {"clienti": clienti, "fatture": fatture}


def test_create_selects_all_fields() -> None:
    tables = _tables()
    spec = QuerySpec.create(tables["fatture"], name="fatture_query")
    assert spec.base == "fatture"
    assert spec.refs() == ["fatture.numero", "fatture.cliente", "fatture.importo"]
    assert spec.output_names() == ["numero", "cliente", "importo"]
    assert spec.validate(tables) == []


def test_output_names_alias_and_duplicates() -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[
            QueryField("fatture", "cliente"),
            QueryField("clienti", "nome", alias="cliente_nome"),
            QueryField("clienti", "citta"),
            QueryField("fatture", "importo"),
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
    names = spec.output_names()
    assert names == ["cliente", "cliente_nome", "citta", "importo"]
    assert spec.field_items()[1] == ("clienti", "nome", "cliente_nome")
    assert spec.validate(_tables()) == []


def test_output_names_duplicate_fields_are_qualified() -> None:
    spec = QuerySpec(
        name="q",
        base="fatture",
        fields=[QueryField("fatture", "cliente"), QueryField("clienti", "cliente")],
    )
    assert spec.output_names() == ["fatture_cliente", "clienti_cliente"]


def test_roundtrip_json() -> None:
    spec = QuerySpec(
        name="q",
        caption="Query demo",
        base="fatture",
        distinct=True,
        fields=[QueryField("fatture", "numero"), QueryField("clienti", "nome", "cliente_nome")],
        joins=[QueryJoin("left", "clienti", "fatture.cliente", "clienti.codice")],
        filters=[QueryFilter("fatture.importo", "ge", "100")],
        sorts=[QuerySort("fatture.numero", "desc")],
    )
    clone = QuerySpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()
    assert clone.distinct is True
    assert clone.joins[0].kind == "left"


def test_parse_ref() -> None:
    assert parse_ref("fatture.cliente") == ("fatture", "cliente")
    for invalid in ("", "cliente", "a.b.c", ".x", "x."):
        try:
            parse_ref(invalid)
        except ValueError:
            continue
        raise AssertionError(f"Riferimento accettato: {invalid!r}")


def test_validation_reports_missing_and_invalid_parts() -> None:
    tables = _tables()
    spec = QuerySpec(name="", base="inesistente")
    errors = spec.validate(tables)
    assert any("nome" in error for error in errors)
    assert any("base inesistente" in error for error in errors)

    spec = QuerySpec(name="q", base="fatture", fields=[QueryField("fatture", "sconosciuto")])
    spec.joins = [
        QueryJoin("full", "clienti", "fatture.cliente", "clienti.codice"),
        QueryJoin("left", "clienti", "fatture.cliente", "clienti.nome"),
    ]
    spec.filters = [
        QueryFilter("fatture.importo", "eq", ""),
        QueryFilter("x", "eq", "1"),
        QueryFilter("fatture.numero", "boh", "1"),
    ]
    spec.sorts = [QuerySort("fatture.sconosciuto", "up")]
    errors = spec.validate(tables)
    assert any("Campo inesistente" in error for error in errors)
    assert any("Tipo di join non valido" in error for error in errors)
    assert any("già presente" in error for error in errors)
    assert any("valore mancante" in error for error in errors)
    assert any("Riferimento non valido" in error for error in errors)
    assert any("Operatore di filtro non valido" in error for error in errors)
    assert any("Direzione di ordinamento" in error for error in errors)
    assert set(ALL_OPERATORS) == {
        "eq",
        "ne",
        "gt",
        "ge",
        "lt",
        "le",
        "contains",
        "starts",
        "ends",
        "like",
        "between",
        "ref",
        "null",
        "notnull",
    }
