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
    from .core.project import Project
    from .designers.form_builder import FormBuilderDialog
    from .designers.menu_builder import MenuBuilderDialog
    from .designers.project_builder import build_project, validate_project
    from .designers.report_builder import ReportBuilderDialog
    from .designers.script_builder import ScriptBuilderDialog
    from .designers.table_builder import TableBuilderDialog
    from .io.pdf_export import export_pdf, page_pixmap
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
    FormBuilderDialog(project, FormSpec.from_dict(form_artifact))
    checks.append("form builder")

    report_artifact = project.artifact("reports", "fatture_per_cliente")
    report_dialog = ReportBuilderDialog(project, ReportSpec.from_dict(report_artifact))
    checks.append("report builder")

    ScriptBuilderDialog(project, project.artifact("scripts", "riepilogo_fatture"))
    checks.append("script builder")

    MenuBuilderDialog(project, project.artifact("menus", "principale"))
    checks.append("menu builder")

    spec = ReportSpec.from_dict(report_artifact)
    from .ui.project_runner import ProjectRunner
    from .ui.report_preview import ReportPreviewDialog

    preview = ReportPreviewDialog(project, "fatture_per_cliente")
    assert preview.pages, "anteprima report vuota"
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
    del table_dialog, report_dialog
    app.processEvents()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run_smoke())
