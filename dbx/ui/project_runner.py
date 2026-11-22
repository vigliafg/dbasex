"""Esecuzione del progetto: menu runtime + form principale (G2, G4)."""

from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QMenuBar,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import FormSpec
from ..core.project import Project
from ..designers.script_builder import QtScriptUI
from ..runtime.form_runtime import FormRuntime
from ..runtime.script_engine import ScriptEngine
from .report_preview import ReportPreviewDialog


class ProjectRunner(QDialog):
    """Esegue l'applicazione: menu del progetto + form principale."""

    def __init__(
        self,
        project: Project,
        form_name: str = "",
        menu_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(str(project.settings.get("title") or project.name))
        self.resize(980, 720)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.menu_bar = QMenuBar(self)
        layout.addWidget(self.menu_bar)
        self.body = QWidget(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.body, 1)
        self._build_menu(menu_name)
        self.current: FormRuntime | None = None
        if form_name:
            self.open_form(form_name)

    # ------------------------------------------------------------------ menu
    def _build_menu(self, menu_name: str) -> None:
        names = self.project.names("menus")
        if not names:
            file_menu = self.menu_bar.addMenu("&Progetto")
            quit_action = QAction("Esci", self)
            quit_action.triggered.connect(self.accept)
            file_menu.addAction(quit_action)
            return
        selected = menu_name if self.project.artifact("menus", menu_name) else names[0]
        artifact = self.project.artifact("menus", selected) or {}
        menu = self.menu_bar.addMenu(selected)
        for item in artifact.get("items", []):
            action = item.get("action")
            if action == "separator":
                menu.addSeparator()
                continue
            if action == "quit":
                entry = QAction(item.get("label", "Esci"), self)
                entry.triggered.connect(self.accept)
                menu.addAction(entry)
                continue
            entry = QAction(item.get("label", "Voce"), self)
            target = str(item.get("target", ""))
            entry.triggered.connect(lambda _checked=False, a=action, t=target: self._dispatch(a, t))
            menu.addAction(entry)
        menu.addSeparator()
        quit_action = QAction("Esci", self)
        quit_action.triggered.connect(self.accept)
        menu.addAction(quit_action)

    def _dispatch(self, action: str, target: str) -> None:
        if action == "open_form":
            self.open_form(target)
        elif action == "open_report":
            try:
                ReportPreviewDialog(self.project, target, self).exec()
            except ValueError as exc:
                QMessageBox.warning(self, "Report", str(exc))
        elif action == "run_script":
            engine = ScriptEngine(self.project, QtScriptUI(self.project, self))
            artifact = self.project.artifact("scripts", target)
            if artifact is None:
                QMessageBox.warning(self, "Script", f"Script inesistente: {target}")
                return
            result = engine.run(artifact.get("steps", []))
            if result.error:
                QMessageBox.warning(self, "Script", result.error)

    # ------------------------------------------------------------------ form
    def open_form(self, name: str) -> None:
        artifact = self.project.artifact("forms", name)
        if artifact is None:
            QMessageBox.warning(self, "Form", f"Form inesistente: {name}")
            return
        if self.current is not None:
            self.current.setParent(None)
            self.current.deleteLater()
        try:
            self.current = FormRuntime(self.project, FormSpec.from_dict(artifact), parent=self.body)
        except Exception as exc:  # pragma: no cover - difensivo
            QMessageBox.warning(self, "Form", str(exc))
            return
        self.body_layout.addWidget(self.current)
        self.setWindowTitle(f"{self.project.name} — {name}")
