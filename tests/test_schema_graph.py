"""Test del grafo ER derivato dai metadati delle tabelle."""

from __future__ import annotations

from dbx.core.metadata import ForeignKey, Index, Table
from dbx.core.schema_graph import SchemaGraph


def test_graph_from_demo_tables_has_relationship(demo_project) -> None:
    graph = SchemaGraph.from_project(demo_project)
    assert set(graph.nodes) == {"clienti", "fatture"}
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.child == "fatture"
    assert edge.parent == "clienti"
    assert edge.columns == ("cliente",)
    assert edge.ref_columns == ("codice",)
    assert edge.cardinality == "1:N"
    assert graph.neighbors("clienti") == ["fatture"]
    assert graph.outgoing("fatture") == [edge]
    assert graph.incoming("clienti") == [edge]
    assert graph.validate() == []
    assert graph.summary()["tables"] == 2


def test_unique_foreign_key_is_one_to_one() -> None:
    from dbx.core import types as T
    from dbx.core.metadata import Field

    clienti = Table(name="clienti", fields=[Field("codice", T.TEXT, size=10, pk=True)])
    fatture = Table(
        name="fatture",
        fields=[Field("cliente", T.TEXT, size=10)],
        foreign_keys=[ForeignKey(columns=["cliente"], ref_table="clienti", ref_columns=["codice"])],
        indexes=[Index(fields=["cliente"], unique=True, name="ux_fatture_cliente")],
    )
    graph = SchemaGraph.from_tables([clienti, fatture])
    assert graph.edges[0].cardinality == "1:1"


def test_explicit_tables_and_missing_target_validation() -> None:
    from dbx.core import types as T
    from dbx.core.metadata import Field

    clienti = Table(name="clienti", fields=[Field("codice", T.TEXT, size=10, pk=True)])
    fatture = Table(
        name="fatture",
        fields=[Field("cliente", T.TEXT, size=10)],
        foreign_keys=[ForeignKey(columns=["cliente"], ref_table="inesistente", ref_columns=["id"])],
    )
    graph = SchemaGraph.from_tables([clienti, fatture])
    assert len(graph.edges) == 1
    assert graph.validate()
    assert graph.table("CLIENTI") is clienti
