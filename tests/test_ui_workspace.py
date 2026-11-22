"""Test delle finestre di uso quotidiano: Command Window e Browse/DataView."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from dbx.config import load_config
from dbx.ui.command_window import CommandWindow
from dbx.ui.data_view import DataView, EditingOptionsDialog


def test_command_window_help_and_clear(qapp, demo_project) -> None:
    window = CommandWindow(demo_project)
    try:
        window.input.setText("HELP")
        window.execute()
        assert "TABELLE" in window.output.toPlainText()
        assert window.status.property("state") == "ok"
        window.input.setText("CLEAR")
        window.execute()
        assert window.output.toPlainText() == ""
        assert window.status.text() == "Risultati cancellati"
    finally:
        window.deleteLater()


def test_command_window_use_record_and_history(qapp, demo_project) -> None:
    window = CommandWindow(demo_project)
    try:
        window.input.setText("USE clienti")
        window.execute()
        assert window.rowset is not None
        window.input.setText("RECORD")
        window.execute()
        assert "codice" in window.output.toPlainText()
        assert window._history == ["USE clienti", "RECORD"]
        window._history_previous()
        assert window.input.text() == "RECORD"
        window._history_previous()
        assert window.input.text() == "USE clienti"
        window._history_next()
        assert window.input.text() == "RECORD"
        window._history_next()
        assert window.input.text() == ""
    finally:
        window.deleteLater()


def test_command_window_error_status(qapp, demo_project) -> None:
    window = CommandWindow(demo_project)
    try:
        window.input.setText("USE inesistente")
        window.execute()
        assert window.status.property("state") == "error"
        assert "sconosciuta" in window.status.text()
        window.input.setText("1 +")
        window.execute()
        assert window.status.property("state") == "error"
    finally:
        window.deleteLater()


def test_data_view_navigation(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    try:
        assert view.rowset.index == 0
        assert view.status.text() == "Record 1 di 3"
        assert not view.first_button.isEnabled()
        assert view.next_button.isEnabled()
        view.last_record()
        assert view.rowset.index == 2
        assert view.grid.currentRow() == 2
        assert view.status.text().startswith("Record 3 di 3")
        assert view.next_button.isEnabled() is False
        view.previous_record()
        assert view.rowset.index == 1
        view.first_record()
        assert view.rowset.index == 0
        assert view.grid.currentRow() == 0
    finally:
        view.deleteLater()


def test_data_view_filter_and_order_status(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    try:
        view.search_edit.setText("Alfa")
        view.apply_filter()
        assert "filtro: Alfa" in view.status.text()
        assert view.rowset.count() == 1
        view.search_edit.clear()
        view.apply_filter()
        view.order_combo.setCurrentIndex(1)
        assert "ordine:" in view.status.text()
    finally:
        view.deleteLater()


def test_data_view_inplace_edit_and_rollback(qapp, demo_project, monkeypatch) -> None:
    view = DataView(demo_project, "fatture")
    messages: list[str] = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *_args, **_kwargs: messages.append("warning"))
    try:
        column = [field.name for field in view.table.fields].index("importo")
        item = view.grid.item(0, column)
        record_id = item.data(Qt.ItemDataRole.UserRole)
        item.setText("999.5")
        record = view.rowset.load(int(record_id))
        assert record is not None and float(record["importo"]) == 999.5
        item.setText("non numerico")
        assert messages, "la modifica non valida deve mostrare un avviso"
        assert item.text() == "999.5"
        record = view.rowset.load(int(record_id))
        assert record is not None and float(record["importo"]) == 999.5
    finally:
        view.deleteLater()


def test_data_view_persists_column_widths(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    try:
        view.grid.setColumnWidth(0, 123)
        view._persist_columns()
        config = load_config()
        assert config["browse_columns"][view._column_key]["codice"] == 123
    finally:
        view.deleteLater()
    reopened = DataView(demo_project, "clienti")
    try:
        assert reopened.grid.columnWidth(0) == 123
    finally:
        reopened.deleteLater()


def test_editing_options_apply(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    try:
        view.options["alternate"] = False
        view.options["record_numbers"] = False
        view._apply_options()
        assert view.grid.alternatingRowColors() is False
        assert view.grid.verticalHeader().isHidden()
        dialog = EditingOptionsDialog(view.options)
        try:
            assert dialog.options()["alternate"] is False
        finally:
            dialog.deleteLater()
    finally:
        view.deleteLater()
