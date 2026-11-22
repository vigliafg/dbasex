"""Test del Menu Designer (O6)."""

from __future__ import annotations

from dbx.designers.menu_builder import MenuBuilderDialog, MenuBuilderWidget
from dbx.ui.main_window import MainWindow


def _artifact(demo_project):
    artifact = demo_project.artifact("menus", "principale")
    assert artifact is not None
    return artifact


def _preview_labels(editor: MenuBuilderWidget) -> list[str]:
    menu = editor.preview_bar.actions()[0].menu()
    return [action.text() for action in menu.actions()]


def test_menu_builder_basics(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        assert editor.tree.topLevelItemCount() == len(editor.items)
        assert editor.label_edit.isEnabled()
        assert editor.action_combo.count() == len(
            {"open_form", "open_report", "run_script", "separator", "quit"}
        )
        labels = _preview_labels(editor)
        assert "Clienti" in labels
        assert editor.is_dirty() is False
    finally:
        editor.close()


def test_add_item_and_separator(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        before = len(editor.items)
        editor.add_item()
        assert len(editor.items) == before + 1
        assert editor.tree.topLevelItemCount() == before + 1
        editor.add_separator()
        assert editor.items[-1]["action"] == "separator"
        assert "— separatore —" == editor.tree.topLevelItem(editor.tree.topLevelItemCount() - 1).text(0)
        labels = _preview_labels(editor)
        assert labels[-1] == ""  # separatore
    finally:
        editor.close()


def test_edit_label_updates_tree_and_preview(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        editor.label_edit.setText("Elenco clienti")
        editor._on_property_edited("Elenco clienti")
        assert editor.items[0]["label"] == "Elenco clienti"
        assert editor.tree.topLevelItem(0).text(0) == "Elenco clienti"
        assert "Elenco clienti" in _preview_labels(editor)
    finally:
        editor.close()


def test_typed_action_switches_target_list(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        index = editor.action_combo.findData("run_script")
        editor.action_combo.setCurrentIndex(index)
        assert editor.items[0]["action"] == "run_script"
        targets = [editor.target_combo.itemText(i) for i in range(editor.target_combo.count())]
        assert "riepilogo_fatture" in targets
        editor.target_combo.setCurrentText("riepilogo_fatture")
        assert editor.items[0]["target"] == "riepilogo_fatture"
        index = editor.action_combo.findData("quit")
        editor.action_combo.setCurrentIndex(index)
        assert not editor.target_combo.isEnabled()
    finally:
        editor.close()


def test_move_and_remove(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        first = editor.items[0]["label"]
        second = editor.items[1]["label"]
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        editor.move_item(1)
        assert editor.items[0]["label"] == second
        assert editor.items[1]["label"] == first
        editor.tree.setCurrentItem(editor.tree.topLevelItem(0))
        before = len(editor.items)
        editor.remove_item()
        assert len(editor.items) == before - 1
    finally:
        editor.close()


def test_save_roundtrip(qapp, demo_project) -> None:
    editor = MenuBuilderWidget(demo_project, _artifact(demo_project))
    try:
        editor.add_separator()
        assert editor.is_dirty() is True
        assert editor.save() is True
        assert editor.is_dirty() is False
        artifact = demo_project.artifact("menus", editor.name)
        assert artifact is not None
        assert artifact["items"][-1]["action"] == "separator"
        reopened = MenuBuilderWidget(demo_project, artifact)
        try:
            assert reopened.items == editor.items
        finally:
            reopened.close()
    finally:
        editor.close()


def test_main_window_opens_menu_designer_in_mdi(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("menus", "principale")
        qapp.processEvents()
        sub = window.editors.find("menus:principale")
        assert sub is not None
        assert isinstance(sub.widget(), MenuBuilderWidget)
        assert window.mode_label.text().endswith("Design")
    finally:
        window.close()


def test_alias_keeps_legacy_name(qapp, demo_project) -> None:
    assert MenuBuilderDialog is MenuBuilderWidget
    legacy = MenuBuilderDialog(demo_project, _artifact(demo_project))
    try:
        assert legacy.tree.topLevelItemCount() > 0
    finally:
        legacy.close()
