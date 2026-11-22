"""Cattura headless delle finestre dBX per il QA visivo.

Uso:

    python tools/capture_ui.py [--theme silver|dark]

Le immagini vengono salvate in ``docs/reference/dbx-ui/renders/``.
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

from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402

from dbx.core.form_model import FormSpec  # noqa: E402
from dbx.designers.form_builder import FormBuilderDialog  # noqa: E402
from dbx.designers.report_builder import ReportBuilderDialog  # noqa: E402
from dbx.designers.table_builder import TableBuilderDialog  # noqa: E402
from dbx.runtime.form_runtime import FormPreviewDialog  # noqa: E402
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


def run(theme: str = "silver") -> int:
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
        form_dialog = FormBuilderDialog(project, form_spec)
        widgets.append(form_dialog)
        captured.append(_capture(app, form_dialog, "05-form-designer.png", (1160, 760)))

        form_preview = FormPreviewDialog(project, FormSpec.from_dict(form_artifact))
        widgets.append(form_preview)
        captured.append(_capture(app, form_preview, "06-form-runtime.png", (760, 560)))

        report_artifact = project.artifact("reports", "fatture_per_cliente")
        if report_artifact is None:
            raise RuntimeError("fatture_per_cliente non presente nel progetto demo")
        report_dialog = ReportBuilderDialog(project, ReportSpec.from_dict(report_artifact))
        widgets.append(report_dialog)
        captured.append(_capture(app, report_dialog, "07-report-designer.png", (1140, 780)))

        report_preview = ReportPreviewDialog(project, ReportSpec.from_dict(report_artifact))
        widgets.append(report_preview)
        captured.append(_capture(app, report_preview, "08-report-preview.png", (940, 800)))

        command_window = CommandWindow(project)
        widgets.append(command_window)
        captured.append(_capture(app, command_window, "09-command-window.png", (760, 520)))
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
    parser.add_argument("--theme", default="silver", choices=["silver", "light", "dark"])
    args = parser.parse_args(argv)
    try:
        return run(args.theme)
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
