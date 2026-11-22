"""Test del Project Editor (O6)."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.designers.project_builder import ProjectEditorWidget
from dbx.ui.main_window import MainWindow


def test_project_editor_tree_and_settings(qapp, demo_project) -> None:
    editor = ProjectEditorWidget(demo_project)
    opened: list[tuple[str, str]] = []
    editor.open_object.connect(lambda category, name: opened.append((category, name)))
    try:
        assert editor.tree.topLevelItemCount() == 6
        root = editor.tree.topLevelItem(0)
        child = root.child(0)
        editor._activate(child, 0)
        assert opened and opened[0][1]
        assert editor.form_combo.count() > 1
        assert editor.menu_combo.count() > 1
        assert "Nessun problema" in editor.validation.toPlainText()
        editor.title_edit.setText("Titolo di prova")
        assert editor.is_dirty() is True
        editor.save_settings()
        assert demo_project.settings["title"] == "Titolo di prova"
        assert editor.is_dirty() is False
        assert editor.status_label.text() == "Impostazioni salvate"
    finally:
        editor.close()


def test_project_editor_validation_lists_errors(qapp, demo_project) -> None:
    demo_project.settings["main_form"] = "form_inesistente"
    editor = ProjectEditorWidget(demo_project)
    try:
        errors = editor.validate_now()
        assert errors
        assert "inesistente" in editor.validation.toPlainText().lower()
    finally:
        demo_project.settings["main_form"] = "form_clienti"
        editor.close()


def test_project_editor_build(qapp, demo_project, tmp_path) -> None:
    editor = ProjectEditorWidget(demo_project)
    try:
        editor.destination_edit.setText(str(tmp_path / "dist"))
        target = editor.build()
        assert target is not None
        assert target.exists()
        assert target.suffix == ".zip"
        assert "Build creata" in editor.status_label.text()
    finally:
        editor.close()


def test_main_window_opens_project_editor(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.act_project.trigger()
        qapp.processEvents()
        sub = window.editors.find("project:editor")
        assert sub is not None
        assert isinstance(sub.widget(), ProjectEditorWidget)
        assert window.mode_label.text().endswith("Progetto")
        labels = [action.text() for action in window.menuBar().actions()]
        assert "&Progetto" in labels
    finally:
        window.close()


def test_project_editor_header_shows_path(qapp, demo_project) -> None:
    editor = ProjectEditorWidget(demo_project)
    try:
        assert str(demo_project.path) in editor.path_label.text()
        assert editor.status_label is not None
        item = editor.tree.topLevelItem(0)
        assert item.data(0, Qt.ItemDataRole.UserRole) == ("", "")
    finally:
        editor.close()
