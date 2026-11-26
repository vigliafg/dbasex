"""Scenari D — CSV, Database Designer, manutenzione e regole storiche."""

from __future__ import annotations

import json
from unittest import mock

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.refactor import check_database, compact_database, duplicate_object, rename_table
from dbx.core.search import SearchCriterion, SearchRequest
from dbx.io.csv_io import (
    detect_delimiter,
    export_rows,
    read_csv,
    read_table,
    records_from_table,
    suggest_mapping,
)
from dbx.runtime.rowset import Rowset, re_evaluate
from dbx.designers.database_designer import DatabaseDesignerWidget, RelationshipDialog
from dbx.ui.import_wizard import ImportCsvDialog

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _target_table() -> Table:
    return Table(
        name="importati",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("nome", T.TEXT, size=60, caption="Nome"),
            Field("importo", T.DECIMAL, size=12, fmt=".2f"),
            Field("data", T.DATE),
            Field("attivo", T.BOOLEAN),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
        ],
    )


@scenario(
    "dat-01-csv-detect",
    "D01 — Rilevamento di delimitatore e codifica",
    "data",
    features=("CSV-DETECT-DELIM", "CSV-DETECT-ENCODING", "CSV-HEADER"),
    min_checks=9,
    budget_s=6.0,
)
def dat_csv_detect(ctx: E2EContext) -> None:
    samples = {
        "comma.csv": "codice,nome,importo\nA1,Alfa,10.5\nA2,Beta,20\n",
        "semicolon.csv": "codice;nome;importo\nA1;Alfa;10,5\nA2;Beta;20\n",
        "tab.tsv": "codice\tnome\timporto\nA1\tAlfa\t10.5\n",
    }
    paths = {}
    for name, content in samples.items():
        path = ctx.work / name
        path.write_text(content, encoding="utf-8")
        paths[name] = path
    ctx.check_close(detect_delimiter(samples["comma.csv"].splitlines()[0]), ",", "virgola")
    ctx.check_close(detect_delimiter(samples["semicolon.csv"].splitlines()[0]), ";", "punto e virgola")
    ctx.check_close(detect_delimiter(samples["tab.tsv"].splitlines()[0]), "\t", "tab")
    delimiters = []
    for name, path in paths.items():
        delimiter, encoding, rows = read_table(str(path), "auto", "auto")
        delimiters.append(delimiter)
        ctx.check(len(rows) >= 2, f"righe lette da {name}")
        ctx.check(encoding.lower().replace("-", "") in ("utf8", "utf8sig"), f"codifica {name}")
    ctx.check(delimiters == [",", ";", "\t"], "delimitatori automatici")
    latin = ctx.work / "latin.csv"
    latin.write_bytes("codice;nome\nA1;Città\n".encode("latin-1"))
    _delimiter, encoding, rows = read_table(str(latin), "auto", "auto")
    ctx.check_close(rows[1][1], "Città", "codifica latin-1 letta")
    ctx.check(encoding.lower().replace("-", "") in ("iso88591", "latin1", "cp1252"), "codifica rilevata")


@scenario(
    "dat-02-csv-mapping",
    "D02 — Mappatura, tipi e calcolati nell'import",
    "data",
    features=("CSV-MAPPING", "CSV-TYPES", "CSV-CALCULATED", "CSV-HEADER"),
    min_checks=9,
    budget_s=8.0,
)
def dat_csv_mapping(ctx: E2EContext) -> None:
    project = ctx.new_project("ImportMappatura")
    fixtures.apply(project, _target_table())
    path = ctx.work / "clienti.csv"
    path.write_text(
        "Codice;Nome;Importo;Data;Attivo\nI1;Alfa;10,50;2026-01-10;Sì\nI2;Beta;20;2026-02-10;No\n",
        encoding="utf-8",
    )
    dialog = ctx.track(ImportCsvDialog(project, "importati"))
    dialog.path_edit.setText(str(path))
    dialog.delimiter_combo.setCurrentIndex(dialog.delimiter_combo.findData(";"))
    dialog.reload_preview()
    ctx.check_close(len(dialog._rows), 3, "intestazione più due righe")
    mapping = dialog.current_mapping()
    ctx.check_close(mapping, ["codice", "nome", "importo", "data", "attivo"], "mappatura automatica")
    ctx.check(dialog.mapping_table.rowCount() == 5, "cinque colonne mappate")
    records = records_from_table(dialog._rows, project.require_table("importati"), mapping, True)
    ctx.check_close(records[0]["importo"], 10.5, "decimale convertito")
    ctx.check_close(str(records[0]["data"]), "2026-01-10", "data convertita")
    ctx.check(bool(records[0]["attivo"]) is True, "booleano convertito")
    count, rejected = dialog._insert_records(records, False)
    ctx.check_close(count, 2, "due record importati")
    ctx.check_close(rejected, [], "nessuno scarto")
    rows = Rowset(project.db, project.require_table("importati")).open(order="codice").rows()
    ctx.check_close(rows[0]["nome_maiuscolo"], "ALFA", "calcolato dopo import")
    ctx.capture(dialog, "data-import-mapping", (900, 680))


@scenario(
    "dat-03-csv-rejects",
    "D03 — Scarti di import e conteggi",
    "data",
    features=("CSV-REJECTS", "CSV-MAPPING"),
    min_checks=7,
    budget_s=8.0,
)
def dat_csv_rejects(ctx: E2EContext) -> None:
    project = ctx.new_project("ImportScarti")
    fixtures.apply(project, _target_table())
    path = ctx.work / "scarti.csv"
    path.write_text("codice;nome\nI1;Valido\n;Senza codice\nI3;Altro\n", encoding="utf-8")
    dialog = ctx.track(ImportCsvDialog(project, "importati"))
    dialog.path_edit.setText(str(path))
    dialog.reload_preview()
    count, rejected = dialog._insert_records(
        records_from_table(dialog._rows, project.require_table("importati"), dialog.current_mapping(), True),
        False,
    )
    ctx.check_close(count, 2, "due record validi")
    ctx.check_close(len(rejected), 1, "uno scarto")
    ctx.check("Riga 3" in rejected[0], "riga dello scarto indicata", rejected[0])
    ctx.check("Obbligatorio" in rejected[0] or "obbligatorio" in rejected[0], "motivo dello scarto")
    ctx.check_close(Rowset(project.db, project.require_table("importati")).count(), 2, "solo validi in tabella")
    mapping = dialog.current_mapping()
    ctx.check_close(mapping[0], "codice", "mappatura conservata")
    ctx.check(dialog.import_button.isEnabled(), "pulsante importa abilitato")


@scenario(
    "dat-04-csv-clear-backup",
    "D04 — Svuotamento con backup e reimport",
    "data",
    features=("CSV-CLEAR-BACKUP", "CSV-REJECTS", "MNT-BACKUP"),
    min_checks=4,
    budget_s=8.0,
)
def dat_csv_clear_backup(ctx: E2EContext) -> None:
    project = ctx.new_project("ImportSvuota")
    fixtures.apply(project, _target_table())
    Rowset(project.db, project.require_table("importati")).insert({"codice": "OLD", "nome": "Vecchio"})
    path = ctx.work / "nuovi.csv"
    path.write_text("codice;nome\nN1;Nuovo\nN2;Altro\n", encoding="utf-8")
    dialog = ctx.track(ImportCsvDialog(project, "importati"))
    dialog.path_edit.setText(str(path))
    dialog.clear_box.setChecked(True)
    dialog.reload_preview()
    dialog.run_import()
    ctx.check_close(dialog.imported, 2, "due record importati")
    ctx.check(any(project.backups_path.iterdir()), "backup prima dello svuotamento")
    rows = Rowset(project.db, project.require_table("importati")).open(order="codice").rows()
    ctx.check_close([row["codice"] for row in rows], ["N1", "N2"], "vecchi record rimossi")
    ctx.check_close(rows[0]["nome_maiuscolo"], "NUOVO", "calcolato sul nuovo import")


@scenario(
    "dat-05-csv-export",
    "D05 — Export CSV dalla Browse",
    "data",
    features=("CSV-EXPORT", "CSV-EXPORT-CALC"),
    min_checks=6,
    budget_s=8.0,
)
def dat_csv_export(ctx: E2EContext) -> None:
    project = ctx.new_project("ExportCsv")
    fixtures.settled_project(project)
    view = ctx.data_view(project, "clienti")
    target = ctx.work / "export.csv"
    with mock.patch(
        "dbx.ui.data_view.QFileDialog.getSaveFileName",
        return_value=(str(target), "CSV (*.csv)"),
    ):
        view.export_csv()
    ctx.check(target.exists(), "file CSV creato")
    content = target.read_text(encoding="utf-8-sig")
    ctx.check("C001" in content and "Alfa" in content, "dati esportati")
    ctx.check("ALFA SRL" in content.upper() or "ALFA" in content.upper(), "calcolato esportato")
    ctx.check(content.splitlines()[0].startswith("codice"), "intestazioni esportate")
    ctx.check_close(len(content.splitlines()), 6, "cinque record più intestazione")
    ctx.check("Roma" in content, "città esportata")


@scenario(
    "dat-06-er-diagram",
    "D06 — Database Designer: vista, zoom ed export",
    "data",
    features=("ER-VIEW", "ER-LAYOUT", "ER-ZOOM", "ER-EXPORT-PNG", "ER-EXPORT-SVG", "ER-CARD", "ER-INSPECTOR"),
    min_checks=10,
    budget_s=12.0,
    screenshots=("data-er-diagram",),
)
def dat_er_diagram(ctx: E2EContext) -> None:
    project = ctx.new_project("SchemaER")
    fixtures.settled_project(project)
    designer = ctx.track(DatabaseDesignerWidget(project))
    ctx.check_close(len(designer.graph.nodes), 2, "due nodi")
    ctx.check_close(len(designer.graph.edges), 1, "una relazione")
    ctx.check(designer.canvas.card_rect("clienti").width() > 0, "card clienti disegnata")
    ctx.check_close(designer.table_list.count(), 2, "elenco tabelle")
    designer.select_table("fatture")
    ctx.check_close(designer.selected_table, "fatture", "tabella selezionata")
    ctx.check("fatture" in designer.status_label.text(), "stato selezione")
    designer.zoom_combo.setCurrentIndex(designer.zoom_combo.findData(150))
    ctx.check_close(round(designer.diagram.zoom * 100), 150, "zoom 150%")
    designer.auto_layout()
    ctx.check(designer.diagram.nodes, "auto-layout produce posizioni")
    png = ctx.work / "schema.png"
    svg = ctx.work / "schema.svg"
    with mock.patch(
        "dbx.designers.database_designer.QFileDialog.getSaveFileName",
        side_effect=[(str(png), "PNG (*.png)"), (str(svg), "SVG (*.svg)")],
    ):
        designer.export_png()
        designer.export_svg()
    ctx.check(png.exists() and png.stat().st_size > 1000, "PNG non vuoto")
    ctx.check(svg.exists() and "<svg" in svg.read_text(encoding="utf-8"), "SVG valido")
    ctx.capture(designer, "data-er-diagram", (1180, 760))


@scenario(
    "dat-07-er-relation",
    "D07 — Creazione relazione dal Database Designer",
    "data",
    features=("ER-RELATION", "ER-INSPECTOR", "TB-FK", "TB-BACKUP"),
    min_checks=7,
    budget_s=10.0,
)
def dat_er_relation(ctx: E2EContext) -> None:
    project = ctx.new_project("NuovaRelazione")
    fixtures.apply(project, fixtures.clienti_table())
    child = fixtures.fatture_table()
    child.foreign_keys = []
    fixtures.apply(project, child)
    fixtures.seed_clienti(project)
    designer = ctx.track(DatabaseDesignerWidget(project))
    dialog = ctx.track(RelationshipDialog(designer.graph))
    dialog.child_table.setCurrentIndex(dialog.child_table.findData("fatture"))
    dialog.parent_table.setCurrentIndex(dialog.parent_table.findData("clienti"))
    dialog.child_field.setCurrentIndex(dialog.child_field.findData("cliente"))
    dialog.parent_field.setCurrentIndex(dialog.parent_field.findData("codice"))
    dialog.on_delete.setCurrentIndex(dialog.on_delete.findData("CASCADE"))
    relationship = dialog.relationship()
    ctx.check(relationship is not None, "relazione costruita")
    child_name, fk = relationship
    ctx.check(designer._apply_relationship(child_name, fk), "relazione applicata")
    designer._refresh_schema()
    project = ctx.reopen(project)
    saved = project.require_table("fatture")
    ctx.check_close(len(saved.foreign_keys), 1, "FK persistita")
    ctx.check_close(saved.foreign_keys[0].on_delete, "CASCADE", "azione ON DELETE")
    rows = project.db.query('PRAGMA foreign_key_list("fatture")')
    ctx.check_close(rows[0]["table"], "clienti", "FK nel database")
    ctx.check(any(project.backups_path.iterdir()), "backup della relazione")
    designer.select_table("fatture")
    ctx.check("fatture" in designer.selection_label.text() or "fatture" in designer.status_label.text(), "ispettore aggiornato")


@scenario(
    "dat-08-er-schema-edit",
    "D08 — Modifica schema dal diagramma",
    "data",
    features=("ER-SCHEMA-EDIT", "ER-VIEW", "ER-CARD"),
    min_checks=4,
    budget_s=10.0,
)
def dat_er_schema_edit(ctx: E2EContext) -> None:
    project = ctx.new_project("ModificaSchema")
    fixtures.settled_project(project)
    designer = ctx.track(DatabaseDesignerWidget(project))
    opened: list[tuple[str, str]] = []
    designer.open_table.connect(lambda name, mode: opened.append((name, mode)))
    designer.select_table("clienti")
    designer.edit_table()
    ctx.check_close(opened, [("clienti", "edit")], "richiesta di modifica struttura")
    builder = ctx.table_builder(project, project.require_table("clienti"))
    builder._add_field_row(Field("telefono", T.TEXT, size=30))
    builder._apply()
    designer._refresh_schema()
    node = designer.graph.table("clienti")
    ctx.check(node is not None and node.field("telefono") is not None, "card aggiornata con il nuovo campo")
    ctx.check(designer.canvas.card_height(node) > 0, "altezza card ricalcolata")
    designer.select_table("clienti")
    ctx.check("clienti" in designer.table_list.currentItem().text(), "selezione mantenuta")


@scenario(
    "dat-09-rename-refs",
    "D09 — Rinomina tabella e aggiornamento riferimenti",
    "data",
    features=("MNT-RENAME-REFS", "MNT-BACKUP"),
    min_checks=10,
    budget_s=10.0,
)
def dat_rename_refs(ctx: E2EContext) -> None:
    project = ctx.demo_project("Rinomina")
    before = json.dumps(project.objects, ensure_ascii=False)
    ctx.check("clienti" in before, "riferimenti iniziali")
    rename_table(project, "clienti", "clienti2")
    project = ctx.reopen(project)
    ctx.check("clienti2" in project.names("tables"), "tabella rinominata")
    ctx.check("clienti" not in project.names("tables"), "vecchio nome assente")
    queries = json.dumps(project.objects["queries"], ensure_ascii=False)
    forms = json.dumps(project.objects["forms"], ensure_ascii=False)
    reports = json.dumps(project.objects["reports"], ensure_ascii=False)
    ctx.check("clienti2" in queries, "query aggiornata")
    ctx.check("clienti2" in forms or not forms, "form aggiornato")
    ctx.check(all(project.artifact("reports", name) for name in project.names("reports")), "report ancora leggibili")
    ctx.check(project.db.has_table("clienti2"), "tabella SQLite rinominata")
    ctx.check(not project.db.has_table("clienti"), "vecchia tabella assente")
    ctx.check(Rowset(project.db, project.require_table("clienti2")).open().count() >= 3, "dati preservati")
    ctx.check(any(project.backups_path.iterdir()), "backup della rinomina")


@scenario(
    "dat-10-duplicate",
    "D10 — Duplicazione di tabelle e oggetti",
    "data",
    features=("MNT-DUPLICATE", "MNT-DUPLICATE-DATA"),
    min_checks=10,
    budget_s=10.0,
)
def dat_duplicate(ctx: E2EContext) -> None:
    project = ctx.demo_project("Duplicazione")
    source_count = Rowset(project.db, project.require_table("clienti")).open().count()
    copy = duplicate_object(project, "tables", "clienti", "clienti_copia")
    ctx.check_close(copy, "clienti_copia", "tabella copiata")
    ctx.check_close(Rowset(project.db, project.require_table("clienti_copia")).open().count(), source_count, "dati copiati")
    for category, name in (
        ("forms", "form_clienti"),
        ("queries", "fatture_clienti"),
        ("reports", "fatture_per_cliente"),
        ("scripts", "riepilogo_fatture"),
        ("menus", "principale"),
    ):
        if name not in project.names(category):
            continue
        target = duplicate_object(project, category, name, f"{name}_copia")
        ctx.check(target in project.names(category), f"{category} duplicato")
        cloned = project.artifact(category, target)
        ctx.check(cloned is not None, f"{category}: artefatto leggibile")
    project = ctx.reopen(project)
    ctx.check("clienti_copia" in project.names("tables"), "duplicato persistito")
    ctx.check_close(
        Rowset(project.db, project.require_table("clienti_copia")).open().count(),
        source_count,
        "dati del duplicato dopo riapertura",
    )


@scenario(
    "dat-11-maintenance",
    "D11 — Compattazione e verifica integrità",
    "data",
    features=("MNT-COMPACT", "MNT-INTEGRITY", "MNT-BACKUP"),
    min_checks=7,
    budget_s=10.0,
)
def dat_maintenance(ctx: E2EContext) -> None:
    project = ctx.demo_project("Manutenzione")
    before = context_size(project)
    backup = compact_database(project)
    ctx.check(backup is not None, "backup di compattazione")
    ctx.check(any(project.backups_path.iterdir()), "file di backup presente")
    ctx.check_close(check_database(project).lower(), "ok", "integrità SQLite")
    ctx.check(project.database_file.exists(), "database ancora presente")
    ctx.check(Rowset(project.db, project.require_table("clienti")).open().count() >= 3, "dati leggibili dopo VACUUM")
    ctx.check(context_size(project) <= before + 4096, "dimensione non cresciuta")
    project = ctx.reopen(project)
    ctx.check(project.require_table("clienti") is not None, "progetto riaperto")


def context_size(project) -> int:
    return project.database_file.stat().st_size if project.database_file.exists() else 0


@scenario(
    "dat-12-reevaluate",
    "D12 — Riapplica regole ai record storici",
    "data",
    features=("MNT-REEVALUATE", "TB-FIELD-CASE", "TB-FIELD-DOMAIN"),
    min_checks=6,
    budget_s=10.0,
)
def dat_reevaluate(ctx: E2EContext) -> None:
    project = ctx.new_project("Riapplica")
    table = Table(
        name="storici",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("sigla", T.TEXT, size=10, case_mode="upper"),
            Field("voto", T.INTEGER, domain_min="1", domain_max="10"),
            Field("stato", T.CHOICE, choices=[{"value": "A", "label": "Aperto"}, {"value": "C", "label": "Chiuso"}]),
        ],
    )
    fixtures.apply(project, table)
    project.db.execute(
        'INSERT INTO "storici" ("codice", "sigla", "voto", "stato") VALUES (?, ?, ?, ?)',
        ("S1", "abc", 99, "X"),
    )
    project.db.execute(
        'INSERT INTO "storici" ("codice", "sigla", "voto", "stato") VALUES (?, ?, ?, ?)',
        ("S2", "ok", 5, "A"),
    )
    updated, issues = re_evaluate(project.require_table("storici"), project.db)
    ctx.check(updated >= 1, "record normalizzati")
    codes = {issue.code for issue in issues}
    ctx.check("domain_stale" in codes, "avviso dominio storico")
    ctx.check("choice_stale" in codes, "avviso scelta storica")
    rows = {row["codice"]: row for row in Rowset(project.db, project.require_table("storici")).open().rows()}
    ctx.check_close(rows["S1"]["sigla"], "ABC", "maiuscole applicate")
    ctx.check_close(rows["S2"]["voto"], 5, "valore valido invariato")
    ctx.check_close(rows["S2"]["stato"], "A", "scelta valida invariata")
