"""Test UI offscreen di Scelta, gruppi del Table Builder ed errori validazione."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox

from dbx.core import types as T
from dbx.core.form_model import FormControl, FormPage, FormSpec
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.designers.table_builder import COL_TYPE, TableBuilderDialog
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.rowset import Rowset
from dbx.ui.data_view import CHOICE_ROLE, DataView, RecordDialog


def make_project(tmp_path, name="Validazione") -> Project:
    project = Project.create(tmp_path / name, name)
    table = Table(
        name="clienti",
        fields=[
            Field("nome", T.TEXT),
            Field(
                "stato",
                T.CHOICE,
                choices=[
                    {"value": "A", "label": "Attivo"},
                    {"value": "S", "label": "Sospeso"},
                ],
            ),
        ],
    )
    project.apply_table(table)
    rowset = Rowset(project.db, table)
    rowset.insert({"nome": "Ada", "stato": "A"})
    rowset.insert({"nome": "Bob", "stato": "S"})
    return project


def test_table_builder_choice_group_follows_type(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        state_row = [f.name for f in table.fields].index("stato")
        dialog.fields_grid.setCurrentCell(state_row, COL_TYPE)
        dialog._load_field_meta(state_row)
        assert dialog.choice_group.isEnabled()
        name_row = [f.name for f in table.fields].index("nome")
        dialog.fields_grid.setCurrentCell(name_row, COL_TYPE)
        dialog._load_field_meta(name_row)
        assert not dialog.choice_group.isEnabled()
    finally:
        dialog.close()


def test_table_builder_choice_metadata_survives_roundtrip(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        state_row = [f.name for f in table.fields].index("stato")
        dialog.fields_grid.setCurrentCell(state_row, COL_TYPE)
        dialog._load_field_meta(state_row)
        dialog._add_choice_row("X", "Extra")
        updated = dialog.current_table()
        field = updated.field("stato")
        assert {"value": "X", "label": "Extra"} in field.choices
        clone = Table.from_dict(updated.to_dict())
        assert clone.field("stato").choices == field.choices
    finally:
        dialog.close()


def test_data_view_choice_shows_label_and_saves_value(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    view = DataView(project, "clienti")
    try:
        column = [f.name for f in view.table.fields].index("stato")
        item = view.grid.item(0, column)
        assert item.text() == "Attivo"
        assert item.data(CHOICE_ROLE) == "A"
        item.setText("Sospeso")
        item.setData(CHOICE_ROLE, "S")
        assert view.rowset.rows()[0]["stato"] == "S"
    finally:
        view.close()


def test_record_dialog_choice_maps_label_to_value(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = RecordDialog(table, db=project.db)
    try:
        combo = dialog.editors["stato"]
        assert isinstance(combo, QComboBox)
        assert [combo.itemText(index) for index in range(combo.count())] == [
            "",
            "Attivo",
            "Sospeso",
        ]
        combo.setCurrentIndex(combo.findData("S"))
        assert dialog.values()["stato"] == "S"
    finally:
        dialog.close()


def test_form_runtime_choice_uses_combo_and_saves_value(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    spec = FormSpec(
        name="scelta_form",
        caption="Scelta",
        table="clienti",
        width=420,
        height=240,
        pages=[
            FormPage(
                controls=[
                    FormControl(id="f1", kind="field", field="stato", x=8, y=8, w=160, h=22),
                ]
            )
        ],
    )
    runtime = FormRuntime(project, spec)
    try:
        binder = runtime.binders[0]
        assert isinstance(binder.widget, QComboBox)
        assert binder.widget.currentText() == "Attivo"
        binder.widget.setCurrentIndex(binder.widget.findData("S"))
        assert runtime.save() is True
        assert runtime.rowset.current["stato"] == "S"
    finally:
        runtime.close()
