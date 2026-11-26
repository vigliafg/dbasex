"""Contesto E2E 2.0: estende il contesto storico con helper UI e di verifica."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from e2e_scenarios import HarnessContext, ScenarioFailure
from dbx.core.project import Project

from . import ui


class E2EContext(HarnessContext):
    """Contesto condiviso dagli scenari granulari."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.widgets: list[Any] = []

    def begin(self, scenario: str) -> None:
        super().begin(scenario)
        self.widgets = []

    def finish(self) -> None:
        for widget in reversed(self.widgets):
            try:
                widget.close()
                widget.deleteLater()
            except Exception:
                pass
        self.widgets = []
        super().finish()

    # ------------------------------------------------------------- progetti
    def new_project(self, name: str = "E2E") -> Project:
        return super().new_project(name)

    def reopen(self, project: Project) -> Project:
        """Salva, chiude e riapre il progetto verificando la persistenza."""

        path = project.path
        project.save()
        project.close()
        reopened = Project.open(path)
        self.projects = [item for item in self.projects if item is not project]
        self.projects.append(reopened)
        return reopened

    # ---------------------------------------------------------------- widget
    def track(self, widget: Any) -> Any:
        self.widgets.append(widget)
        return widget

    def main_window(self, project: Project | None = None):
        from dbx.ui.main_window import MainWindow

        window = MainWindow(project)
        return self.track(window)

    def table_builder(self, project: Project, table=None):
        from dbx.designers.table_builder import TableBuilderDialog

        builder = TableBuilderDialog(project, table)
        return self.track(builder)

    def data_view(self, project: Project, table_name: str):
        from dbx.ui.data_view import DataView

        view = DataView(project, table_name)
        return self.track(view)

    def capture(self, widget: Any, name: str, size: tuple[int, int] | None = None) -> str | None:
        result = super().capture(widget, name, size)
        return result

    # -------------------------------------------------------------- verifiche
    def check_close(self, actual: Any, expected: Any, name: str) -> None:
        self.check(actual == expected, name, f"atteso {expected!r}, ottenuto {actual!r}")

    def check_contains(self, container: Any, item: Any, name: str) -> None:
        self.check(item in container, name, f"{item!r} non presente")

    @contextmanager
    def expect_error(self, exc_type: type[BaseException], contains: str = "") -> Iterator[None]:
        """Verifica che il blocco sollevi l'errore atteso (e solo quello)."""

        try:
            yield
        except exc_type as exc:
            message = str(exc)
            ok = contains.lower() in message.lower() if contains else True
            self.check(
                ok,
                f"errore atteso {exc_type.__name__}",
                f"atteso «{contains}», ottenuto «{message}»",
            )
        except Exception as exc:  # noqa: BLE001 - messaggio diagnostico
            self.check(
                False,
                f"errore atteso {exc_type.__name__}",
                f"ricevuto {type(exc).__name__}: {exc}",
            )
        else:
            self.check(False, f"errore atteso {exc_type.__name__}", "nessun errore sollevato")

    # ------------------------------------------------------------------ SQL
    @contextmanager
    def sql_statements(self, project: Project) -> Iterator[list[str]]:
        """Registra gli statement SQL eseguiti sul database del progetto."""

        statements: list[str] = []
        connection: sqlite3.Connection = project.db.con

        def trace(statement: str) -> None:
            statements.append(statement)

        connection.set_trace_callback(trace)
        try:
            yield statements
        finally:
            connection.set_trace_callback(None)

    # ------------------------------------------------------------------ file
    def artifact_path(self, project: Project, category: str, name: str) -> Path:
        from dbx.core.metadata import slugify

        suffixes = {
            "tables": "table",
            "diagrams": "diagram",
            "queries": "query",
            "forms": "form",
            "reports": "report",
            "labels": "label",
            "scripts": "script",
            "menus": "menu",
        }
        return project.objects_path / category / f"{slugify(name)}.{suffixes[category]}.json"

    def read_artifact(self, project: Project, category: str, name: str) -> dict[str, Any]:
        import json

        path = self.artifact_path(project, category, name)
        self.check(path.exists(), f"artefatto {category}/{name} su disco", str(path))
        return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["E2EContext", "ScenarioFailure", "ui"]
