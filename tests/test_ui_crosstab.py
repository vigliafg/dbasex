"""Test UI della finestra Crosstab (0.7 O6)."""

from __future__ import annotations

from dbx.core.query_model import QueryAggregate, QueryField, QueryJoin, QuerySpec


def _pivot_spec() -> QuerySpec:
    return QuerySpec(
        name="pivot_fatture",
        base="fatture",
        fields=[
            QueryField("clienti", "nome", alias="cliente"),
            QueryField("fatture", "pagata"),
        ],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        group_by=["clienti.nome", "fatture.pagata"],
        aggregates=[QueryAggregate("sum", "fatture", "importo", "totale")],
    )


def test_crosstab_dialog_defaults_and_matrix(qapp, demo_project):
    from dbx.ui.crosstab_dialog import CrosstabDialog
    from dbx.ui.query_results import QueryResultsWidget

    widget = QueryResultsWidget(demo_project, _pivot_spec())
    try:
        assert widget.crosstab_button.isEnabled()
        dialog = CrosstabDialog(widget.result, "Fatture")
        assert dialog.crosstab is not None
        assert dialog.table.rowCount() == 4
        assert dialog.table.columnCount() == 4
        assert dialog.table.horizontalHeaderItem(0).text() == "Nome \\ Pagata"
        assert dialog.table.horizontalHeaderItem(3).text() == "Totale"
        assert dialog.table.item(3, 0).text() == "Totale"
        assert dialog.summary.text().startswith("3 righe · 2 colonne")
        assert dialog.rebuild() is True
        dialog.close()
    finally:
        widget.deleteLater()


def test_crosstab_dialog_switches_dimensions(qapp, demo_project):
    from dbx.ui.crosstab_dialog import CrosstabDialog
    from dbx.ui.query_results import QueryResultsWidget

    widget = QueryResultsWidget(demo_project, _pivot_spec())
    try:
        dialog = CrosstabDialog(widget.result, "Fatture")
        dialog.row_combo.setCurrentIndex(dialog.row_combo.findData("pagata"))
        dialog.column_combo.setCurrentIndex(dialog.column_combo.findData("cliente"))
        assert dialog.crosstab is not None
        assert dialog.crosstab.row_values == [False, True]
        assert dialog.crosstab.column_values == ["Alfa Srl", "Beta Studio", "Gamma snc"]
        dialog.close()
    finally:
        widget.deleteLater()
