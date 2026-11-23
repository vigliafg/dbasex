"""Test dell'adattamento delle finestre allo schermo disponibile."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QWidget

from dbx.ui.main_window import MainWindow
from dbx.ui.window_fit import available_geometry, fit_to_available


def test_fit_to_available_shrinks_widget(qapp) -> None:
    area = available_geometry()
    widget = QWidget()
    try:
        widget.resize(area.width() + 500, area.height() + 500)
        fit_to_available(widget, move=False)
        assert widget.width() <= area.width()
        assert widget.height() <= area.height()
    finally:
        widget.deleteLater()


def test_main_window_fits_screen_on_show(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        qapp.processEvents()
        area = available_geometry(window)
        assert window.width() <= area.width()
        assert window.height() <= area.height()
        assert area.contains(window.frameGeometry())
    finally:
        window.close()


def test_dialog_is_kept_inside_screen(qapp) -> None:
    area = available_geometry()
    dialog = QDialog()
    try:
        dialog.resize(area.width() + 600, area.height() + 600)
        QTimer.singleShot(0, dialog.accept)
        dialog.exec()
        assert dialog.width() <= area.width()
        assert dialog.height() <= area.height()
    finally:
        dialog.deleteLater()


def test_workspace_keeps_fifth_split_and_tab_fill(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.resize(1024, 600)
        window.show()
        qapp.processEvents()
        window.open_object("tables", "clienti")
        qapp.processEvents()
        tab = window.editors.find("tables:clienti")
        assert tab is not None
        left, right = window.workspace_splitter.sizes()
        assert left <= max(240, window.workspace_splitter.width() // 5) + 4
        assert right > left
        window.open_object("queries", "fatture_clienti")
        qapp.processEvents()
        left, right = window.workspace_splitter.sizes()
        assert left <= max(240, window.workspace_splitter.width() // 5) + 4
        assert right > left
        query = window.editors.find("queries:fatture_clienti")
        assert query is not None
        assert query.widget().width() <= window.editors.width()
        window.resize(760, 480)
        qapp.processEvents()
        qapp.processEvents()
        left, right = window.workspace_splitter.sizes()
        assert left <= max(240, window.workspace_splitter.width() // 5) + 4
        assert query.widget().width() <= window.editors.width()
        assert query.widget().height() <= window.editors.height()
    finally:
        window.close()
