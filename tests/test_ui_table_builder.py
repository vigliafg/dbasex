"""Test della finestra Table Structure."""

from __future__ import annotations

from unittest import mock

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QAbstractItemView, QDialog

from dbx.core import types as T
from dbx.core.metadata import Field
from dbx.designers.table_builder import (
    COL_INDEX,
    COL_NAME,
    FIELD_COLUMNS,
    TableBuilderDialog,
)
from dbx.ui.data_view import DataView
from dbx.ui.main_window import MainWindow


def test_table_structure_columns_and_identity(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        assert FIELD_COLUMNS == ["Field", "Name", "Type", "Width", "Decimal", "Index"]
        assert dialog.fields_grid.columnCount() == 6
        assert dialog.fields_grid.rowCount() == len(table.fields)
        assert dialog.fields_grid.verticalHeader().isHidden()
        assert dialog.current_table().to_dict() == table.to_dict()
        assert dialog.updated_label.text().startswith("Updated:")
        assert "Records: 3" in dialog.records_label.text()
        assert dialog.bytes_label.text().startswith("Bytes Used:")
    finally:
        dialog.close()


def test_table_structure_identity_with_decimal_and_relations(qapp, demo_project) -> None:
    table = demo_project.require_table("fatture")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        assert dialog.current_table().to_dict() == table.to_dict()
        names = ["numero", "cliente", "data", "descrizione", "importo", "pagata"]
        row = names.index("cliente")
        item = dialog.fields_grid.item(row, COL_INDEX)
        assert item.data(Qt.ItemDataRole.UserRole) == "idx_fatture_cliente"
    finally:
        dialog.close()


def test_table_structure_reorders_fields_without_losing_ids(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        ids = [field.id for field in dialog.current_table().fields]
        dialog._move_field_to(0, 2)
        reordered = [field.id for field in dialog.current_table().fields]
        assert reordered[:3] == [ids[1], ids[2], ids[0]]
        displayed = [
            dialog.fields_grid.item(row, COL_NAME).text() for row in range(3)
        ]
        assert displayed == ["nome", "citta", "codice"]
    finally:
        dialog.close()


def test_table_structure_add_and_remove_field(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        before = dialog.fields_grid.rowCount()
        dialog._add_field_row(Field("extra", T.TEXT))
        assert dialog.fields_grid.rowCount() == before + 1
        assert dialog.current_table().fields[-1].name == "extra"
        dialog.fields_grid.setCurrentCell(before, COL_NAME)
        dialog._remove_field_row()
        assert dialog.fields_grid.rowCount() == before
        assert all(field.name != "extra" for field in dialog.current_table().fields)
    finally:
        dialog.close()


def test_table_structure_tab_on_last_cell_adds_field(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        before = dialog.fields_grid.rowCount()
        dialog.fields_grid.setCurrentCell(before - 1, COL_INDEX)
        QTest.keyClick(dialog.fields_grid, Qt.Key.Key_Tab)
        assert dialog.fields_grid.rowCount() == before + 1
        assert dialog.fields_grid.currentRow() == before
        assert dialog.fields_grid.currentColumn() == COL_NAME
    finally:
        dialog.close()


def test_table_structure_active_row_is_double_height(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        dialog.fields_grid.setCurrentCell(0, COL_NAME)
        first = dialog.fields_grid.rowHeight(0)
        second = dialog.fields_grid.rowHeight(1)
        assert first > second
    finally:
        dialog.close()


def test_table_structure_renames_propagate_to_indexes_and_relations(qapp, demo_project) -> None:
    table = demo_project.require_table("fatture")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        names = [field.name for field in table.fields]
        row = names.index("cliente")
        dialog.fields_grid.item(row, COL_NAME).setText("cliente_codice")
        result = dialog.current_table()
        assert result.fields[row].name == "cliente_codice"
        assert any("cliente_codice" in index.fields for index in result.indexes)
        assert result.foreign_keys
        assert result.foreign_keys[0].columns == ["cliente_codice"]
        assert result.foreign_keys[0].ref_columns == ["codice"]
    finally:
        dialog.close()


def test_table_structure_index_column_uses_advanced_model(qapp, demo_project) -> None:
    table = demo_project.require_table("fatture")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        from PyQt6.QtWidgets import QTableWidgetItem

        dialog.index_grid.insertRow(0)
        dialog.index_grid.setItem(0, 0, QTableWidgetItem("mio_indice"))
        dialog.index_grid.setItem(0, 1, QTableWidgetItem("descrizione"))
        unique = QTableWidgetItem()
        unique.setFlags(unique.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        unique.setCheckState(Qt.CheckState.Unchecked)
        dialog.index_grid.setItem(0, 2, unique)
        choices = dict(dialog._index_choices())
        assert "mio_indice" in choices
        names = [field.name for field in table.fields]
        row = names.index("pagata")
        item = dialog.fields_grid.item(row, COL_INDEX)
        item.setText("mio_indice")
        item.setData(Qt.ItemDataRole.UserRole, "mio_indice")
        result = dialog.current_table()
        assert any(index.name == "mio_indice" for index in result.indexes)
    finally:
        dialog.close()


def test_table_structure_extended_field_properties(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        row = 1
        dialog.fields_grid.setCurrentCell(row, COL_NAME)
        dialog.field_caption_edit.setText("Nome completo")
        dialog.required_check.setChecked(True)
        dialog.default_edit.setText("Cliente")
        dialog.fmt_edit.setText("")
        dialog.lookup_edit.setText("")
        field = dialog.current_table().fields[row]
        assert field.caption == "Nome completo"
        assert field.required is True
        assert field.default == "Cliente"
        assert field.pk is False
        first = dialog.current_table().fields[0]
        assert first.pk is True, "la chiave primaria deve essere preservata"
    finally:
        dialog.close()


def test_table_structure_exclusive_toggle(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        assert dialog.exclusive_button.isChecked()
        dialog.exclusive_button.click()
        assert dialog.fields_grid.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
        assert dialog.apply_button.isEnabled() is False
        dialog.exclusive_button.click()
        assert dialog.apply_button.isEnabled() is True
    finally:
        dialog.close()


def test_table_structure_add_records(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        added = dialog.add_records(2)
        assert added == 2
        rows = demo_project.db.query('SELECT COUNT(*) AS n FROM "clienti"')[0]
        assert int(rows["n"]) == 5
        assert "Records: 5" in dialog.records_label.text()
    finally:
        dialog.close()


def test_table_structure_save_as_creates_copy(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        copy = dialog.save_as("clienti_copia", "Copia clienti")
        assert copy is not None
        assert copy.name == "clienti_copia"
        created = demo_project.table("clienti_copia")
        assert created is not None
        assert created.caption == "Copia clienti"
        assert [field.name for field in created.fields] == [
            field.name for field in table.fields
        ]
    finally:
        dialog.close()


def test_browse_requests_structure_instead_of_modal(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    requested: list[str] = []
    view.structure_requested.connect(requested.append)
    try:
        view.edit_structure()
        assert requested == ["clienti"]
    finally:
        view.deleteLater()


def test_structure_roundtrip_updates_open_browse(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("tables", "clienti")
        qapp.processEvents()
        view = window.editors.current_editor()
        assert isinstance(view, DataView)
        before = view.grid.columnCount()
        view.edit_structure()
        qapp.processEvents()
        tab = window.editors.find("database:designer")
        assert tab is not None
        designer = tab.widget()
        assert designer.selected_table == "clienti"

        def apply_extra(dialog):
            dialog._add_field_row(Field("extra", T.TEXT))
            dialog._apply()
            return QDialog.DialogCode.Accepted

        with mock.patch.object(TableBuilderDialog, "exec", apply_extra):
            designer.edit_table_by_name("clienti")
        qapp.processEvents()
        assert view.grid.columnCount() == before + 1
        assert view.table.field("extra") is not None
    finally:
        window.close()
