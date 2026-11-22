"""Test del layout del diagramma ER."""

from __future__ import annotations

from dbx.core.diagram_model import DiagramSpec
from dbx.core.schema_graph import SchemaGraph


def test_diagram_from_graph_roundtrip(demo_project) -> None:
    graph = SchemaGraph.from_project(demo_project)
    spec = DiagramSpec.from_graph(graph)
    assert set(spec.nodes) == {"clienti", "fatture"}
    assert spec.nodes["clienti"].x < spec.nodes["fatture"].x
    clone = DiagramSpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()


def test_diagram_preserves_positions_and_forgets_deleted_tables(demo_project) -> None:
    graph = SchemaGraph.from_project(demo_project)
    spec = DiagramSpec.from_graph(graph)
    spec.place("clienti", 512, 128)
    spec.zoom = 1.5
    spec.notes = "Schema dimostrativo"

    previous = DiagramSpec.from_dict(spec.to_dict())
    rebuilt = DiagramSpec.from_graph(graph, previous=previous)
    assert rebuilt.node("clienti").x == 512
    assert rebuilt.node("clienti").y == 128
    assert rebuilt.zoom == 1.5
    assert rebuilt.notes == "Schema dimostrativo"

    clienti_only = SchemaGraph.from_tables([demo_project.require_table("clienti")])
    rebuilt.forget_missing(clienti_only)
    assert set(rebuilt.nodes) == {"clienti"}


def test_diagram_from_project_uses_saved_artifact(demo_project) -> None:
    graph = SchemaGraph.from_project(demo_project)
    spec = DiagramSpec.from_graph(graph)
    spec.place("fatture", 777, 333)
    demo_project.put_object("diagrams", spec.to_dict(), previous_name="schema")
    loaded = DiagramSpec.from_project(demo_project, graph)
    assert loaded.node("fatture").x == 777
    assert loaded.node("fatture").y == 333


def test_auto_layout_is_deterministic(demo_project) -> None:
    graph = SchemaGraph.from_project(demo_project)
    first = DiagramSpec.from_graph(graph)
    first.auto_layout(graph)
    second = DiagramSpec.from_graph(graph)
    second.auto_layout(graph)
    assert first.to_dict() == second.to_dict()
