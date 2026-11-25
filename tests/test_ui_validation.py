"""Test UI offscreen di Scelta, gruppi del Table Builder ed errori validazione."""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QComboBox

from dbx.core import types as T
from dbx.core.form_model import FormControl, FormPage, FormSpec
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.designers.table_builder import COL_TYPE, TableBuilderDialog
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.rowset import Rowset
from dbx.runtime.validation import ValidationError
from dbx.ui.data_view import (
    CHOICE_ROLE,
    DataView,
    InputCellDelegate,
    RecordDialog,
)
from dbx.ui.input_editors import MaskValidator


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
            Field("quantita", T.INTEGER),
            Field("sconto", T.DECIMAL),
            Field("targa", T.TEXT, size=6, mask="AA 999", case_mode="upper"),
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


def test_table_builder_domain_group_follows_type(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        for name, enabled in (
            ("quantita", True),
            ("sconto", True),
            ("nome", False),
            ("stato", False),
        ):
            row = [f.name for f in table.fields].index(name)
            dialog.fields_grid.setCurrentCell(row, COL_TYPE)
            dialog._load_field_meta(row)
            assert dialog.domain_group.isEnabled() is enabled
    finally:
        dialog.close()


def test_table_builder_domain_metadata_survives_roundtrip(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        row = [f.name for f in table.fields].index("sconto")
        dialog.fields_grid.setCurrentCell(row, COL_TYPE)
        dialog._load_field_meta(row)
        dialog.domain_mode_combo.setCurrentIndex(
            dialog.domain_mode_combo.findData("range")
        )
        dialog.domain_min_edit.setText("0")
        dialog.domain_max_edit.setText("50")
        dialog.domain_message_edit.setText("Sconto tra 0 e 50")
        updated = dialog.current_table()
        field = updated.field("sconto")
        assert (field.domain_min, field.domain_max) == ("0", "50")
        assert field.domain_message == "Sconto tra 0 e 50"
        clone = Table.from_dict(updated.to_dict())
        assert clone.field("sconto").domain_max == "50"

        row = [f.name for f in updated.fields].index("quantita")
        dialog.fields_grid.setCurrentCell(row, COL_TYPE)
        dialog._load_field_meta(row)
        dialog.domain_mode_combo.setCurrentIndex(
            dialog.domain_mode_combo.findData("ranges")
        )
        dialog._add_domain_range("1", "10")
        dialog._add_domain_range("20", "30")
        middle = dialog.current_table().field("quantita")
        assert middle.domain_ranges == [["1", "10"], ["20", "30"]]
        assert middle.domain_min == "" and middle.domain_max == ""
    finally:
        dialog.close()


def test_record_dialog_reports_domain_issue(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    field = table.field("sconto")
    field.domain_min = "0"
    field.domain_max = "50"
    rowset = Rowset(project.db, table)
    dialog = RecordDialog(table, db=project.db, validator=rowset.check_insert)
    try:
        dialog.editors["sconto"].setText("51")
        with pytest.raises(ValidationError) as exc:
            rowset.check_insert(dialog.values())
        assert [issue.code for issue in exc.value.issues] == ["domain"]
        dialog.apply_issues(exc.value.issues)
        assert dialog.editors["sconto"].property("state") == "error"
    finally:
        dialog.close()


def test_table_builder_input_rules_follow_text_type(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        for name, enabled in (
            ("nome", True),
            ("targa", True),
            ("stato", False),
            ("quantita", False),
        ):
            row = [f.name for f in table.fields].index(name)
            dialog.fields_grid.setCurrentCell(row, COL_TYPE)
            dialog._load_field_meta(row)
            assert dialog.mask_edit.isEnabled() is enabled
            assert dialog.case_mode_combo.isEnabled() is enabled
        row = [f.name for f in table.fields].index("targa")
        dialog.fields_grid.setCurrentCell(row, COL_TYPE)
        dialog._load_field_meta(row)
        assert dialog.mask_edit.text() == "AA 999"
        assert dialog.case_mode_combo.currentData() == "upper"
    finally:
        dialog.close()


def test_table_builder_input_rules_survive_roundtrip(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    table = project.require_table("clienti")
    dialog = TableBuilderDialog(project, table)
    try:
        row = [f.name for f in table.fields].index("targa")
        dialog.fields_grid.setCurrentCell(row, COL_TYPE)
        dialog._load_field_meta(row)
        dialog.mask_edit.setText("999 AAA")
        dialog.case_mode_combo.setCurrentIndex(
            dialog.case_mode_combo.findData("lower")
        )
        updated = dialog.current_table()
        field = updated.field("targa")
        assert field.mask == "999 AAA"
        assert field.case_mode == "lower"
        assert Table.from_dict(updated.to_dict()).field("targa").mask == "999 AAA"
    finally:
        dialog.close()


def test_data_view_masked_delegate_shapes_value(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    view = DataView(project, "clienti")
    try:
        column = [f.name for f in view.table.fields].index("targa")
        delegate = view.grid.itemDelegateForColumn(column)
        assert isinstance(delegate, InputCellDelegate)
        model = view.grid.model()
        index = model.index(0, column)
        editor = delegate.createEditor(view.grid.viewport(), None, index)
        validator = editor.validator()
        assert isinstance(validator, MaskValidator)
        assert validator.validate("a1 123", 0)[0] == validator.State.Invalid
        assert validator.validate("ab 123", 0)[0] == validator.State.Acceptable
        editor.setText("ab 123")
        delegate.setModelData(editor, model, index)
        assert view.rowset.rows()[0]["targa"] == "AB 123"
    finally:
        view.close()


def test_form_runtime_applies_input_rules(qapp, tmp_path) -> None:
    project = make_project(tmp_path)
    spec = FormSpec(
        name="input_form",
        caption="Input",
        table="clienti",
        width=420,
        height=240,
        pages=[
            FormPage(
                controls=[
                    FormControl(id="f1", kind="field", field="targa", x=8, y=8, w=160, h=22),
                ]
            )
        ],
    )
    runtime = FormRuntime(project, spec)
    try:
        binder = runtime.binders[0]
        binder.widget.setText("ab 123")
        assert binder.widget.text() == "AB 123"
        assert binder.get_value() == "AB 123"
        assert runtime.save() is True
        assert runtime.rowset.current["targa"] == "AB 123"
    finally:
        runtime.close()
