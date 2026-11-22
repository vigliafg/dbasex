"""Finestra principale di dBX: shell MDI, menu, SpeedBar e status bar (A4, G1–G6)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, QSize, Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QKeyEvent, QKeySequence, QLinearGradient
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
from ..designers.form_builder import FormDesignerWidget
from ..designers.form_expert import FormExpert
from ..designers.menu_builder import MenuBuilderWidget
from ..designers.project_builder import BuildError, ProjectEditorWidget, build_project, validate_project
from ..designers.report_builder import ReportDesignerWidget
from ..designers.script_builder import QtScriptUI, ScriptBuilderWidget
from ..designers.table_builder import TableBuilderDialog
from ..runtime.form_runtime import FormRuntime
from ..runtime.report_engine import ReportSpec
from ..runtime.script_engine import ScriptEngine
from . import design, icons
from .command_window import CommandWindow
from .data_view import DataView
from .editor_host import EditorHost, editor_title, editor_widget
from .menu import DescriptiveMenu, add_entry, add_submenu_entry
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
    "FormDesignerWidget": "Design",
    "FormBuilderDialog": "Design",
    "ReportBuilderDialog": "Design",
    "ReportDesignerWidget": "Design",
    "ScriptBuilderDialog": "Modifica",
    "ScriptBuilderWidget": "Modifica",
    "MenuBuilderDialog": "Design",
    "MenuBuilderWidget": "Design",
    "ProjectEditorWidget": "Progetto",
    "FormRuntime": "Esecuzione",
    "FormPreviewDialog": "Esecuzione",
    "ReportPreviewDialog": "Anteprima",
    "CommandWindow": "Comandi",
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
        self._sync_mdi_background()
        self.editors.activated.connect(self._on_editor_activated)
        self.editors.closed.connect(self._on_editor_closed)
        self.editors.opened.connect(self._on_editor_opened)

    def _sync_mdi_background(self) -> None:
        app = QApplication.instance()
        name = app.property("dbx_theme") if app is not None else None
        palette = design.palette(name if isinstance(name, str) else None)
        gradient = QLinearGradient(0, 0, 1600, 1000)
        gradient.setColorAt(0.0, QColor(palette["mdi_bg"]))
        gradient.setColorAt(1.0, QColor(palette["mdi_bg_alt"]))
        self.mdi.setBackground(QBrush(gradient))

    def _build_navigator(self) -> None:
        self.navigator = Navigator()
        self.navigator.open_object.connect(self.open_object)
        self.navigator.run_object.connect(self.run_object)
        self.navigator.new_object.connect(self.new_object)
        self.navigator.delete_object.connect(self.delete_object)
        self.navigator.structure_object.connect(self.open_table_structure)
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
            "Esci", "chiudi", self, QKeySequence.StandardKey.Quit
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
        self.act_speedbar = icons.make_action("SpeedBar", "finestra", self, checkable=True)
        self.act_speedbar.setChecked(True)
        self.act_statusbar = icons.make_action("Barra di stato", "elenco", self, checkable=True)
        self.act_statusbar.setChecked(True)
        self.act_zoom_in = icons.make_action(
            "Aumenta zoom", "zoom_in", self, QKeySequence("Ctrl++")
        )
        self.act_zoom_out = icons.make_action(
            "Riduci zoom", "zoom_out", self, QKeySequence("Ctrl+-")
        )
        self.act_zoom_reset = icons.make_action(
            "Zoom 100%", "aggiorna", self, QKeySequence("Ctrl+0")
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
        self.act_project = icons.make_action("Modifica progetto…", "elenco", self)
        self.act_project.triggered.connect(self.open_project_editor)

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
        menu.setNativeMenuBar(False)

        def add(target, action, description: str) -> None:
            add_entry(target, action, description)

        file_menu = DescriptiveMenu("&Progetto", menu)
        menu.addMenu(file_menu)
        add(file_menu, self.act_new, "Crea un nuovo progetto dBX in una cartella")
        add(file_menu, self.act_open, "Apri un progetto dBX esistente")
        add(file_menu, self.act_save, "Salva il progetto e i suoi oggetti")
        self._recent_menu = DescriptiveMenu("Progetti recenti", file_menu)
        self._recent_menu.setIcon(icons.icon("elenco"))
        add_submenu_entry(
            file_menu, self._recent_menu, "Apri uno dei progetti usati di recente"
        )
        file_menu.addSeparator()
        add(file_menu, self.act_project, "Apri il Project Editor del progetto corrente")
        file_menu.addSeparator()
        add(file_menu, self.act_close, "Chiudi il progetto e tutte le sue finestre")
        add(file_menu, self.act_quit, "Esci da dBX")

        edit_menu = DescriptiveMenu("&Modifica", menu)
        menu.addMenu(edit_menu)
        add(edit_menu, self.act_undo, "Annulla l'ultima modifica nell'editor attivo")
        add(edit_menu, self.act_redo, "Ripeti la modifica annullata")
        edit_menu.addSeparator()
        add(edit_menu, self.act_cut, "Taglia la selezione negli appunti")
        add(edit_menu, self.act_copy, "Copia la selezione negli appunti")
        add(edit_menu, self.act_paste, "Incolla il contenuto degli appunti")
        edit_menu.addSeparator()
        add(edit_menu, self.act_delete, "Elimina la selezione o il record corrente")

        view_menu = DescriptiveMenu("&Visualizza", menu)
        menu.addMenu(view_menu)
        add(view_menu, self.act_speedbar, "Mostra o nascondi la barra degli strumenti")
        add(view_menu, self.act_statusbar, "Mostra o nascondi la barra di stato")
        view_menu.addSeparator()
        add(view_menu, self.act_zoom_in, "Ingrandisci il documento attivo")
        add(view_menu, self.act_zoom_out, "Riduci il documento attivo")
        add(view_menu, self.act_zoom_reset, "Riporta il documento al 100%")
        view_menu.addSeparator()
        add(view_menu, self.act_refresh, "Ricarica l'elenco degli oggetti del Navigator")

        objects_menu = DescriptiveMenu("&Oggetto", menu)
        menu.addMenu(objects_menu)
        add(objects_menu, self.act_table, "Crea una nuova tabella con campi e relazioni")
        add(objects_menu, self.act_form, "Crea un form con il Form Expert o da zero")
        add(objects_menu, self.act_report, "Crea un report a bande con gruppi e totali")
        add(objects_menu, self.act_script, "Crea un programma MiniScript")
        add(objects_menu, self.act_menu, "Crea il menu dell'applicazione")

        run_menu = DescriptiveMenu("&Procedure", menu)
        menu.addMenu(run_menu)
        add(run_menu, self.act_run, "Esegui il progetto con menu e form principale")
        add(run_menu, self.act_validate, "Controlla tabelle, riferimenti e oggetti")
        add(run_menu, self.act_build, "Crea cartella e zip pronti da distribuire")
        run_menu.addSeparator()
        add(run_menu, self.act_command, "Apri la Command Window per comandi ed espressioni")
        run_menu.addSeparator()
        add(run_menu, self.act_demo, "Genera un progetto dimostrativo completo")

        properties_menu = DescriptiveMenu("&Proprietà", menu)
        menu.addMenu(properties_menu)
        add(properties_menu, self.act_settings, "Imposta titolo, form e menu principale")
        add(properties_menu, self.act_project, "Apri il Project Editor con validazione e build")

        self._window_menu = DescriptiveMenu("&Finestra", menu)
        menu.addMenu(self._window_menu)
        self._window_actions: list[tuple[object, QAction]] = []

        help_menu = DescriptiveMenu("&?", menu)
        menu.addMenu(help_menu)
        add(help_menu, self.act_guide, "Scorciatoie, flusso di lavoro e comandi rapidi")
        add(help_menu, self.act_about, "Versione, motore e informazioni su dBX")

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
            if category == "forms":
                self.new_form_wizard()
                return
            table_name, ok = QInputDialog.getItem(
                self, "Nuovo oggetto", "Tabella di riferimento:", tables, 0, False
            )
            if not ok:
                return
            table = self.project.require_table(table_name)
            spec = ReportSpec.create(
                self._unique_name("reports", f"report_{table.name}"),
                table.name,
                f"Report {table.display_name()}",
            )
            spec.bands["detail"][0].expr = table.fields[0].name
            designer = ReportDesignerWidget(self.project, spec, self)
            self._wire_report_designer(designer)
            self._open_designer(f"reports:new:{id(designer)}", designer, category)
            return
        if category == "scripts":
            widget = ScriptBuilderWidget(
                self.project,
                {"name": self._unique_name("scripts", "script"), "steps": []},
                self,
            )
            self._wire_script_designer(widget)
            self._open_designer(f"scripts:new:{id(widget)}", widget, category)
            return
        if category == "menus":
            widget = MenuBuilderWidget(
                self.project,
                {"name": self._unique_name("menus", "principale"), "items": []},
                self,
            )
            self._wire_menu_designer(widget)
            self._open_designer(f"menus:new:{id(widget)}", widget, category)

    def _after_new_table(self, dialog: TableBuilderDialog) -> None:
        self._refresh_navigator()
        name = dialog.current_table().name
        if name:
            self.open_object("tables", name)

    def _open_designer(self, key: str, widget: QWidget, category: str):
        icon = icons.icon(OBJECT_ICONS.get(category, "finestra"))
        if isinstance(widget, QDialog):
            return self.editors.open_dialog(key, widget, icon=icon, size=widget.size())
        sub = self.editors.open(
            key,
            widget.windowTitle() or "Finestra",
            widget,
            icon=icon,
            size=widget.size(),
        )
        widget.windowTitleChanged.connect(sub.setWindowTitle)
        return sub

    def new_form_wizard(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        tables = self.project.names("tables")
        if not tables:
            QMessageBox.information(self, "dBX", "Crea prima una tabella.")
            return
        suggested = self._unique_name("forms", f"form_{tables[0]}")
        wizard = FormExpert(self.project, self, suggested_name=suggested)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        spec = wizard.build_spec()
        errors = spec.validate()
        if errors:
            QMessageBox.warning(self, "Form non valido", "\n".join(errors))
            return
        if self.project.artifact("forms", spec.name) is not None:
            answer = QMessageBox.question(
                self,
                "Form esistente",
                f"Il form «{spec.name}» esiste già. Sostituirlo?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.project.put_object("forms", spec.to_dict())
        self.project.save()
        self._refresh_navigator()
        self.open_form_designer(spec.name)
        self.statusBar().showMessage(f"Form {spec.name} creato", 4000)

    def open_form_designer(self, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        artifact = self.project.artifact("forms", name)
        if artifact is None:
            QMessageBox.warning(self, "Form", f"Form inesistente: {name}")
            return
        key = f"forms:{name}"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        designer = FormDesignerWidget(self.project, FormSpec.from_dict(artifact), self)
        designer.preview_handler = self.preview_form
        designer.saved.connect(self._refresh_navigator)
        designer.status_message.connect(
            lambda text: self.statusBar().showMessage(text, 4000)
        )
        sub = self.editors.open(
            key,
            f"Form Designer ({designer.spec.caption or designer.spec.name})",
            designer,
            icon=icons.icon("form"),
            size=QSize(1160, 760),
        )
        designer.windowTitleChanged.connect(sub.setWindowTitle)

    def preview_form(self, spec: FormSpec, record_id: int | None = None, key: str = "") -> None:
        if not self._require_project():
            return
        assert self.project is not None
        target = key or f"preview:forms:{spec.name}"
        self.editors.remove(target)
        try:
            runtime = FormRuntime(self.project, spec, record_id)
        except (ProjectError, ValueError) as exc:
            QMessageBox.warning(self, "Form", str(exc))
            return
        runtime.browse_handler = lambda table: self.open_object("tables", table)
        runtime.report_handler = self._show_report_preview
        self.editors.open(
            target,
            f"{spec.caption or spec.name} — Esecuzione",
            runtime,
            icon=icons.icon("form"),
            size=QSize(860, 660),
        )

    def _show_report_preview(self, dialog: ReportPreviewDialog) -> None:
        name = getattr(getattr(dialog, "spec", None), "name", "")
        key = f"preview:reports:{name}" if name else "preview:reports"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        self.editors.open_dialog(key, dialog, icon=icons.icon("report"), size=QSize(940, 800))

    def _wire_report_designer(self, designer: ReportDesignerWidget) -> None:
        designer.preview_handler = self.preview_report
        designer.new_requested.connect(lambda: self.new_object("reports"))
        designer.open_requested.connect(self.choose_report)
        designer.saved.connect(self._refresh_navigator)
        designer.status_message.connect(
            lambda text: self.statusBar().showMessage(text, 4000)
        )

    def open_report_designer(self, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        artifact = self.project.artifact("reports", name)
        if artifact is None:
            QMessageBox.warning(self, "Report", f"Report inesistente: {name}")
            return
        key = f"reports:{name}"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        designer = ReportDesignerWidget(self.project, ReportSpec.from_dict(artifact), self)
        self._wire_report_designer(designer)
        sub = self.editors.open(
            key,
            f"Report Designer ({designer.spec.name})",
            designer,
            icon=icons.icon("report"),
            size=QSize(1180, 800),
        )
        designer.windowTitleChanged.connect(sub.setWindowTitle)

    def choose_report(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        names = self.project.names("reports")
        if not names:
            QMessageBox.information(self, "dBX", "Il progetto non ha report.")
            return
        name, ok = QInputDialog.getItem(self, "Apri report", "Report:", names, 0, False)
        if ok and name:
            self.open_report_designer(name)

    def preview_report(self, spec: ReportSpec) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        try:
            dialog = ReportPreviewDialog(self.project, spec, self)
        except ValueError as exc:
            QMessageBox.warning(self, "Report", str(exc))
            return
        self._show_report_preview(dialog)

    def _wire_script_designer(self, designer: ScriptBuilderWidget) -> None:
        designer.saved.connect(self._refresh_navigator)
        designer.status_message.connect(
            lambda text: self.statusBar().showMessage(text, 4000)
        )

    def open_script_designer(self, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        artifact = self.project.artifact("scripts", name)
        if artifact is None:
            QMessageBox.warning(self, "Script", f"Script inesistente: {name}")
            return
        key = f"scripts:{name}"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        designer = ScriptBuilderWidget(self.project, artifact, self)
        self._wire_script_designer(designer)
        sub = self.editors.open(
            key,
            f"Program Editor ({name})",
            designer,
            icon=icons.icon("script"),
            size=QSize(1140, 740),
        )
        designer.windowTitleChanged.connect(sub.setWindowTitle)

    def _wire_menu_designer(self, designer: MenuBuilderWidget) -> None:
        designer.saved.connect(self._refresh_navigator)
        designer.status_message.connect(
            lambda text: self.statusBar().showMessage(text, 4000)
        )

    def open_menu_designer(self, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        artifact = self.project.artifact("menus", name)
        if artifact is None:
            QMessageBox.warning(self, "Menu", f"Menu inesistente: {name}")
            return
        key = f"menus:{name}"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        designer = MenuBuilderWidget(self.project, artifact, self)
        self._wire_menu_designer(designer)
        sub = self.editors.open(
            key,
            f"Menu Designer ({name})",
            designer,
            icon=icons.icon("menu"),
            size=QSize(860, 560),
        )
        designer.windowTitleChanged.connect(sub.setWindowTitle)

    def open_project_editor(self) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        key = "project:editor"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        editor = ProjectEditorWidget(self.project, self)
        editor.open_object.connect(self.open_object)
        editor.saved.connect(self._refresh_navigator)
        editor.status_message.connect(
            lambda text: self.statusBar().showMessage(text, 4000)
        )
        sub = self.editors.open(
            key,
            f"Project Editor ({self.project.name})",
            editor,
            icon=icons.icon("impostazioni"),
            size=QSize(900, 620),
        )
        editor.windowTitleChanged.connect(sub.setWindowTitle)

    def open_table_structure(self, name: str) -> None:
        if not self._require_project():
            return
        assert self.project is not None
        key = f"structure:{name}"
        existing = self.editors.find(key)
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        table = self.project.table(name)
        if table is None:
            QMessageBox.warning(self, "Struttura", f"Tabella inesistente: {name}")
            return
        dialog = TableBuilderDialog(self.project, table, self)
        dialog.table_changed.connect(self._on_table_structure_changed)
        dialog.table_created.connect(self._refresh_navigator)
        dialog.accepted.connect(self._refresh_navigator)
        self.editors.open_dialog(
            key,
            dialog,
            icon=icons.icon("tabella"),
            size=QSize(1040, 720),
        )

    def _on_table_structure_changed(self, name: str) -> None:
        self._refresh_navigator()
        for sub in self.editors.windows():
            widget = editor_widget(sub.widget())
            if isinstance(widget, DataView) and widget.table.name == name:
                widget.reload_structure()

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
                view.structure_requested.connect(self.open_table_structure)
                self.record_label.setText(view.status.text())
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
                self.open_form_designer(name)
                return
            if category == "reports":
                self.open_report_designer(name)
                return
            if category == "scripts":
                self.open_script_designer(name)
                return
            if category == "menus":
                self.open_menu_designer(name)
                return
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
                self.preview_form(
                    FormSpec.from_dict(artifact), key=f"preview:forms:{name}"
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
        add_entry(self._window_menu, self.act_cascade, "Sovrapponi le finestre documento")
        add_entry(self._window_menu, self.act_tile, "Affianca le finestre documento")
        self._window_menu.addSeparator()
        add_entry(self._window_menu, self.act_close_window, "Chiudi la finestra documento attiva")
        add_entry(self._window_menu, self.act_close_all, "Chiudi tutte le finestre documento")
        self._window_menu.addSeparator()
        self._window_actions = []
        windows = self.editors.windows()
        if not windows:
            empty = icons.make_action("(nessuna finestra aperta)", "finestra", self)
            empty.setEnabled(False)
            add_entry(self._window_menu, empty, "Apri un oggetto dal Navigator per creare una finestra")
            return
        current = self.editors.current()
        for sub in windows:
            action = icons.make_action(sub.windowTitle(), "finestra", self)
            action.setCheckable(True)
            action.setChecked(sub is current)
            action.triggered.connect(
                lambda _checked=False, target=sub: self.mdi.setActiveSubWindow(target)
            )
            add_entry(self._window_menu, action, "Passa a questa finestra documento")
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
        if not isinstance(editor_widget(widget), DataView):
            self.record_label.setText("Record: —")

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
        assert self.project is not None
        existing = self.editors.find("command")
        if existing is not None:
            self.mdi.setActiveSubWindow(existing)
            return
        self.editors.open(
            "command",
            f"Command Window — {self.project.name}",
            CommandWindow(self.project),
            icon=icons.icon("testo"),
            size=QSize(760, 520),
        )

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
        self._sync_mdi_background()
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
            action = icons.make_action(path, "apri", self, tooltip=f"Apri {path}")
            action.triggered.connect(lambda _checked=False, p=path: self.open_recent(p))
            add_entry(self._recent_menu, action, "Apri questo progetto recente")

    def _update_actions(self) -> None:
        enabled = self.project is not None
        for action in (
            getattr(self, "act_save", None),
            getattr(self, "act_print", None),
            getattr(self, "act_close", None),
            getattr(self, "act_settings", None),
            getattr(self, "act_project", None),
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
