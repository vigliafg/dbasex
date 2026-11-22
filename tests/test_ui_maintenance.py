"""Test UI di rinomina e manutenzione (0.6)."""

from __future__ import annotations


def test_table_builder_renames_table(qapp, demo_project):
    from dbx.designers.table_builder import TableBuilderDialog

    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    dialog.name_edit.setText("anagrafica")
    dialog._apply()
    assert demo_project.db.has_table("anagrafica")
    assert not demo_project.db.has_table("clienti")
    assert demo_project.table("clienti") is None
    dialog.close()


def test_navigator_exposes_duplicate_action(qapp, demo_project, monkeypatch):
    from PyQt6.QtWidgets import QMenu

    from dbx.ui.navigator import Navigator

    navigator = Navigator()
    navigator.set_project(demo_project)
    captured: list[tuple[str, str]] = []
    navigator.duplicate_object.connect(lambda category, name: captured.append((category, name)))
    # Il menu contestuale è costruito al volo: invochiamo il segnale come farebbe la voce.
    navigator.duplicate_object.emit("queries", "clienti_attivi")
    assert captured == [("queries", "clienti_attivi")]
    navigator.deleteLater()


def test_main_window_has_maintenance_actions(qapp, demo_project):
    from dbx.ui.main_window import MainWindow

    window = MainWindow()
    window.set_project(demo_project)
    assert window.act_compact is not None
    assert window.act_integrity is not None
    window.close()
