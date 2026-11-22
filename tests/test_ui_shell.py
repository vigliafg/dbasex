"""Test della shell: token di design, tema e finestra principale."""

from __future__ import annotations

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
        assert window.tabs.count() == 0
        assert window.project_label.text().startswith(demo_project.name)
        titles = [action.text() for action in window.menuBar().actions()]
        assert "&Progetto" in titles
        assert "&Oggetto" in titles
        assert "&Procedure" in titles
        assert "&Visualizza" in titles
        toolbar = window.findChild(QToolBar, "main_toolbar")
        assert toolbar is not None
    finally:
        window.close()
