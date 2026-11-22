"""Test della finestra Query Results."""

from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog

from dbx.ui.main_window import MainWindow
from dbx.ui.query_results import QueryResultsWidget


def test_results_grid_and_formatting(qapp, demo_project) -> None:
    widget = QueryResultsWidget(demo_project, "fatture_clienti")
    try:
        assert widget.result is not None
        assert len(widget.result) == 5
        assert widget.table.rowCount() == 5
        assert widget.table.columnCount() == 5
        headers = [
            widget.table.horizontalHeaderItem(index).text()
            for index in range(widget.table.columnCount())
        ]
        assert headers == ["Numero", "Data", "Nome", "Importo", "Pagata"]
        assert widget.table.item(0, 1).text() == "15/01/2026"
        assert widget.table.item(0, 2).text() == "Alfa Srl"
        assert widget.table.item(0, 4).text() == "Sì"
        assert widget.table.item(1, 4).text() == "No"
        assert widget.row_values(0)["cliente_nome"] == "Alfa Srl"
        assert "5 righe" in widget.info_label.text()
    finally:
        widget.close()


def test_results_refresh_and_filtered_query(qapp, demo_project) -> None:
    widget = QueryResultsWidget(demo_project, "clienti_attivi")
    try:
        assert len(widget.result) == 2
        assert widget.table.rowCount() == 2
        assert widget.refresh() is True
        assert len(widget.result) == 2
    finally:
        widget.close()


def test_export_csv(qapp, demo_project, tmp_path, monkeypatch) -> None:
    widget = QueryResultsWidget(demo_project, "fatture_clienti")
    target = tmp_path / "risultato.csv"
    try:
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            staticmethod(lambda *args, **kwargs: (str(target), "CSV (*.csv)")),
        )
        path = widget.export_csv()
        assert path == target
        text = target.read_text(encoding="utf-8-sig")
        assert text.splitlines()[0].startswith("numero;data;cliente_nome;importo;pagata")
        assert "Alfa Srl" in text
    finally:
        widget.close()


def test_main_window_opens_query_results(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.run_object("queries", "fatture_clienti")
        qapp.processEvents()
        sub = window.editors.find("results:queries:fatture_clienti")
        assert sub is not None
        assert isinstance(sub.widget(), QueryResultsWidget)
        assert window.mode_label.text().endswith("Risultati")
        window.run_object("queries", "fatture_clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
    finally:
        window.close()
