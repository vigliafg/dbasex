"""Test del Query Designer."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QMessageBox

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.query_model import QueryJoin, QuerySpec
from dbx.designers.query_builder import (
    JoinDialog,
    NewQueryDialog,
    QueryDesignerWidget,
)
from dbx.ui.main_window import MainWindow


def _designer(project, name: str = "fatture_clienti") -> QueryDesignerWidget:
    spec = QuerySpec.from_project(project, name)
    assert spec is not None
    return QueryDesignerWidget(project, spec)


def test_designer_loads_and_previews(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        assert designer.tree.topLevelItemCount() == 2
        assert designer.fields_table.rowCount() == 5
        assert designer.filters_table.rowCount() == 0
        sql = designer.sql_edit.toPlainText()
        assert 'INNER JOIN "clienti"' in sql
        assert 'ORDER BY "fatture"."numero" ASC' in sql
        result = designer.run_preview()
        assert result is not None
        assert len(result) == 5
        assert designer.result_table.rowCount() == 5
        assert designer.result_table.columnCount() == 5
        assert designer.result_label.text() == "5 righe"
        assert designer.is_dirty() is False
    finally:
        designer.close()


def test_add_remove_field_and_alias(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        designer.add_field("clienti", "citta")
        assert [item.ref for item in designer.spec.fields][-1] == "clienti.citta"
        assert designer.fields_table.rowCount() == 6
        assert designer.is_dirty() is True
        assert designer.run_preview() is not None
        assert designer.result_table.columnCount() == 6

        designer.fields_table.item(5, 1).setText("citta_cliente")
        assert designer.spec.fields[-1].alias == "citta_cliente"
        assert "citta_cliente" in designer.sql_edit.toPlainText()

        designer.fields_table.selectRow(5)
        designer.remove_selected_field()
        assert designer.fields_table.rowCount() == 5
        assert all(item.ref != "clienti.citta" for item in designer.spec.fields)
    finally:
        designer.close()


def test_filters_sorts_and_preview(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        designer.spec.sorts = []
        designer._refresh_sorts()
        designer.add_filter("fatture.importo", "gt", "1000")
        designer.add_sort("fatture.importo", "desc")
        assert designer.filters_table.rowCount() == 1
        assert designer.sorts_table.rowCount() == 1
        designer.sql_edit.clear()
        result = designer.run_preview()
        assert result is not None
        assert [row["numero"] for row in result.rows] == [3, 1]
        assert "WHERE" in designer.sql_edit.toPlainText()

        designer.move_sort(-1)
        assert designer.spec.sorts[0].field == "fatture.importo"
        assert designer.spec.sorts[0].direction == "desc"

        designer.filters_table.selectRow(0)
        designer.remove_selected_filter()
        assert designer.spec.filters == []
        designer.sorts_table.selectRow(0)
        designer.remove_selected_sort()
        assert designer.spec.sorts == []
    finally:
        designer.close()


def test_add_and_remove_join(qapp, demo_project, monkeypatch) -> None:
    citta = Table(
        name="citta",
        fields=[Field("nome", T.TEXT, size=30, pk=True), Field("provincia", T.TEXT, size=2)],
    )
    demo_project.apply_table(citta)
    designer = _designer(demo_project)
    try:
        join = QueryJoin("left", "citta", "clienti.citta", "citta.nome")
        monkeypatch.setattr(JoinDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
        monkeypatch.setattr(JoinDialog, "join", lambda self: join)
        designer.add_join()
        assert [item.table for item in designer.spec.joins] == ["clienti", "citta"]
        assert designer.tree.topLevelItemCount() == 3

        designer.add_field("citta", "provincia")
        assert designer.spec.fields[-1].ref == "citta.provincia"
        designer.tree.setCurrentItem(designer.tree.topLevelItem(2))
        designer.remove_selected_table()
        assert [item.table for item in designer.spec.joins] == ["clienti"]
        assert all(item.ref != "citta.provincia" for item in designer.spec.fields)
        assert designer.tree.topLevelItemCount() == 2
    finally:
        designer.close()


def test_join_dialog_suggests_foreign_key(qapp, demo_project) -> None:
    spec = QuerySpec.create(demo_project.require_table("clienti"), name="q")
    dialog = JoinDialog(demo_project, spec)
    try:
        assert dialog.table_combo.currentData() == "fatture"
        assert dialog.left_combo.currentData() == "clienti.codice"
        assert dialog.right_combo.currentData() == "cliente"
        join = dialog.join()
        assert join is not None
        assert join.left == "clienti.codice"
        assert join.right == "fatture.cliente"
        assert join.kind == "inner"
    finally:
        dialog.close()


def test_save_and_rename(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        designer.name_edit.setText("fatture_clienti_2")
        designer.caption_edit.setText("Fatture e clienti")
        designer._on_name_changed()
        assert designer.is_dirty() is True
        assert designer.save() is True
        assert designer.is_dirty() is False
        assert "fatture_clienti_2" in demo_project.names("queries")
        assert "fatture_clienti" not in demo_project.names("queries")
        artifact = demo_project.artifact("queries", "fatture_clienti_2")
        assert artifact is not None
        assert artifact["name"] == "fatture_clienti_2"
        assert artifact["caption"] == "Fatture e clienti"
    finally:
        designer.close()


def test_invalid_save_is_blocked(qapp, demo_project, monkeypatch) -> None:
    designer = _designer(demo_project)
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: warnings.append(str(args[2]))
    )
    try:
        designer.spec.fields = []
        assert designer.save() is False
        assert warnings and "seleziona alcun campo" in warnings[0]
    finally:
        designer.close()


def test_new_query_dialog(qapp, demo_project, monkeypatch) -> None:
    dialog = NewQueryDialog(demo_project, suggested_name="query_clienti")
    try:
        assert dialog.name_edit.text() == "query_clienti"
        dialog.caption_edit.setText("Clienti")
        dialog.table_combo.setCurrentIndex(dialog.table_combo.findData("clienti"))
        spec = dialog.spec()
        assert spec.name == "query_clienti"
        assert spec.base == "clienti"
        assert spec.validate(demo_project.tables()) == []
    finally:
        dialog.close()

    empty = NewQueryDialog(demo_project)
    warnings: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args, **kwargs: warnings.append(str(args[2]))
    )
    try:
        empty.accept()
        assert warnings and "nome" in warnings[0].lower()
    finally:
        empty.close()


def test_main_window_opens_query_designer(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("queries", "fatture_clienti")
        qapp.processEvents()
        sub = window.editors.find("queries:fatture_clienti")
        assert sub is not None
        assert isinstance(sub.widget(), QueryDesignerWidget)
        assert window.mode_label.text().endswith("Query")
        window.open_object("queries", "fatture_clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
    finally:
        window.close()


def test_main_window_creates_query_from_dialog(qapp, demo_project, monkeypatch) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        spec = QuerySpec.create(demo_project.require_table("fatture"), name="query_nuova")
        monkeypatch.setattr(NewQueryDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
        monkeypatch.setattr(NewQueryDialog, "spec", lambda self: spec)
        window.new_object("queries")
        qapp.processEvents()
        assert demo_project.artifact("queries", "query_nuova") is not None
        sub = window.editors.find("queries:query_nuova")
        assert sub is not None
        assert isinstance(sub.widget(), QueryDesignerWidget)
    finally:
        window.close()
