"""Verifica end-to-end headless: progetto demo, designer, report PDF, build."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def run_smoke() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("DBX_CONFIG_DIR", str(Path(tempfile.mkdtemp(prefix="dbx-smoke-config-"))))
    from PyQt6.QtWidgets import QApplication

    from .core import types as T
    from .core.form_model import FormSpec
    from .core.metadata import Field, Table
    from .core.crosstab import build_crosstab
    from .core.label_model import LabelSpec
    from .core.query_engine import run_query
    from .core.query_model import QueryAggregate, QueryField, QueryJoin, QuerySpec
    from .core.refactor import check_database, duplicate_object
    from .core.search import SearchCriterion, SearchRequest
    from .designers.database_designer import DatabaseDesignerWidget
    from .designers.form_builder import FormDesignerWidget
    from .designers.form_expert import FormExpert
    from .designers.label_builder import LabelDesignerWidget
    from .designers.project_builder import build_project, validate_project
    from .designers.query_builder import QueryDesignerWidget
    from .designers.query_expert import QueryExpert
    from .designers.menu_builder import MenuBuilderWidget
    from .designers.project_builder import ProjectEditorWidget
    from .designers.report_builder import ReportDesignerWidget
    from .designers.report_expert import ReportExpert
    from .ui.query_results import QueryResultsWidget
    from .designers.script_builder import ScriptBuilderWidget
    from .designers.table_builder import TableBuilderDialog
    from .designers.table_expert import TableExpert
    from .io.pdf_export import export_pdf, page_pixmap
    from .runtime.form_runtime import FormRuntime
    from .runtime.label_engine import render_labels_for_project
    from .runtime.report_engine import Control, ReportSpec
    from .runtime.script_engine import ScriptEngine
    from .samples import create_demo_project
    from .ui.app import create_application
    from .ui.data_view import DataView
    from .ui.main_window import MainWindow
    from .ui.report_preview import ReportPreviewDialog, build_pages

    app = QApplication.instance() or create_application(["dbx-smoke"])
    # In headless non devono comparire dialoghi modali: le traceback vanno su stderr.
    import sys
    import traceback

    def _headless_hook(exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _headless_hook
    root = Path(tempfile.mkdtemp(prefix="dbx-smoke-"))
    project = create_demo_project(root / "Rubrica")
    checks: list[str] = []

    errors = validate_project(project)
    assert not errors, "validazione progetto: " + "; ".join(errors)
    checks.append("validazione progetto")

    window = MainWindow(project)
    window._refresh_navigator()
    checks.append("finestra principale + navigator")

    view = DataView(project, "clienti")
    assert view.rowset.count() == 3
    view._search = SearchRequest([SearchCriterion("citta", "contains", "Roma")])
    view.refresh()
    assert len(view.rowset) == 1
    view.clear_find()
    assert len(view.rowset) == 3
    checks.append("vista dati + find mode")

    table_dialog = TableBuilderDialog(project, project.require_table("clienti"))
    assert "clienti" in table_dialog.current_table().name
    checks.append("table builder")

    table_expert = TableExpert(project, suggested_name="table_smoke")
    table_expert.template_combo.setCurrentIndex(
        max(0, table_expert.template_combo.findData("contatti"))
    )
    table_spec = table_expert.build_table()
    table_spec.validate()
    assert table_spec.fields and table_spec.field("email") is not None
    checks.append("table expert")

    query_expert = QueryExpert(project, suggested_name="query_smoke")
    query_spec = query_expert.build_spec()
    assert query_spec.validate(project.tables()) == []
    checks.append("query expert")

    report_expert = ReportExpert(project, suggested_name="report_smoke")
    report_spec = report_expert.build_spec()
    assert report_spec.validate() == []
    checks.append("report expert")

    form_artifact = project.artifact("forms", "form_clienti")
    form_designer = FormDesignerWidget(project, FormSpec.from_dict(form_artifact))
    assert form_designer.canvas.page.controls
    assert form_designer.object_combo.count() > 1
    checks.append("form designer")

    expert = FormExpert(project, suggested_name="form_smoke")
    expert.initializePage(1)
    expert_spec = expert.build_spec()
    assert expert_spec.validate() == []
    checks.append("form expert")

    runtime = FormRuntime(project, FormSpec.from_dict(form_artifact))
    runtime.perform("next")
    assert runtime.rowset.index == 1
    checks.append("form runtime + eventi")

    report_artifact = project.artifact("reports", "fatture_per_cliente")
    report_dialog = ReportDesignerWidget(project, ReportSpec.from_dict(report_artifact))
    assert len(report_dialog.canvas.band_tops()) == 7
    checks.append("report designer a bande")

    database_designer = DatabaseDesignerWidget(project)
    assert len(database_designer.graph.nodes) == 2
    assert len(database_designer.graph.edges) == 1
    checks.append("database designer ER")

    query_spec = QuerySpec.from_project(project, "fatture_clienti")
    assert query_spec is not None
    query_designer = QueryDesignerWidget(project, query_spec)
    query_result = query_designer.run_preview()
    assert query_result is not None and len(query_result) == 5
    assert query_designer.tree.topLevelItemCount() == 2
    checks.append("query designer")

    query_designer.set_mode("qbe")
    assert len(query_designer.qbe_page.images()) == 2
    query_designer.qbe_page.set_cell("fatture", "importo", 0, "500..1300")
    query_designer.qbe_page.apply_and_notify()
    assert any(item.op == "between" for item in query_spec.filters)
    assert query_designer.run_preview() is not None
    checks.append("qbe mode")

    query_results = QueryResultsWidget(project, "fatture_clienti")
    assert query_results.table.rowCount() == 5
    assert query_results.table.columnCount() == 5
    checks.append("query results")

    aggregate_spec = QuerySpec(
        name="smoke_aggregato",
        base="fatture",
        aggregates=[
            QueryAggregate("count", "fatture", alias="numero"),
            QueryAggregate("sum", "fatture", "importo", "totale"),
        ],
    )
    aggregate_result = run_query(project, aggregate_spec)
    assert aggregate_result.rows[0]["numero"] == 5
    assert aggregate_result.rows[0]["totale"] == 5900.5
    checks.append("aggregati query")

    pivot_spec = QuerySpec(
        name="smoke_pivot",
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
    crosstab = build_crosstab(
        run_query(project, pivot_spec), "cliente", "pagata", "totale"
    )
    assert crosstab.grand_total == 5900.5
    assert len(crosstab.row_values) == 3
    checks.append("crosstab read-only")

    label_table = project.require_table("clienti")
    label_spec = LabelSpec.create(
        "etichette_smoke",
        label_table.name,
        [field.name for field in label_table.fields],
        title="Etichette clienti",
    )
    label_spec.template = "[nome]\n[citta]"
    label_spec.filter = "attivo = 1"
    label_spec.order = "nome"
    label_pages = render_labels_for_project(project, label_spec)
    label_text_value = " ".join(
        op.text for page in label_pages for op in page.ops if op.kind == "text"
    )
    assert "Alfa Srl" in label_text_value
    assert "Gamma snc" not in label_text_value
    label_designer = LabelDesignerWidget(project, label_spec)
    assert label_designer.fields_list.count() == len(label_table.fields)
    assert "2 record" in label_designer.status_label.text()
    checks.append("etichette e mail merge")

    query_form = FormRuntime(project, FormSpec.from_dict(project.artifact("forms", "form_clienti_attivi")))
    assert query_form.read_only is True
    assert query_form.rowset.count() == 2
    checks.append("form su query")

    query_report = ReportPreviewDialog(project, "fatture_clienti_report")
    assert query_report.pages
    checks.append("report su query")

    script_editor = ScriptBuilderWidget(project, project.artifact("scripts", "riepilogo_fatture"))
    assert script_editor.tree.topLevelItemCount() > 0
    assert script_editor.text_view.line_number_width() > 0
    checks.append("program editor")

    menu_designer = MenuBuilderWidget(project, project.artifact("menus", "principale"))
    assert menu_designer.tree.topLevelItemCount() == len(menu_designer.items)
    checks.append("menu designer")

    project_editor = ProjectEditorWidget(project)
    assert project_editor.tree.topLevelItemCount() == 8
    checks.append("project editor")

    spec = ReportSpec.from_dict(report_artifact)
    from .ui.project_runner import ProjectRunner

    preview = ReportPreviewDialog(project, "fatture_per_cliente")
    assert preview.pages, "anteprima report vuota"
    assert preview.total_label.text().startswith("Totale:")
    checks.append("anteprima report")
    runner = ProjectRunner(project, "form_clienti", "principale")
    assert runner.current is not None
    checks.append("project runner con menu")

    pages = build_pages(project, spec)
    assert pages, "il report non ha prodotto pagine"
    pixmap = page_pixmap(pages[0], 1.0)
    assert not pixmap.isNull()
    pdf = export_pdf(pages, root / "report.pdf", "smoke")
    assert pdf.exists() and pdf.stat().st_size > 1000
    checks.append(f"report: {len(pages)} pagine, PDF {pdf.stat().st_size} byte")

    chart_spec = ReportSpec.from_dict(report_artifact)
    chart_spec.bands["summary"].append(
        Control(
            id="grafico_smoke",
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
    )
    chart_pages = build_pages(project, chart_spec)
    chart_ops = [
        op for page in chart_pages for op in page.ops if op.kind == "chart"
    ]
    assert chart_ops and chart_ops[0].series
    chart_pdf = export_pdf(chart_pages, root / "chart.pdf", "grafico")
    assert chart_pdf.exists() and chart_pdf.stat().st_size > 1000
    checks.append("grafici report")

    engine = ScriptEngine(project)
    result = engine.run_named("riepilogo_fatture")
    assert result.error is None, result.error
    assert any("Fattura" in line for line in result.log), result.log
    checks.append(f"script: {len(result.log)} righe di log")

    core = ScriptEngine(project).run(
        [
            {"action": "select_table", "params": {"table": "clienti", "order": "codice"}},
            {"action": "go_record", "params": {"mode": "number", "number": "2"}},
            {"action": "set_field", "params": {"field": "note", "expr": '"smoke"'}},
            {"action": "commit_record", "params": {}},
        ]
    )
    assert core.error is None, core.error
    checks.append("script core actions")

    imported_table = Table(
        name="import_smoke",
        fields=[
            Field("codice", T.TEXT, required=True),
            Field("nome", T.TEXT),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
            Field("progressivo", T.INTEGER, auto_serial=True),
        ],
    )
    project.apply_table(imported_table)
    csv_path = root / "import_smoke.csv"
    csv_path.write_text("codice;nome\nC1;Alfa\nC2;Beta\n", encoding="utf-8")
    from .io.csv_io import records_from_table
    from .ui.import_wizard import ImportCsvDialog

    importer = ImportCsvDialog(project, "import_smoke")
    importer.path_edit.setText(str(csv_path))
    importer.reload_preview()
    imported = importer._insert_records(
        records_from_table(
            importer._rows,
            imported_table,
            importer.current_mapping(),
            importer.header_box.isChecked(),
        ),
        False,
    )
    assert imported == 2
    from .runtime.rowset import Rowset as SmokeRowset

    computed = SmokeRowset(project.db, project.require_table("import_smoke")).open().rows()
    assert [row["nome_maiuscolo"] for row in computed] == ["ALFA", "BETA"]
    assert [row["progressivo"] for row in computed] == [1, 2]
    checks.append(f"import csv: {imported} record + calcolati")

    duplicate = duplicate_object(project, "queries", "clienti_attivi")
    assert project.artifact("queries", duplicate) is not None
    assert check_database(project) == "ok"
    checks.append("duplicazione oggetti + integrità")

    target = build_project(project, root / "dist")
    assert target.exists()
    checks.append(f"build: {target.name}")

    window.close()
    project.close()
    print("SMOKE OK")
    for check in checks:
        print("  -", check)
    del (
    table_dialog,
    report_dialog,
    database_designer,
    query_designer,
    query_results,
    query_form,
    query_report,
    form_designer,
    expert,
    runtime,
    script_editor,
    menu_designer,
    project_editor,
    importer,
)
    app.processEvents()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_smoke())
