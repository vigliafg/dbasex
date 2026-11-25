"""Test del Database Designer ER."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from dbx.core import types as T
from dbx.core.metadata import Field, ForeignKey, Table
from dbx.designers.database_designer import (
    DatabaseDesignerWidget,
    RelationshipDialog,
)
from dbx.ui.main_window import MainWindow


def test_designer_shows_graph_and_cards(qapp, demo_project) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    try:
        assert set(designer.graph.nodes) == {"clienti", "fatture"}
        assert len(designer.graph.edges) == 1
        assert set(designer.diagram.nodes) == {"clienti", "fatture"}
        assert designer.canvas.card_rect("clienti").width() > 200
        assert designer.status_label.text().startswith("2 tabelle")
        assert designer.inspector.item("tables") is not None
    finally:
        designer.close()


def test_drag_moves_node_and_layout_roundtrip(qapp, demo_project) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    try:
        designer.show()
        qapp.processEvents()
        card = designer.canvas.card_rect("fatture")
        start = card.center().toPoint()
        end = start + QPoint(60, 30)
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(designer.canvas, end)
        QTest.mouseRelease(
            designer.canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            end,
        )
        assert designer.diagram.node("fatture").x >= 100
        assert designer.is_dirty() is True
        assert designer.save() is True
        assert designer.is_dirty() is False
        artifact = demo_project.artifact("diagrams", "schema")
        assert artifact is not None
        assert any(node["table"] == "fatture" for node in artifact["nodes"])
    finally:
        designer.close()


def test_zoom_and_auto_layout(qapp, demo_project) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    try:
        base_width = designer.canvas.width()
        designer.zoom_combo.setCurrentIndex(6)  # 200%
        assert designer.canvas.zoom == 2.0
        assert designer.canvas.width() > base_width
        designer.zoom_combo.setCurrentIndex(0)  # 25%
        assert designer.canvas.zoom == 0.25
        designer.auto_layout()
        assert designer.diagram.node("clienti").x == 40
        assert designer.diagram.node("fatture").x == 360
    finally:
        designer.close()


def test_new_relationship(qapp, demo_project, monkeypatch) -> None:
    table = Table(
        name="ordini",
        fields=[
            Field("id", T.INTEGER, pk=True),
            Field("cliente", T.TEXT, size=8),
        ],
    )
    demo_project.apply_table(table)
    designer = DatabaseDesignerWidget(demo_project)
    try:
        monkeypatch.setattr(RelationshipDialog, "exec", lambda self: RelationshipDialog.DialogCode.Accepted)
        monkeypatch.setattr(
            RelationshipDialog,
            "relationship",
            lambda self: (
                "ordini",
                ForeignKey(columns=["cliente"], ref_table="clienti", ref_columns=["codice"]),
            ),
        )
        designer.new_relationship()
        designer._refresh_schema()
        assert any(edge.child == "ordini" for edge in designer.graph.edges)
        artifact = demo_project.artifact("tables", "ordini")
        assert artifact is not None
        assert artifact["foreign_keys"][0]["ref_table"] == "clienti"
    finally:
        designer.close()


def test_delete_table(qapp, demo_project, monkeypatch) -> None:
    table = Table(name="temporanea", fields=[Field("id", T.INTEGER, pk=True)])
    demo_project.apply_table(table)
    designer = DatabaseDesignerWidget(demo_project)
    try:
        designer.selected_table = "temporanea"
        designer.canvas.selected_table = "temporanea"
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        designer.delete_table()
        designer._refresh_schema()
        assert demo_project.artifact("tables", "temporanea") is None
        assert "temporanea" not in designer.graph.nodes
    finally:
        designer.close()


def test_delete_relationship(qapp, demo_project, monkeypatch) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    try:
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )
        designer.selected_edge = designer.graph.edges[0]
        designer.canvas.selected_edge = designer.selected_edge
        designer.delete_relationship()
        designer._refresh_schema()
        assert designer.graph.edges == []
        artifact = demo_project.artifact("tables", "fatture")
        assert artifact is not None
        assert artifact["foreign_keys"] == []
    finally:
        designer.close()


def test_export_png_and_svg(qapp, demo_project, tmp_path, monkeypatch) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    png = tmp_path / "schema.png"
    svg = tmp_path / "schema.svg"
    try:
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kwargs: (str(png), "PNG (*.png)")),
        )
        designer.export_png()
        assert png.exists() and png.stat().st_size > 1000
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kwargs: (str(svg), "SVG (*.svg)")),
        )
        designer.export_svg()
        assert svg.exists() and svg.stat().st_size > 500
        assert "<svg" in svg.read_text(encoding="utf-8")
    finally:
        designer.close()


def test_main_window_opens_database_in_one_tab(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_database_designer()
        qapp.processEvents()
        tab = window.editors.find("database:designer")
        assert tab is not None
        assert isinstance(tab.widget(), DatabaseDesignerWidget)
        assert window.mode_label.text().endswith("Database")
        window.open_database_designer()
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
    finally:
        window.close()


def test_table_actions_emit_workspace_tabs(qapp, demo_project) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    opened: list[tuple[str, str]] = []
    designer.open_table.connect(lambda name, mode: opened.append((name, mode)))
    try:
        assert designer.table_list.count() == 2
        designer.select_table("clienti")
        designer.edit_table()
        designer.open_data_for_selected()
        assert opened == [("clienti", "edit"), ("clienti", "browse")]
    finally:
        designer.close()


def test_main_window_opens_structure_and_browse_from_database(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_database_designer()
        qapp.processEvents()
        database = window.editors.find("database:designer")
        assert database is not None
        designer = database.widget()
        designer.select_table("clienti")
        designer.edit_table()
        qapp.processEvents()
        structure = window.editors.find("structure:clienti")
        assert structure is not None
        assert structure.widget().dialog.embedded is True
        assert window.editors.find("database:designer") is not None
        designer.open_data_for_selected()
        qapp.processEvents()
        assert window.editors.find("tables:clienti") is not None
        assert len(window.editors.windows()) == 3
    finally:
        window.close()


def test_diagram_canvas_is_the_main_viewport(qapp, demo_project) -> None:
    designer = DatabaseDesignerWidget(demo_project)
    try:
        designer.resize(1180, 760)
        designer.show()
        qapp.processEvents()
        sizes = designer.splitter.sizes()
        assert sizes[1] > sizes[0] + sizes[2]
        assert sizes[1] / sum(sizes) > 0.6
        # Il pannello deve stare anche nell'area documenti di una finestra 1280.
        assert designer.minimumSizeHint().width() <= 900
    finally:
        designer.close()
