"""Cattura headless delle finestre dBX per il QA visivo.

Uso:

    python tools/capture_ui.py [--theme silver|dark]

Le immagini vengono salvate in ``docs/reference/dbx-ui/renders/``.
Il tema predefinito è ``aurora``; ``silver`` resta per il confronto storico.
Lo script usa il progetto demo e non apre dialoghi modali.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import traceback
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DBX_CONFIG_DIR", tempfile.mkdtemp(prefix="dbx-capture-config-"))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QPoint  # noqa: E402
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

from dbx.core.form_model import FormSpec  # noqa: E402
from dbx.core.query_model import QuerySpec  # noqa: E402
from dbx.designers.database_designer import DatabaseDesignerWidget  # noqa: E402
from dbx.designers.form_builder import FormDesignerWidget  # noqa: E402
from dbx.designers.menu_builder import MenuBuilderWidget  # noqa: E402
from dbx.designers.project_builder import ProjectEditorWidget  # noqa: E402
from dbx.designers.query_builder import QueryDesignerWidget  # noqa: E402
from dbx.designers.report_builder import ReportBuilderDialog  # noqa: E402
from dbx.designers.script_builder import ScriptBuilderWidget  # noqa: E402
from dbx.designers.table_builder import TableBuilderDialog  # noqa: E402
from dbx.runtime.form_runtime import FormRuntime  # noqa: E402
from dbx.runtime.report_engine import ReportSpec  # noqa: E402
from dbx.samples import create_demo_project  # noqa: E402
from dbx.ui.app import create_application  # noqa: E402
from dbx.ui.command_window import CommandWindow  # noqa: E402
from dbx.ui.data_view import DataView  # noqa: E402
from dbx.ui.main_window import MainWindow  # noqa: E402
from dbx.ui.navigator import Navigator  # noqa: E402
from dbx.ui.report_preview import ReportPreviewDialog  # noqa: E402
from dbx.ui.theme import apply_theme  # noqa: E402

OUTPUT_DIR = ROOT / "docs" / "reference" / "dbx-ui" / "renders"


def _capture(app: QApplication, widget: QWidget, name: str, size: tuple[int, int]) -> Path:
    widget.resize(*size)
    widget.show()
    app.processEvents()
    app.processEvents()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    pixmap = widget.grab()
    if pixmap.isNull() or not pixmap.save(str(path), "PNG"):
        raise RuntimeError(f"impossibile salvare {path}")
    widget.hide()
    app.processEvents()
    return path


def _capture_menu(app: QApplication, menu, name: str) -> Path:
    menu.popup(menu.parentWidget().mapToGlobal(QPoint(80, 80)) if menu.parentWidget() else QPoint(80, 80))
    app.processEvents()
    app.processEvents()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / name
    pixmap = menu.grab()
    if pixmap.isNull() or not pixmap.save(str(path), "PNG"):
        raise RuntimeError(f"impossibile salvare {path}")
    menu.close()
    app.processEvents()
    return path


def run(theme: str = "aurora") -> int:
    app = QApplication.instance() or create_application(["dbx-capture"], theme)
    resolved = apply_theme(app, theme)
    root = Path(tempfile.mkdtemp(prefix="dbx-capture-"))
    project = create_demo_project(root / "Rubrica")
    widgets: list[QWidget] = []
    captured: list[Path] = []
    try:
        window = MainWindow(project)
        widgets.append(window)
        captured.append(_capture(app, window, "01-desktop.png", (1280, 800)))

        window.open_object("tables", "clienti")
        window.open_object("forms", "form_clienti")
        window.editors.cascade()
        app.processEvents()
        captured.append(_capture(app, window, "10-desktop-mdi.png", (1280, 800)))

        window.show()
        app.processEvents()
        project_menu = window.menuBar().actions()[0].menu()
        captured.append(_capture_menu(app, project_menu, "14-menu-progetto.png"))

        navigator = Navigator()
        navigator.set_project(project)
        widgets.append(navigator)
        captured.append(_capture(app, navigator, "02-navigator.png", (420, 620)))

        data_view = DataView(project, "clienti")
        widgets.append(data_view)
        captured.append(_capture(app, data_view, "03-browse-clienti.png", (1000, 620)))

        table_dialog = TableBuilderDialog(project, project.require_table("clienti"))
        widgets.append(table_dialog)
        captured.append(_capture(app, table_dialog, "04-table-structure.png", (1040, 720)))

        form_artifact = project.artifact("forms", "form_clienti")
        if form_artifact is None:
            raise RuntimeError("form_clienti non presente nel progetto demo")
        form_spec = FormSpec.from_dict(form_artifact)
        form_dialog = FormDesignerWidget(project, form_spec)
        widgets.append(form_dialog)
        captured.append(_capture(app, form_dialog, "05-form-designer.png", (1160, 760)))

        form_preview = FormRuntime(project, FormSpec.from_dict(form_artifact))
        widgets.append(form_preview)
        captured.append(_capture(app, form_preview, "06-form-runtime.png", (860, 660)))

        report_artifact = project.artifact("reports", "fatture_per_cliente")
        if report_artifact is None:
            raise RuntimeError("fatture_per_cliente non presente nel progetto demo")
        report_dialog = ReportBuilderDialog(project, ReportSpec.from_dict(report_artifact))
        widgets.append(report_dialog)
        captured.append(_capture(app, report_dialog, "07-report-designer.png", (1180, 800)))

        report_preview = ReportPreviewDialog(project, ReportSpec.from_dict(report_artifact))
        widgets.append(report_preview)
        captured.append(_capture(app, report_preview, "08-report-preview.png", (940, 800)))

        command_window = CommandWindow(project)
        widgets.append(command_window)
        captured.append(_capture(app, command_window, "09-command-window.png", (760, 520)))

        script_artifact = project.artifact("scripts", "riepilogo_fatture")
        if script_artifact is None:
            raise RuntimeError("riepilogo_fatture non presente nel progetto demo")
        script_editor = ScriptBuilderWidget(project, script_artifact)
        widgets.append(script_editor)
        captured.append(_capture(app, script_editor, "11-script-editor.png", (1040, 700)))

        menu_artifact = project.artifact("menus", "principale")
        if menu_artifact is None:
            raise RuntimeError("principale non presente nel progetto demo")
        menu_designer = MenuBuilderWidget(project, menu_artifact)
        widgets.append(menu_designer)
        captured.append(_capture(app, menu_designer, "12-menu-designer.png", (860, 560)))

        project_editor = ProjectEditorWidget(project)
        widgets.append(project_editor)
        captured.append(_capture(app, project_editor, "13-project-editor.png", (900, 640)))

        database_designer = DatabaseDesignerWidget(project)
        widgets.append(database_designer)
        captured.append(
            _capture(app, database_designer, "15-database-designer.png", (1180, 760))
        )

        query_spec = QuerySpec.from_project(project, "fatture_clienti")
        if query_spec is None:
            raise RuntimeError("fatture_clienti non presente nel progetto demo")
        query_designer = QueryDesignerWidget(project, query_spec)
        widgets.append(query_designer)
        query_designer.run_preview()
        captured.append(_capture(app, query_designer, "16-query-designer.png", (1120, 760)))
    finally:
        for widget in reversed(widgets):
            widget.close()
            widget.deleteLater()
        app.processEvents()
        project.close()

    print(f"Tema: {resolved}")
    print(f"Immagini in {OUTPUT_DIR}")
    for path in captured:
        print(f"  - {path.name} ({path.stat().st_size} byte)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cattura headless delle finestre dBX")
    parser.add_argument("--theme", default="aurora", choices=["aurora", "bright", "light", "silver", "dark"])
    args = parser.parse_args(argv)
    try:
        return run(args.theme)
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
