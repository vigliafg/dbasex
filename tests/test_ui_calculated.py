"""Test UI dei campi calcolati e automatici (0.7 O4)."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.core import types as T
from dbx.core.metadata import Field


def test_table_builder_creates_calculated_field(qapp, demo_project):
    from dbx.designers.table_builder import TableBuilderDialog

    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    dialog._add_field_row(Field("nome_maiuscolo", T.TEXT))
    dialog.calculated_edit.setText("UPPER([nome])")
    dialog._apply()
    updated = demo_project.require_table("clienti")
    field = updated.field("nome_maiuscolo")
    assert field is not None and field.calculated == "UPPER([nome])"
    assert field.stored is False
    columns = [row["name"] for row in demo_project.db.query("PRAGMA table_info('clienti')")]
    assert "nome_maiuscolo" not in columns
    dialog.close()


def test_table_builder_creates_auto_fields(qapp, demo_project):
    from dbx.designers.table_builder import TableBuilderDialog

    table = demo_project.require_table("fatture")
    dialog = TableBuilderDialog(demo_project, table)
    dialog._add_field_row(Field("progressivo", T.INTEGER))
    dialog.auto_serial_check.setChecked(True)
    dialog._store_field_meta()
    dialog._add_field_row(Field("inserita", T.DATE))
    dialog.auto_date_combo.setCurrentIndex(dialog.auto_date_combo.findData("insert"))
    dialog._store_field_meta()
    dialog._apply()
    updated = demo_project.require_table("fatture")
    assert updated.field("progressivo").auto_serial is True
    assert updated.field("inserita").auto_date == "insert"
    dialog.close()


def test_data_view_shows_calculated_values_read_only(qapp, demo_project):
    from dbx.ui.data_view import DataView

    table = demo_project.require_table("clienti")
    table.fields.append(Field("nome_breve", T.TEXT, calculated="LEFT([nome], 3)"))
    demo_project.apply_table(table)
    view = DataView(demo_project, "clienti")
    column = [field.name for field in view.table.fields].index("nome_breve")
    first = view.grid.item(0, column)
    assert first is not None
    assert first.text()
    assert not bool(first.flags() & Qt.ItemFlag.ItemIsEditable)
    view.deleteLater()


def test_record_dialog_skips_calculated_fields(qapp, demo_project):
    from dbx.ui.data_view import RecordDialog

    table = demo_project.require_table("clienti")
    table.fields.append(Field("doppio_nome", T.TEXT, calculated="[nome] + [nome]"))
    dialog = RecordDialog(table)
    assert "doppio_nome" not in dialog.editors
    assert "nome" in dialog.editors
    dialog.close()
