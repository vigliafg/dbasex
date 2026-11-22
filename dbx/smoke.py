"""Verifica end-to-end headless: progetto demo, designer, report PDF, build."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def run_smoke() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("DBX_CONFIG_DIR", str(Path(tempfile.mkdtemp(prefix="dbx-smoke-config-"))))
    from PyQt6.QtWidgets import QApplication

    from .core.form_model import FormSpec
    from .designers.database_designer import DatabaseDesignerWidget
    from .designers.form_builder import FormDesignerWidget
    from .designers.form_expert import FormExpert
    from .designers.project_builder import build_project, validate_project
    from .designers.menu_builder import MenuBuilderWidget
    from .designers.project_builder import ProjectEditorWidget
    from .designers.report_builder import ReportDesignerWidget
    from .designers.script_builder import ScriptBuilderWidget
    from .designers.table_builder import TableBuilderDialog
    from .io.pdf_export import export_pdf, page_pixmap
    from .runtime.form_runtime import FormRuntime
    from .runtime.report_engine import ReportSpec
    from .runtime.script_engine import ScriptEngine
    from .samples import create_demo_project
    from .ui.app import create_application
    from .ui.data_view import DataView
    from .ui.main_window import MainWindow
    from .ui.report_preview import build_pages

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
    checks.append("vista dati")

    table_dialog = TableBuilderDialog(project, project.require_table("clienti"))
    assert "clienti" in table_dialog.current_table().name
    checks.append("table builder")

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

    script_editor = ScriptBuilderWidget(project, project.artifact("scripts", "riepilogo_fatture"))
    assert script_editor.tree.topLevelItemCount() > 0
    assert script_editor.text_view.line_number_width() > 0
    checks.append("program editor")

    menu_designer = MenuBuilderWidget(project, project.artifact("menus", "principale"))
    assert menu_designer.tree.topLevelItemCount() == len(menu_designer.items)
    checks.append("menu designer")

    project_editor = ProjectEditorWidget(project)
    assert project_editor.tree.topLevelItemCount() == 6
    checks.append("project editor")

    spec = ReportSpec.from_dict(report_artifact)
    from .ui.project_runner import ProjectRunner
    from .ui.report_preview import ReportPreviewDialog

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

    engine = ScriptEngine(project)
    result = engine.run_named("riepilogo_fatture")
    assert result.error is None, result.error
    assert any("Fattura" in line for line in result.log), result.log
    checks.append(f"script: {len(result.log)} righe di log")

    target = build_project(project, root / "dist")
    assert target.exists()
    checks.append(f"build: {target.name}")

    window.close()
    project.close()
    print("SMOKE OK")
    for check in checks:
        print("  -", check)
    del table_dialog, report_dialog, database_designer, form_designer, expert, runtime, script_editor, menu_designer, project_editor
    app.processEvents()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_smoke())
