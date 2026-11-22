"""Layout del diagramma ER: posizioni, zoom e note.

Il diagramma non contiene lo schema: solo dove disegnare le tabelle. I metadati
restano in ``Table`` e vengono letti da :class:`SchemaGraph`. Il layout è un
artefatto di progetto, quindi si salva e si riapre con il progetto.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .schema_graph import SchemaGraph

DEFAULT_SPACING_X = 320.0
DEFAULT_SPACING_Y = 240.0
DEFAULT_COLUMNS = 3


@dataclass
class DiagramNode:
    table: str
    x: float = 40.0
    y: float = 40.0

    def to_dict(self) -> dict[str, Any]:
        return {"table": self.table, "x": round(float(self.x), 2), "y": round(float(self.y), 2)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramNode":
        return cls(
            table=str(data.get("table", "")),
            x=float(data.get("x", 40.0) or 0.0),
            y=float(data.get("y", 40.0) or 0.0),
        )


@dataclass
class DiagramSpec:
    name: str = "schema"
    caption: str = "Schema ER"
    nodes: dict[str, DiagramNode] = dc_field(default_factory=dict)
    zoom: float = 1.0
    notes: str = ""

    # ------------------------------------------------------------------ layout
    @classmethod
    def from_graph(
        cls,
        graph: SchemaGraph,
        name: str = "schema",
        caption: str = "Schema ER",
        previous: "DiagramSpec | None" = None,
    ) -> "DiagramSpec":
        spec = cls(name=name, caption=caption)
        if previous is not None:
            spec.zoom = previous.zoom
            spec.notes = previous.notes
        existing = {key.lower(): node for key, node in (previous.nodes.items() if previous else [])}
        for index, table in enumerate(graph.nodes.values()):
            old = existing.get(table.name.lower())
            if old is not None:
                node = DiagramNode(table=table.name, x=old.x, y=old.y)
            else:
                node = DiagramNode(
                    table=table.name,
                    x=40.0 + (index % DEFAULT_COLUMNS) * DEFAULT_SPACING_X,
                    y=40.0 + (index // DEFAULT_COLUMNS) * DEFAULT_SPACING_Y,
                )
            spec.nodes[table.name] = node
        return spec

    def node(self, table: str) -> DiagramNode | None:
        target = str(table).lower()
        for key, node in self.nodes.items():
            if key.lower() == target:
                return node
        return None

    def place(self, table: str, x: float, y: float) -> DiagramNode:
        node = self.node(table)
        if node is None:
            node = DiagramNode(table=table)
            self.nodes[table] = node
        node.x = max(0.0, float(x))
        node.y = max(0.0, float(y))
        return node

    def forget_missing(self, graph: SchemaGraph) -> None:
        valid = {name.lower() for name in graph.nodes}
        self.nodes = {
            key: node for key, node in self.nodes.items() if key.lower() in valid
        }

    def auto_layout(
        self,
        graph: SchemaGraph,
        columns: int = DEFAULT_COLUMNS,
        spacing_x: float = DEFAULT_SPACING_X,
        spacing_y: float = DEFAULT_SPACING_Y,
    ) -> None:
        for index, table in enumerate(graph.nodes.values()):
            self.place(
                table.name,
                40.0 + (index % max(1, columns)) * spacing_x,
                40.0 + (index // max(1, columns)) * spacing_y,
            )

    # -------------------------------------------------------------------- JSON
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "caption": self.caption,
            "zoom": round(float(self.zoom), 3),
            "notes": self.notes,
            "nodes": [node.to_dict() for node in self.nodes.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagramSpec":
        nodes: dict[str, DiagramNode] = {}
        raw_nodes = data.get("nodes", [])
        if isinstance(raw_nodes, dict):
            raw_nodes = [
                {"table": name, **value} for name, value in raw_nodes.items() if isinstance(value, dict)
            ]
        for entry in raw_nodes or []:
            if not isinstance(entry, dict):
                continue
            node = DiagramNode.from_dict(entry)
            if node.table:
                nodes[node.table] = node
        zoom = float(data.get("zoom", 1.0) or 1.0)
        return cls(
            name=str(data.get("name") or "schema"),
            caption=str(data.get("caption") or "Schema ER"),
            nodes=nodes,
            zoom=max(0.25, min(2.0, zoom)),
            notes=str(data.get("notes", "")),
        )

    @classmethod
    def from_project(cls, project, graph: SchemaGraph | None = None) -> "DiagramSpec":
        graph = graph or SchemaGraph.from_project(project)
        artifact = project.artifact("diagrams", "schema")
        if artifact:
            previous = cls.from_dict(artifact)
            previous.forget_missing(graph)
            return cls.from_graph(
                graph,
                name=previous.name,
                caption=previous.caption,
                previous=previous,
            )
        return cls.from_graph(graph)
