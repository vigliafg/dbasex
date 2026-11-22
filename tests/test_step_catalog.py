"""Test del catalogo azioni e dello Step Picker (0.4/O5)."""

from __future__ import annotations

from dbx.designers.script_builder import ScriptBuilderWidget
from dbx.designers.step_picker import StepPickerDialog
from dbx.runtime.script_engine import (
    ACTIONS,
    ACTION_CATEGORIES,
    actions_by_category,
)


def test_every_action_has_category_and_description() -> None:
    assert ACTIONS
    for key, definition in ACTIONS.items():
        assert definition["label"], key
        assert definition["category"] in ACTION_CATEGORIES, key
        assert definition["description"].strip(), key
        for param in definition["params"]:
            assert len(param) == 3, key
            assert param[1] and param[2]


def test_actions_by_category_covers_every_action_once() -> None:
    grouped = actions_by_category()
    listed = [key for keys in grouped.values() for key in keys]
    assert sorted(listed) == sorted(ACTIONS)
    assert len(listed) == len(set(listed))
    assert all(grouped[name] for name in grouped)


def test_step_picker_lists_categories_and_actions(qapp) -> None:
    dialog = StepPickerDialog()
    try:
        assert dialog.tree.topLevelItemCount() == len(actions_by_category())
        dialog.select_action("export_csv")
        assert dialog.selected_action() == "export_csv"
        assert "Esporta CSV" in dialog.description_label.text()
        assert "Stampa/File" in dialog.description_label.text()
        assert dialog.ok_button is not None and dialog.ok_button.isEnabled()
    finally:
        dialog.close()


def test_step_picker_filter(qapp) -> None:
    dialog = StepPickerDialog()
    try:
        dialog.filter_edit.setText("csv")
        visible = [
            item.text(0)
            for item in dialog._all_action_items()
            if not item.isHidden()
        ]
        assert visible == ["Esporta CSV"]
        dialog.filter_edit.clear()
        assert all(not item.isHidden() for item in dialog._all_action_items())
    finally:
        dialog.close()


def test_inspector_shows_category_and_description(qapp, demo_project) -> None:
    artifact = demo_project.artifact("scripts", "riepilogo_fatture")
    assert artifact is not None
    editor = ScriptBuilderWidget(demo_project, artifact)
    try:
        first = editor.tree.topLevelItem(0)
        assert first is not None
        editor.tree.setCurrentItem(first)
        category = editor.inspector.item("category")
        description = editor.inspector.item("description")
        assert category is not None
        assert description is not None
        assert category.text(1)
        assert description.text(1)
    finally:
        editor.close()
