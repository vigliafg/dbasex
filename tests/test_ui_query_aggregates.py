"""Test UI degli aggregati nel Query Designer (0.7 O5)."""

from __future__ import annotations

from dbx.core.query_model import (
    QueryAggregate,
    QueryField,
    QuerySort,
    QuerySpec,
)


def _grouped_spec(demo_project) -> QuerySpec:
    spec = QuerySpec(
        name="fatture_per_cliente",
        caption="Fatture per cliente",
        base="fatture",
        fields=[QueryField("clienti", "nome", alias="cliente")],
        joins=list(QuerySpec.from_project(demo_project, "fatture_clienti").joins),
        group_by=["clienti.nome"],
        aggregates=[
            QueryAggregate("count", "fatture", alias="numero_fatture"),
            QueryAggregate("sum", "fatture", "importo", "totale"),
        ],
        sorts=[QuerySort("totale", "desc")],
    )
    return spec


def test_designer_shows_grouping_and_aggregates(qapp, demo_project):
    from dbx.designers.query_builder import QueryDesignerWidget

    designer = QueryDesignerWidget(demo_project, _grouped_spec(demo_project))
    try:
        assert designer.group_table.rowCount() == 1
        assert designer.aggregates_table.rowCount() == 2
        sum_field = designer.aggregates_table.cellWidget(1, 1)
        assert sum_field.currentData() == "fatture.importo"
        sql = designer.sql_edit.toPlainText()
        assert "GROUP BY" in sql
        assert 'SUM("fatture"."importo") AS "totale"' in sql
        assert 'COUNT(*) AS "numero_fatture"' in sql
        result = designer.run_preview()
        assert result is not None
        assert len(result) == 3
        assert designer.result_label.text() == "3 righe"
        assert designer.spec.grouped is True
    finally:
        designer.close()


def test_designer_add_group_and_aggregate(qapp, demo_project):
    from dbx.designers.query_builder import QueryDesignerWidget

    spec = QuerySpec.from_project(demo_project, "clienti_attivi")
    designer = QueryDesignerWidget(demo_project, spec)
    try:
        before = designer.group_table.rowCount()
        designer.add_group_field()
        assert designer.group_table.rowCount() == before + 1
        assert designer.spec.group_by

        before_agg = designer.aggregates_table.rowCount()
        designer.add_aggregate()
        assert designer.aggregates_table.rowCount() == before_agg + 1
        assert designer.spec.aggregates[-1].function == "count"
        assert designer.spec.aggregates[-1].table == "clienti"

        designer.aggregates_table.selectRow(before_agg)
        designer.remove_aggregate()
        assert designer.aggregates_table.rowCount() == before_agg
        assert designer.is_dirty() is True
    finally:
        designer.close()


def test_query_results_show_aggregate_columns(qapp, demo_project):
    from dbx.ui.query_results import QueryResultsWidget

    spec = _grouped_spec(demo_project)
    demo_project.put_object("queries", spec.to_dict())
    demo_project.save()
    widget = QueryResultsWidget(demo_project, spec.name)
    try:
        assert widget.table.rowCount() == 3
        assert widget.table.columnCount() == 3
        headers = [
            widget.table.horizontalHeaderItem(column).text()
            for column in range(widget.table.columnCount())
        ]
        assert headers == ["Nome", "Conteggio dei record", "Somma di importo"]
    finally:
        widget.deleteLater()
