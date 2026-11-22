"""Test della shell: token di design, tema, MDI, menu, SpeedBar e status bar."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar

from dbx.ui import design
from dbx.ui.main_window import MainWindow


def test_design_tokens_silver() -> None:
    silver = design.palette("silver")
    assert design.DEFAULT_THEME == "silver"
    assert silver["window_bg"] == "#c0c0c0"
    assert silver["selection_bg"] == "#000080"
    assert design.METRICS.grid_step == 8
    assert design.METRICS.ruler_size == 18
    assert design.UI_FONT.family == "MS Sans Serif"


def test_theme_aliases_and_qss() -> None:
    assert design.normalize_theme("light") == "light"
    assert design.palette("light") is design.SILVER
    assert design.palette("dark") is design.SILVER_DARK
    assert design.normalize_theme("inesistente") == design.DEFAULT_THEME
    assert "$" not in design.qss("silver")
    assert "font-size" in design.qss("dark")


def test_main_window_basics(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert window.project is demo_project
        assert window.navigator is not None
        assert window.mdi.subWindowList() == []
        assert window.project_label.text().startswith(demo_project.name)
        titles = [action.text() for action in window.menuBar().actions()]
        assert titles == [
            "&Progetto",
            "&Modifica",
            "&Visualizza",
            "&Oggetto",
            "&Procedure",
            "&Proprietà",
            "&Finestra",
            "&?",
        ]
        toolbar = window.findChild(QToolBar, "main_toolbar")
        assert toolbar is not None
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert toolbar.iconSize().width() == design.METRICS.icon_size
        assert window.pos_label.text().startswith("Pos:")
        assert window.object_label.text().startswith("Oggetto:")
        assert window.record_label.text().startswith("Record:")
        assert window.mode_label.text().startswith("Modalità:")
        assert not window.act_undo.isEnabled()
        assert not window.act_zoom_in.isEnabled()
    finally:
        window.close()


def test_mdi_opens_two_documents_and_dedupes(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("tables", "clienti")
        window.open_object("forms", "form_clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 2
        keys = {sub.property("dbx_key") for sub in window.editors.windows()}
        assert keys == {"tables:clienti", "forms:form_clienti"}
        assert window.object_label.text().startswith("Oggetto: Form Designer")
        assert window.mode_label.text().endswith("Design")

        window.open_object("tables", "clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 2

        window.editors.cascade()
        window.editors.tile()
        window.act_close_window.trigger()
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
        window.act_close_all.trigger()
        qapp.processEvents()
        assert window.editors.windows() == []
        assert window.object_label.text() == "Oggetto: —"
    finally:
        window.close()


def test_window_menu_lists_documents(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("tables", "clienti")
        qapp.processEvents()
        labels = [action.text() for action in window._window_menu.actions()]
        assert "Sovrapponi" in labels
        assert "Affianca" in labels
        assert any(label.startswith("Browse") for label in labels)
    finally:
        window.close()


def test_mdi_replaces_tabs(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert not hasattr(window, "tabs")
        assert window.centralWidget() is window.mdi
    finally:
        window.close()


def test_command_window_opens_in_mdi_once(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_command_window()
        qapp.processEvents()
        assert window.editors.find("command") is not None
        window.open_command_window()
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
        assert "Command Window" in window.object_label.text()
    finally:
        window.close()
