"""Entry point di dBX: `python -m dbx [progetto]`."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dbx", description="dBX — personal database in stile dBASE 5.5")
    parser.add_argument("project", nargs="?", help="cartella o file project.dbx.json da aprire")
    parser.add_argument("--demo", action="store_true", help="crea e apre un progetto dimostrativo")
    parser.add_argument("--smoke", action="store_true", help="verifica headless di app, report e build")
    parser.add_argument(
        "--theme", choices=["silver", "light", "dark"], help="tema dell'interfaccia (silver è il default)"
    )
    parser.add_argument("--version", action="version", version=f"dBX {__version__}")
    args = parser.parse_args(argv)

    if args.smoke:
        from .smoke import run_smoke

        return run_smoke()

    from PyQt6.QtWidgets import QMessageBox

    from .config import load_config
    from .core.project import Project, ProjectError
    from .samples import create_demo_project
    from .ui.app import create_application, splash
    from .ui.main_window import MainWindow

    config = load_config()
    theme = args.theme or str(config.get("theme", "silver"))
    app = create_application(sys.argv, theme)
    splash_screen = splash(theme)
    splash_screen.show()
    app.processEvents()

    project = None
    if args.project:
        try:
            project = Project.open(args.project)
        except ProjectError as exc:
            QMessageBox.critical(None, "Apertura non riuscita", str(exc))
            return 2
    elif args.demo:
        project = create_demo_project(Path(tempfile.mkdtemp(prefix="dbx-demo-")) / "Rubrica")

    window = MainWindow(project)
    window.show()
    splash_screen.finish(window)
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
