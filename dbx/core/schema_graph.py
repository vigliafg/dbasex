"""Grafo ER del progetto: tabelle come nodi, foreign key come archi.

Il grafo è una vista sui metadati reali: non duplica campi o relazioni e non
modifica il database. Serve al Database Designer per disegnare e validare lo
schema senza introdurre un secondo modello dei dati.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .metadata import ForeignKey, Table, validate_project_tables


@dataclass(frozen=True)
class SchemaEdge:
    """Relazione ER derivata da una ``ForeignKey``."""

    name: str
    child: str
    columns: tuple[str, ...]
    parent: str
    ref_columns: tuple[str, ...]
    on_delete: str = "NO ACTION"
    cardinality: str = "1:N"

    @property
    def label(self) -> str:
        return ", ".join(self.columns)


class SchemaGraph:
    """Grafo delle tabelle e delle relazioni di un progetto."""

    def __init__(self, tables: Iterable[Table]) -> None:
        self.nodes: dict[str, Table] = {}
        for table in tables:
            self.nodes[table.name] = table
        self.edges: list[SchemaEdge] = []
        for table in self.nodes.values():
            for fk in table.foreign_keys:
                self.edges.append(self._edge(table, fk))

    # ------------------------------------------------------------------ build
    @classmethod
    def from_tables(cls, tables: Iterable[Table]) -> "SchemaGraph":
        return cls(tables)

    @classmethod
    def from_project(cls, project) -> "SchemaGraph":
        return cls(project.tables().values())

    @staticmethod
    def _edge(table: Table, fk: ForeignKey) -> SchemaEdge:
        return SchemaEdge(
            name=fk.resolved_name(table.name),
            child=table.name,
            columns=tuple(fk.columns),
            parent=fk.ref_table,
            ref_columns=tuple(fk.ref_columns),
            on_delete=fk.on_delete,
            cardinality="1:1" if SchemaGraph._is_unique(table, fk.columns) else "1:N",
        )

    @staticmethod
    def _is_unique(table: Table, columns: list[str]) -> bool:
        wanted = {str(name).lower() for name in columns}
        if not wanted:
            return False
        primary = {field.name.lower() for field in table.fields if field.pk}
        if primary and primary == wanted:
            return True
        for index in table.indexes:
            if index.unique and {field.lower() for field in index.fields} == wanted:
                return True
        return False

    # ------------------------------------------------------------------- query
    def table(self, name: str) -> Table | None:
        target = str(name).lower()
        for key, table in self.nodes.items():
            if key.lower() == target:
                return table
        return None

    def edges_for(self, table_name: str) -> list[SchemaEdge]:
        target = str(table_name).lower()
        return [
            edge
            for edge in self.edges
            if edge.child.lower() == target or edge.parent.lower() == target
        ]

    def outgoing(self, table_name: str) -> list[SchemaEdge]:
        target = str(table_name).lower()
        return [edge for edge in self.edges if edge.child.lower() == target]

    def incoming(self, table_name: str) -> list[SchemaEdge]:
        target = str(table_name).lower()
        return [edge for edge in self.edges if edge.parent.lower() == target]

    def neighbors(self, table_name: str) -> list[str]:
        target = str(table_name).lower()
        result: list[str] = []
        for edge in self.edges:
            other = edge.parent if edge.child.lower() == target else edge.child
            if other.lower() != target and other not in result:
                result.append(other)
        return result

    # --------------------------------------------------------------- validazione
    def validate(self) -> list[str]:
        errors = validate_project_tables(self.nodes.values())
        for edge in self.edges:
            if self.table(edge.parent) is None:
                errors.append(f"{edge.child}: relazione verso tabella inesistente {edge.parent}")
        return errors

    def summary(self) -> dict[str, Any]:
        return {
            "tables": len(self.nodes),
            "relationships": len(self.edges),
            "one_to_many": sum(1 for edge in self.edges if edge.cardinality == "1:N"),
            "one_to_one": sum(1 for edge in self.edges if edge.cardinality == "1:1"),
        }
