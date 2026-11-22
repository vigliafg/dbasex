"""Finestra principale di dBX: shell MDI, menu, SpeedBar e status bar (A4, G1–G6)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtGui import QAction, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMdiArea,
    QToolBar,
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
from .editor_host import EditorHost, editor_title, editor_widget
from .navigator import Navigator
from .report_preview import ReportPreviewDialog
from .theme import apply_theme

OBJECT_ICONS = {
    "tables": "tabella",
    "forms": "form",
    "reports": "report",
    "scripts": "script",
    "menus": "menu",
}

MODES = {
    "DataView": "Sfoglia",
    "TableBuilderDialog": "Struttura",
    "FormBuilderDialog": "Design",
    "ReportBuilderDialog": "Design",
    "ScriptBuilderDialog": "Modifica",
    "MenuBuilderDialog": "Design",
    "FormPreviewDialog": "Esecuzione",
    "ReportPreviewDialog": "Anteprima",
}

EDIT_METHODS = {
    "undo": "undo",
    "redo": "redo",
    "cut": "cut",
    "copy": "copy",
    "paste": "paste",
}


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
    """Desktop dBX: Navigator a sinistra, area MDI al centro, status bar a riquadri."""

    def __init__(self, project: Project | None = None) -> None:
        super().__init__()
        self.project: Project | None = None
        self.command_window: CommandWindow | None = None
        self.config = load_config()
        self._filter_app: QApplication | None = None
        self.setWindowTitle(f"{APP_NAME} — {__version__}")
        self.resize(1180, 780)
        self._build_ui()
        self._build_actions()
        if project is not None:
            self.set_project(project)
        self._update_actions()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        self._build_mdi()
        self._build_navigator()
        self._build_statusbar()
        self._install_position_filter()

    def _build_mdi(self) -> None:
        self.mdi = QMdiArea(self)
        self.mdi.setObjectName("mdi_area")
        self.mdi.setViewMode(QMdiArea.ViewMode.SubWindowView)
        self.mdi.setOption(QMdiArea.AreaOption.DontMaximizeSubWindowOnActivation, True)
        self.setCentralWidget(self.mdi)
        self.editors = EditorHost(self.mdi, self)
        self.editors.activated.connect(self._on_editor_activated)
        self.editors.closed.connect(self._on_editor_closed)
        self.editors.opened.connect(self._on_editor_opened)

    def _build_navigator(self) -> None:
        self.navigator = Navigator()
        self.navigator.open_object.connect(self.open_object)
        self.navigator.run_object.connect(self.run_object)
        self.navigator.new_object.connect(self.new_object)
        self.navigator.delete_object.connect(self.delete_object)
        dock = QWidget()
        layout = QVBoxLayout(dock)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.navigator)
        self.nav_dock = QDockWidget("Navigator", self)
        self.nav_dock.setObjectName("navigator")
        self.nav_dock.setWidget(dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.nav_dock)

    def _build_statusbar(self) -> None:
        bar = self.statusBar()
        bar.setSizeGripEnabled(False)
        bar.setFixedHeight(design.METRICS.status_height)
        self.project_label = QLabel("Nessun progetto")
        self.project_label.setContentsMargins(4, 0, 4, 0)
        bar.addWidget(self.project_label, 1)
        self.pos_label = self._status_field("Pos: —", 90)
        self.object_label = self._status_field("Oggetto: —", 220)
        self.record_label = self._status_field("Record: —", 160)
        self.mode_label = self._status_field("Modalità: —", 120)
        for label in (self.pos_label, self.object_label, self.record_label, self.mode_label):
            bar.addPermanentWidget(label)
        bar.addPermanentWidget(self._status_field(f"dBX {__version__}", 120))

    def _status_field(self, text: str, width: int) -> QLabel:
        label = QLabel(text)
        label.setObjectName("status_field")
        label.setMinimumWidth(width)
        label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        return label

    def _install_position_filter(self) -> None:
        app = QApplication.instance()
        if app is not None:
            self._filter_app = app
            app.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: D102 - API Qt
        if event.type() == QEvent.Type.MouseMove and isinstance(obj, QWidget) and obj.window() is self:
            point = event.position().toPoint()
            mapped = obj.mapTo(self, point)
            self.pos_label.setText(f"Pos: {mapped.x()},{mapped.y()}")
        return super().eventFilter(obj, event)

    # --------------------------------------------------------------- azioni
    def _build_actions(self) -> None:
        self._build_file_actions()
        self._build_edit_actions()
        self._build_view_actions()
        self._build_object_actions()
        self._build_procedure_actions()
        self._build_properties_actions()
        self._build_window_actions()
        self._build_help_actions()
        self._build_menus()
        self._build_toolbar()
        self._refresh_recent()
        self._refresh_window_menu()
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._update_edit_actions)

    def _build_file_actions(self) -> None:
        self.act_new = icons.make_action(
            "Nuovo progetto…", "nuovo", self, QKeySequence.StandardKey.New
        )
        self.act_open = icons.make_action(
            "Apri progetto…", "apri", self, QKeySequence.StandardKey.Open
        )
        self.act_save = icons.make_action(
            "Salva progetto", "salva", self, QKeySequence.StandardKey.Save
        )
        self.act_print = icons.make_action("Stampa…", "stampa", self)
        self.act_close = icons.make_action("Chiudi progetto", "chiudi", self)
        self.act_quit = icons.make_action(
            "Esci", "annulla", self, QKeySequence.StandardKey.Quit
        )
        self.act_new.triggered.connect(self.new_project)
        self.act_open.triggered.connect(self.open_project)
        self.act_save.triggered.connect(self.save_project)
        self.act_print.triggered.connect(self.print_current)
        self.act_close.triggered.connect(self.close_project)
        self.act_quit.triggered.connect(self.close)

    def _build_edit_actions(self) -> None:
        self.act_undo = icons.make_action(
            "Annulla", "undo", self, QKeySequence.StandardKey.Undo
        )
        self.act_redo = icons.make_action(
            "Ripeti", "redo", self, QKeySequence.StandardKey.Redo
        )
        self.act_cut = icons.make_action(
            "Taglia", "taglia", self, QKeySequence.StandardKey.Cut
        )
        self.act_copy = icons.make_action(
            "Copia", "copia", self, QKeySequence.StandardKey.Copy
        )
        self.act_paste = icons.make_action(
            "Incolla", "incolla", self, QKeySequence.StandardKey.Paste
        )
        self.act_delete = icons.make_action(
            "Elimina", "elimina", self, QKeySequence.StandardKey.Delete
        )
        for action, method in (
            (self.act_undo, "undo"),
            (self.act_redo, "redo"),
            (self.act_cut, "cut"),
            (self.act_copy, "copy"),
            (self.act_paste, "paste"),
        ):
            action.triggered.connect(lambda _checked=False, m=method: self._dispatch_edit(m))
        self.act_delete.triggered.connect(self._dispatch_delete)

    def _build_view_actions(self) -> None:
        self.act_speedbar = icons.make_action("SpeedBar", None, self, checkable=True)
        self.act_speedbar.setChecked(True)
        self.act_statusbar = icons.make_action("Barra di stato", None, self, checkable=True)
        self.act_statusbar.setChecked(True)
        self.act_zoom_in = icons.make_action(
            "Aumenta zoom", "zoom_in", self, QKeySequence("Ctrl++")
        )
        self.act_zoom_out = icons.make_action(
            "Riduci zoom", "zoom_out", self, QKeySequence("Ctrl+-")
        )
        self.act_zoom_reset = icons.make_action(
            "Zoom 100%", None, self, QKeySequence("Ctrl+0")
        )
        self.act_align = icons.make_action("Allinea", "allinea", self)
        self.act_align.setToolTip("Allinea i controlli selezionati (Form Designer, O4)")
        self.act_distribute = icons.make_action("Distribuisci", "distribuisci", self)
        self.act_distribute.setToolTip("Distribuisci i controlli selezionati (Form Designer, O4)")
        self.act_refresh = icons.make_action(
            "Aggiorna Navigator", "aggiorna", self, QKeySequence("Ctrl+R")
        )
        self.act_speedbar.toggled.connect(self._toggle_speedbar)
        self.act_statusbar.toggled.connect(self._toggle_statusbar)
        self.act_zoom_in.triggered.connect(lambda: self._zoom(1.25))
        self.act_zoom_out.triggered.connect(lambda: self._zoom(0.8))
        self.act_zoom_reset.triggered.connect(self._zoom_reset)
        self.act_align.triggered.connect(lambda: self._dispatch_editor("align_selection"))
        self.act_distribute.triggered.connect(
            lambda: self._dispatch_editor("distribute_selection")
        )
        self.act_refresh.triggered.connect(self._refresh_navigator)

    def _build_object_actions(self) -> None:
        self.act_table = icons.make_action("Nuova tabella…", "tabella", self)
        self.act_form = icons.make_action("Nuovo form…", "form", self)
        self.act_report = icons.make_action("Nuovo report…", "report", self)
        self.act_script = icons.make_action("Nuovo script…", "script", self)
        self.act_menu = icons.make_action("Nuovo menu…", "menu", self)
        self.act_table.triggered.connect(lambda: self.new_object("tables"))
        self.act_form.triggered.connect(lambda: self.new_object("forms"))
        self.act_report.triggered.connect(lambda: self.new_object("reports"))
        self.act_script.triggered.connect(lambda: self.new_object("scripts"))
        self.act_menu.triggered.connect(lambda: self.new_object("menus"))

    def _build_procedure_actions(self) -> None:
        self.act_run = icons.make_action("Esegui progetto", "esegui", self, "F5")
        self.act_validate = icons.make_action("Valida progetto", "ok", self)
        self.act_build = icons.make_action("Build distribuibile…", "esporta", self)
        self.act_command = icons.make_action("Command Window", "testo", self, "Ctrl+K")
        self.act_demo = icons.make_action("Crea progetto demo", "campo", self)
        self.act_run.triggered.connect(self.run_project)
        self.act_validate.triggered.connect(self.validate_project_action)
        self.act_build.triggered.connect(self.build_project_action)
        self.act_command.triggered.connect(self.open_command_window)
        self.act_demo.triggered.connect(self.create_demo)

    def _build_properties_actions(self) -> None:
        self.act_settings = icons.make_action("Impostazioni…", "impostazioni", self)
        self.act_settings.triggered.connect(self.edit_settings)

    def _build_window_actions(self) -> None:
        self.act_cascade = icons.make_action("Sovrapponi", "cascata", self)
        self.act_tile = icons.make_action("Affianca", "affianca", self)
        self.act_close_window = icons.make_action(
            "Chiudi finestra", "chiudi", self, QKeySequence.StandardKey.Close
        )
        self.act_close_all = icons.make_action("Chiudi tutte le finestre", "annulla", self)
        self.act_cascade.triggered.connect(self.editors.cascade)
        self.act_tile.triggered.connect(self.editors.tile)
        self.act_close_window.triggered.connect(self.editors.close_current)
        self.act_close_all.triggered.connect(self.editors.close_all)

    def _build_help_actions(self) -> None:
        self.act_about = icons.make_action("Informazioni su dBX", "aiuto", self)
        self.act_guide = icons.make_action("Guida rapida", "aiuto", self, "F1")
        self.act_about.triggered.connect(self.show_about)
        self.act_guide.triggered.connect(self.show_help)

    def _build_menus(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&Progetto")
        for action in (self.act_new, self.act_open, self.act_save):
            file_menu.addAction(action)
        self._recent_menu = file_menu.addMenu("Progetti recenti")
        file_menu.addSeparator()
        file_menu.addAction(self.act_close)
        file_menu.addAction(self.act_quit)

        edit_menu = menu.addMenu("&Modifica")
        for action in (self.act_undo, self.act_redo):
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        for action in (self.act_cut, self.act_copy, self.act_paste):
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_delete)

        view_menu = menu.addMenu("&Visualizza")
        view_menu.addAction(self.act_speedbar)
        view_menu.addAction(self.act_statusbar)
        view_menu.addSeparator()
        for action in (self.act_zoom_in, self.act_zoom_out, self.act_zoom_reset):
            view_menu.addAction(action)
        view_menu.addSeparator()
        view_menu.addAction(self.act_refresh)

        objects_menu = menu.addMenu("&Oggetto")
        for action in (
            self.act_table,
            self.act_form,
            self.act_report,
            self.act_script,
            self.act_menu,
        ):
            objects_menu.addAction(action)

        run_menu = menu.addMenu("&Procedure")
        for action in (self.act_run, self.act_validate, self.act_build):
            run_menu.addAction(action)
        run_menu.addSeparator()
        run_menu.addAction(self.act_command)
        run_menu.addSeparator()
        run_menu.addAction(self.act_demo)

        properties_menu = menu.addMenu("&Proprietà")
        properties_menu.addAction(self.act_settings)

        self._window_menu = menu.addMenu("&Finestra")
        self._window_actions: list[tuple[object, QAction]] = []

        help_menu = menu.addMenu("&?")
        help_menu.addAction(self.act_guide)
        help_menu.addAction(self.act_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("SpeedBar", self)
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(design.METRICS.icon_size, design.METRICS.icon_size))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        groups = (
            (self.act_new, self.act_open, self.act_save, self.act_print),
            (self.act_cut, self.act_copy, self.act_paste),
            (self.act_undo, self.act_redo),
            (self.act_table, self.act_form, self.act_report, self.act_script, self.act_menu),
            (self.act_align, self.act_distribute),
            (self.act_run,),
            (self.act_command,),
            (self.act_guide,),
        )
        for group in groups:
            for action in group:
                shortcut = action.shortcut().toString()
                action.setToolTip(action.text() + (f" ({shortcut})" if shortcut else ""))
                toolbar.addAction(action)
            toolbar.addSeparator()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.toolbar = toolbar

    # ------------------------------------------------------------- progetto
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
        name, ok = QInputDialog.getText(
            self, "Nuovo progetto", "Nome del progetto:", text=Path(folder).name
        )
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
            self,
            "Apri progetto dBX",
            str(Path.home()),
            "Progetto dBX (project.dbx.json);;Tutti i file (*)",
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
        self.editors.close_all()
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
        self.mode_label.setText("Modalità: —")
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

    # -------------------------------------------------------------- oggetti
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
            dialog.accepted.connect(lambda: self._after_new_table(dialog))
            self._open_designer(f"tables:new:{id(dialog)}", dialog, "tables")
            return
        if category in ("forms", "reports"):
            tables = self.project.names("tables")
            if not tables:
                QMessageBox.information(self, "dBX", "Crea prima una tabella.")
                return
            table_name, ok = QInputDialog.getItem(
                self, "Nuovo oggetto", "Tabella di riferimento:", tables, 0, False
            )
            if not ok:
                return
            table = self.project.require_table(table_name)
            if category == "forms":
                spec = FormSpec.create(
                    table, name=self._unique_name("forms", f"form_{table.name}")
                )
                dialog = FormBuilderDialog(self.project, spec, self)
            else:
                spec = ReportSpec.create(
                    self._unique_name("reports", f"report_{table.name}"),
                    table.name,
                    f"Report {table.display_name()}",
                )
                spec.bands["detail"][0].expr = table.fields[0].name
                dialog = ReportBuilderDialog(self.project, spec, self)
            dialog.accepted.connect(self._refresh_navigator)
            self._open_designer(f"{category}:new:{id(dialog)}", dialog, category)
            return
        if category == "scripts":
            dialog = ScriptBuilderDialog(
                self.project,
                {"name": self._unique_name("scripts", "script"), "steps": []},
                self,
            )
            dialog.accepted.connect(self._refresh_navigator)
            self._open_designer(f"scripts:new:{id(dialog)}", dialog, category)
            return
        if category == "menus":
            dialog = MenuBuilderDialog(
                self.project,
                {"name": self._unique_name("menus", "principale"), "items": []},
                self,
            )
            dialog.accepted.connect(self._refresh_navigator)
            self._open_designer(f"menus:new:{id(dialog)}", dialog, category)

    def _after_new_table(self, dialog: TableBuilderDialog) -> None:
        self._refresh_navigator()
        name = dialog.current_table().name
        if name:
            self.open_object("tables", name)

    def _open_designer(self, key: str, dialog: QDialog, category: str):
        return self.editors.open_dialog(
            key,
            dialog,
            icon=icons.icon(OBJECT_ICONS.get(category, "finestra")),
            size=dialog.size(),
        )

    def open_object(self, category: str, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        self.object_label.setText(f"Oggetto: {name}")
        key = f"{category}:{name}"
        try:
            if category == "tables":
                existing = self.editors.find(key)
                if existing is not None:
                    self.mdi.setActiveSubWindow(existing)
                    return
                view = DataView(self.project, name)
                view.status_changed.connect(self.record_label.setText)
                self.editors.open(
                    key,
                    f"Browse — {name}",
                    view,
                    icon=icons.icon("tabella"),
                    size=QSize(1000, 620),
                )
                return
            if category not in OBJECT_ICONS or category == "tables":
                return
            artifact = self.project.artifact(category, name)
            if artifact is None:
                return
            existing = self.editors.find(key)
            if existing is not None:
                self.mdi.setActiveSubWindow(existing)
                return
            if category == "forms":
                dialog = FormBuilderDialog(self.project, FormSpec.from_dict(artifact), self)
            elif category == "reports":
                dialog = ReportBuilderDialog(self.project, ReportSpec.from_dict(artifact), self)
            elif category == "scripts":
                dialog = ScriptBuilderDialog(self.project, artifact, self)
            else:
                dialog = MenuBuilderDialog(self.project, artifact, self)
            dialog.accepted.connect(self._refresh_navigator)
            self._open_designer(key, dialog, category)
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
                self.editors.open_dialog(
                    f"preview:forms:{name}",
                    dialog,
                    icon=icons.icon("form"),
                    size=QSize(760, 620),
                )
        elif category == "reports":
            dialog = ReportPreviewDialog(self.project, name, self)
            self.editors.open_dialog(
                f"preview:reports:{name}",
                dialog,
                icon=icons.icon("report"),
                size=QSize(940, 800),
            )
        elif category == "scripts":
            artifact = self.project.artifact("scripts", name)
            if artifact:
                engine = ScriptEngine(self.project, QtScriptUI(self.project, self))
                result = engine.run(artifact.get("steps", []))
                if result.error:
                    QMessageBox.warning(self, "Script", result.error)
                else:
                    QMessageBox.information(
                        self, "Script", "\n".join(result.log[-12:]) or "Eseguito"
                    )

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

    def _refresh_navigator(self) -> None:
        self.navigator.set_project(self.project)

    # --------------------------------------------------------------- finestre
    def _refresh_window_menu(self) -> None:
        self._window_menu.clear()
        self._window_menu.addAction(self.act_cascade)
        self._window_menu.addAction(self.act_tile)
        self._window_menu.addSeparator()
        self._window_menu.addAction(self.act_close_window)
        self._window_menu.addAction(self.act_close_all)
        self._window_menu.addSeparator()
        self._window_actions = []
        windows = self.editors.windows()
        if not windows:
            empty = self._window_menu.addAction("(nessuna finestra aperta)")
            empty.setEnabled(False)
            return
        current = self.editors.current()
        for sub in windows:
            action = self._window_menu.addAction(sub.windowTitle())
            action.setCheckable(True)
            action.setChecked(sub is current)
            action.triggered.connect(
                lambda _checked=False, target=sub: self.mdi.setActiveSubWindow(target)
            )
            self._window_actions.append((sub, action))

    def _sync_window_menu(self) -> None:
        current = self.editors.current()
        for sub, action in self._window_actions:
            action.setChecked(sub is current)

    def _on_editor_activated(self, widget: QWidget | None) -> None:
        self._sync_window_menu()
        self._update_actions()
        if widget is None:
            self.object_label.setText("Oggetto: —")
            self.mode_label.setText("Modalità: —")
            return
        title = editor_title(widget, "Finestra")
        self.object_label.setText(f"Oggetto: {title}")
        self.mode_label.setText(f"Modalità: {self._mode_for(editor_widget(widget))}")

    def _on_editor_opened(self, _sub=None) -> None:
        self._refresh_window_menu()
        self._update_actions()

    def _on_editor_closed(self) -> None:
        self._refresh_window_menu()
        self._update_actions()
        if not self.editors.windows():
            self.object_label.setText("Oggetto: —")
            self.mode_label.setText("Modalità: —")

    def _mode_for(self, widget: QWidget | None) -> str:
        target = widget
        for _ in range(2):
            if target is None:
                break
            name = type(target).__name__
            if name in MODES:
                return MODES[name]
            target = target.parentWidget()
        return "Finestra"

    # --------------------------------------------------------------- comandi
    def _dispatch_edit(self, method: str) -> None:
        target = QApplication.focusWidget()
        if target is None:
            return
        function = getattr(target, method, None)
        if callable(function):
            function()

    def _dispatch_delete(self) -> None:
        target = QApplication.focusWidget()
        if target is None:
            return
        event = QKeyEvent(
            QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier
        )
        QApplication.sendEvent(target, event)

    def _update_edit_actions(self, _old=None, _new=None) -> None:
        target = QApplication.focusWidget()
        for action, method in (
            (getattr(self, "act_undo", None), "undo"),
            (getattr(self, "act_redo", None), "redo"),
            (getattr(self, "act_cut", None), "cut"),
            (getattr(self, "act_copy", None), "copy"),
            (getattr(self, "act_paste", None), "paste"),
        ):
            if action is not None:
                action.setEnabled(target is not None and callable(getattr(target, method, None)))
        if getattr(self, "act_delete", None) is not None:
            self.act_delete.setEnabled(self._has_selection(target))

    @staticmethod
    def _has_selection(target: QWidget | None) -> bool:
        if target is None:
            return False
        checker = getattr(target, "hasSelectedText", None)
        if callable(checker):
            return bool(checker())
        cursor = getattr(target, "textCursor", None)
        if callable(cursor):
            try:
                return bool(cursor().hasSelection())
            except Exception:  # pragma: no cover - difensivo
                return False
        return False

    def _toggle_speedbar(self, visible: bool) -> None:
        self.toolbar.setVisible(visible)

    def _toggle_statusbar(self, visible: bool) -> None:
        self.statusBar().setVisible(visible)

    def _zoom(self, factor: float) -> None:
        editor = self.editors.current_editor()
        setter = getattr(editor, "set_zoom", None)
        zoom = getattr(editor, "zoom", None)
        if callable(setter) and isinstance(zoom, (int, float)):
            setter(float(zoom) * factor)

    def _zoom_reset(self) -> None:
        editor = self.editors.current_editor()
        setter = getattr(editor, "set_zoom", None)
        baseline = getattr(editor, "baseline", None)
        if callable(setter):
            if isinstance(baseline, (int, float)):
                setter(float(baseline))
            else:
                setter(1.0)

    def print_current(self) -> None:
        editor = self.editors.current_editor()
        printer = getattr(editor, "print_pages", None)
        if callable(printer):
            printer()

    def _dispatch_editor(self, method: str) -> None:
        editor = self.editors.current_editor()
        function = getattr(editor, method, None)
        if callable(function):
            function()

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
            QMessageBox.information(
                self, "Validazione", "Progetto valido: nessun problema rilevato."
            )

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
        self._update_actions()

    def show_help(self) -> None:
        QMessageBox.information(
            self,
            "Guida rapida",
            "Progetto: Nuovo, Apri, Salva.\n"
            "Oggetto: crea tabelle, form, report, script e menu.\n"
            "Procedure: esegui, valida, build e Command Window.\n"
            "Finestra: sovrapponi, affianca, chiudi.\n\n"
            "Scorciatoie: F5 esegui · Ctrl+K Command Window · Ctrl+W chiudi finestra.",
        )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            "Informazioni su dBX",
            f"<b>dBX {__version__}</b><br>"
            "Personal database multipiattaforma ispirato a dBASE 5.5 for Windows.<br>"
            "Motore SQLite, interfaccia PyQt6.<br><br>"
            "Table Builder · Form Builder · Report Builder · MiniScript · Project Builder",
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
            getattr(self, "act_print", None),
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
        editor = self.editors.current_editor() if hasattr(self, "editors") else None
        if getattr(self, "act_print", None) is not None:
            self.act_print.setEnabled(enabled and callable(getattr(editor, "print_pages", None)))
        if getattr(self, "act_zoom_in", None) is not None:
            zoomable = callable(getattr(editor, "set_zoom", None))
            self.act_zoom_in.setEnabled(zoomable)
            self.act_zoom_out.setEnabled(zoomable)
            self.act_zoom_reset.setEnabled(zoomable)
        if getattr(self, "act_align", None) is not None:
            self.act_align.setEnabled(
                enabled and callable(getattr(editor, "align_selection", None))
            )
            self.act_distribute.setEnabled(
                enabled and callable(getattr(editor, "distribute_selection", None))
            )
        if getattr(self, "act_close_window", None) is not None:
            has_windows = bool(self.editors.windows()) if hasattr(self, "editors") else False
            for action in (self.act_close_window, self.act_close_all, self.act_cascade, self.act_tile):
                action.setEnabled(has_windows)
        self._update_edit_actions()

    def closeEvent(self, event) -> None:  # noqa: D102
        app = QApplication.instance()
        if app is not None:
            try:
                app.focusChanged.disconnect(self._update_edit_actions)
            except TypeError:  # pragma: no cover - già scollegato
                pass
            if self._filter_app is not None:
                self._filter_app.removeEventFilter(self)
                self._filter_app = None
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
