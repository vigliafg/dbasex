"""Test del Program Editor MiniScript (O6)."""

from __future__ import annotations


from dbx.designers.script_builder import (
    ActionDialog,
    CodeEditor,
    ScriptBuilderDialog,
    ScriptBuilderWidget,
    ScriptHighlighter,
)
from dbx.runtime.script_engine import to_text
from dbx.ui.main_window import MainWindow


def _artifact(demo_project):
    artifact = demo_project.artifact("scripts", "riepilogo_fatture")
    assert artifact is not None
    return artifact


def test_program_editor_basics(qapp, demo_project) -> None:
    editor = ScriptBuilderWidget(demo_project, _artifact(demo_project))
    try:
        assert isinstance(editor.text_view, CodeEditor)
        assert editor.text_view.line_number_area is not None
        assert editor.text_view.line_number_area.width() >= 0
        assert isinstance(editor.text_view.highlighter, ScriptHighlighter)
        assert editor.tree.topLevelItemCount() > 0
        assert "MESSAGE" in editor.text_view.toPlainText().upper()
        assert editor.count_label.text().endswith("azioni")
        assert editor.is_dirty() is False
        assert editor.inspector.item("steps") is not None
    finally:
        editor.close()


def test_source_to_actions_roundtrip(qapp, demo_project) -> None:
    editor = ScriptBuilderWidget(demo_project, {"name": "prova", "steps": []})
    try:
        editor.text_view.setPlainText('MESSAGE "Ciao"\nSTATUS "Pronto"')
        assert editor._source_dirty is True
        editor.apply_text()
        assert len(editor.steps) == 2
        assert editor.steps[0]["action"] == "message"
        assert editor.steps[0]["params"]["text"] == "Ciao"
        assert editor.tree.topLevelItemCount() == 2
        assert 'MESSAGE "Ciao"' in editor.text_view.toPlainText()
        assert editor._source_dirty is False
    finally:
        editor.close()


def test_invalid_source_is_rejected(qapp, demo_project, monkeypatch) -> None:
    from PyQt6.QtWidgets import QMessageBox

    messages: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: messages.append("warning"))
    editor = ScriptBuilderWidget(demo_project, {"name": "prova", "steps": []})
    try:
        editor.text_view.setPlainText("SCONOSCIUTO qualcosa")
        editor.apply_text()
        assert messages
        assert editor.steps == []
    finally:
        editor.close()


def test_add_action_updates_tree_and_source(qapp, demo_project, monkeypatch) -> None:
    from PyQt6.QtWidgets import QDialog

    from dbx.designers.step_picker import StepPickerDialog

    monkeypatch.setattr(StepPickerDialog, "exec", lambda self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr(StepPickerDialog, "selected_action", lambda self: "message")
    monkeypatch.setattr(ActionDialog, "exec", lambda self: ActionDialog.DialogCode.Accepted)
    monkeypatch.setattr(ActionDialog, "params", lambda self: {"text": "ciao"})
    editor = ScriptBuilderWidget(demo_project, {"name": "prova", "steps": []})
    try:
        editor.add_action()
        assert len(editor.steps) == 1
        assert editor.steps[0]["params"]["text"] == "ciao"
        assert 'MESSAGE "ciao"' in editor.text_view.toPlainText()
        assert editor.tree.topLevelItem(0).text(0) == "Messaggio"
    finally:
        editor.close()


def test_move_and_remove_action(qapp, demo_project) -> None:
    steps = [
        {"action": "message", "params": {"text": "uno"}},
        {"action": "message", "params": {"text": "due"}},
    ]
    editor = ScriptBuilderWidget(demo_project, {"name": "prova", "steps": steps})
    try:
        assert editor.tree.topLevelItemCount() == 2
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        editor.move_action(1)
        assert editor.steps[0]["params"]["text"] == "due"
        assert editor.steps[1]["params"]["text"] == "uno"
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        editor.remove_action()
        assert len(editor.steps) == 1
    finally:
        editor.close()


def test_inspector_edits_parameter(qapp, demo_project) -> None:
    editor = ScriptBuilderWidget(
        demo_project,
        {"name": "prova", "steps": [{"action": "message", "params": {"text": "prima"}}]},
    )
    try:
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        item = editor.inspector.item("param:text")
        assert item is not None
        item.setText(1, "dopo")
        assert editor.steps[0]["params"]["text"] == "dopo"
        assert 'MESSAGE "dopo"' in editor.text_view.toPlainText()
    finally:
        editor.close()


def test_run_script_logs_without_dialogs(qapp, demo_project) -> None:
    editor = ScriptBuilderWidget(
        demo_project,
        {
            "name": "prova",
            "steps": [
                {"action": "set", "params": {"variable": "totale", "expr": "2 + 2"}},
            ],
        },
    )
    try:
        editor.run_script()
        assert ":totale = 4" in editor.log.toPlainText()
    finally:
        editor.close()


def test_save_roundtrip_and_dirty(qapp, demo_project) -> None:
    editor = ScriptBuilderWidget(demo_project, _artifact(demo_project))
    try:
        editor.steps = [{"action": "message", "params": {"text": "salvato"}}]
        editor.refresh_text()
        assert editor.is_dirty() is True
        assert editor.save() is True
        assert editor.is_dirty() is False
        artifact = demo_project.artifact("scripts", editor.name)
        assert artifact is not None
        assert artifact["steps"] == [{"action": "message", "params": {"text": "salvato"}}]
        reopened = ScriptBuilderWidget(demo_project, artifact)
        try:
            assert reopened.steps == editor.steps
            assert to_text(reopened.steps) == editor.text_view.toPlainText()
        finally:
            reopened.close()
    finally:
        editor.close()


def test_main_window_opens_program_editor_in_mdi(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("scripts", "riepilogo_fatture")
        qapp.processEvents()
        sub = window.editors.find("scripts:riepilogo_fatture")
        assert sub is not None
        assert isinstance(sub.widget(), ScriptBuilderWidget)
        assert window.mode_label.text().endswith("Modifica")
    finally:
        window.close()


def test_alias_keeps_legacy_name(qapp, demo_project) -> None:
    assert ScriptBuilderDialog is ScriptBuilderWidget
    legacy = ScriptBuilderDialog(demo_project, _artifact(demo_project))
    try:
        assert legacy.tree.topLevelItemCount() > 0
    finally:
        legacy.close()
