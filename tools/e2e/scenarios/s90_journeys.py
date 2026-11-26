"""Scenari K — Journey realistici, compatibilità, prestazioni e distribuzione."""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

from dbx.core import types as T
from dbx.core.form_model import FormControl, FormPage, FormSpec
from dbx.core.label_model import LabelSpec
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.core.query_engine import run_query
from dbx.core.query_model import QueryField, QueryJoin, QuerySpec
from dbx.core.refactor import compact_database
from dbx.core.search import SearchCriterion, SearchRequest, count_matches
from dbx.designers.project_builder import build_project, validate_project
from dbx.io.csv_io import export_rows, read_table
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.label_engine import render_labels_for_project
from dbx.runtime.report_engine import BAND_NAMES, Control, ReportSpec
from dbx.runtime.rowset import Rowset
from dbx.runtime.script_engine import ScriptEngine, new_step
from dbx.ui.data_view import DataView
from dbx.ui.report_preview import build_pages

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario
from .s80_shell import _assets, _project


def _query_join(project, name: str = "fatture_clienti") -> QuerySpec:
    return QuerySpec(
        name=name,
        caption="Fatture per cliente",
        base="fatture",
        fields=[QueryField("fatture", "numero"), QueryField("clienti", "nome"), QueryField("fatture", "importo")],
        joins=[QueryJoin("inner", "clienti", "fatture.cliente", "clienti.codice")],
    )


@scenario(
    "jrn-01-new-app",
    "K01 — Nuova applicazione: tabella → query → form → report → script → menu → build",
    "journey",
    features=("JOURNEY-NEWAPP", "BUILD-FOLDER", "PROJECT-VALIDATE"),
    min_checks=11,
    budget_s=15.0,
)
def jrn_new_app(ctx: E2EContext) -> None:
    project = ctx.new_project("NuovaApp")
    fixtures.settled_project(project)
    query = _query_join(project)
    project.put_object("queries", query.to_dict())
    form = FormSpec.create_master_detail(
        project.require_table("clienti"), project.require_table("fatture"), "codice", "cliente", name="form_clienti"
    )
    project.put_object("forms", form.to_dict())
    report = ReportSpec.create("report_clienti", "clienti", "Clienti")
    report.bands["detail"][0].expr = "nome"
    report.groups = [{"field": "citta", "label": "Città"}]
    report.band_visible["group_header"] = True
    report.bands["group_header"] = [Control(id="g", kind="text", x=0, y=0, w=80, h=6, text="Città: [citta]")]
    project.put_object("reports", report.to_dict())
    project.put_object(
        "scripts",
        {"name": "benvenuto", "params": [], "steps": [new_step("status", text="Benvenuto")]},
    )
    project.put_object(
        "menus",
        {"name": "principale", "items": [{"label": "Clienti", "action": "open_form", "target": "form_clienti"}, {"label": "Esci", "action": "quit", "target": ""}]},
    )
    project.settings["main_form"] = "form_clienti"
    project.settings["main_menu"] = "principale"
    project.save()
    ctx.check_close(len(project.names("tables")), 2, "due tabelle")
    ctx.check_close(run_query(project, query).rows[0]["nome"], "Alfa Srl", "query join")
    ctx.check_close(FormSpec.from_dict(project.artifact("forms", "form_clienti")).table, "clienti", "form principale")
    ctx.check("Città: Roma" in "\n".join(op.text for p in build_pages(project, report) for op in p.ops), "report raggruppato")
    ctx.check_close(validate_project(project), [], "progetto valido")
    archive = build_project(project, ctx.work / "dist")
    ctx.check(archive.exists(), "build creata")
    reopened = ctx.reopen(project)
    ctx.check_close(len(reopened.names("queries")), 1, "query persistita")
    ctx.check_close(len(reopened.names("forms")), 1, "form persistito")
    ctx.check_close(reopened.settings.get("main_form"), "form_clienti", "form principale persistito")
    ctx.check(reopened.artifact("menus", "principale") is not None, "menu persistito")
    ctx.check_close(len(reopened.names("scripts")), 1, "script persistito")


@scenario(
    "jrn-02-sportello",
    "K02 — Sportello: ricerca, modifica, incasso, riepilogo e riavvio",
    "journey",
    features=("JOURNEY-SPORTELLO", "DV-CRUD", "DV-FIND", "REP-PDF", "LBL-PDF"),
    min_checks=8,
    budget_s=15.0,
)
def jrn_sportello(ctx: E2EContext) -> None:
    project = _project(ctx, "Sportello")
    table = project.require_table("clienti")
    request = SearchRequest([SearchCriterion("citta", "eq", "Roma")])
    ctx.check_close(count_matches(project.db, table, request), 2, "ricerca clienti Roma")
    rows = Rowset(project.db, table).open()
    record = rows.find("codice", "C001")
    rows.update(record["_id"], {"saldo": 1500.0})
    ctx.check_close(float(Rowset(project.db, table).open().find("codice", "C001")["saldo"]), 1500.0, "incasso registrato")
    view = ctx.data_view(project, "clienti")
    view.order_combo.setCurrentIndex(view.order_combo.findData("codice"))
    ctx.check_close(view.grid.rowCount(), 5, "browse allo sportello")
    query = _query_join(project, "sportello_query")
    project.put_object("queries", query.to_dict())
    result = run_query(project, query)
    ctx.check_close(len(result.rows), 4, "riepilogo fatture")
    report = ReportSpec.create("sportello_report", "clienti", "Sportello")
    report.bands["detail"][0].expr = "nome"
    pages = build_pages(project, report)
    ctx.check(pages, "report sportello")
    label = LabelSpec.create("sportello_labels", "clienti", ["nome", "citta"])
    label.template = "[nome] — [citta]"
    ctx.check_close(len(render_labels_for_project(project, label)), 1, "etichette sportello")
    project.save()
    reopened = ctx.reopen(project)
    ctx.check_close(float(Rowset(reopened.db, reopened.require_table("clienti")).open().find("codice", "C001")["saldo"]), 1500.0, "incasso dopo riavvio")
    ctx.check(reopened.artifact("queries", "sportello_query") is not None, "query dopo riavvio")


@scenario(
    "jrn-03-import",
    "K03 — Import e bonifica: CSV sporco, normalizzazione, dedup, export e mailing",
    "journey",
    features=("JOURNEY-IMPORT", "CSV-DETECT-DELIM", "CSV-MAPPING", "MNT-REEVALUATE", "CSV-EXPORT", "LBL-PREVIEW"),
    min_checks=8,
    budget_s=15.0,
)
def jrn_import(ctx: E2EContext) -> None:
    project = ctx.new_project("Bonifica")
    table = Table(
        name="contatti",
        fields=[Field("nome", T.TEXT, size=40), Field("citta", T.TEXT, size=30)],
    )
    fixtures.apply(project, table)
    source = ctx.work / "contatti.csv"
    source.write_text("nome;citta\n alfa ;roma\nBeta;milano\nalfa;roma\nGamma;torino\n", encoding="utf-8")
    delimiter, _encoding, rows = read_table(str(source), "auto", "auto")
    ctx.check_close(delimiter, ";", "delimitatore rilevato")
    target = Rowset(project.db, project.require_table("contatti"))
    for row in rows[1:]:
        target.insert({"nome": row[0].strip(), "citta": row[1].strip()})
    ctx.check_close(target.count(), 4, "righe importate")
    unique = project.db.query('SELECT DISTINCT "nome", "citta" FROM "contatti" ORDER BY "nome"')
    ctx.check_close(len(unique), 3, "duplicati individuati")
    project.db.execute('DELETE FROM "contatti" WHERE rowid NOT IN (SELECT MIN(rowid) FROM "contatti" GROUP BY "nome", "citta")')
    ctx.check_close(Rowset(project.db, project.require_table("contatti")).count(), 3, "dedup")
    normalized = Rowset(project.db, project.require_table("contatti")).open()
    for row in normalized.rows():
        normalized.update(row["_id"], {"nome": row["nome"].strip().upper(), "citta": row["citta"].title()})
    ctx.check_close(
        [row["nome"] for row in Rowset(project.db, project.require_table("contatti")).open().rows()],
        ["ALFA", "BETA", "GAMMA"],
        "normalizzazione",
    )
    exported = ctx.work / "puliti.csv"
    export_rows(exported, ["nome", "citta"], Rowset(project.db, project.require_table("contatti")).open().rows())
    ctx.check(exported.exists() and "ALFA" in exported.read_text(encoding="utf-8-sig"), "export bonificato")
    label = LabelSpec.create("mailing", "contatti", ["nome", "citta"])
    label.template = "[nome]\n[citta]"
    pages = render_labels_for_project(project, label)
    ctx.check_close(len(pages), 1, "mailing pronto")
    ctx.check("ALFA" in "\n".join(op.text for page in pages for op in page.ops), "etichetta bonificata")


@scenario(
    "jrn-04-closing",
    "K04 — Chiusura mensile: parametri, solleciti, report, PDF, backup e compattazione",
    "journey",
    features=("JOURNEY-CLOSING", "SCR-PARAMS", "QRY-AGG-SUM", "REP-PDF", "MNT-BACKUP", "MNT-COMPACT"),
    min_checks=8,
    budget_s=15.0,
)
def jrn_closing(ctx: E2EContext) -> None:
    project = _project(ctx, "Chiusura")
    project.put_object(
        "scripts",
        {
            "name": "solleciti",
            "params": [{"name": "mese", "label": "Mese", "default": "01"}],
            "steps": [new_step("status", text="Chiusura :mese")],
        },
    )
    project.save()
    result = ScriptEngine(project).run_named("solleciti", params={"mese": "03"})
    ctx.check(result.error is None, "script parametrico")
    ctx.check("Chiusura 03" in result.log, "parametro usato")
    query = QuerySpec(
        name="totali_mese",
        base="fatture",
        fields=[QueryField("fatture", "cliente")],
        group_by=["fatture.cliente"],
        aggregates=[],
    )
    from dbx.core.query_model import QueryAggregate

    query.aggregates = [QueryAggregate("sum", "fatture", "importo", "totale")]
    grouped = run_query(project, query)
    ctx.check_close(len(grouped.rows), 3, "tre clienti con fatture")
    ctx.check_close(sum(row["totale"] for row in grouped.rows), 750.5, "totale mensile")
    report = ReportSpec.create("chiusura_report", "clienti", "Chiusura")
    report.bands["detail"][0].expr = "nome"
    pages = build_pages(project, report)
    from dbx.io.pdf_export import export_pdf

    pdf = export_pdf(pages, ctx.work / "chiusura.pdf", "Chiusura")
    ctx.check(pdf.exists() and pdf.stat().st_size > 1000, "PDF chiusura")
    backup = project.backup("chiusura")
    ctx.check(backup is not None and Path(backup).exists(), "backup creato")
    message = compact_database(project)
    ctx.check(isinstance(message, str) and "compatt" in message.lower() or message is not None, "compattazione")
    ctx.check(Rowset(project.db, project.require_table("clienti")).count() == 5, "dati intatti dopo compattazione")


@scenario(
    "jrn-05-one-to-many",
    "K05 — Due tabelle 1:N: form con portale, query join, report raggruppato",
    "journey",
    features=("JOURNEY-1N", "FRM-PORTAL-LINK", "QRY-JOIN-INNER", "REP-GROUP"),
    min_checks=5,
    budget_s=12.0,
)
def jrn_one_to_many(ctx: E2EContext) -> None:
    project = _project(ctx, "UnoAMolti")
    form = FormSpec.create_master_detail(
        project.require_table("clienti"), project.require_table("fatture"), "codice", "cliente", name="clienti_fatture"
    )
    runtime = FormRuntime(project, form)
    ctx.track(runtime)
    runtime.rowset.first()
    runtime.load_current()
    ctx.check_close(runtime.grids[0][0].rowCount(), 2, "portale del primo cliente")
    runtime.rowset.goto(3)
    runtime.load_current()
    ctx.check_close(runtime.grids[0][0].rowCount(), 1, "portale del quarto cliente")
    query = _query_join(project, "clienti_fatture_query")
    ctx.check_close(len(run_query(project, query).rows), 4, "query uno-a-molti")
    report = ReportSpec.create("clienti_report", "clienti", "Clienti")
    report.bands["detail"][0].expr = "nome"
    report.groups = [{"field": "citta", "label": "Città"}]
    report.band_visible["group_header"] = True
    report.bands["group_header"] = [Control(id="g", kind="text", x=0, y=0, w=80, h=6, text="Città: [citta]")]
    pages = build_pages(project, report)
    ctx.check("Città: Roma" in "\n".join(op.text for page in pages for op in page.ops), "report raggruppato")
    ctx.check_close(validate_project(project), [], "progetto valido")


@scenario(
    "jrn-06-restart",
    "K06 — Sessione lunga e riavvio: tutto persistito, nessuna perdita",
    "journey",
    features=("JOURNEY-RESTART", "PROJ-SAVE", "DETERMINISM"),
    min_checks=10,
    budget_s=12.0,
)
def jrn_restart(ctx: E2EContext) -> None:
    project = _project(ctx, "Riavvio")
    _assets(project)
    query = _query_join(project, "riavvio_query")
    project.put_object("queries", query.to_dict())
    project.put_object(
        "scripts",
        {"name": "riavvio_script", "params": [{"name": "x", "label": "X", "default": "1"}], "steps": [new_step("status", text=":x")]},
    )
    project.save()
    first = run_query(project, query)
    second = run_query(project, query)
    ctx.check_close(first.rows, second.rows, "query deterministica")
    reopened = ctx.reopen(project)
    ctx.check_close(len(reopened.names("tables")), 2, "tabelle dopo riavvio")
    ctx.check_close(len(reopened.names("queries")), 2, "query dopo riavvio")
    ctx.check_close(len(reopened.names("forms")), 1, "form dopo riavvio")
    ctx.check_close(len(reopened.names("reports")), 1, "report dopo riavvio")
    ctx.check_close(len(reopened.names("scripts")), 2, "script dopo riavvio")
    ctx.check_close(len(reopened.names("menus")), 1, "menu dopo riavvio")
    ctx.check_close(validate_project(reopened), [], "progetto coerente")
    ctx.check(reopened.settings.get("main_form") == "form_clienti", "impostazioni conservate")
    ctx.check(reopened.artifact("scripts", "riavvio_script")["params"][0]["name"] == "x", "parametri conservati")


@scenario(
    "jrn-07-legacy",
    "K07 — Progetto legacy: apri, modifica, salva e riapri",
    "journey",
    features=("JOURNEY-LEGACY", "PROJ-COMPAT", "REP-LEGACY", "FRM-LEGACY-JSON"),
    min_checks=6,
    budget_s=10.0,
)
def jrn_legacy(ctx: E2EContext) -> None:
    project = _project(ctx, "Legacy")
    project.objects["forms"]["legacy_form"] = {
        "name": "legacy_form",
        "table": "clienti",
        "pages": [{"caption": "Dati", "controls": [{"id": "c1", "kind": "field", "field": "nome", "x": 8, "y": 8, "w": 180, "h": 24}]}],
    }
    project.objects["reports"]["legacy_report"] = {
        "name": "legacy_report",
        "title": "Legacy",
        "table": "clienti",
        "bands": {"detail": [{"id": "d", "kind": "field", "expr": "nome"}]},
    }
    project.save()
    reopened = ctx.reopen(project)
    form = FormSpec.from_dict(reopened.artifact("forms", "legacy_form"))
    report = ReportSpec.from_dict(reopened.artifact("reports", "legacy_report"))
    ctx.check_close(form.source_type, "table", "form legacy")
    ctx.check_close(form.pages[0].controls[0].field, "nome", "campo legacy")
    ctx.check_close(report.effective_band_order(), list(BAND_NAMES), "bande completate")
    ctx.check(report.validate() == [], "report legacy valido")
    form.caption = "Legacy aggiornato"
    reopened.put_object("forms", form.to_dict(), previous_name="legacy_form")
    reopened.save()
    again = ctx.reopen(reopened)
    ctx.check_close(FormSpec.from_dict(again.artifact("forms", "legacy_form")).caption, "Legacy aggiornato", "modifica salvata")
    ctx.check(validate_project(again) == [], "legacy valido dopo modifica")


@scenario(
    "jrn-08-perf-10k",
    "K08 — Prestazioni con 10.000 righe",
    "quality",
    features=("PERF-BROWSE", "PERF-QUERY", "PERF-REPORT", "PERF-PDF"),
    min_checks=8,
    budget_s=40.0,
)
def jrn_perf_10k(ctx: E2EContext) -> None:
    project = ctx.new_project("Prestazioni")
    table = Table(
        name="movimenti",
        caption="Movimenti",
        fields=[
            Field("codice", T.TEXT, size=12, required=True, pk=True),
            Field("citta", T.TEXT, size=30),
            Field("importo", T.DECIMAL, size=12),
        ],
    )
    fixtures.apply(project, table)
    rows = [(f"M{i:05d}", ["Roma", "Milano", "Torino", "Napoli"][i % 4], float(i % 1000)) for i in range(10_000)]
    project.db.executemany('INSERT INTO "movimenti" ("codice", "citta", "importo") VALUES (?, ?, ?)', rows)
    project.db.con.commit()
    ctx.check_close(Rowset(project.db, project.require_table("movimenti")).count(), 10_000, "diecimila righe")
    started = time.perf_counter()
    view = ctx.data_view(project, "movimenti")
    ctx.qapp.processEvents()
    ctx.check(time.perf_counter() - started < 8.0, "Browse 10k")
    ctx.check_close(view.grid.rowCount(), 10_000, "griglia completa")
    query = QuerySpec(
        name="totali_citta",
        base="movimenti",
        fields=[QueryField("movimenti", "citta")],
        group_by=["movimenti.citta"],
        aggregates=[],
    )
    from dbx.core.query_model import QueryAggregate

    query.aggregates = [QueryAggregate("sum", "movimenti", "importo", "totale")]
    started = time.perf_counter()
    result = run_query(project, query)
    ctx.check(time.perf_counter() - started < 3.0, "query aggregata 10k")
    ctx.check_close(len(result.rows), 4, "quattro gruppi")
    report = ReportSpec.create("perf_report", "movimenti", "Prestazioni")
    report.bands["detail"][0].expr = "codice"
    report.filter = '"citta" = \'Roma\''
    started = time.perf_counter()
    pages = build_pages(project, report)
    ctx.check(time.perf_counter() - started < 8.0, "report 10k filtrato")
    ctx.check(pages, "pagine generate")
    from dbx.io.pdf_export import export_pdf

    started = time.perf_counter()
    pdf = export_pdf(pages, ctx.work / "perf.pdf", "Prestazioni")
    ctx.check(time.perf_counter() - started < 15.0, "PDF generato")
    ctx.check(pdf.exists(), "file PDF prestazioni")


@scenario(
    "jrn-09-perf-ui",
    "K09 — Prestazioni UI: form 100 controlli, tabella 50 campi, report 200 controlli",
    "quality",
    features=("PERF-FORM100", "PERF-TABLE50", "PERF-REPORT200"),
    min_checks=6,
    budget_s=15.0,
)
def jrn_perf_ui(ctx: E2EContext) -> None:
    project = _project(ctx, "PrestazioniUI")
    spec = FormSpec(name="form_100", table="clienti")
    spec.pages = [FormPage(caption="Dati")]
    for index in range(100):
        spec.pages[0].controls.append(
            FormControl(id=f"c{index}", kind="label", text=f"Etichetta {index}", x=8 + (index % 4) * 140, y=8 + (index // 4) * 20, w=120, h=16)
        )
    started = time.perf_counter()
    runtime = FormRuntime(project, spec)
    ctx.track(runtime)
    ctx.check(time.perf_counter() - started < 2.0, "form 100 controlli")
    ctx.check_close(len(runtime.spec.pages[0].controls), 100, "cento controlli")

    wide = Table(name="larga", fields=[Field(f"campo_{i:02d}", T.TEXT, size=20) for i in range(50)])
    fixtures.apply(project, wide)
    from dbx.designers.table_builder import TableBuilderDialog

    started = time.perf_counter()
    builder = ctx.track(TableBuilderDialog(project, project.require_table("larga")))
    ctx.check(time.perf_counter() - started < 2.0, "tabella 50 campi")
    ctx.check_close(len(builder.current_table().fields), 50, "cinquanta campi")

    report = ReportSpec.create("report_200", "clienti", "Report 200")
    report.bands["detail"] = [
        Control(id=f"c{i}", kind="text", x=(i % 10) * 17, y=(i // 10) * 6, w=16, h=5, text=f"t{i}")
        for i in range(200)
    ]
    started = time.perf_counter()
    pages = build_pages(project, report)
    ctx.check(time.perf_counter() - started < 3.0, "report 200 controlli")
    ctx.check(pages, "report ampio renderizzato")


@scenario(
    "jrn-10-distribution",
    "K10 — Distribuzione: build, estrazione, apertura e uso della copia",
    "journey",
    features=("JOURNEY-NEWAPP", "BUILD-ZIP", "BUILD-REOPEN", "DOCS-COVERAGE"),
    min_checks=8,
    budget_s=15.0,
)
def jrn_distribution(ctx: E2EContext) -> None:
    project = _project(ctx, "Distribuzione")
    assets = _assets(project)
    archive = build_project(project, ctx.work / "dist")
    extract = ctx.work / "estratto"
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract)
    built = Project.open(extract / "project.dbx.json")
    try:
        ctx.check_close(len(built.names("tables")), 2, "tabelle della copia")
        ctx.check_close(validate_project(built), [], "copia valida")
        runtime = FormRuntime(built, FormSpec.from_dict(built.artifact("forms", assets["form"])))
        ctx.check_close(runtime.rowset.count(), 5, "form dalla copia")
        ctx.check_close(run_query(built, _query_join(built, "copia_query")).rows[0]["nome"], "Alfa Srl", "query dalla copia")
        ctx.check(built.artifact("menus", assets["menu"]) is not None, "menu nella copia")
        ctx.check(built.database_file.exists(), "database nella copia")
        coverage = Path("docs/e2e-coverage.md")
        ctx.check(coverage.exists() and "Copertura funzionale E2E" in coverage.read_text(encoding="utf-8"), "matrice di copertura")
        runtime.deleteLater()
    finally:
        built.close()
    ctx.check(archive.stat().st_size > 1000, "archivio distribuibile")
