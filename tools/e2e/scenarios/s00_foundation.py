"""Scenari A — fondamenta: progetto, compatibilità, CLI, temi, recenti."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

from dbx.config import add_recent, forget_recent, load_config, recent_projects
from dbx.core import types as T
from dbx.core.project import CATEGORIES, Project
from dbx.designers.project_builder import ProjectEditorWidget, validate_project
from dbx.samples import create_demo_project
from dbx.ui import design
from dbx.ui.theme import apply_theme

from ..context import E2EContext
from ..registry import scenario

ROOT = __import__("pathlib").Path(__file__).resolve().parents[3]


@scenario(
    "proj-01-new-empty",
    "A01 — Nuovo progetto vuoto e riapertura",
    "project",
    features=("PROJ-NEW", "PROJ-SAVE"),
    min_checks=8,
    budget_s=6.0,
    screenshots=("fund-project-empty",),
)
def proj_new_empty(ctx: E2EContext) -> None:
    project = ctx.new_project("Vuoto")
    ctx.check(project.manifest_path.exists(), "manifest creato")
    manifest = json.loads(project.manifest_path.read_text(encoding="utf-8"))
    ctx.check(manifest["name"] == "Vuoto", "nome nel manifest")
    ctx.check(manifest["format_version"] >= 1, "versione formato")
    for category in CATEGORIES:
        ctx.check(
            (project.objects_path / category).is_dir(),
            f"cartella oggetti {category}",
        )
    ctx.check(project.data_path.joinpath("Vuoto.sqlite").exists(), "database SQLite creato")
    reopened = ctx.reopen(project)
    ctx.check(reopened.name == "Vuoto", "nome dopo riapertura")
    ctx.check(not reopened.tables(), "nessuna tabella dopo riapertura")
    ctx.check(validate_project(reopened) == [], "progetto vuoto valido")
    ctx.capture(ctx.main_window(reopened), "fund-project-empty", (1180, 780))


@scenario(
    "proj-02-demo",
    "A02 — Progetto demo completo",
    "project",
    features=("PROJ-DEMO", "PROJ-SAVE"),
    min_checks=10,
    budget_s=8.0,
    screenshots=("fund-demo",),
)
def proj_demo(ctx: E2EContext) -> None:
    project = ctx.demo_project("Demo")
    ctx.check(validate_project(project) == [], "demo valida")
    ctx.check_close(len(project.names("tables")), 2, "due tabelle nella demo")
    ctx.check_close(len(project.names("queries")), 2, "due query nella demo")
    ctx.check_close(len(project.names("forms")), 3, "tre form nella demo")
    ctx.check_close(len(project.names("reports")), 2, "due report nella demo")
    ctx.check_close(len(project.names("scripts")), 2, "due script nella demo")
    ctx.check("principale" in project.names("menus"), "menu principale presente")
    clienti = project.require_table("clienti")
    ctx.check(clienti.field("codice") is not None, "campo codice")
    from dbx.runtime.rowset import Rowset

    ctx.check(Rowset(project.db, clienti).open().count() >= 3, "clienti con dati")
    reopened = ctx.reopen(project)
    ctx.check(reopened.require_table("fatture").foreign_keys, "relazione dopo riapertura")
    ctx.capture(ctx.main_window(reopened), "fund-demo", (1180, 780))


@scenario(
    "proj-03-settings",
    "A03 — Impostazioni progetto e persistenza",
    "project",
    features=("PROJ-SETTINGS", "PROJ-SAVE"),
    min_checks=8,
    budget_s=8.0,
    screenshots=("fund-settings",),
)
def proj_settings(ctx: E2EContext) -> None:
    project = ctx.demo_project("Impostazioni")
    editor = ctx.track(ProjectEditorWidget(project))
    ctx.check(editor.tree.topLevelItemCount() >= 7, "albero oggetti popolato")
    editor.title_edit.setText("Gestionale demo")
    form_index = editor.form_combo.findData("form_clienti")
    ctx.check(form_index >= 0, "form principale selezionabile")
    editor.form_combo.setCurrentIndex(max(0, form_index))
    menu_index = editor.menu_combo.findData("principale")
    ctx.check(menu_index >= 0, "menu principale selezionabile")
    editor.menu_combo.setCurrentIndex(max(0, menu_index))
    editor.save_settings()
    ctx.check(not editor.is_dirty(), "editor non sporco dopo salvataggio")
    reopened = ctx.reopen(project)
    ctx.check_close(reopened.settings.get("title"), "Gestionale demo", "titolo persistito")
    ctx.check_close(reopened.settings.get("main_form"), "form_clienti", "form persistito")
    ctx.check_close(reopened.settings.get("main_menu"), "principale", "menu persistito")
    ctx.check(validate_project(reopened) == [], "progetto con impostazioni valido")
    ctx.capture(editor, "fund-settings", (900, 640))


@scenario(
    "proj-04-legacy",
    "A04 — Compatibilità artefatti legacy",
    "project",
    features=("PROJ-COMPAT", "TB-FIELD-INCREMENT", "TB-FIELD-CHOICE-DYNAMIC"),
    min_checks=7,
    budget_s=5.0,
)
def proj_legacy(ctx: E2EContext) -> None:
    project = ctx.new_project("Legacy")
    legacy_table = {
        "name": "vecchia",
        "caption": "",
        "fields": [
            {"name": "codice", "type": "text", "size": 8},
            {"name": "serie", "type": "integer", "auto_serial": True},
            {"name": "stato", "type": "text", "lookup": "stati.codice"},
        ],
        "indexes": [],
        "foreign_keys": [],
    }
    project.put_object("tables", legacy_table)
    project.save()
    reopened = ctx.reopen(project)
    table = reopened.require_table("vecchia")
    ctx.check(table is not None, "tabella legacy caricata")
    ctx.check_close(table.field("serie").increment, "records", "auto_serial migrato a increment")
    stato = table.field("stato")
    ctx.check_close(stato.type, T.CHOICE, "lookup testuale migrato a Scelta")
    ctx.check_close(stato.choice_table, "stati", "tabella sorgente migrata")
    ctx.check(stato.choice_allow_other, "testo libero legacy preservato")
    ctx.check(table.to_dict()["fields"][2].get("lookup", "") == "", "lookup rimosso nel round-trip")
    ctx.check_close(reopened.names("tables"), ["vecchia"], "unica tabella legacy")
    ctx.check_close(table.fields[0].size, 8, "lunghezza campo legacy")


@scenario(
    "proj-05-save-reopen",
    "A05 — Salvataggio, chiusura e riapertura con dati",
    "project",
    features=("PROJ-SAVE", "TB-NEW"),
    min_checks=6,
    budget_s=5.0,
)
def proj_save_reopen(ctx: E2EContext) -> None:
    from .. import fixtures

    project = ctx.new_project("Persistenza")
    fixtures.apply(project, fixtures.clienti_table())
    fixtures.seed_clienti(project)
    project.save()
    reopened = ctx.reopen(project)
    table = reopened.require_table("clienti")
    from dbx.runtime.rowset import Rowset

    rows = Rowset(reopened.db, table).open()
    ctx.check_close(rows.count(), 5, "cinque record dopo riapertura")
    ctx.check_close(rows.first()["codice"], "C001", "primo record persistito")
    ctx.check_close(reopened.artifact("tables", "clienti")["caption"], "Clienti", "didascalia persistita")
    ctx.check(reopened.backups_path.is_dir(), "cartella backup presente")
    ctx.check((reopened.objects_path / "tables" / "clienti.table.json").exists(), "JSON tabella su disco")
    manifest = json.loads(reopened.manifest_path.read_text(encoding="utf-8"))
    ctx.check("saved_at" in manifest, "manifest con data di salvataggio")
    ctx.check_close(Rowset(reopened.db, table).open(order="codice").rows()[4]["codice"], "C005", "ultimo record persistito")


@scenario(
    "proj-06-cli",
    "A06 — Avvio da riga di comando",
    "project",
    features=("PROJ-CLI",),
    min_checks=4,
    budget_s=20.0,
)
def proj_cli(ctx: E2EContext) -> None:
    version = subprocess.run(
        [sys.executable, "-m", "dbx", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    ctx.check(version.returncode == 0, "CLI --version esce con 0", version.stderr[-200:])
    ctx.check(version.stdout.strip().startswith("dBX "), "CLI riporta la versione", version.stdout.strip())
    help_text = subprocess.run(
        [sys.executable, "-m", "dbx", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    ctx.check(help_text.returncode == 0, "CLI --help esce con 0")
    for option in ("--demo", "--theme", "--smoke", "--version"):
        ctx.check(option in help_text.stdout, f"CLI espone {option}")


@scenario(
    "proj-07-themes",
    "A07 — Temi Aurora, Silver e Dark",
    "project",
    features=("PROJ-THEME",),
    min_checks=9,
    budget_s=8.0,
    screenshots=("fund-theme-dark",),
)
def proj_themes(ctx: E2EContext) -> None:
    for theme in ("aurora", "silver", "dark"):
        resolved = apply_theme(ctx.qapp, theme)
        ctx.check(resolved == theme, f"tema {theme} applicato", resolved)
        ctx.check(bool(ctx.qapp.styleSheet()), f"QSS generato per {theme}")
    apply_theme(ctx.qapp, "aurora")
    ctx.check_close(design.normalize_theme("dark"), "dark", "alias dark")
    ctx.check_close(design.normalize_theme("light"), "light", "alias light")
    window = ctx.main_window()
    window.toggle_theme(True)
    ctx.check_close(load_config().get("theme"), "dark", "tema scuro persistito")
    ctx.check(design.palette("dark") is design.SILVER_DARK, "palette scura")
    ctx.capture(window, "fund-theme-dark", (1180, 780))
    window.toggle_theme(False)
    ctx.check_close(load_config().get("theme"), design.DEFAULT_THEME, "tema predefinito ripristinato")


@scenario(
    "proj-08-recent",
    "A08 — Progetti recenti e progetto mancante",
    "project",
    features=("PROJ-RECENT",),
    min_checks=5,
    budget_s=6.0,
)
def proj_recent(ctx: E2EContext) -> None:
    project = ctx.new_project("Recente")
    add_recent(project.path)
    ctx.check(str(project.path.resolve()) in recent_projects(), "progetto nei recenti")
    window = ctx.main_window()
    ctx.check(window._recent_menu.actions(), "menu recenti popolato")
    forget_recent(project.path)
    ctx.check(str(project.path.resolve()) not in recent_projects(), "progetto rimosso dai recenti")
    project.close()
    shutil.rmtree(project.path, ignore_errors=True)
    ctx.check(str(project.path.resolve()) not in recent_projects(), "progetto mancante non elencato")
    ctx.check(load_config().get("max_recent", 0) >= 1, "limite recenti configurato")
