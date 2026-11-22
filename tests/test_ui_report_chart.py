"""Test UI dei grafici nel Report Designer e in anteprima (0.8 O8)."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog

from dbx.runtime.report_engine import Control, ReportSpec


def _chart() -> Control:
    return Control(
        id="grafico",
        kind="chart",
        x=0,
        y=20,
        w=170,
        h=45,
        text="Importo per cliente",
        expr="[importo]",
        category="[cliente]",
        func="sum",
        chart_type="bar",
        border=True,
    )


def test_chart_dialog_builds_control(qapp, demo_project) -> None:
    from dbx.designers.report_builder import ChartDialog

    dialog = ChartDialog(demo_project, "fatture", [{"field": "cliente"}])
    try:
        assert dialog.type_combo.currentData() == "bar"
        assert dialog.category_combo.currentData() == "cliente"
        band, control = dialog.control()
        assert band == "summary"
        assert control.kind == "chart"
        assert control.expr == "[importo]"
        assert control.category == "[cliente]"
        assert control.func == "sum"
        assert control.w == 170

        dialog.type_combo.setCurrentIndex(dialog.type_combo.findData("pie"))
        dialog.category_combo.setCurrentIndex(
            dialog.category_combo.findData("pagata")
        )
        _band, pie = dialog.control()
        assert pie.chart_type == "pie"
        assert pie.category == "[pagata]"
    finally:
        dialog.close()


def test_designer_inserts_chart(qapp, demo_project, monkeypatch) -> None:
    from dbx.designers.report_builder import ChartDialog, ReportDesignerWidget

    spec = ReportSpec.from_dict(
        demo_project.artifact("reports", "fatture_per_cliente")
    )
    designer = ReportDesignerWidget(demo_project, spec)
    try:
        control = _chart()
        monkeypatch.setattr(
            ChartDialog, "exec", lambda self: QDialog.DialogCode.Accepted
        )
        monkeypatch.setattr(
            ChartDialog, "control", lambda self: ("summary", control)
        )
        before = len(designer.spec.bands["summary"])
        designer.insert_chart()
        assert len(designer.spec.bands["summary"]) == before + 1
        assert designer.spec.bands["summary"][-1].kind == "chart"
        assert designer.selected_id == control.id
        assert designer.is_dirty() is True
    finally:
        designer.close()


def test_preview_paints_chart(qapp, demo_project) -> None:
    from dbx.io.pdf_export import page_pixmap
    from dbx.ui.report_preview import ReportPreviewDialog

    spec = ReportSpec.from_dict(
        demo_project.artifact("reports", "fatture_per_cliente")
    )
    spec.bands["summary"].append(_chart())
    dialog = ReportPreviewDialog(demo_project, spec)
    try:
        assert dialog.pages
        chart_ops = [
            op for page in dialog.pages for op in page.ops if op.kind == "chart"
        ]
        assert len(chart_ops) == 1
        pixmap = page_pixmap(dialog.pages[0], 1.5)
        assert not pixmap.isNull()
        assert pixmap.width() > 100
    finally:
        dialog.close()


def test_chart_control_appears_in_inspector(qapp, demo_project) -> None:
    from dbx.designers.report_builder import ReportDesignerWidget

    spec = ReportSpec.from_dict(
        demo_project.artifact("reports", "fatture_per_cliente")
    )
    chart = _chart()
    spec.bands["summary"].append(chart)
    designer = ReportDesignerWidget(demo_project, spec)
    try:
        designer.selected_id = chart.id
        designer.canvas.selected = chart.id
        designer._show_control(chart)
        for key in ("chart_type", "category", "expr", "func"):
            assert designer.inspector.item(key) is not None
    finally:
        designer.close()


def test_report_validation_accepts_chart(demo_project) -> None:
    spec = ReportSpec.from_dict(
        demo_project.artifact("reports", "fatture_per_cliente")
    )
    spec.bands["summary"].append(_chart())
    assert spec.validate() == []
