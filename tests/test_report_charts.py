"""Test dei grafici nel report (0.8 O8)."""

from __future__ import annotations

import pytest

from dbx.runtime.report_engine import (
    CHART_TYPES,
    Control,
    ReportSpec,
    render_report,
)
from dbx.runtime.rowset import Rowset


def _chart(**changes) -> Control:
    values = {
        "id": "chart1",
        "kind": "chart",
        "x": 0,
        "y": 20,
        "w": 170,
        "h": 45,
        "text": "Importo per cliente",
        "expr": "[importo]",
        "func": "sum",
        "chart_type": "bar",
        "category": "[cliente]",
        "border": True,
    }
    values.update(changes)
    return Control(**values)


def _spec(demo_project) -> ReportSpec:
    return ReportSpec.from_dict(
        demo_project.artifact("reports", "fatture_per_cliente")
    )


def _rows(demo_project, spec):
    table = demo_project.require_table("fatture")
    return Rowset(demo_project.db, table).open(order=spec.order).rows()


def _chart_ops(pages):
    return [op for page in pages for op in page.ops if op.kind == "chart"]


def test_bar_chart_aggregates_groups(demo_project):
    spec = _spec(demo_project)
    spec.bands["summary"].append(_chart())
    pages = render_report(spec, _rows(demo_project, spec))
    charts = _chart_ops(pages)
    assert len(charts) == 1
    chart = charts[0]
    assert chart.chart_type == "bar"
    assert chart.text == "Importo per cliente"
    assert chart.series == [
        ("C001", 1650.0),
        ("C002", 3450.5),
        ("C003", 800.0),
    ]


def test_pie_and_line_chart_types(demo_project):
    spec = _spec(demo_project)
    spec.bands["summary"].append(
        _chart(id="pie", chart_type="pie", category="[pagata]", text="Pagate")
    )
    spec.bands["summary"].append(
        _chart(id="line", chart_type="line", category="[cliente]", text="Linee")
    )
    pages = render_report(spec, _rows(demo_project, spec))
    charts = {op.chart_type: op for op in _chart_ops(pages)}
    assert set(charts) == {"pie", "line"}
    assert sorted(charts["pie"].series) == [("No", 3900.5), ("Sì", 2000.0)]
    assert charts["pie"].text == "Pagate"
    assert len(charts["line"].series) == 3


def test_count_chart_without_expression(demo_project):
    spec = _spec(demo_project)
    spec.bands["summary"].append(
        _chart(expr="", func="count", category="[pagata]", text="Conteggio")
    )
    pages = render_report(spec, _rows(demo_project, spec))
    chart = _chart_ops(pages)[0]
    assert dict(chart.series) == {"No": 3.0, "Sì": 2.0}


def test_group_footer_chart_is_limited_to_group(demo_project):
    spec = _spec(demo_project)
    spec.bands["group_footer"].append(
        _chart(y=10, category="[cliente]", text="Totale gruppo")
    )
    pages = render_report(spec, _rows(demo_project, spec))
    charts = _chart_ops(pages)
    assert len(charts) == 3
    assert all(len(chart.series) == 1 for chart in charts)
    assert [chart.series[0][1] for chart in charts] == [1650.0, 3450.5, 800.0]


def test_chart_validation():
    spec = ReportSpec(name="r", table="fatture")
    spec.bands["summary"].append(_chart(chart_type="bolle"))
    errors = spec.validate()
    assert any("tipo di grafico" in error for error in errors)

    spec = ReportSpec(name="r", table="fatture")
    spec.bands["summary"].append(_chart(expr=""))
    assert any("non ha un'espressione" in error for error in spec.validate())

    spec = ReportSpec(name="r", table="fatture")
    spec.bands["summary"].append(_chart(func="median"))
    assert any("funzione del grafico" in error for error in spec.validate())

    spec = ReportSpec(name="r", table="fatture")
    spec.bands["summary"].append(_chart(expr="", func="count"))
    assert spec.validate() == []


def test_chart_control_round_trip():
    control = _chart(chart_type="pie", category="[pagata]")
    clone = Control.from_dict(control.to_dict())
    assert clone.chart_type == "pie"
    assert clone.category == "[pagata]"
    assert clone.to_dict() == control.to_dict()
    assert set(CHART_TYPES) == {"bar", "line", "pie"}


def test_chart_summary_from_query_source(demo_project):
    spec = ReportSpec(
        name="query_chart",
        title="Grafico su query",
        source_type="query",
        query="fatture_clienti",
    )
    spec.bands["summary"].append(
        _chart(expr="[importo]", category="[cliente_nome]", func="sum")
    )
    from dbx.core.query_engine import run_query
    from dbx.core.query_model import QuerySpec

    query = QuerySpec.from_project(demo_project, "fatture_clienti")
    assert query is not None
    rows = run_query(demo_project, query).rows
    pages = render_report(spec, rows)
    chart = _chart_ops(pages)[0]
    assert chart.series[0][0] == "Alfa Srl"
    assert pytest.approx(sum(value for _label, value in chart.series)) == 5900.5
