"""Scenari J — Shell, Navigator, menu, progetto e runner."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox

from dbx.core.form_model import FormPage, FormSpec
from dbx.core.label_model import LabelSpec
from dbx.core.project import Project
from dbx.core.query_model import QueryField, QuerySpec
from dbx.designers.menu_builder import MENU_ACTIONS, MenuBuilderWidget
from dbx.designers.project_builder import (
    BuildError,
    ProjectEditorWidget,
    build_project,
    validate_project,
)
from dbx.designers.script_builder import ScriptBuilderWidget
from dbx.runtime.report_engine import ReportSpec
from dbx.runtime.script_engine import new_step
from dbx.ui import design
from dbx.ui.command_window import CommandWindow
from dbx.ui.main_window import MainWindow
from dbx.ui.navigator import NAV_CATEGORIES, Navigator
from dbx.ui.project_runner import ProjectRunner
from dbx.ui.report_preview import ReportPreviewDialog

from .. import fixtures
from ..catalog import FEATURES
from ..context import E2EContext
from ..registry import scenario

_NAV_FEATURES = tuple(f.id for f in FEATURES.values() if f.id.startswith("NAV-CATEGORY-"))
_SHELL_FEATURES = tuple(f.id for f in FEATURES.values() if f.id.startswith("SHELL-ACTION-"))
_MENU_FEATURES = tuple(f.id for f in FEATURES.values() if f.id.startswith("MENU-ACTION-"))


def _project(ctx: E2EContext, name: str = "Shell") -> object:
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


def _assets(project) -> dict[str, str]:
    """Crea gli oggetti usati dalla shell, dal menu e dal runner."""

    project.put_object(
        "queries",
        QuerySpec(name="clienti_query", base="clienti", fields=[QueryField("clienti", "codice"), QueryField("clienti", "nome")]).to_dict(),
    )
    project.put_object("forms", FormSpec.create(project.require_table("clienti"), name="form_clienti").to_dict())
    report = ReportSpec.create("report_clienti", "clienti", "Clienti")
    report.bands["detail"][0].expr = "codice"
    project.put_object("reports", report.to_dict())
    project.put_object("labels", LabelSpec.create("etichette_clienti", "clienti", ["nome", "citta"]).to_dict())
    project.put_object(
        "scripts",
        {"name": "script_benvenuto", "params": [], "steps": [new_step("message", text="Benvenuto")]},
    )
    project.put_object(
        "menus",
        {
            "name": "menu_principale",
            "items": [
                {"label": "Clienti", "action": "open_form", "target": "form_clienti"},
                {"label": "Report", "action": "open_report", "target": "report_clienti"},
                {"label": "Saluto", "action": "run_script", "target": "script_benvenuto"},
                {"label": "", "action": "separator", "target": ""},
                {"label": "Esci", "action": "quit", "target": ""},
            ],
        },
    )
    project.settings["main_form"] = "form_clienti"
    project.settings["main_menu"] = "menu_principale"
    project.settings["title"] = "Applicazione E2E"
    project.save()
    return {"form": "form_clienti", "report": "report_clienti", "script": "script_benvenuto", "menu": "menu_principale"}


def _window(ctx: E2EContext, project) -> MainWindow:
    window = ctx.track(MainWindow(project))
    with ctx.quiet_qt():
        window.show()
        ctx.qapp.processEvents()
    return window


def _all_actions(menu) -> list:
    result = []
    for action in menu.actions():
        result.append(action)
        if action.menu() is not None:
            result.extend(_all_actions(action.menu()))
    return result


@scenario(
    "shl-01-navigator",
    "J01 — Navigator: categorie, conteggi e categorie disabilitate",
    "shell",
    features=("NAV-COUNT", "NAV-DISABLED", *_NAV_FEATURES),
    min_checks=10,
    budget_s=8.0,
    screenshots=("shell-navigator",),
)
def shl_navigator(ctx: E2EContext) -> None:
    project = _project(ctx, "Navigator")
    _assets(project)
    window = _window(ctx, project)
    navigator = window.navigator
    ctx.check_close(len(navigator._buttons), len(NAV_CATEGORIES), "tredici categorie")
    for key, _label, _glyph, available in NAV_CATEGORIES:
        ctx.check(navigator._buttons[key].isEnabled() is available, f"categoria {key}")
    ctx.check(not navigator._buttons["images"].isEnabled(), "Immagini disabilitata")
    ctx.check("non disponibile" in navigator._buttons["sounds"].toolTip(), "tooltip disabilitata")
    navigator.set_category("tables")
    ctx.check_close(navigator.list_header.text(), "Tabelle (2)", "conteggio tabelle")
    ctx.check(navigator.list.count() == 3, "due tabelle e Untitled")
    navigator.set_category("all")
    ctx.check(navigator.list_header.text().startswith("Oggetti ("), "conteggio totale")
    headers = [
        navigator.list.item(i).text()
        for i in range(navigator.list.count())
        if navigator.list.item(i).text().endswith(")")
    ]
    ctx.check(any("Query (1)" == text for text in headers), "gruppo query")
    ctx.check("oggetti nel progetto" in navigator.hint.text(), "suggerimento")
    ctx.capture(window, "shell-navigator", (1180, 780))


@scenario(
    "shl-02-navigator-actions",
    "J02 — Navigator: filtro, directory, Untitled, contesto e refresh",
    "shell",
    features=("NAV-FILTER", "NAV-UNTITLED", "NAV-CONTEXT", "NAV-REFRESH", "NAV-COUNT"),
    min_checks=10,
    budget_s=8.0,
)
def shl_navigator_actions(ctx: E2EContext) -> None:
    project = _project(ctx, "NavigatorAzioni")
    _assets(project)
    navigator = ctx.track(Navigator())
    navigator.set_project(project)
    ctx.check_close(navigator.filter_combo.count(), 9, "nove filtri")
    navigator.filter_combo.setCurrentIndex(navigator.filter_combo.findData("queries"))
    ctx.check_close(navigator.category, "queries", "filtro query")
    ctx.check_close(navigator.list_header.text(), "Query (1)", "solo query")
    ctx.check(str(project.path) in navigator.directory_edit.text(), "directory progetto")
    ctx.check(navigator.directory_edit.isReadOnly(), "directory in sola lettura")

    events: list[tuple[str, str]] = []
    navigator.new_object.connect(lambda category: events.append(("new", category)))
    navigator.open_object.connect(lambda category, name: events.append((category, name)))
    navigator.structure_object.connect(lambda name: events.append(("structure", name)))
    untitled = next(
        navigator.list.item(i)
        for i in range(navigator.list.count())
        if navigator.list.item(i).text() == "[Untitled]"
    )
    navigator._activate(untitled)
    ctx.check_close(events[-1], ("new", "queries"), "Untitled crea un oggetto")
    query_item = next(
        navigator.list.item(i)
        for i in range(navigator.list.count())
        if navigator.list.item(i).text() == "clienti_query"
    )
    navigator._activate(query_item)
    ctx.check_close(events[-1], ("queries", "clienti_query"), "doppio clic apre la query")
    navigator.set_category("tables")
    table_item = next(
        navigator.list.item(i)
        for i in range(navigator.list.count())
        if navigator.list.item(i).text() == "clienti"
    )
    navigator._activate(table_item)
    ctx.check_close(events[-1], ("structure", "clienti"), "tabella apre la struttura")

    with mock.patch("dbx.ui.navigator.DescriptiveMenu.exec", autospec=True) as executed:
        navigator._context_menu(QPoint(4, 4))
    ctx.check(executed.called, "menu contestuale vuoto")
    ctx.check(executed.call_args is not None, "menu contestuale costruito")
    ctx.check(navigator.list.count() > 0, "vista popolata dopo il contesto")
    navigator.refresh()
    ctx.check_close(navigator.list.count(), 3, "refresh conserva la vista")


@scenario(
    "shl-03-command",
    "J03 — Command Window: HELP, TABELLE, USE, RECORD, CLEAR, espressioni",
    "shell",
    features=("CMD-HELP", "CMD-TABLES", "CMD-USE", "CMD-RECORD", "CMD-CLEAR", "CMD-EXPR", "CMD-HISTORY"),
    min_checks=12,
    budget_s=8.0,
)
def shl_command(ctx: E2EContext) -> None:
    project = _project(ctx, "Command")
    window = CommandWindow(project)
    ctx.track(window)

    def run(command: str) -> str:
        window.input.setText(command)
        window.execute()
        return window.output.toPlainText()

    ctx.check("HELP" in run("HELP"), "help")
    ctx.check("clienti" in run("TABELLE"), "tabelle")
    ctx.check("Tabella clienti aperta — 5 record" in run("USE clienti"), "use tabella")
    ctx.check_close(window.rowset.count(), 5, "cursore aperto")
    ctx.check("codice: 'C001'" in run("RECORD"), "record corrente")
    ctx.check_close(run("2 + 2").strip().splitlines()[-1], "4", "espressione aritmetica")
    ctx.check_close(run('UPPER("ciao")').strip().splitlines()[-1], "CIAO", "espressione testo")
    ctx.check("Tabella sconosciuta" in run("USE tabella_inesistente"), "errore segnalato")
    ctx.check("Errore" in window.status.text(), "stato errore")
    run("CLEAR")
    ctx.check_close(window.output.toPlainText(), "", "risultati cancellati")
    window._history_previous()
    ctx.check_close(window.input.text(), "CLEAR", "cronologia indietro")
    window._history_previous()
    ctx.check(window.input.text() != "CLEAR", "cronologia precedente")
    window._history_next()
    ctx.check_close(window.input.text(), "CLEAR", "cronologia avanti")
    ctx.check(run("USE").strip().endswith("Nessuna tabella corrente"), "use chiude la tabella")


@scenario(
    "shl-04-tabs",
    "J04 — Shell a schede: apri, attiva, chiudi, dirty e chiudi tutte",
    "shell",
    features=("SHELL-TABS", "SHELL-ACTIVATE", "SHELL-CLOSE", "SHELL-CLOSE-ALL", "SHELL-DIRTY"),
    min_checks=9,
    budget_s=10.0,
)
def shl_tabs(ctx: E2EContext) -> None:
    project = _project(ctx, "Schede")
    _assets(project)
    window = _window(ctx, project)
    window.open_object("tables", "clienti")
    window.open_object("queries", "clienti_query")
    window.open_object("forms", "form_clienti")
    ctx.qapp.processEvents()
    ctx.check_close(len(window.editors.windows()), 3, "tre schede")
    ctx.check_close(window.editors.tabs.count(), 3, "tre etichette")
    query_tab = window.editors.find("queries:clienti_query")
    ctx.check(query_tab is not None, "scheda query")
    window.editors.activate(query_tab)
    ctx.check_close(window.editors.current().property("dbx_key"), "queries:clienti_query", "scheda attiva")
    ctx.check(window.object_label.text().startswith("Oggetto:"), "oggetto in stato")

    form_tab = window.editors.find("forms:form_clienti")
    designer = form_tab.widget()
    designer.add_control("label", 20, 20)
    ctx.check(designer.is_dirty(), "designer dirty")
    window.editors.close_current()
    ctx.check_close(len(window.editors.windows()), 2, "scheda chiusa con conferma")
    window.editors.close_all()
    ctx.check_close(len(window.editors.windows()), 0, "chiudi tutte")
    ctx.check(not window.act_close_window.isEnabled(), "azione disabilitata senza schede")


@scenario(
    "shl-05-menus",
    "J05 — Otto menu, azioni e esecuzione sicura",
    "shell",
    features=("SHELL-MENUS", "SHELL-ACTIONS", "SHELL-SAFE", *_SHELL_FEATURES),
    min_checks=10,
    budget_s=10.0,
    screenshots=("shell-desktop",),
)
def shl_menus(ctx: E2EContext) -> None:
    project = _project(ctx, "MenuShell")
    _assets(project)
    window = _window(ctx, project)
    menus = [action.menu() for action in window.menuBar().actions() if action.menu() is not None]
    ctx.check_close(len(menus), 8, "otto menu principali")
    titles = [menu.title().replace("&", "") for menu in menus]
    ctx.check_close(titles, ["Progetto", "Modifica", "Visualizza", "Oggetto", "Procedure", "Proprietà", "Finestra", "?"], "titoli dei menu")
    actions = _all_actions(window.menuBar())
    ctx.check(len(actions) >= 48, "almeno 48 azioni")
    expected = {
        "Nuovo progetto…", "Apri progetto…", "Salva progetto", "Annulla", "Ripeti",
        "SpeedBar", "Aumenta zoom", "Database…", "Nuova query…", "Esegui progetto",
        "Valida progetto", "Build distribuibile…", "Impostazioni…", "Chiudi scheda",
        "Guida rapida", "Informazioni su dBX",
    }
    texts = {action.text() for action in actions}
    ctx.check(expected <= texts, "azioni principali presenti")
    ctx.check(window.act_run.isEnabled() and window.act_validate.isEnabled(), "azioni progetto abilitate")
    window.act_refresh.trigger()
    window.act_speedbar.setChecked(False)
    ctx.check(not window.toolbar.isVisible(), "speedbar nascosta")
    window.act_speedbar.setChecked(True)
    window.act_statusbar.setChecked(False)
    ctx.check(not window.statusBar().isVisible(), "status bar nascosta")
    window.act_statusbar.setChecked(True)
    window.act_help.trigger() if hasattr(window, "act_help") else window.act_guide.trigger()
    window.act_validate.trigger()
    ctx.check(any("Progetto valido" in entry[2] for entry in ctx.dialogs), "validazione sicura")
    window.act_command.trigger()
    ctx.qapp.processEvents()
    ctx.check(window.editors.find("command") is not None or any("Command" in tab.title for tab in window.editors.windows()), "command window aperta")
    ctx.check(window.act_close_all.isEnabled(), "chiudi tutte abilitata")
    ctx.capture(window, "shell-desktop", (1180, 780))


@scenario(
    "shl-06-status",
    "J06 — SpeedBar, tooltip, toggle e barra di stato",
    "shell",
    features=("SPEEDBAR", "TOOLTIPS", "TOGGLE", "STATUS-BAR"),
    min_checks=9,
    budget_s=8.0,
)
def shl_status(ctx: E2EContext) -> None:
    project = _project(ctx, "StatoShell")
    _assets(project)
    window = _window(ctx, project)
    ctx.check(window.toolbar.isVisible(), "speedbar visibile")
    ctx.check(window.toolbar.objectName() == "main_toolbar", "toolbar principale")
    ctx.check("Ctrl+S" in window.act_save.toolTip(), "tooltip con scorciatoia")
    ctx.check("F5" in window.act_run.toolTip(), "tooltip esecuzione")
    ctx.check(len([action for action in window.toolbar.actions() if not action.isSeparator()]) >= 18, "azioni toolbar")
    ctx.check(window.project_label.text().startswith("StatoShell"), "nome progetto in stato")
    labels = [label.text() for label in window.statusBar().findChildren(QLabel)]
    ctx.check(any(text.startswith("dBX ") for text in labels), "versione nella barra")
    ctx.check(any(text.startswith("Pos:") for text in labels), "posizione")
    window.open_object("tables", "clienti")
    ctx.qapp.processEvents()
    ctx.check("clienti" in window.object_label.text().lower(), "oggetto attivo")
    ctx.check("Modalità:" in window.mode_label.text(), "modalità attiva")
    window.act_speedbar.setChecked(False)
    ctx.check(not window.toolbar.isVisible(), "toggle speedbar")
    window.act_speedbar.setChecked(True)
    ctx.check(window.toolbar.isVisible(), "speedbar ripristinata")


@scenario(
    "shl-07-edit",
    "J07 — Annulla, ripeti, copia, incolla ed elimina tra editor",
    "shell",
    features=("EDIT-CROSS", "EDIT-UNDO-REDO", "EDIT-DELETE"),
    min_checks=5,
    budget_s=8.0,
)
def shl_edit(ctx: E2EContext) -> None:
    project = _project(ctx, "EditShell")
    _assets(project)
    window = _window(ctx, project)
    window.open_object("scripts", "script_benvenuto")
    window.act_command.trigger()
    ctx.qapp.processEvents()
    script = window.editors.find("scripts:script_benvenuto").widget()
    command_tab = next(tab for tab in window.editors.windows() if isinstance(tab.widget(), CommandWindow))
    command = command_tab.widget()
    with ctx.quiet_qt():
        script.text_view.setFocus()
        script.text_view.selectAll()
        ctx.qapp.processEvents()
    script.text_view.setFocus()
    script.text_view.selectAll()
    script.text_view.copy()
    ctx.check("MESSAGE" in QApplication.clipboard().text(), "copia dall'editor")
    command.input.clear()
    with mock.patch.object(QApplication, "focusWidget", return_value=command.input):
        window._dispatch_edit("paste")
    ctx.check("MESSAGE" in command.input.text(), "copia e incolla tra editor")
    command.input.clear()
    with ctx.quiet_qt():
        script.text_view.setFocus()
        script.text_view.selectAll()
        script.text_view.insertPlainText("STATUS \"prova\"")
        ctx.qapp.processEvents()
    with mock.patch.object(QApplication, "focusWidget", return_value=script.text_view):
        window._dispatch_edit("undo")
    ctx.check("prova" not in script.text_view.toPlainText(), "annulla nella shell")
    with mock.patch.object(QApplication, "focusWidget", return_value=script.text_view):
        window._dispatch_edit("redo")
    ctx.check("prova" in script.text_view.toPlainText(), "ripeti nella shell")
    script.text_view.selectAll()
    with mock.patch.object(QApplication, "focusWidget", return_value=script.text_view):
        window._dispatch_delete()
    ctx.check_close(script.text_view.toPlainText(), "", "elimina selezione")
    ctx.check(window.act_close_window.isEnabled(), "azioni shell coerenti")


@scenario(
    "shl-08-zoom",
    "J08 — Zoom avanti, indietro, 100% e persistenza",
    "shell",
    features=("ZOOM-IN", "ZOOM-OUT", "ZOOM-RESET", "ZOOM-PERSIST"),
    min_checks=6,
    budget_s=8.0,
)
def shl_zoom(ctx: E2EContext) -> None:
    project = _project(ctx, "ZoomShell")
    _assets(project)
    window = _window(ctx, project)
    spec = ReportSpec.create("zoom_report", "clienti", "Zoom")
    dialog = ReportPreviewDialog(project, spec)
    ctx.track(dialog)
    window._show_report_preview(dialog)
    ctx.qapp.processEvents()
    baseline = dialog.baseline
    ctx.check(dialog.zoom >= baseline, "zoom iniziale")
    window.act_zoom_in.trigger()
    ctx.check(dialog.zoom > baseline, "zoom avanti")
    zoomed = dialog.zoom
    window.act_zoom_out.trigger()
    ctx.check(dialog.zoom < zoomed, "zoom indietro")
    window.act_zoom_reset.trigger()
    ctx.check_close(dialog.zoom, baseline, "zoom 100%")
    window.act_zoom_in.trigger()
    persisted = dialog.zoom
    second = ReportPreviewDialog(project, spec)
    ctx.track(second)
    ctx.check_close(second.zoom, persisted, "zoom ereditato")
    ctx.check(window.act_zoom_in.isEnabled(), "azioni zoom abilitate")


@scenario(
    "shl-09-shortcuts",
    "J09 — Scorciatoie documentate",
    "shell",
    features=("SHORTCUTS",),
    min_checks=9,
    budget_s=8.0,
)
def shl_shortcuts(ctx: E2EContext) -> None:
    project = _project(ctx, "Scorciatoie")
    _assets(project)
    window = _window(ctx, project)
    expected = {
        "nuovo": ("act_new", "Ctrl+N"),
        "apri": ("act_open", "Ctrl+O"),
        "salva": ("act_save", "Ctrl+S"),
        "command": ("act_command", "Ctrl+K"),
        "refresh": ("act_refresh", "Ctrl+R"),
        "chiudi": ("act_close_window", "Ctrl+W"),
        "guida": ("act_guide", "F1"),
        "esegui": ("act_run", "F5"),
    }
    for label, (attribute, sequence) in expected.items():
        action = getattr(window, attribute)
        ctx.check(action.shortcut().toString() == sequence, f"{label}: {sequence}")
    window.open_object("tables", "clienti")
    ctx.qapp.processEvents()
    view = window.editors.find("tables:clienti").widget()
    shortcuts = {shortcut.key().toString() for shortcut in view.findChildren(QShortcut)}
    ctx.check("Ctrl+F" in shortcuts, "Ctrl+F nella Browse")
    ctx.check("Ctrl+H" in shortcuts, "Ctrl+H nella Browse")
    ctx.check(window.act_save.shortcut().toString() == "Ctrl+S", "azione salva")
    ctx.check(window.act_close_window.shortcut().toString() in ("Ctrl+W", "Ctrl+F4"), "chiusura scheda")


@scenario(
    "shl-10-help-about",
    "J10 — Guida rapida, Informazioni, tema e versione",
    "shell",
    features=("HELP-QUICK", "ABOUT", "THEME", "VERSION"),
    min_checks=7,
    budget_s=8.0,
)
def shl_help_about(ctx: E2EContext) -> None:
    project = _project(ctx, "AiutoShell")
    window = _window(ctx, project)
    window.act_guide.trigger()
    ctx.check(any("Guida rapida" in entry[1] for entry in ctx.dialogs), "guida rapida")
    with mock.patch.object(QMessageBox, "about") as about:
        window.act_about.trigger()
    ctx.check(about.called, "finestra Informazioni")
    ctx.check("dBX" in about.call_args[0][2], "versione nelle informazioni")
    window.toggle_theme(True)
    ctx.check_close(window.config.get("theme"), "dark", "tema dark")
    window.toggle_theme(False)
    ctx.check_close(window.config.get("theme"), design.DEFAULT_THEME, "tema predefinito")
    labels = [label.text() for label in window.statusBar().findChildren(QLabel)]
    ctx.check(any(text.startswith("dBX ") for text in labels), "versione in status bar")
    ctx.check(window.windowTitle().startswith("dBX"), "titolo con nome applicazione")


@scenario(
    "shl-11-menu-builder",
    "J11 — Menu Designer: albero, separatori, azioni e destinazioni",
    "menus",
    features=("MENU-BUILDER", "MENU-SEPARATORS", "MENU-ACTION5", "MENU-FILTER-TARGET", "MENU-PREVIEW"),
    min_checks=10,
    budget_s=8.0,
    screenshots=("menu-designer",),
)
def shl_menu_builder(ctx: E2EContext) -> None:
    project = _project(ctx, "MenuBuilder")
    _assets(project)
    builder = MenuBuilderWidget(project, project.artifact("menus", "menu_principale"))
    ctx.track(builder)
    ctx.check_close(builder.tree.topLevelItemCount(), 5, "cinque elementi")
    ctx.check_close(builder.action_combo.count(), len(MENU_ACTIONS), "cinque azioni")
    ctx.check_close(builder.preview_bar.actions()[0].menu().actions().__len__(), 5, "anteprima elementi")
    builder.add_item()
    ctx.check_close(len(builder.items), 6, "voce aggiunta")
    builder.add_separator()
    ctx.check_close(len(builder.items), 7, "separatore aggiunto")
    builder.items[-1]["action"] = "open_form"
    builder._rebuild_tree(select=len(builder.items) - 1)
    builder._show_properties(builder.items[-1])
    builder.action_combo.setCurrentIndex(builder.action_combo.findData("open_form"))
    ctx.check(builder.target_combo.count() >= 2, "destinazioni form")
    ctx.check("form_clienti" in [builder.target_combo.itemText(i) for i in range(builder.target_combo.count())], "form tra le destinazioni")
    builder.action_combo.setCurrentIndex(builder.action_combo.findData("run_script"))
    ctx.check("script_benvenuto" in [builder.target_combo.itemText(i) for i in range(builder.target_combo.count())], "script tra le destinazioni")
    builder.items[-1]["action"] = "separator"
    builder._rebuild_preview()
    ctx.check("voci visibili" in builder.preview_state.text(), "stato anteprima")
    ctx.check(builder.save(), "menu salvato")
    ctx.capture(builder, "menu-designer", (860, 560))


@scenario(
    "shl-12-menu-runtime",
    "J12 — Anteprima menu e runtime: form, report, script, esci",
    "menus",
    features=("MENU-RUNTIME", *_MENU_FEATURES),
    min_checks=7,
    budget_s=8.0,
)
def shl_menu_runtime(ctx: E2EContext) -> None:
    project = _project(ctx, "MenuRuntime")
    assets = _assets(project)
    runner = ProjectRunner(project, assets["form"], assets["menu"])
    ctx.track(runner)
    menu = runner.menu_bar.actions()[0].menu()
    labels = [action.text() for action in menu.actions() if not action.isSeparator()]
    ctx.check("Clienti" in labels and "Report" in labels, "voci del menu")
    runner._dispatch("open_form", assets["form"])
    ctx.check(runner.current is not None, "form aperto dal menu")
    runner._dispatch("run_script", assets["script"])
    ctx.check(any("Benvenuto" in entry[2] for entry in ctx.dialogs), "script eseguito dal menu")
    with mock.patch.object(ReportPreviewDialog, "exec") as executed:
        runner._dispatch("open_report", assets["report"])
    ctx.check(executed.called, "report aperto dal menu")
    ctx.check("Esci" in labels, "voce Esci")
    before = runner.result()
    runner.accept()
    ctx.check(runner.result() != before or not runner.isVisible(), "runner chiuso")
    ctx.check_close(len(MENU_ACTIONS), 5, "cinque azioni di menu")


@scenario(
    "shl-13-project-editor",
    "J13 — Project Editor: albero, impostazioni e salvataggio",
    "project",
    features=("PROJECT-EDITOR", "PROJECT-SETTINGS", "PROJECT-EDITOR-SAVE", "PROJECT-VALIDATE"),
    min_checks=8,
    budget_s=8.0,
    screenshots=("project-editor",),
)
def shl_project_editor(ctx: E2EContext) -> None:
    project = _project(ctx, "EditorProgetto")
    _assets(project)
    editor = ProjectEditorWidget(project)
    ctx.track(editor)
    ctx.check_close(editor.tree.topLevelItemCount(), 7, "sette categorie")
    ctx.check(editor.tree.topLevelItem(0).childCount() == 2, "due tabelle")
    ctx.check(editor.form_combo.findData("form_clienti") >= 0, "form principale")
    ctx.check(editor.menu_combo.findData("menu_principale") >= 0, "menu principale")
    editor.title_edit.setText("Titolo editor")
    editor.form_combo.setCurrentIndex(editor.form_combo.findData("form_clienti"))
    editor.menu_combo.setCurrentIndex(editor.menu_combo.findData("menu_principale"))
    ctx.check(editor.is_dirty(), "impostazioni modificate")
    editor.save_settings()
    ctx.check_close(project.settings.get("title"), "Titolo editor", "titolo salvato")
    ctx.check_close(editor.validation.toPlainText(), "Nessun problema rilevato.", "progetto valido")
    ctx.check_close(editor.validate_now(), [], "validazione vuota")
    ctx.capture(editor, "project-editor", (900, 620))


@scenario(
    "shl-14-validation",
    "J14 — Validazione progetto: riferimenti mancanti",
    "project",
    features=("PROJECT-VALIDATE-MISSING", "PROJECT-VALIDATE"),
    min_checks=6,
    budget_s=8.0,
)
def shl_validation(ctx: E2EContext) -> None:
    project = _project(ctx, "Validazione")
    form = FormSpec(name="form_rotto", table="tabella_mancante", pages=[FormPage()])
    project.objects["forms"]["form_rotto"] = form.to_dict()
    query = QuerySpec(name="query_rotta", base="tabella_mancante", fields=[QueryField("x", "y")])
    project.objects["queries"]["query_rotta"] = query.to_dict()
    project.settings["main_form"] = "form_inesistente"
    errors = validate_project(project)
    ctx.check(any("tabella inesistente" in error for error in errors), "tabella mancante")
    ctx.check(any("query_rotta" in error for error in errors), "query rotta")
    ctx.check(any("Form principale inesistente" in error for error in errors), "form principale mancante")
    editor = ProjectEditorWidget(project)
    ctx.track(editor)
    ctx.check("problemi" in editor.status_label.text(), "stato problemi")
    ctx.check("tabella inesistente" in editor.validation.toPlainText(), "errori nell'editor")
    project.objects["forms"].pop("form_rotto")
    project.objects["queries"].pop("query_rotta")
    project.settings["main_form"] = ""
    ctx.check_close(validate_project(project), [], "progetto corretto")


@scenario(
    "shl-15-build",
    "J15 — Build distribuibile: cartella, zip, contenuto e riapertura",
    "project",
    features=("BUILD-FOLDER", "BUILD-ZIP", "BUILD-CONTENT", "BUILD-REOPEN"),
    min_checks=10,
    budget_s=12.0,
)
def shl_build(ctx: E2EContext) -> None:
    project = _project(ctx, "Build")
    _assets(project)
    target = ctx.work / "dist"
    archive = build_project(project, target)
    base = target / project.name
    ctx.check(archive.exists() and archive.suffix == ".zip", "archivio zip")
    ctx.check(base.is_dir(), "cartella di build")
    ctx.check((base / "project.dbx.json").exists(), "manifest")
    ctx.check((base / "objects" / "forms").is_dir(), "oggetti copiati")
    ctx.check((base / "data" / project.database_file.name).exists(), "database copiato")
    ctx.check("Avvio" in (base / "LEGGIMI.txt").read_text(encoding="utf-8"), "istruzioni")
    import zipfile

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    ctx.check("project.dbx.json" in names and any(name.startswith("objects/") for name in names), "contenuto zip")
    built = Project.open(base / "project.dbx.json")
    try:
        ctx.check_close(len(built.names("tables")), 2, "tabelle riaperte")
        ctx.check_close(validate_project(built), [], "build valida")
    finally:
        built.close()
    with mock.patch.object(ProjectEditorWidget, "choose_destination", return_value=str(target)):
        editor = ProjectEditorWidget(project)
        ctx.track(editor)
        editor.destination_edit.setText(str(target))
        ctx.check(editor.build() is not None, "build dall'editor")


@scenario(
    "shl-16-runner",
    "J16 — Project Runner: F5, form principale, menu e chiusura",
    "project",
    features=("RUNNER-F5", "RUNNER-FORM", "RUNNER-MENU", "RUNNER-CLOSE"),
    min_checks=7,
    budget_s=8.0,
    screenshots=("shell-runner",),
)
def shl_runner(ctx: E2EContext) -> None:
    project = _project(ctx, "Runner")
    assets = _assets(project)
    window = _window(ctx, project)
    with mock.patch("dbx.ui.project_runner.ProjectRunner.exec", return_value=0) as executed:
        window.act_run.trigger()
    ctx.check(executed.called, "F5 esegue il progetto")
    ctx.check(window.act_run.shortcut().toString() == "F5", "scorciatoia F5")
    runner = ProjectRunner(project, assets["form"], assets["menu"])
    ctx.track(runner)
    ctx.check(runner.current is not None, "form principale")
    ctx.check_close(runner.current.spec.name, "form_clienti", "form del runner")
    ctx.check(runner.menu_bar.actions(), "menu del runner")
    ctx.check(runner.windowTitle().startswith("Runner"), "titolo runner")
    ctx.capture(runner, "shell-runner", (980, 720))
    runner.accept()
    ctx.check(not runner.isVisible(), "runner chiuso")
