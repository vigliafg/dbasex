"""Finestra principale di dBX (A4, G1–G6)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__
from ..config import add_recent, load_config, recent_projects, save_config
from ..core.form_model import FormSpec
from ..core.project import CATEGORY_LABELS, Project, ProjectError
from ..designers.form_builder import FormBuilderDialog
from ..designers.menu_builder import MenuBuilderDialog
from ..designers.project_builder import BuildError, build_project, validate_project
from ..designers.report_builder import ReportBuilderDialog
from ..designers.script_builder import QtScriptUI, ScriptBuilderDialog
from ..designers.table_builder import TableBuilderDialog
from ..runtime.form_runtime import FormPreviewDialog
from ..runtime.report_engine import ReportSpec
from ..runtime.script_engine import ScriptEngine
from . import design, icons
from .command_window import CommandWindow
from .data_view import DataView
from .navigator import Navigator
from .report_preview import ReportPreviewDialog
from .theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Impostazioni progetto")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.title_edit = QLineEdit(str(project.settings.get("title", project.caption)))
        form.addRow("Titolo applicazione", self.title_edit)
        self.form_combo = QComboBox()
        self.form_combo.addItem("(nessuno)", "")
        for name in project.names("forms"):
            self.form_combo.addItem(name, name)
        index = self.form_combo.findData(str(project.settings.get("main_form", "")))
        self.form_combo.setCurrentIndex(max(0, index))
        form.addRow("Form principale", self.form_combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self) -> None:
        self.project.settings["title"] = self.title_edit.text().strip()
        self.project.settings["main_form"] = self.form_combo.currentData() or ""


class MainWindow(QMainWindow):
    """Finestra principale con Navigator, schede e comandi di progetto."""

    def __init__(self, project: Project | None = None) -> None:
        super().__init__()
        self.project: Project | None = None
        self.command_window: CommandWindow | None = None
        self.config = load_config()
        self.setWindowTitle(f"{APP_NAME} — {__version__}")
        self.resize(1180, 780)
        self._build_ui()
        self._build_actions()
        if project is not None:
            self.set_project(project)
        self._update_actions()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.setCentralWidget(self.tabs)
        self.navigator = Navigator()
        self.navigator.open_object.connect(self.open_object)
        self.navigator.run_object.connect(self.run_object)
        self.navigator.new_object.connect(self.new_object)
        self.navigator.delete_object.connect(self.delete_object)
        dock = QWidget()
        layout = QVBoxLayout(dock)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.navigator)
        from PyQt6.QtWidgets import QDockWidget

        self.nav_dock = QDockWidget("Navigator", self)
        self.nav_dock.setObjectName("navigator")
        self.nav_dock.setWidget(dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_dock)
        self.project_label = QLabel("Nessun progetto")
        self.statusBar().addWidget(self.project_label, 1)
        self.object_label = QLabel("Oggetto: —")
        self.record_label = QLabel("Record: —")
        self.statusBar().addPermanentWidget(self.object_label)
        self.statusBar().addPermanentWidget(self.record_label)
        self.statusBar().addPermanentWidget(QLabel(f"dBX {__version__} · SQLite"))

    def _build_actions(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&Progetto")
        self.act_new = QAction("Nuovo progetto…", self, shortcut=QKeySequence.StandardKey.New)
        self.act_open = QAction("Apri progetto…", self, shortcut=QKeySequence.StandardKey.Open)
        self.act_save = QAction("Salva", self, shortcut=QKeySequence.StandardKey.Save)
        self.act_close = QAction("Chiudi progetto", self)
        self.act_settings = QAction("Impostazioni…", self)
        self.act_quit = QAction("Esci", self, shortcut=QKeySequence.StandardKey.Quit)
        for action in (self.act_new, self.act_open, self.act_save):
            file_menu.addAction(action)
        self._recent_menu = file_menu.addMenu("Progetti recenti")
        file_menu.addSeparator()
        file_menu.addAction(self.act_close)
        file_menu.addAction(self.act_quit)
        self.act_new.triggered.connect(self.new_project)
        self.act_open.triggered.connect(self.open_project)
        self.act_save.triggered.connect(self.save_project)
        self.act_close.triggered.connect(self.close_project)
        self.act_settings.triggered.connect(self.edit_settings)
        self.act_quit.triggered.connect(self.close)

        objects_menu = menu.addMenu("&Oggetto")
        self.act_table = QAction("Nuova tabella…", self)
        self.act_form = QAction("Nuovo form…", self)
        self.act_report = QAction("Nuovo report…", self)
        self.act_script = QAction("Nuovo script…", self)
        self.act_menu = QAction("Nuovo menu…", self)
        for action in (self.act_table, self.act_form, self.act_report, self.act_script, self.act_menu):
            objects_menu.addAction(action)
        self.act_table.triggered.connect(lambda: self.new_object("tables"))
        self.act_form.triggered.connect(lambda: self.new_object("forms"))
        self.act_report.triggered.connect(lambda: self.new_object("reports"))
        self.act_script.triggered.connect(lambda: self.new_object("scripts"))
        self.act_menu.triggered.connect(lambda: self.new_object("menus"))

        run_menu = menu.addMenu("&Procedure")
        self.act_run = QAction("Esegui progetto", self, shortcut="F5")
        self.act_validate = QAction("Valida progetto", self)
        self.act_build = QAction("Build distribuibile…", self)
        self.act_command = QAction("Finestra comandi", self, shortcut="Ctrl+K")
        self.act_demo = QAction("Crea progetto demo", self)
        for action in (self.act_run, self.act_validate, self.act_build, self.act_command):
            run_menu.addAction(action)
        run_menu.addSeparator()
        run_menu.addAction(self.act_demo)
        self.act_run.triggered.connect(self.run_project)
        self.act_validate.triggered.connect(self.validate_project_action)
        self.act_build.triggered.connect(self.build_project_action)
        self.act_command.triggered.connect(self.open_command_window)
        self.act_demo.triggered.connect(self.create_demo)

        view_menu = menu.addMenu("&Visualizza")
        self.act_dark = QAction("Tema scuro", self, checkable=True)
        self.act_dark.setChecked(self.config.get("theme") == "dark")
        self.act_dark.toggled.connect(self.toggle_theme)
        view_menu.addAction(self.act_dark)
        self.act_refresh = QAction("Aggiorna Navigator", self, shortcut="F5")
        self.act_refresh.setShortcut(QKeySequence("Ctrl+R"))
        self.act_refresh.triggered.connect(self._refresh_navigator)
        view_menu.addAction(self.act_refresh)

        properties_menu = menu.addMenu("&Proprietà")
        properties_menu.addAction(self.act_settings)

        window_menu = menu.addMenu("&Finestra")
        nav_toggle = self.nav_dock.toggleViewAction()
        nav_toggle.setText("Navigator")
        nav_toggle.setIcon(icons.icon("elenco"))
        window_menu.addAction(nav_toggle)
        window_menu.addAction(self.act_command)
        window_menu.addSeparator()
        self.act_close_tab = QAction("Chiudi scheda", self)
        self.act_close_tab.triggered.connect(lambda: self._close_tab(self.tabs.currentIndex()))
        window_menu.addAction(self.act_close_tab)

        help_menu = menu.addMenu("&?")
        self.act_about = icons.make_action("Informazioni su dBX", "aiuto", self)
        self.act_about.triggered.connect(self.show_about)
        help_menu.addAction(self.act_about)

        for action, glyph in (
            (self.act_new, "nuovo"),
            (self.act_open, "apri"),
            (self.act_save, "salva"),
            (self.act_close, "chiudi"),
            (self.act_settings, "impostazioni"),
            (self.act_quit, "annulla"),
            (self.act_table, "tabella"),
            (self.act_form, "form"),
            (self.act_report, "report"),
            (self.act_script, "script"),
            (self.act_menu, "menu"),
            (self.act_run, "esegui"),
            (self.act_validate, "ok"),
            (self.act_build, "esporta"),
            (self.act_command, "testo"),
            (self.act_demo, "campo"),
            (self.act_refresh, "aggiorna"),
        ):
            action.setIcon(icons.icon(glyph))
            action.setProperty("dbx_icon", glyph)

        toolbar = self.addToolBar("SpeedBar")
        toolbar.setObjectName("main_toolbar")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toolbar.setIconSize(QSize(16, 16))
        for text, action in (
            ("Nuovo", self.act_new),
            ("Apri", self.act_open),
            ("Salva", self.act_save),
            ("Tabella", self.act_table),
            ("Form", self.act_form),
            ("Report", self.act_report),
            ("Script", self.act_script),
            ("Menu", self.act_menu),
            ("Esegui", self.act_run),
            ("Valida", self.act_validate),
            ("Build", self.act_build),
            ("Comandi", self.act_command),
            ("Navigator", nav_toggle),
            ("Guida", self.act_about),
        ):
            action.setIconText(text)
        for group in (
            (self.act_new, self.act_open, self.act_save),
            (self.act_table, self.act_form, self.act_report, self.act_script, self.act_menu),
            (self.act_run, self.act_validate, self.act_build),
            (self.act_command, nav_toggle, self.act_about),
        ):
            for action in group:
                toolbar.addAction(action)
            toolbar.addSeparator()
        self._refresh_recent()

    # ----------------------------------------------------------------- progetto
    def set_project(self, project: Project) -> None:
        self.project = project
        self.navigator.set_project(project)
        title = str(project.settings.get("title") or project.caption or project.name)
        self.setWindowTitle(f"{APP_NAME} — {title}")
        self.project_label.setText(f"{project.name} — {project.path}")
        self._refresh_recent()
        self._update_actions()
        add_recent(project.path)

    def new_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Cartella del nuovo progetto")
        if not folder:
            return
        name, ok = QInputDialog.getText(self, "Nuovo progetto", "Nome del progetto:", text=Path(folder).name)
        if not ok or not name.strip():
            return
        try:
            project = Project.create(folder, name.strip())
        except ProjectError as exc:
            QMessageBox.warning(self, "Progetto non creato", str(exc))
            return
        self._adopt(project)
        self.statusBar().showMessage("Progetto creato", 4000)

    def open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Apri progetto dBX", str(Path.home()), "Progetto dBX (project.dbx.json);;Tutti i file (*)"
        )
        if not path:
            return
        try:
            project = Project.open(path)
        except ProjectError as exc:
            answer = QMessageBox.question(
                self,
                "Apertura non riuscita",
                f"{exc}\n\nForzare l'apertura?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                project = Project.open(path, force=True)
            except ProjectError as exc2:
                QMessageBox.critical(self, "Apertura non riuscita", str(exc2))
                return
        self._adopt(project)

    def open_recent(self, path: str) -> None:
        try:
            project = Project.open(path)
        except ProjectError as exc:
            QMessageBox.warning(self, "Apertura non riuscita", str(exc))
            return
        self._adopt(project)

    def _adopt(self, project: Project) -> None:
        if self.project is not None:
            self.close_project()
        self.set_project(project)
        self.statusBar().showMessage(f"Progetto {project.name} aperto", 4000)

    def save_project(self) -> None:
        if self.project is None:
            return
        try:
            self.project.save()
        except OSError as exc:
            QMessageBox.warning(self, "Salvataggio non riuscito", str(exc))
            return
        self.statusBar().showMessage("Progetto salvato", 3000)

    def close_project(self) -> None:
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if widget is not None:
                widget.deleteLater()
        if self.project is not None:
            try:
                self.project.save()
            except OSError:
                pass
            self.project.close()
        self.project = None
        self.navigator.set_project(None)
        self.project_label.setText("Nessun progetto")
        self.object_label.setText("Oggetto: —")
        self.record_label.setText("Record: —")
        if self.command_window is not None:
            self.command_window.close()
            self.command_window = None
        self.setWindowTitle(f"{APP_NAME} — {__version__}")
        self._update_actions()

    def edit_settings(self) -> None:
        if self.project is None:
            return
        dialog = SettingsDialog(self.project, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.apply()
            self.project.save()
            self.set_project(self.project)

    # ---------------------------------------------------------------- oggetti
    def _require_project(self) -> bool:
        if self.project is None:
            QMessageBox.information(self, "dBX", "Apri o crea prima un progetto.")
            return False
        return True

    def _unique_name(self, category: str, base: str) -> str:
        assert self.project is not None
        base = base.strip() or "oggetto"
        existing = {name.lower() for name in self.project.names(category)}
        if base.lower() not in existing:
            return base
        index = 2
        while f"{base}_{index}".lower() in existing:
            index += 1
        return f"{base}_{index}"

    def new_object(self, category: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        if category == "tables":
            dialog = TableBuilderDialog(self.project, None, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_navigator()
                self.open_object("tables", dialog.table.name)
            return
        if category in ("forms", "reports"):
            tables = self.project.names("tables")
            if not tables:
                QMessageBox.information(self, "dBX", "Crea prima una tabella.")
                return
            table_name, ok = QInputDialog.getItem(self, "Nuovo oggetto", "Tabella di riferimento:", tables, 0, False)
            if not ok:
                return
            table = self.project.require_table(table_name)
            if category == "forms":
                spec = FormSpec.create(table, name=self._unique_name("forms", f"form_{table.name}"))
                dialog = FormBuilderDialog(self.project, spec, self)
            else:
                spec = ReportSpec.create(
                    self._unique_name("reports", f"report_{table.name}"), table.name, f"Report {table.display_name()}"
                )
                spec.bands["detail"][0].expr = table.fields[0].name
                dialog = ReportBuilderDialog(self.project, spec, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_navigator()
            return
        if category == "scripts":
            dialog = ScriptBuilderDialog(
                self.project, {"name": self._unique_name("scripts", "script"), "steps": []}, self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_navigator()
            return
        if category == "menus":
            dialog = MenuBuilderDialog(
                self.project, {"name": self._unique_name("menus", "principale"), "items": []}, self
            )
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self._refresh_navigator()

    def open_object(self, category: str, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        self.object_label.setText(f"Oggetto: {name}")
        try:
            if category == "tables":
                view = DataView(self.project, name)
                view.status_changed.connect(self.record_label.setText)
                self._open_tab(f"tabella:{name}", name, view)
            elif category == "forms":
                artifact = self.project.artifact("forms", name)
                if artifact is None:
                    return
                FormBuilderDialog(self.project, FormSpec.from_dict(artifact), self).exec()
                self._refresh_navigator()
            elif category == "reports":
                artifact = self.project.artifact("reports", name)
                if artifact is None:
                    return
                ReportBuilderDialog(self.project, ReportSpec.from_dict(artifact), self).exec()
                self._refresh_navigator()
            elif category == "scripts":
                artifact = self.project.artifact("scripts", name)
                if artifact is None:
                    return
                ScriptBuilderDialog(self.project, artifact, self).exec()
                self._refresh_navigator()
            elif category == "menus":
                artifact = self.project.artifact("menus", name)
                if artifact is None:
                    return
                MenuBuilderDialog(self.project, artifact, self).exec()
                self._refresh_navigator()
        except ValueError as exc:
            QMessageBox.warning(self, "Oggetto non apribile", str(exc))

    def run_object(self, category: str, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        if category == "tables":
            self.open_object(category, name)
        elif category == "forms":
            artifact = self.project.artifact("forms", name)
            if artifact:
                dialog = FormPreviewDialog(self.project, FormSpec.from_dict(artifact), self)
                dialog.exec()
        elif category == "reports":
            dialog = ReportPreviewDialog(self.project, name, self)
            dialog.exec()
        elif category == "scripts":
            artifact = self.project.artifact("scripts", name)
            if artifact:
                engine = ScriptEngine(self.project, QtScriptUI(self.project, self))
                result = engine.run(artifact.get("steps", []))
                if result.error:
                    QMessageBox.warning(self, "Script", result.error)
                else:
                    QMessageBox.information(self, "Script", "\n".join(result.log[-12:]) or "Eseguito")

    def delete_object(self, category: str, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        answer = QMessageBox.question(
            self,
            "Elimina oggetto",
            f"Eliminare {CATEGORY_LABELS.get(category, category)} «{name}»?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            if category == "tables":
                self.project.drop_table(name)
            else:
                self.project.remove_object(category, name)
                self.project.save()
        except ProjectError as exc:
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self._refresh_navigator()

    # ------------------------------------------------------------------ schede
    def _open_tab(self, key: str, title: str, widget: QWidget) -> None:
        for index in range(self.tabs.count()):
            if self.tabs.widget(index).property("dbx_key") == key:
                self.tabs.setCurrentIndex(index)
                return
        widget.setProperty("dbx_key", key)
        self.tabs.addTab(widget, title)
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def _close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget is not None:
            widget.deleteLater()

    def _refresh_navigator(self) -> None:
        self.navigator.set_project(self.project)

    # ------------------------------------------------------------------ comandi
    def run_project(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        main_form = str(self.project.settings.get("main_form", ""))
        if not main_form:
            forms = self.project.names("forms")
            main_form = forms[0] if forms else ""
        if not main_form:
            QMessageBox.information(self, "dBX", "Il progetto non ha form da eseguire.")
            return
        if self.project.artifact("forms", main_form) is None:
            QMessageBox.warning(self, "dBX", f"Form principale inesistente: {main_form}")
            return
        from .project_runner import ProjectRunner

        menu_name = str(self.project.settings.get("main_menu", ""))
        ProjectRunner(self.project, main_form, menu_name, self).exec()

    def validate_project_action(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        errors = validate_project(self.project)
        if errors:
            QMessageBox.warning(self, "Validazione", "\n".join(errors[:25]))
        else:
            QMessageBox.information(self, "Validazione", "Progetto valido: nessun problema rilevato.")

    def build_project_action(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        folder = QFileDialog.getExistingDirectory(self, "Cartella di destinazione del build")
        if not folder:
            return
        try:
            target = build_project(self.project, Path(folder))
        except BuildError as exc:
            QMessageBox.warning(self, "Build non riuscita", str(exc))
            return
        QMessageBox.information(self, "Build completato", f"Creato:\n{target}")

    def open_command_window(self) -> None:
        if not self._require_project():
            return
        if getattr(self, "command_window", None) is not None and self.command_window.isVisible():
            self.command_window.raise_()
            self.command_window.activateWindow()
            return
        self.command_window = CommandWindow(self.project, self)
        self.command_window.show()
        self.command_window.raise_()

    def create_demo(self) -> None:
        from ..samples import create_demo_project
        import tempfile

        folder = Path(tempfile.mkdtemp(prefix="dbx-demo-")) / "Rubrica"
        try:
            project = create_demo_project(folder)
        except Exception as exc:  # pragma: no cover - difensivo
            QMessageBox.critical(self, "Demo non creata", str(exc))
            return
        self._adopt(project)
        self.statusBar().showMessage(f"Demo creata in {folder}", 6000)

    def toggle_theme(self, dark: bool) -> None:
        theme = "dark" if dark else design.DEFAULT_THEME
        self.config["theme"] = theme
        save_config(self.config)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme)

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "Informazioni su dBX",
            f"<b>dBX {__version__}</b><br>"
            "Personal database multipiattaforma ispirato a dBASE 5.5 for Windows.<br>"
            "Motore SQLite, interfaccia PyQt6.<br><br>"
            "Table Builder · Form/Table Builder · Report Builder · MiniScript · Project Builder",
        )

    def _refresh_recent(self) -> None:
        self._recent_menu.clear()
        entries = recent_projects()
        if not entries:
            self._recent_menu.addAction("(nessun progetto recente)").setEnabled(False)
            return
        for path in entries:
            action = QAction(path, self)
            action.triggered.connect(lambda _checked=False, p=path: self.open_recent(p))
            self._recent_menu.addAction(action)

    def _update_actions(self) -> None:
        enabled = self.project is not None
        for action in (
            getattr(self, "act_save", None),
            getattr(self, "act_close", None),
            getattr(self, "act_settings", None),
            getattr(self, "act_table", None),
            getattr(self, "act_form", None),
            getattr(self, "act_report", None),
            getattr(self, "act_script", None),
            getattr(self, "act_menu", None),
            getattr(self, "act_run", None),
            getattr(self, "act_validate", None),
            getattr(self, "act_build", None),
            getattr(self, "act_command", None),
        ):
            if action is not None:
                action.setEnabled(enabled)

    def closeEvent(self, event) -> None:  # noqa: D102
        self.config["window"] = {
            "width": self.width(),
            "height": self.height(),
            "x": self.x(),
            "y": self.y(),
        }
        save_config(self.config)
        if self.project is not None:
            try:
                self.project.save()
            except OSError:
                pass
            self.project.close()
        super().closeEvent(event)
