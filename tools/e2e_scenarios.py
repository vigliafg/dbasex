"""Scenari end-to-end del harness dBX (0.9+).

Ogni scenario usa un progetto temporaneo isolato e percorre una funzionalità
completa: modello dati, query, form, report, etichette, script, manutenzione,
designer e build. Le funzioni non usano pytest: il runner
``tools/e2e_harness.py`` raccoglie esiti, tempi, log e screenshot.
"""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field as dc_field
from datetime import date
from pathlib import Path
from typing import Any, Callable
from unittest import mock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from dbx import __version__
from dbx.core import types as T
from dbx.core.crosstab import build_crosstab
from dbx.core.form_model import FormSpec
from dbx.core.label_model import LabelSpec
from dbx.core.metadata import Field, ForeignKey, Index, Table
from dbx.core.project import Project
from dbx.core.query_engine import query_table, run_query
from dbx.core.query_model import (
    QueryAggregate,
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
)
from dbx.core.refactor import (
    check_database,
    compact_database,
    duplicate_object,
    rename_table,
)
from dbx.core.search import (
    SearchCriterion,
    SearchRequest,
    count_matches,
    delete_find,
    replace_in_rowset,
    save_find,
    saved_finds,
)
from dbx.designers.project_builder import build_project, validate_project
from dbx.io.csv_io import export_rows, records_from_table
from dbx.io.pdf_export import export_pdf, page_pixmap
from dbx.runtime.label_engine import render_labels_for_project
from dbx.runtime.report_engine import Control, ReportSpec
from dbx.runtime.rowset import Rowset, RowsetError
from dbx.runtime.script_engine import (
    NullUI,
    ScriptEngine,
    ScriptError,
    from_text,
    new_step,
    script_parameters,
    to_text,
)
from dbx.samples import create_demo_project
from dbx.ui.report_preview import ReportPreviewDialog, build_pages
from dbx.ui.theme import apply_theme

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# Contesto e utilita'
# --------------------------------------------------------------------------- #
class ScenarioFailure(AssertionError):
    """Fallimento di un controllo E2E."""


@dataclass
class HarnessContext:
    """Stato condiviso tra runner e scenari."""

    output: Path
    qapp: QApplication
    screenshots_enabled: bool = True
    keep: bool = False
    dialogs: list[tuple[str, str, str]] = dc_field(default_factory=list)
    checks: list[dict[str, str]] = dc_field(default_factory=list)
    projects: list[Project] = dc_field(default_factory=list)
    screenshots: list[str] = dc_field(default_factory=list)
    info: dict[str, Any] = dc_field(default_factory=dict)
    _tmp: Path | None = None

    def begin(self, scenario: str) -> None:
        self.dialogs = []
        self.checks = []
        self.projects = []
        self.screenshots = []
        self._tmp = Path(tempfile.mkdtemp(prefix=f"dbx-e2e-{scenario}-"))
        self.info = {}

    def finish(self) -> None:
        for project in reversed(self.projects):
            try:
                project.close()
            except Exception:
                pass
        self.projects = []
        if self._tmp is not None and not self.keep:
            shutil.rmtree(self._tmp, ignore_errors=True)
        self._tmp = None

    @property
    def work(self) -> Path:
        if self._tmp is None:
            raise RuntimeError("Contesto non inizializzato")
        return self._tmp

    def new_project(self, name: str = "E2E") -> Project:
        project = Project.create(self.work / name, name)
        self.projects.append(project)
        return project

    def demo_project(self, name: str = "Rubrica") -> Project:
        project = create_demo_project(self.work / name, name)
        self.projects.append(project)
        return project

    # ------------------------------------------------------------------ esiti
    def check(self, condition: Any, name: str, detail: str = "") -> None:
        if condition:
            self.checks.append({"name": name, "status": "pass", "detail": detail})
            return
        self.checks.append({"name": name, "status": "fail", "detail": detail})
        raise ScenarioFailure(f"{name}: {detail}" if detail else name)

    def note(self, key: str, value: Any) -> None:
        self.info[str(key)] = value

    # --------------------------------------------------------------- dialoghi
    @contextmanager
    def auto_dialogs(self):
        """Neutralizza i dialoghi modali: nessun test deve bloccarsi in attesa."""
        ctx = self

        def information(_parent, title, text, *args, **kwargs):
            ctx.dialogs.append(("info", str(title), str(text)))
            return QMessageBox.StandardButton.Ok

        def warning(_parent, title, text, *args, **kwargs):
            ctx.dialogs.append(("warning", str(title), str(text)))
            return QMessageBox.StandardButton.Ok

        def critical(_parent, title, text, *args, **kwargs):
            ctx.dialogs.append(("critical", str(title), str(text)))
            return QMessageBox.StandardButton.Ok

        def question(_parent, title, text, *args, **kwargs):
            ctx.dialogs.append(("question", str(title), str(text)))
            return QMessageBox.StandardButton.Yes

        def get_text(_parent, title, label, *args, **kwargs):
            ctx.dialogs.append(("input", str(title), str(label)))
            return "valore", True

        def get_item(_parent, title, label, items, *args, **kwargs):
            ctx.dialogs.append(("item", str(title), str(label)))
            return (items[0] if items else "", True)

        with ExitStack() as stack:
            for target, name, replacement in (
                (QMessageBox, "information", information),
                (QMessageBox, "warning", warning),
                (QMessageBox, "critical", critical),
                (QMessageBox, "question", question),
                (QInputDialog, "getText", get_text),
                (QInputDialog, "getItem", get_item),
                (QFileDialog, "getSaveFileName", lambda *a, **k: ("", "")),
                (QFileDialog, "getOpenFileName", lambda *a, **k: ("", "")),
                (QFileDialog, "getExistingDirectory", lambda *a, **k: ""),
            ):
                stack.enter_context(mock.patch.object(target, name, replacement))
            yield

    @contextmanager
    def quiet_qt(self):
        """Silenzia i warning del plugin offscreen durante show/grab."""
        saved = os.dup(2)
        sink = open(os.devnull, "w")
        os.dup2(sink.fileno(), 2)
        try:
            yield
        finally:
            os.dup2(saved, 2)
            os.close(saved)
            sink.close()

    # ------------------------------------------------------------ screenshot
    def capture(self, widget: Any, name: str, size: tuple[int, int] | None = None) -> str | None:
        if not self.screenshots_enabled:
            return None
        from PyQt6.QtWidgets import QWidget

        if not isinstance(widget, QWidget):
            return None
        if size:
            widget.resize(*size)
        target = self.output / "screenshots" / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.quiet_qt():
            widget.show()
            self.qapp.processEvents()
            widget.resize(*size)
            self.qapp.processEvents()
        pixmap = widget.grab()
        if not pixmap.isNull() and pixmap.save(str(target), "PNG"):
            self.screenshots.append(str(target))
            widget.hide()
            self.qapp.processEvents()
            return str(target)
        widget.hide()
        return None


# --------------------------------------------------------------------------- #
# Scenari
# --------------------------------------------------------------------------- #
def scenario_environment(ctx: HarnessContext) -> None:
    """Versioni, import dei moduli e progetto demo valido."""
    ctx.note("python", platform.python_version())
    ctx.note("platform", platform.platform())
    ctx.note("dbx_version", __version__)
    try:
        from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR

        ctx.note("qt", QT_VERSION_STR)
        ctx.note("pyqt", PYQT_VERSION_STR)
    except Exception:  # pragma: no cover - difensivo
        pass

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = ""
    for line in pyproject.splitlines():
        if line.strip().startswith("version ="):
            declared = line.split("=", 1)[1].strip().strip('"')
            break
    ctx.check(declared == __version__, "versione coerente tra pyproject e pacchetto", declared)

    modules = [
        "dbx.core.db",
        "dbx.core.expressions",
        "dbx.core.query_engine",
        "dbx.runtime.report_engine",
        "dbx.runtime.label_engine",
        "dbx.runtime.form_runtime",
        "dbx.runtime.script_engine",
        "dbx.ui.main_window",
        "dbx.designers.report_builder",
        "dbx.designers.label_builder",
        "dbx.io.pdf_export",
        "dbx.io.csv_io",
    ]
    for module in modules:
        importlib.import_module(module)
    ctx.check(True, "import dei moduli principali", f"{len(modules)} moduli")

    process = subprocess.run(
        [sys.executable, "-m", "dbx", "--version"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env=dict(os.environ),
    )
    ctx.check(process.returncode == 0, "CLI --version eseguibile", process.stderr[-300:])
    ctx.check(
        process.stdout.strip() == f"dBX {__version__}",
        "CLI --version riporta la versione",
        process.stdout.strip(),
    )

    project = ctx.demo_project("Demo")
    errors = validate_project(project)
    ctx.check(not errors, "progetto demo valido", "; ".join(errors))
    ctx.check(len(project.names("tables")) == 2, "progetto demo con due tabelle")
    ctx.check(len(project.names("queries")) == 2, "progetto demo con due query")
    ctx.check(len(project.names("forms")) == 3, "progetto demo con tre form")
    ctx.check(len(project.names("reports")) == 2, "progetto demo con due report")
    ctx.check(len(project.names("scripts")) == 2, "progetto demo con due script")
    ctx.check("principale" in project.names("menus"), "progetto demo con menu principale")


def _e2e_tables(project: Project) -> tuple[Table, Table]:
    clienti = Table(
        name="clienti",
        caption="Clienti E2E",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("nome", T.TEXT, size=60, required=True),
            Field("anni", T.INTEGER, default="0"),
            Field("saldo", T.DECIMAL, default="0"),
            Field("attivo", T.BOOLEAN, default="1"),
            Field("creato", T.DATE, auto_date="insert"),
            Field("note", T.MEMO),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
            Field("progressivo", T.INTEGER, auto_serial=True),
        ],
        indexes=[Index(fields=["codice"], unique=True), Index(fields=["nome"])],
    )
    fatture = Table(
        name="fatture",
        caption="Fatture E2E",
        fields=[
            Field("numero", T.INTEGER, required=True, pk=True),
            Field("cliente", T.TEXT, size=8, required=True),
            Field("data", T.DATE),
            Field("importo", T.DECIMAL, default="0"),
            Field("pagata", T.BOOLEAN, default="0"),
        ],
        indexes=[Index(fields=["cliente"]), Index(fields=["data"])],
        foreign_keys=[
            ForeignKey(
                columns=["cliente"],
                ref_table="clienti",
                ref_columns=["codice"],
                on_delete="RESTRICT",
            )
        ],
    )
    project.apply_table(clienti)
    project.apply_table(fatture)
    return project.require_table("clienti"), project.require_table("fatture")


def scenario_project_tables(ctx: HarnessContext) -> None:
    """Creazione tabelle, tipi, indici, FK, calcoli, auto-enter e CRUD."""
    project = ctx.new_project("Tabelle")
    clienti, fatture = _e2e_tables(project)
    ctx.check(clienti.field("nome_maiuscolo") is not None, "campo calcolato creato")
    ctx.check(clienti.field("progressivo").auto_serial, "serie automatica creata")
    ctx.check(len(fatture.foreign_keys) == 1, "chiave esterna creata")
    ctx.check(len(project.db.table_names()) >= 2, "tabelle presenti in SQLite")

    rows = Rowset(project.db, clienti)
    ids: list[int] = []
    for record in (
        {"codice": "C001", "nome": "Alfa Srl", "anni": 36, "saldo": 1200.5, "attivo": True},
        {"codice": "C002", "nome": "Beta Studio", "anni": 28, "saldo": 0, "attivo": True},
        {"codice": "C003", "nome": "Gamma snc", "anni": 45, "saldo": -50, "attivo": False},
    ):
        ids.append(rows.insert(record))
    ctx.check(len(ids) == 3, "tre record inseriti")
    rows.open(order="codice")
    ctx.check([row["progressivo"] for row in rows.rows()] == [1, 2, 3], "serie automatica progressiva")
    ctx.check(rows.rows()[0]["nome_maiuscolo"] == "ALFA SRL", "campo calcolato valorizzato")
    ctx.check(isinstance(rows.rows()[0]["creato"], date), "data automatica di creazione")

    try:
        rows.insert({"codice": "C001", "nome": "Duplicato"})
        ctx.check(False, "indice univoco su codice")
    except RowsetError:
        ctx.check(True, "indice univoco su codice")

    rows.update(ids[0], {"nome": "Alfa S.p.A.", "saldo": 1300})
    rows.open(order="codice")
    ctx.check(rows.rows()[0]["nome_maiuscolo"] == "ALFA S.P.A.", "calcolo aggiornato dopo modifica")
    ctx.check(rows.rows()[0]["saldo"] == 1300, "aggiornamento parziale mantenuto")

    rows.first()
    ctx.check(rows.current["codice"] == "C001", "navigazione first")
    rows.next()
    ctx.check(rows.current["codice"] == "C002", "navigazione next")
    rows.last()
    ctx.check(rows.current["codice"] == "C003", "navigazione last")
    ctx.check(rows.find("codice", "C002") is not None, "ricerca nel rowset")

    fatture_rows = Rowset(project.db, fatture)
    for record in (
        {"numero": 1, "cliente": "C001", "data": "2026-01-10", "importo": 100.0, "pagata": True},
        {"numero": 2, "cliente": "C001", "data": "2026-02-10", "importo": 200.0, "pagata": False},
        {"numero": 3, "cliente": "C002", "data": "2026-03-10", "importo": 300.0, "pagata": False},
    ):
        fatture_rows.insert(record)
    ctx.check(fatture_rows.count() == 3, "fatture collegate inserite")
    try:
        fatture_rows.insert({"numero": 4, "cliente": "C999", "importo": 1})
        ctx.check(False, "vincolo di chiave esterna")
    except RowsetError:
        ctx.check(True, "vincolo di chiave esterna")
    try:
        Rowset(project.db, project.require_table("clienti")).delete(ids[0])
        ctx.check(False, "ON DELETE RESTRICT")
    except RowsetError:
        ctx.check(True, "ON DELETE RESTRICT")

    fatture_rows.delete(3)
    ctx.check(fatture_rows.count() == 2, "eliminazione record")

    from dbx.ui.data_view import DataView

    view = DataView(project, "clienti")
    try:
        ctx.check(view.rowset.count() == 3, "DataView carica i record")
        view._search = SearchRequest([SearchCriterion("nome", "contains", "Alfa")])
        view.refresh()
        ctx.check(len(view.rowset) == 1, "filtro DataView")
        view.clear_find()
        view.goto_record(2)
        ctx.check(view.rowset.index == 2, "navigazione DataView")
        ctx.capture(view, "e2e-data-view", (1000, 620))
    finally:
        view.deleteLater()


def scenario_search_csv(ctx: HarnessContext) -> None:
    """Find mode, sostituzione, ricerche salvate, import ed export CSV."""
    project = ctx.demo_project("Ricerca")
    clienti = project.require_table("clienti")

    request = SearchRequest([SearchCriterion("citta", "contains", "Roma")])
    ctx.check(count_matches(project.db, clienti, request) == 1, "Find mode: contiene")
    request_all = SearchRequest(
        [
            SearchCriterion("nome", "contains", "a"),
            SearchCriterion("attivo", "eq", "1"),
        ]
    )
    ctx.check(count_matches(project.db, clienti, request_all) == 2, "Find mode: criteri AND")
    request_or = SearchRequest(
        [
            SearchCriterion("citta", "eq", "Milano"),
            SearchCriterion("citta", "eq", "Torino"),
        ],
        match="any",
    )
    ctx.check(count_matches(project.db, clienti, request_or) == 2, "Find mode: criteri OR")
    request_omit = SearchRequest([SearchCriterion("attivo", "eq", "1", omit=True)])
    ctx.check(count_matches(project.db, clienti, request_omit) == 1, "Find mode: Ometti")

    rowset = Rowset(project.db, clienti).open(order="codice")
    changed = replace_in_rowset(rowset, "Srl", "S.p.A.", field="nome")
    ctx.check(changed == 1, "sostituzione su campo testuale", f"{changed} celle")
    project.save()

    save_find(project, "clienti", "solo Roma", request)
    ctx.check("solo Roma" in saved_finds(project, "clienti"), "ricerca salvata")
    ctx.check(delete_find(project, "clienti", "solo Roma"), "ricerca salvata eliminata")

    from dbx.ui.find_dialog import FindDialog

    dialog = FindDialog(project, clienti, request)
    try:
        ctx.check(dialog.request().match == "all", "FindDialog legge i criteri")
        ctx.check(dialog.grid.columnCount() == 4, "FindDialog popola la griglia")
    finally:
        dialog.close()

    imported = Table(
        name="import_clienti",
        fields=[
            Field("codice", T.TEXT, size=8, required=True),
            Field("nome", T.TEXT, size=60),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
        ],
    )
    project.apply_table(imported, backup=False)
    csv_path = ctx.work / "clienti.csv"
    csv_path.write_text("codice;nome\nI1;Alfa\nI2;Beta\n", encoding="utf-8")

    from dbx.ui.import_wizard import ImportCsvDialog

    importer = ImportCsvDialog(project, "import_clienti")
    try:
        importer.path_edit.setText(str(csv_path))
        importer.reload_preview()
        ctx.check(len(importer._rows) == 3, "anteprima CSV con intestazione")
        records = records_from_table(
            importer._rows,
            imported,
            importer.current_mapping(),
            importer.header_box.isChecked(),
        )
        count = importer._insert_records(records, False)
        ctx.check(count == 2, "import CSV in tabella esistente")
        ctx.check(
            [row["nome_maiuscolo"] for row in Rowset(project.db, imported).open().rows()]
            == ["ALFA", "BETA"],
            "campi calcolati sui record importati",
        )
        importer.clear_box.setChecked(True)
        importer.run_import()
        ctx.check(importer.imported == 2, "import con svuotamento")
        ctx.check(
            Rowset(project.db, imported).open().count() == 2,
            "svuotamento seguito da import",
        )
        ctx.check(
            any(project.backups_path.iterdir()),
            "backup prima dello svuotamento",
        )
        ctx.capture(importer, "e2e-import-csv", (900, 620))
    finally:
        importer.close()

    export_path = ctx.work / "export.csv"
    export_rows(
        export_path,
        imported.field_names,
        Rowset(project.db, imported).open().rows(),
        table=imported,
    )
    content = export_path.read_text(encoding="utf-8-sig")
    ctx.check("I1" in content and "ALFA" in content, "export CSV con calcolati")


def scenario_queries_crosstab(ctx: HarnessContext) -> None:
    """Query con join, filtri, aggregati, QBE, Crosstab e griglia risultati."""
    project = ctx.demo_project("Query")
    spec = QuerySpec.from_project(project, "fatture_clienti")
    ctx.check(spec is not None, "query demo caricata")
    result = run_query(project, spec)
    ctx.check(len(result) == 5, "query join: cinque righe")
    ctx.check(len(result.columns) == 5, "query join: cinque colonne")
    ctx.check(result.rows[0]["cliente_nome"] == "Alfa Srl", "join risolve il cliente")

    aggregate = QuerySpec(
        name="agg_e2e",
        base="fatture",
        group_by=["fatture.cliente"],
        aggregates=[
            QueryAggregate("sum", "fatture", "importo", "totale"),
            QueryAggregate("count", "fatture", alias="numero_fatture"),
        ],
        sorts=[QuerySort("totale", "desc")],
    )
    ctx.check(aggregate.validate(project.tables()) == [], "aggregati validi")
    grouped = run_query(project, aggregate)
    ctx.check(len(grouped) == 3, "GROUP BY: tre gruppi")
    ctx.check(grouped.rows[0]["totale"] == 3450.5, "somma per gruppo")
    ctx.check(sum(row["totale"] for row in grouped.rows) == 5900.5, "totale aggregato")

    crosstab = build_crosstab(result, "cliente_nome", "pagata", "importo")
    ctx.check(len(crosstab.row_values) == 3, "Crosstab: tre righe")
    ctx.check(len(crosstab.column_values) == 2, "Crosstab: due colonne")
    ctx.check(crosstab.grand_total == 5900.5, "Crosstab: totale generale")

    from dbx.designers.query_builder import QueryDesignerWidget

    designer = QueryDesignerWidget(project, QuerySpec.from_project(project, "fatture_clienti"))
    try:
        designer.set_mode("qbe")
        ctx.check(designer.qbe_page.images(), "QBE con tabelle")
        designer.qbe_page.set_cell("fatture", "importo", 0, "500..1300")
        designer.qbe_page.apply_and_notify()
        ctx.check(
            any(item.op == "between" for item in designer.spec.filters),
            "QBE applica l'intervallo",
        )
        ctx.check(designer.run_preview() is not None, "QBE esegue l'anteprima")
        ctx.capture(designer, "e2e-query-designer", (1100, 700))
    finally:
        designer.close()

    from dbx.ui.query_results import QueryResultsWidget

    results = QueryResultsWidget(project, "fatture_clienti")
    try:
        ctx.check(results.table.rowCount() == 5, "Query Results: righe")
        ctx.check(results.table.columnCount() == 5, "Query Results: colonne")
        ctx.check("sola lettura" in results.info_label.text(), "Query Results read-only")
        export_path = ctx.work / "query.csv"
        with mock.patch.object(
            QFileDialog, "getSaveFileName", lambda *a, **k: (str(export_path), "")
        ):
            ctx.check(results.export_csv() == export_path, "Query Results esporta CSV")
        ctx.check(export_path.exists() and export_path.stat().st_size > 0, "file CSV query creato")
        ctx.capture(results, "e2e-query-results", (1000, 620))
    finally:
        results.close()

    from dbx.ui.crosstab_dialog import CrosstabDialog

    dialog = CrosstabDialog(result, "Fatture per cliente")
    try:
        dialog.row_combo.setCurrentIndex(
            max(0, dialog.row_combo.findData("cliente_nome"))
        )
        dialog.column_combo.setCurrentIndex(
            max(0, dialog.column_combo.findData("pagata"))
        )
        dialog.value_combo.setCurrentIndex(
            max(0, dialog.value_combo.findData("importo"))
        )
        ctx.check(dialog.rebuild(), "CrosstabDialog costruisce la matrice")
        ctx.check(dialog.table.rowCount() == 4, "CrosstabDialog con totali")
        ctx.capture(dialog, "e2e-crosstab", (940, 620))
    finally:
        dialog.close()


def scenario_forms_runtime(ctx: HarnessContext) -> None:
    """CRUD, navigazione, eventi, vista Lista, portale e form su query."""
    project = ctx.demo_project("Form")
    from dbx.core.form_model import FormSpec
    from dbx.runtime.form_runtime import FormRuntime

    spec = FormSpec.from_dict(project.artifact("forms", "form_clienti"))
    runtime = FormRuntime(project, spec)
    try:
        ctx.check(runtime.rowset.count() == 3, "form runtime carica i clienti")
        ctx.check("Record 1 di 3" in runtime._status.text(), "stato del form")
        runtime.perform("next")
        ctx.check(runtime.rowset.index == 1, "navigazione successivo")
        runtime.perform("last")
        ctx.check(runtime.rowset.index == 2, "navigazione ultimo")
        runtime.perform("first")
        ctx.check(runtime.rowset.index == 0, "navigazione primo")

        names = {binder.control.field: binder for binder in runtime.binders}
        names["nome"].widget.setText("Alfa E2E")
        ctx.check(runtime.save() is True, "salvataggio modifica")
        ctx.check(runtime.rowset.current["nome"] == "Alfa E2E", "modifica persistita")

        runtime.perform("new")
        names["codice"].widget.setText("C900")
        names["nome"].widget.setText("Nuovo E2E")
        ctx.check(runtime.save() is True, "creazione nuovo record")
        ctx.check(runtime.rowset.count() == 4, "conteggio dopo creazione")
        ctx.check(runtime.is_list_view() is False, "salvataggio torna alla scheda")

        list_spec = FormSpec.from_dict(project.artifact("forms", "form_clienti"))
        list_spec.view_mode = "list"
        list_spec.list_fields = "codice,nome,citta"
        list_runtime = FormRuntime(project, list_spec)
        try:
            ctx.check(list_runtime.is_list_view(), "vista Lista iniziale")
            ctx.check(list_runtime._list.columnCount() == 3, "colonne Lista configurate")
            list_runtime._list.selectRow(3)
            ctx.check(list_runtime.rowset.current["codice"] == "C900", "selezione Lista")
            list_runtime.toggle_view()
            ctx.check(not list_runtime.is_list_view(), "ritorno alla scheda")
            list_runtime._set_view("list")
            ctx.capture(list_runtime, "e2e-form-list", (900, 620))
        finally:
            list_runtime.deleteLater()

        runtime.perform("message:Evento E2E")
        ctx.check("Evento E2E" in runtime._status.text(), "evento form message")

        runtime.perform("delete")
        ctx.check(runtime.rowset.count() == 3, "eliminazione con conferma")
    finally:
        runtime.deleteLater()

    portal_spec = FormSpec.from_dict(project.artifact("forms", "form_fatture"))
    grid_control = next(
        control for control in portal_spec.all_controls() if control.kind == "grid"
    )
    grid_control.order = "importo desc"
    grid_control.filter = "[importo] >= 200"
    portal = FormRuntime(project, portal_spec)
    try:
        portal.rowset.goto(1)
        portal.load_current()
        ctx.check(portal.rowset.current["codice"] == "C002", "form master-detail sul cliente")
        ctx.check(portal.grids[0][0].rowCount() == 2, "portale filtrato")
        ctx.check(portal.grids[0][0].item(0, 4).text() == "3200", "portale ordinato")
        ctx.capture(portal, "e2e-form-portal", (900, 800))
    finally:
        portal.deleteLater()

    query_spec = FormSpec.from_dict(project.artifact("forms", "form_clienti_attivi"))
    query_runtime = FormRuntime(project, query_spec)
    try:
        ctx.check(query_runtime.read_only, "form su query read-only")
        query_runtime.perform("new")
        ctx.check("sola lettura" in query_runtime._status.text(), "blocco scrittura su query")
    finally:
        query_runtime.deleteLater()


def scenario_reports_labels(ctx: HarnessContext) -> None:
    """Report a bande, totali, grafici, PDF, anteprima ed etichette."""
    project = ctx.demo_project("Stampa")
    spec = ReportSpec.from_dict(project.artifact("reports", "fatture_per_cliente"))
    pages = build_pages(project, spec)
    text = " ".join(op.text for page in pages for op in page.ops)
    ctx.check(pages, "report produce pagine")
    ctx.check("Fatture per cliente" in text, "titolo del report")
    ctx.check("Totale generale: 5.900,50" in text, "totale generale del report")
    ctx.check(text.count("Totale cliente:") == 3, "totali di gruppo")
    ctx.check(not page_pixmap(pages[0], 1.0).isNull(), "pagina renderizzabile")
    pdf = export_pdf(pages, ctx.work / "report.pdf", "E2E")
    ctx.check(pdf.exists() and pdf.stat().st_size > 1000, "export PDF del report")

    chart_spec = ReportSpec.from_dict(project.artifact("reports", "fatture_per_cliente"))
    chart_spec.bands["summary"].append(
        Control(
            id="e2e_chart",
            kind="chart",
            x=0,
            y=20,
            w=170,
            h=45,
            text="Importo per cliente",
            expr="[importo]",
            category="[cliente]",
            func="sum",
            chart_type="bar",
            border=True,
        )
    )
    chart_pages = build_pages(project, chart_spec)
    charts = [
        op for page in chart_pages for op in page.ops if op.kind == "chart"
    ]
    ctx.check(len(charts) == 1, "controllo grafico nel report")
    ctx.check(
        charts[0].series == [("C001", 1650.0), ("C002", 3450.5), ("C003", 800.0)],
        "serie del grafico a barre",
    )
    chart_pdf = export_pdf(chart_pages, ctx.work / "chart.pdf", "Grafico")
    ctx.check(chart_pdf.stat().st_size > 1000, "PDF con grafico")

    preview = ReportPreviewDialog(project, chart_spec)
    try:
        ctx.check(len(preview.pages) >= 1, "anteprima report con grafico")
        ctx.check(preview.total_label.text().startswith("Totale:"), "anteprima conta le pagine")
        preview.set_zoom(2.0)
        expected_zoom = f"{int(round(2.0 / preview.baseline * 100))}%"
        ctx.check(expected_zoom in preview.zoom_label.text(), "zoom dell'anteprima")
        ctx.capture(preview, "e2e-report-preview", (940, 800))
    finally:
        preview.close()

    from dbx.designers.report_builder import ReportDesignerWidget

    designer = ReportDesignerWidget(project, chart_spec)
    try:
        ctx.check(designer.canvas.spec is not None, "Report Designer carica il foglio")
        ctx.check(
            any(
                control.kind == "chart"
                for controls in designer.spec.bands.values()
                for control in controls
            ),
            "Report Designer mostra il grafico",
        )
        ctx.capture(designer, "e2e-report-designer", (1180, 800))
    finally:
        designer.close()

    from dbx.core.label_model import LabelSpec
    from dbx.designers.label_builder import LabelDesignerWidget
    from dbx.ui.label_preview import LabelPreviewDialog

    table = project.require_table("clienti")
    label = LabelSpec.create(
        "etichette_e2e",
        table.name,
        [field.name for field in table.fields],
        title="Etichette E2E",
    )
    label.template = "[nome]\n[citta]"
    label.filter = "attivo = 1"
    label.order = "nome"
    label.border = True
    label.start_offset = 1
    ctx.check(label.validate() == [], "etichetta valida")
    label_pages = render_labels_for_project(project, label)
    label_text = " ".join(
        op.text for page in label_pages for op in page.ops if op.kind == "text"
    )
    ctx.check("Alfa Srl" in label_text and "Gamma snc" not in label_text, "mail merge filtrato")
    ctx.check(label_pages, "etichetta produce un foglio")
    label_pdf = export_pdf(label_pages, ctx.work / "labels.pdf", "Etichette")
    ctx.check(label_pdf.stat().st_size > 1000, "PDF delle etichette")

    label_preview = LabelPreviewDialog(project, label)
    try:
        ctx.check(label_preview.pages, "anteprima etichette")
        ctx.check(label_preview.info.text().endswith("1 pagina"), "anteprima: un foglio")
        ctx.capture(label_preview, "e2e-label-preview", (940, 800))
    finally:
        label_preview.close()

    label_designer = LabelDesignerWidget(project, label)
    try:
        ctx.check(label_designer.fields_list.count() == len(table.fields), "Label Designer campi")
        ctx.check(label_designer.save() is True, "salvataggio etichetta")
        ctx.check(
            project.artifact("labels", "etichette_e2e") is not None,
            "etichetta nel progetto",
        )
        ctx.capture(label_designer, "e2e-label-designer", (1060, 680))
    finally:
        label_designer.close()
    ctx.check(validate_project(project) == [], "progetto valido dopo etichetta")


def scenario_scripts_automation(ctx: HarnessContext) -> None:
    """Script core, parametri, globali, transazioni e Program Editor."""
    project = ctx.demo_project("Script")
    engine = ScriptEngine(project)
    result = engine.run_named("riepilogo_fatture")
    ctx.check(result.error is None, "script demo eseguito", result.error or "")
    ctx.check(any("Fattura" in line for line in result.log), "log dello script demo")

    result = engine.run_named("fatture_sopra_soglia")
    ctx.check(result.error is None, "script parametrizzato eseguito", result.error or "")
    ctx.check(result.variables["soglia"] == "1000", "parametro predefinito")
    ctx.check(any("Fatture sopra 1000" in line for line in result.log), "parametro nei messaggi")
    ctx.check(project.globals.get("ultima_soglia") == "1000", "variabile globale salvata")

    result = ScriptEngine(project).run_named(
        "fatture_sopra_soglia", params={"soglia": "2000"}
    )
    ctx.check(result.error is None, "script con parametro sostituito", result.error or "")
    ctx.check(project.globals.get("ultima_soglia") == "2000", "globale aggiornata")

    project.set_global("e2e_global", "persistente")
    project.save()
    ctx.check(ScriptEngine(project).globals["e2e_global"] == "persistente", "globale condivisa")
    cleared = ScriptEngine(project).run(
        [new_step("unset_global", variable="e2e_global")]
    )
    ctx.check(cleared.error is None and "e2e_global" not in project.globals, "globale cancellata")

    helper = Table(name="note_e2e", fields=[Field("testo", T.TEXT)])
    project.apply_table(helper, backup=False)
    core = ScriptEngine(project).run(
        [
            new_step("select_table", table="note_e2e"),
            new_step("new_record"),
            new_step("set_field", field="testo", expr='"prima"'),
            new_step("commit_record"),
            new_step("duplicate_record"),
            new_step("set_field", field="testo", expr='"seconda"'),
        ]
    )
    ctx.check(core.error is None, "azioni core sugli script", core.error or "")
    ctx.check(Rowset(project.db, helper).open().count() == 2, "nuovo e duplica record")

    rollback = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE note_e2e SET testo = 'annullata'"),
            new_step("rollback_transaction"),
        ]
    )
    ctx.check(rollback.error is None, "rollback esplicito", rollback.error or "")
    ctx.check(
        all(row["testo"] != "annullata" for row in Rowset(project.db, helper).open().rows()),
        "rollback annulla le scritture",
    )

    commit = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE note_e2e SET testo = 'confermata'"),
            new_step("commit_transaction"),
        ]
    )
    ctx.check(commit.error is None, "commit esplicito", commit.error or "")
    ctx.check(
        any(row["testo"] == "confermata" for row in Rowset(project.db, helper).open().rows()),
        "commit conserva le scritture",
    )

    automatic = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE note_e2e SET testo = 'persa'"),
            new_step("halt", message="stop"),
        ]
    )
    ctx.check(automatic.error is None, "transazione interrotta senza errore")
    ctx.check(
        any("annullata automaticamente" in line for line in automatic.log),
        "rollback automatico",
    )

    steps = [
        new_step("set_global", variable="testo", expr='"x"'),
        new_step("unset_global", variable="testo"),
        new_step("begin_transaction"),
        new_step("rollback_transaction"),
    ]
    text = to_text(steps)
    parsed = from_text(text)
    ctx.check(to_text(parsed) == text, "round-trip della forma testuale")
    ctx.check(
        [step["action"] for step in parsed]
        == ["set_global", "unset_global", "begin_transaction", "rollback_transaction"],
        "azioni di automazione nel testo",
    )

    class RecordingUI(NullUI):
        def __init__(self) -> None:
            self.answers: list[str] = []
            self.confirms: list[str] = []
            self.beeps = 0
            self.forms: list[str] = []
            self.queries: list[str] = []
            self.reports: list[str] = []

        def ask(self, prompt, default=""):
            self.answers.append(prompt)
            return "Ada"

        def confirm(self, text):
            self.confirms.append(text)
            return True

        def custom_dialog(self, title, message, default=""):
            return "ok"

        def beep(self):
            self.beeps += 1

        def open_form(self, name):
            self.forms.append(name)

        def open_query(self, name):
            self.queries.append(name)

        def open_report(self, name):
            self.reports.append(name)

    ui = RecordingUI()
    project.put_object(
        "scripts",
        {"name": "saluta_e2e", "steps": [new_step("message", text="Ciao :chi")]},
    )
    confirm_step = new_step("confirm", text="Procedo?")
    confirm_step["steps"].append(new_step("beep"))
    export_path = ctx.work / "script_export.csv"
    extra = ScriptEngine(project, ui).run(
        [
            new_step("ask", prompt="Chi?", variable="chi"),
            new_step("custom_dialog", title="Titolo", message="Valore?", variable="valore"),
            new_step("message", text=":chi / :valore"),
            new_step("open_form", form="form_clienti"),
            new_step("open_query", query="clienti_attivi"),
            new_step("open_report", report="fatture_per_cliente"),
            new_step("call", script="saluta_e2e"),
            new_step("export_csv", table="clienti", path=str(export_path)),
            confirm_step,
            new_step("beep"),
        ]
    )
    ctx.check(extra.error is None, "azioni script rimanenti", extra.error or "")
    ctx.check(ui.answers == ["Chi?"], "azione ask")
    ctx.check(ui.confirms == ["Procedo?"], "azione confirm")
    ctx.check(any("Ada / ok" in line for line in extra.log), "dialogo personalizzato")
    ctx.check(ui.forms and ui.queries and ui.reports, "apertura form/query/report da script")
    ctx.check(any("Ciao Ada" in line for line in extra.log), "chiamata a un altro script")
    ctx.check(export_path.exists(), "export CSV da script")
    ctx.check(ui.beeps == 2, "segnale acustico")

    artifact = project.artifact("scripts", "fatture_sopra_soglia")
    ctx.check([entry["name"] for entry in script_parameters(artifact)] == ["soglia"], "parametri dichiarati")
    from dbx.designers.script_builder import ScriptBuilderWidget

    editor = ScriptBuilderWidget(project, artifact)
    try:
        ctx.check(editor.params[0]["name"] == "soglia", "Program Editor carica i parametri")
        editor.run_script()
        ctx.check("Fatture sopra 1000" in editor.log.toPlainText(), "Program Editor esegue")
        ctx.check(editor.save() is True, "Program Editor salva")
        ctx.capture(editor, "e2e-script-editor", (1100, 700))
    finally:
        editor.close()

    project.put_object(
        "scripts",
        {"name": "rotto_e2e", "params": ["nome non valido"], "steps": []},
    )
    errors = validate_project(project)
    ctx.check(
        any("Script rotto_e2e" in error for error in errors),
        "validazione dei parametri non validi",
    )
    project.remove_object("scripts", "rotto_e2e")
    ctx.check(validate_project(project) == [], "progetto valido dopo la pulizia")


def scenario_maintenance(ctx: HarnessContext) -> None:
    """Rinomina, duplicazione, backup, compattazione e integrita'."""
    project = ctx.demo_project("Manutenzione")
    project.backup(reason="e2e")
    ctx.check(
        any(project.backups_path.iterdir()),
        "backup creato",
    )

    duplicate_query = duplicate_object(project, "queries", "clienti_attivi")
    ctx.check(
        project.artifact("queries", duplicate_query) is not None,
        "duplicazione query",
    )
    duplicate_table = duplicate_object(project, "tables", "clienti")
    ctx.check(
        project.require_table(duplicate_table).field("nome") is not None,
        "duplicazione tabella",
    )
    ctx.check(
        Rowset(project.db, project.require_table(duplicate_table)).open().count() == 3,
        "duplicazione tabella copia i dati",
    )
    project.drop_table(duplicate_table)

    project.put_object(
        "labels",
        {
            "name": "et_manutenzione",
            "table": "clienti",
            "template": "[clienti.nome]",
            "filter": "[clienti.attivo] = 1",
        },
    )
    project.save()
    rename_table(project, "clienti", "anagrafica")
    artifact = project.artifact("labels", "et_manutenzione")
    ctx.check(artifact["table"] == "anagrafica", "rinomina aggiorna l'etichetta")
    ctx.check(artifact["template"] == "[anagrafica.nome]", "rinomina aggiorna il modello")
    ctx.check(artifact["filter"] == "[anagrafica.attivo] = 1", "rinomina aggiorna il filtro")
    ctx.check(validate_project(project) == [], "progetto valido dopo rinomina")
    ctx.check(check_database(project) == "ok", "integrita' del database")
    backup = compact_database(project)
    ctx.check(backup is not None and Path(backup).exists(), "compattazione con backup")


def scenario_ui_designers(ctx: HarnessContext) -> None:
    """Shell MDI, Navigator, designer ed esperti su tutte le categorie."""
    project = ctx.demo_project("UI")
    table = project.require_table("clienti")
    from dbx.core.label_model import LabelSpec

    label = LabelSpec.create(
        "etichette_ui",
        table.name,
        [field.name for field in table.fields],
        title="Etichette UI",
    )
    project.put_object("labels", label.to_dict())
    project.save()

    from dbx.ui.main_window import MainWindow

    window = MainWindow(project)
    try:
        with ctx.quiet_qt():
            window.show()
            ctx.qapp.processEvents()
        ctx.check(window.navigator.list.count() > 0, "Navigator popolato")
        ctx.check("Oggetti" in window.navigator.list_header.text(), "intestazione Navigator")
        ctx.capture(window, "e2e-main-window", (1280, 800))

        window.open_object("tables", "clienti")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("tables:clienti") is not None, "apertura Browse")
        window.open_object("queries", "fatture_clienti")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("queries:fatture_clienti") is not None, "apertura Query Designer")
        window.open_object("forms", "form_clienti")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("forms:form_clienti") is not None, "apertura Form Designer")
        window.open_object("reports", "fatture_per_cliente")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("reports:fatture_per_cliente") is not None, "apertura Report Designer")
        window.open_object("labels", "etichette_ui")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("labels:etichette_ui") is not None, "apertura Label Designer")
        window.open_object("scripts", "riepilogo_fatture")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("scripts:riepilogo_fatture") is not None, "apertura Program Editor")
        window.open_object("menus", "principale")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("menus:principale") is not None, "apertura Menu Designer")

        ctx.check(window.editors.windows(), "schede documento aperte")
        ctx.check(window.editors.tabs.count() == len(window.editors.windows()), "etichette orizzontali delle schede")
        ctx.qapp.processEvents()
        ctx.capture(window, "e2e-main-window-tabs", (1280, 800))
    finally:
        window.close()

    from dbx.designers.database_designer import DatabaseDesignerWidget
    from dbx.designers.form_builder import FormDesignerWidget
    from dbx.designers.form_expert import FormExpert
    from dbx.designers.menu_builder import MenuBuilderWidget
    from dbx.designers.project_builder import ProjectEditorWidget
    from dbx.designers.query_expert import QueryExpert
    from dbx.designers.report_expert import ReportExpert
    from dbx.designers.table_builder import TableBuilderDialog
    from dbx.designers.table_expert import TableExpert
    from dbx.ui.command_window import CommandWindow
    from dbx.ui.navigator import Navigator

    navigator = Navigator()
    try:
        navigator.set_project(project)
        ctx.check(navigator.filter_combo.count() >= 8, "Navigator: filtri categoria")
        ctx.capture(navigator, "e2e-navigator", (420, 620))
    finally:
        navigator.deleteLater()

    table_dialog = TableBuilderDialog(project, table)
    try:
        ctx.check(table_dialog.current_table().name == "clienti", "Table Builder")
        ctx.capture(table_dialog, "e2e-table-builder", (1040, 720))
    finally:
        table_dialog.close()

    table_expert = TableExpert(project, suggested_name="tabella_e2e")
    try:
        table_expert.template_combo.setCurrentIndex(
            max(0, table_expert.template_combo.findData("contatti"))
        )
        ctx.check(table_expert.build_table().fields, "Table Expert")
    finally:
        table_expert.close()

    query_expert = QueryExpert(project, suggested_name="query_e2e")
    try:
        ctx.check(query_expert.build_spec().validate(project.tables()) == [], "Query Expert")
    finally:
        query_expert.close()

    report_expert = ReportExpert(project, suggested_name="report_e2e")
    try:
        ctx.check(report_expert.build_spec().validate() == [], "Report Expert")
    finally:
        report_expert.close()

    form_expert = FormExpert(project, suggested_name="form_e2e")
    try:
        form_expert.initializePage(1)
        ctx.check(form_expert.build_spec().validate() == [], "Form Expert")
    finally:
        form_expert.close()

    database_designer = DatabaseDesignerWidget(project)
    try:
        opened: list[tuple[str, str]] = []
        database_designer.open_table.connect(
            lambda name, mode: opened.append((name, mode))
        )
        ctx.check(len(database_designer.graph.nodes) == 2, "Database Designer ER")
        ctx.check(database_designer.table_list.count() == 2, "Database: elenco tabelle")
        database_designer.select_table("clienti")
        database_designer.edit_table()
        database_designer.open_data_for_selected()
        ctx.check(
            opened == [("clienti", "edit"), ("clienti", "browse")],
            "Database: apertura delle schede Modifica e Dati",
        )
        ctx.capture(database_designer, "e2e-database-actions", (1180, 760))
    finally:
        database_designer.close()

    form_designer = FormDesignerWidget(
        project, FormSpec.from_dict(project.artifact("forms", "form_clienti"))
    )
    try:
        ctx.check(form_designer.canvas.page.controls, "Form Designer")
        ctx.capture(form_designer, "e2e-form-designer", (1160, 760))
    finally:
        form_designer.close()

    menu_designer = MenuBuilderWidget(project, project.artifact("menus", "principale"))
    try:
        ctx.check(menu_designer.tree.topLevelItemCount() > 0, "Menu Designer")
    finally:
        menu_designer.close()

    project_editor = ProjectEditorWidget(project)
    try:
        ctx.check(project_editor.tree.topLevelItemCount() >= 7, "Project Editor")
        ctx.capture(project_editor, "e2e-project-editor", (900, 640))
    finally:
        project_editor.close()

    command = CommandWindow(project)
    try:
        for text in ("HELP", "TABELLE", "USE clienti", "RECORD", "2 + 2"):
            command.input.setText(text)
            command.execute()
        output = command.output.toPlainText()
        ctx.check("HELP" in output, "Command Window: HELP")
        ctx.check("clienti" in output, "Command Window: TABELLE/USE")
        ctx.check("C001" in output, "Command Window: RECORD")
        ctx.check("4" in output, "Command Window: espressione")
        ctx.capture(command, "e2e-command-window", (760, 520))
    finally:
        command.close()

    for theme in ("aurora", "silver", "dark"):
        resolved = apply_theme(ctx.qapp, theme)
        ctx.check(bool(ctx.qapp.styleSheet()), f"tema {theme}", resolved)
    apply_theme(ctx.qapp, "aurora")


def scenario_runner_build(ctx: HarnessContext) -> None:
    """Menu runtime, Project Runner, validazione e build distribuibile."""
    project = ctx.demo_project("Runner")
    errors = validate_project(project)
    ctx.check(not errors, "validazione prima della build", "; ".join(errors))

    from dbx.ui.project_runner import ProjectRunner
    from dbx.ui.script_params import ScriptArgumentsDialog

    runner = ProjectRunner(project, form_name="form_clienti", menu_name="principale")
    try:
        ctx.check(runner.current is not None, "Project Runner apre il form principale")
        ctx.check(len(runner.menu_bar.actions()) >= 1, "Project Runner costruisce il menu")
        runner._dispatch("open_form", "form_fatture")
        ctx.check(runner.current is not None, "dispatch open_form")
        with mock.patch.object(ReportPreviewDialog, "exec", lambda self: QDialog.DialogCode.Accepted):
            runner._dispatch("open_report", "fatture_per_cliente")
        ctx.check(True, "dispatch open_report")
        with (
            mock.patch.object(
                ScriptArgumentsDialog, "exec", lambda self: QDialog.DialogCode.Accepted
            ),
            mock.patch.object(ScriptArgumentsDialog, "values", lambda self: {"soglia": "1500"}),
        ):
            runner._dispatch("run_script", "fatture_sopra_soglia")
        ctx.check(project.globals.get("ultima_soglia") == "1500", "dispatch run_script con parametri")
    finally:
        runner.close()

    dist = ctx.work / "dist"
    built = build_project(project, dist)
    base = dist / project.name
    ctx.check(built.exists() and built.suffix == ".zip", "archivio di build")
    ctx.check(base.exists(), "cartella di build")
    archive = built
    ctx.check(archive.stat().st_size > 1000, "archivio di build non vuoto")

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    ctx.check(any(name.endswith("project.dbx.json") for name in names), "manifest nella build")
    ctx.check(any("objects/" in name and ".form.json" in name for name in names), "form nella build")
    ctx.check(any("data/" in name and name.endswith(".sqlite") for name in names), "database nella build")

    from dbx.core.project import Project as BuiltProject

    reopened = BuiltProject.open(base, force=True)
    try:
        ctx.check(len(reopened.names("tables")) == 2, "build riapribile")
        ctx.check(validate_project(reopened) == [], "build valida")
        ctx.check("principale" in reopened.names("menus"), "menu nella build")
    finally:
        reopened.close()


# --------------------------------------------------------------------------- #
# Workflow realistici
# --------------------------------------------------------------------------- #
@contextmanager
def _typed_record(values: dict[str, Any]):
    """Simula la compilazione del dialogo «Nuovo record» del Browse."""
    from dbx.ui.data_view import RecordDialog

    with (
        mock.patch.object(RecordDialog, "exec", lambda self: QDialog.DialogCode.Accepted),
        mock.patch.object(RecordDialog, "values", lambda self: dict(values)),
    ):
        yield


def _table_rows(project: Project, table_name: str, order: str = "") -> list[dict[str, Any]]:
    rowset = Rowset(project.db, project.require_table(table_name))
    rowset.open(order=order)
    return rowset.rows()


def _grid_row(view: Any, column: int, text: str) -> int:
    for row in range(view.grid.rowCount()):
        item = view.grid.item(row, column)
        if item is not None and item.text() == text:
            return row
    return -1


def _select_grid_row(view: Any, column: int, text: str) -> bool:
    row = _grid_row(view, column, text)
    if row < 0:
        return False
    view.grid.setCurrentCell(row, column)
    view.grid.selectRow(row)
    return True


def _reopen(ctx: HarnessContext, project: Project) -> Project:
    """Chiude e riapre il progetto come farebbe un riavvio dell'applicazione."""
    path = project.path
    project.close()
    reopened = Project.open(path)
    ctx.projects.append(reopened)
    return reopened


def scenario_workflow_nuova_applicazione(ctx: HarnessContext) -> None:
    """Workflow: un consulente crea, collauda e distribuisce una piccola applicazione."""
    project = ctx.new_project("Gestionale")
    clienti, fatture = _e2e_tables(project)
    project.settings["title"] = "Gestionale dBX"
    project.settings["main_form"] = "form_clienti"

    from dbx.ui.data_view import DataView

    clienti_view = DataView(project, "clienti")
    try:
        for record in (
            {"codice": "K001", "nome": "Rossi Impianti", "anni": 12, "saldo": 750.0, "attivo": True},
            {"codice": "K002", "nome": "Bianchi Servizi", "anni": 5, "saldo": 0.0, "attivo": True},
            {"codice": "K003", "nome": "Neri Costruzioni", "anni": 20, "saldo": -120.0, "attivo": False},
        ):
            with _typed_record(record):
                clienti_view.new_record()
        ctx.check(clienti_view.grid.rowCount() == 3, "tre clienti inseriti dal Browse")
        calculated = [field.name for field in clienti_view.table.fields].index("nome_maiuscolo")
        ctx.check(
            clienti_view.grid.item(0, calculated).text() == "ROSSI IMPIANTI",
            "campo calcolato visibile in griglia",
        )
        ctx.capture(clienti_view, "e2e-wf-new-app-browse", (1000, 620))
    finally:
        clienti_view.deleteLater()

    fatture_view = DataView(project, "fatture")
    try:
        for record in (
            {"numero": 1, "cliente": "K001", "data": "2026-01-10", "importo": 100.0, "pagata": True},
            {"numero": 2, "cliente": "K001", "data": "2026-02-10", "importo": 200.0, "pagata": False},
            {"numero": 3, "cliente": "K002", "data": "2026-03-10", "importo": 300.0, "pagata": False},
        ):
            with _typed_record(record):
                fatture_view.new_record()
        ctx.check(fatture_view.grid.rowCount() == 3, "tre fatture inserite dal Browse")
    finally:
        fatture_view.deleteLater()

    aperte = QuerySpec(
        name="fatture_aperte",
        caption="Fatture aperte",
        base="fatture",
        fields=[
            QueryField("fatture", "numero"),
            QueryField("fatture", "cliente"),
            QueryField("fatture", "data"),
            QueryField("fatture", "importo"),
        ],
        filters=[QueryFilter("fatture.pagata", "eq", "0")],
        sorts=[QuerySort("fatture.importo", "desc")],
    )
    project.add_object("queries", aperte.to_dict())
    result = run_query(project, aperte)
    ctx.check(len(result) == 2, "query delle fatture aperte")
    ctx.check(result.rows[0]["importo"] == 300.0, "query ordinata per importo")

    form = FormSpec.create_from_query(
        query_table(project, "fatture_aperte"), "fatture_aperte", name="form_fatture_aperte"
    )
    form.caption = "Fatture aperte"
    project.add_object("forms", form.to_dict())
    clienti_form = FormSpec.create(clienti, name="form_clienti")
    clienti_form.caption = "Clienti"
    project.add_object("forms", clienti_form.to_dict())

    label = LabelSpec.create(
        "etichette_clienti", "clienti", ["codice", "nome", "anni"], "Etichette clienti"
    )
    label.template = "[nome]\n[anni] anni"
    label.filter = "attivo = 1"
    project.add_object("labels", label.to_dict())

    report = ReportSpec.create_for_query(
        "report_fatture_aperte",
        "fatture_aperte",
        [field.name for field in query_table(project, "fatture_aperte").fields],
        "Fatture aperte",
    )
    report.order = "importo desc"
    report.bands["summary"].append(
        Control(
            id="totale_aperto",
            kind="total",
            x=110,
            y=2,
            w=60,
            h=8,
            expr="[importo]",
            func="sum",
            label="Totale aperto: ",
            bold=True,
            align="right",
        )
    )
    project.add_object("reports", report.to_dict())

    riepilogo = [
        new_step("status", text="Riepilogo dell'applicazione"),
        new_step("set", variable="conteggio", expr="0"),
        new_step("set", variable="totale", expr="0"),
    ]
    loop = new_step("foreach", table="fatture", filter="pagata = 0")
    loop["steps"].append(new_step("set", variable="conteggio", expr=":conteggio + 1"))
    loop["steps"].append(new_step("set", variable="totale", expr=":totale + [importo]"))
    riepilogo.extend(
        [
            loop,
            new_step("set_global", variable="fatture_aperte", expr=":conteggio"),
            new_step("set_global", variable="totale_aperto", expr=":totale"),
            new_step("message", text="Aperte: :conteggio — totale: :totale"),
        ]
    )
    project.put_object("scripts", {"name": "riepilogo", "steps": riepilogo})
    project.put_object(
        "menus",
        {
            "name": "principale",
            "items": [
                {"label": "Clienti", "action": "open_form", "target": "form_clienti"},
                {"label": "Fatture aperte", "action": "open_form", "target": "form_fatture_aperte"},
                {"label": "Report fatture aperte", "action": "open_report", "target": "report_fatture_aperte"},
                {"label": "Riepilogo", "action": "run_script", "target": "riepilogo"},
            ],
        },
    )
    project.save()
    ctx.check(validate_project(project) == [], "progetto valido prima del collaudo")

    from dbx.ui.main_window import MainWindow

    window = MainWindow(project)
    try:
        with ctx.quiet_qt():
            window.show()
            ctx.qapp.processEvents()
        for category, name in (
            ("tables", "clienti"),
            ("queries", "fatture_aperte"),
            ("forms", "form_fatture_aperte"),
            ("reports", "report_fatture_aperte"),
            ("labels", "etichette_clienti"),
            ("scripts", "riepilogo"),
        ):
            window.open_object(category, name)
            ctx.qapp.processEvents()
            ctx.check(
                window.editors.find(f"{category}:{name}") is not None,
                f"apertura di {category}:{name} dalla shell",
            )
        ctx.qapp.processEvents()
        ctx.capture(window, "e2e-wf-new-app-shell", (1280, 800))
    finally:
        window.close()

    from dbx.ui.project_runner import ProjectRunner

    runner = ProjectRunner(project, form_name="form_clienti", menu_name="principale")
    try:
        ctx.check(runner.current is not None, "runtime apre il form principale")
        runner._dispatch("open_form", "form_fatture_aperte")
        ctx.check(
            runner.current is not None and runner.current.read_only,
            "runtime apre il form su query in sola lettura",
        )
        with mock.patch.object(
            ReportPreviewDialog, "exec", lambda self: QDialog.DialogCode.Accepted
        ):
            runner._dispatch("open_report", "report_fatture_aperte")
        ctx.check(True, "runtime apre l'anteprima del report")
        runner._dispatch("run_script", "riepilogo")
        ctx.check(int(project.globals.get("fatture_aperte", 0)) == 2, "script conta le fatture aperte")
        ctx.check(
            float(project.globals.get("totale_aperto", 0)) == 500.0,
            "script somma gli importi aperti",
        )
        ctx.capture(runner, "e2e-wf-new-app-runner", (980, 720))
    finally:
        runner.close()

    dist = ctx.work / "dist"
    archive = build_project(project, dist)
    base = dist / project.name
    ctx.check(archive.exists() and archive.suffix == ".zip", "build ZIP dell'applicazione")
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    ctx.check(any("objects/forms/" in name for name in names), "form nella build")
    ctx.check(any(name.endswith(".sqlite") for name in names), "database nella build")

    reopened = _reopen(ctx, project)
    ctx.check(validate_project(reopened) == [], "progetto riaperto valido")
    ctx.check(
        len(_table_rows(reopened, "clienti")) == 3
        and len(_table_rows(reopened, "fatture")) == 3,
        "i dati sopravvivono al riavvio",
    )
    ctx.check(
        int(reopened.globals.get("fatture_aperte", 0)) == 2,
        "variabili globali persistite",
    )
    from dbx.core.project import Project as BuiltProject

    built = BuiltProject.open(base, force=True)
    try:
        ctx.check(
            run_query(built, QuerySpec.from_project(built, "fatture_aperte")).rows[0]["importo"] == 300.0,
            "la copia distribuita interroga gli stessi dati",
        )
        ctx.check(validate_project(built) == [], "copia distribuita valida")
    finally:
        built.close()


def scenario_workflow_sportello(ctx: HarnessContext) -> None:
    """Workflow: una giornata allo sportello tra ricerca, modifica, incasso e stampa."""
    project = ctx.demo_project("Sportello")
    from dbx.ui.data_view import DataView
    from dbx.ui.main_window import MainWindow
    from dbx.runtime.form_runtime import FormRuntime

    window = MainWindow(project)
    try:
        with ctx.quiet_qt():
            window.show()
            ctx.qapp.processEvents()
        window.open_object("tables", "clienti")
        ctx.qapp.processEvents()
        ctx.check(window.editors.find("tables:clienti") is not None, "apertura Browse clienti")
        ctx.capture(window, "e2e-wf-sportello-shell", (1280, 800))
    finally:
        window.close()

    view = DataView(project, "clienti")
    try:
        view._search = SearchRequest([SearchCriterion("citta", "eq", "Roma")])
        view.refresh()
        ctx.check(view.grid.rowCount() == 1, "ricerca del cliente per città")
        ctx.check(view.grid.item(0, 0).text() == "C003", "la ricerca isola il cliente giusto")
        ctx.capture(view, "e2e-wf-sportello-find", (1000, 620))
        view.clear_find()
        ctx.check(view.grid.rowCount() == 3, "azzeramento della ricerca")
    finally:
        view.deleteLater()

    runtime = FormRuntime(project, FormSpec.from_dict(project.artifact("forms", "form_clienti")))
    try:
        ctx.check(runtime.rowset.find("codice", "C003") is not None, "cliente trovato nel form")
        runtime.load_current()
        binders = {binder.control.field: binder for binder in runtime.binders}
        binders["attivo"].widget.setChecked(True)
        binders["telefono"].widget.setText("06 998877")
        ctx.check(runtime.save() is True, "riattivazione del cliente salvata")
        runtime.rowset.find("codice", "C003")
        runtime.load_current()
        ctx.check(binders["attivo"].widget.isChecked(), "cliente attivo dopo il salvataggio")
        ctx.capture(runtime, "e2e-wf-sportello-form", (860, 660))
    finally:
        runtime.deleteLater()

    fatture_view = DataView(project, "fatture")
    try:
        with _typed_record(
            {
                "numero": 6,
                "cliente": "C003",
                "data": "2026-04-02",
                "descrizione": "Manutenzione sito",
                "importo": 600.0,
                "pagata": False,
            }
        ):
            fatture_view.new_record()
        ctx.check(fatture_view.grid.rowCount() == 6, "nuova fattura registrata allo sportello")
        ctx.check(_select_grid_row(fatture_view, 0, "6"), "fattura visibile nel Browse")
        columns = [field.name for field in fatture_view.table.fields]
        column = columns.index("pagata")
        row = _grid_row(fatture_view, 0, "6")
        fatture_view.grid.item(row, column).setText("Sì")
        ctx.check(
            any(
                record["numero"] == 6 and record["pagata"] == 1
                for record in _table_rows(project, "fatture")
            ),
            "incasso registrato modificando la griglia",
        )
        ctx.capture(fatture_view, "e2e-wf-sportello-incasso", (1000, 620))
    finally:
        fatture_view.deleteLater()

    engine = ScriptEngine(project)
    result = engine.run_named("riepilogo_fatture")
    ctx.check(result.error is None, "script di fine giornata", result.error or "")
    ctx.check(any("Fattura 2" in line for line in result.log), "lo script elenca le fatture aperte")
    ctx.check(
        not any("Fattura 6" in line for line in result.log),
        "la fattura incassata non è più nel riepilogo",
    )

    label = LabelSpec.create(
        "etichette_attivi", "clienti", ["codice", "nome", "telefono"], "Clienti attivi"
    )
    label.template = "[nome]\n[telefono]"
    label.filter = "attivo = 1"
    label.order = "nome"
    pages = render_labels_for_project(project, label)
    text = " ".join(op.text for page in pages for op in page.ops if op.kind == "text")
    ctx.check("Gamma snc" in text, "mail merge include il cliente riattivato")
    ctx.check("Beta Studio" in text and "Alfa Srl" in text, "mail merge degli altri clienti attivi")
    label_pdf = export_pdf(pages, ctx.work / "etichette.pdf", "Clienti attivi")
    ctx.check(label_pdf.stat().st_size > 1000, "PDF delle etichette di sportello")

    preview = ReportPreviewDialog(project, "fatture_per_cliente")
    try:
        ctx.check(preview.pages, "anteprima del report di fine giornata")
        preview_text = " ".join(op.text for page in preview.pages for op in page.ops)
        ctx.check("Totale generale: 6.500,50" in preview_text, "totale aggiornato dopo l'incasso")
        ctx.capture(preview, "e2e-wf-sportello-report", (940, 800))
    finally:
        preview.close()

    project.save()
    reopened = _reopen(ctx, project)
    clients = {row["codice"]: row for row in _table_rows(reopened, "clienti")}
    invoices = {row["numero"]: row for row in _table_rows(reopened, "fatture")}
    ctx.check(clients["C003"]["attivo"] == 1, "riattivazione persistita al riavvio")
    ctx.check(clients["C003"]["telefono"] == "06 998877", "recapito aggiornato persistito")
    ctx.check(invoices[6]["pagata"] == 1, "incasso persistito al riavvio")
    ctx.check(len(invoices) == 6, "conteggio fatture stabile al riavvio")


def scenario_workflow_import_bonifica(ctx: HarnessContext) -> None:
    """Workflow: import di un archivio sporco, bonifica e mailing."""
    project = ctx.new_project("Anagrafica")
    contatti = Table(
        name="contatti",
        caption="Contatti",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("nome", T.TEXT, size=60, required=True),
            Field("email", T.TEXT, size=80),
            Field("citta", T.TEXT, size=40),
            Field("attivo", T.BOOLEAN, default="1"),
            Field("note", T.MEMO),
            Field("nome_maiuscolo", T.TEXT, calculated="UPPER([nome])"),
        ],
        indexes=[Index(fields=["codice"], unique=True)],
    )
    project.apply_table(contatti)

    csv_path = ctx.work / "contatti.csv"
    csv_path.write_text(
        "codice;nome;email;citta;attivo\n"
        "K001;Rossi Marco;marco@example.it;milano;1\n"
        "K002;Bianchi Anna;anna@example.it;MILANO;1\n"
        "K003;Verdi Luca;luca@example.it;Milano;0\n"
        "K004;Bianchi Anna;anna@example.it;Torino;1\n"
        "K005;Neri Sara;;Roma;1\n"
        "K006;Gialli Edo;;milano;1\n",
        encoding="utf-8",
    )

    from dbx.ui.import_wizard import ImportCsvDialog
    from dbx.ui.data_view import DataView

    importer = ImportCsvDialog(project, "contatti")
    try:
        importer.path_edit.setText(str(csv_path))
        importer.delimiter_combo.setCurrentIndex(
            max(0, importer.delimiter_combo.findData(";"))
        )
        importer.reload_preview()
        ctx.check(len(importer._rows) == 7, "anteprima CSV con intestazione")
        ctx.check(importer.current_mapping()[:5] == ["codice", "nome", "email", "citta", "attivo"], "mappatura automatica delle colonne")
        importer.run_import()
        ctx.check(importer.imported == 6, "sei contatti importati")
        ctx.capture(importer, "e2e-wf-import-wizard", (900, 680))
    finally:
        importer.close()
    ctx.check(len(_table_rows(project, "contatti")) == 6, "tabella popolata dall'import")
    ctx.check(
        all(row["nome_maiuscolo"] == row["nome"].upper() for row in _table_rows(project, "contatti")),
        "campo calcolato valorizzato sui record importati",
    )

    view = DataView(project, "contatti")
    try:
        rowset = view.rowset
        changed = replace_in_rowset(rowset, "milano", "Milano", field="citta")
        ctx.check(changed == 3, "bonifica delle varianti di città", f"{changed} celle")
        view.refresh()
        ctx.check(
            [row["citta"] for row in _table_rows(project, "contatti", order="codice")]
            == ["Milano", "Milano", "Milano", "Torino", "Roma", "Milano"],
            "città normalizzate",
        )

        duplicate = SearchRequest([SearchCriterion("email", "eq", "anna@example.it")])
        ctx.check(count_matches(project.db, contatti, duplicate) == 2, "duplicato individuato")

        ctx.check(_select_grid_row(view, 0, "K003"), "riga del contatto inattivo selezionata")
        view.delete_record()
        ctx.check(view.grid.rowCount() == 5, "contatto inattivo eliminato dalla griglia")

        ctx.check(_select_grid_row(view, 0, "K004"), "duplicato selezionato")
        view.delete_record()
        ctx.check(view.grid.rowCount() == 4, "anagrafica duplicata eliminata")

        missing = SearchRequest([SearchCriterion("email", "blank")])
        ctx.check(count_matches(project.db, contatti, missing) == 2, "contatti senza email")
        save_find(project, "contatti", "senza email", missing)
        ctx.check("senza email" in saved_finds(project, "contatti"), "ricerca salvata per il controllo")
        view._search = SearchRequest()
        view.refresh()
        ctx.check(view.grid.rowCount() == 4, "archivio bonificato")
        ctx.capture(view, "e2e-wf-import-clean", (1000, 620))
    finally:
        view.deleteLater()

    export_path = ctx.work / "contatti_puliti.csv"
    with mock.patch.object(
        QFileDialog, "getSaveFileName", lambda *a, **k: (str(export_path), "")
    ):
        view = DataView(project, "contatti")
        try:
            view.export_csv()
        finally:
            view.deleteLater()
    content = export_path.read_text(encoding="utf-8-sig")
    ctx.check(content.startswith("codice"), "export con intestazione")
    ctx.check(len(content.strip().splitlines()) == 5, "export dei soli contatti bonificati")
    ctx.check("ROSSI MARCO" in content, "export con campo calcolato")

    label = LabelSpec.create(
        "mailing", "contatti", ["codice", "nome", "email", "citta"], "Mailing contatti"
    )
    label.template = "[nome]\n[citta]"
    label.filter = "attivo = 1"
    label.order = "nome"
    label_pages = render_labels_for_project(project, label)
    label_text = " ".join(op.text for page in label_pages for op in page.ops if op.kind == "text")
    ctx.check("Neri Sara" in label_text and "Gialli Edo" in label_text, "mailing dei contatti attivi")
    ctx.check("Verdi Luca" not in label_text, "mailing esclude i disattivati")
    label_pdf = export_pdf(label_pages, ctx.work / "mailing.pdf", "Mailing")
    ctx.check(label_pdf.stat().st_size > 1000, "PDF del mailing")

    report = ReportSpec.create("report_contatti", "contatti", "Contatti attivi")
    report.filter = "attivo = 1"
    report.order = "nome"
    report.bands["detail"] = [
        Control(id="riga", kind="field", x=0, y=0, w=120, h=6, expr="nome", font_size=10),
        Control(id="citta", kind="field", x=122, y=0, w=48, h=6, expr="citta", font_size=10),
    ]
    project.add_object("labels", label.to_dict())
    project.add_object("reports", report.to_dict())
    project.save()
    ctx.check(validate_project(project) == [], "progetto valido dopo la bonifica")

    from dbx.ui.report_preview import build_pages

    pages = build_pages(project, report)
    page_text = " ".join(op.text for page in pages for op in page.ops)
    ctx.check("Rossi Marco" in page_text, "report sui contatti bonificati")
    ctx.check(validate_project(project) == [], "report e mailing validi")

    reopened = _reopen(ctx, project)
    ctx.check(len(_table_rows(reopened, "contatti")) == 4, "archivio bonificato persistito")
    ctx.check("senza email" in saved_finds(reopened, "contatti"), "ricerca salvata persistita")


def scenario_workflow_chiusura_mensile(ctx: HarnessContext) -> None:
    """Workflow: chiusura mensile, solleciti, stampa e riapertura."""
    project = ctx.demo_project("Chiusura")
    chiusure = Table(
        name="chiusure",
        caption="Chiusure mensili",
        fields=[
            Field("data", T.TEXT, size=10),
            Field("totale", T.DECIMAL, default="0"),
            Field("numero", T.INTEGER, default="0"),
            Field("nota", T.TEXT, size=80),
        ],
    )
    project.apply_table(chiusure)

    steps: list[dict[str, Any]] = [
        new_step("status", text="Chiusura del :data_chiusura"),
        new_step("set", variable="totale", expr="0"),
        new_step("set", variable="numero", expr="0"),
    ]
    loop = new_step("foreach", table="fatture", filter="pagata = 0")
    loop["steps"].append(new_step("set", variable="totale", expr=":totale + [importo]"))
    loop["steps"].append(new_step("set", variable="numero", expr=":numero + 1"))
    steps.extend(
        [
            loop,
            new_step("select_table", table="chiusure"),
            new_step("new_record"),
            new_step("set_field", field="data", expr=":data_chiusura"),
            new_step("set_field", field="totale", expr=":totale"),
            new_step("set_field", field="numero", expr=":numero"),
            new_step("set_field", field="nota", expr='"Chiusura mensile"'),
            new_step("commit_record"),
            new_step("set_global", variable="ultima_chiusura", expr=":data_chiusura"),
            new_step("set_global", variable="ultimo_totale", expr=":totale"),
            new_step("status", text="Chiusura :data_chiusura: :numero fatture, totale :totale"),
        ]
    )
    project.put_object(
        "scripts",
        {
            "name": "chiusura_mensile",
            "params": [
                {"name": "data_chiusura", "label": "Data di chiusura", "default": "2026-03-31"}
            ],
            "steps": steps,
        },
    )

    solleciti = QuerySpec(
        name="solleciti",
        caption="Solleciti",
        base="fatture",
        fields=[
            QueryField("fatture", "numero"),
            QueryField("clienti", "nome", alias="cliente_nome"),
            QueryField("fatture", "importo"),
        ],
        joins=[
            QueryJoin(
                kind="inner",
                table="clienti",
                left="fatture.cliente",
                right="clienti.codice",
            )
        ],
        filters=[QueryFilter("fatture.pagata", "eq", "0")],
        sorts=[QuerySort("fatture.importo", "desc")],
    )
    project.add_object("queries", solleciti.to_dict())
    ctx.check(len(run_query(project, solleciti)) == 3, "query dei solleciti")

    report = ReportSpec.create("solleciti_report", "fatture", "Solleciti")
    report.filter = "pagata = 0"
    report.order = "importo desc"
    report.bands["detail"] = [
        Control(id="numero", kind="field", x=0, y=0, w=20, h=6, expr="numero", font_size=10),
        Control(id="data", kind="field", x=24, y=0, w=28, h=6, expr="data", font_size=10, fmt="DD/MM/YYYY"),
        Control(id="descrizione", kind="field", x=56, y=0, w=70, h=6, expr="descrizione", font_size=10),
        Control(id="importo", kind="field", x=128, y=0, w=42, h=6, expr="importo", font_size=10, align="right"),
    ]
    report.bands["summary"] = [
        Control(
            id="totale_solleciti",
            kind="total",
            x=100,
            y=2,
            w=70,
            h=9,
            expr="[importo]",
            func="sum",
            label="Totale da sollecitare: ",
            bold=True,
            align="right",
        )
    ]
    project.add_object("reports", report.to_dict())

    label = LabelSpec.create_for_query(
        "etichette_solleciti",
        "solleciti",
        ["numero", "cliente_nome", "importo"],
        "Etichette solleciti",
    )
    label.template = "[cliente_nome]\nFattura [numero] — € [importo]"
    label.order = "cliente_nome"
    project.add_object("labels", label.to_dict())
    project.save()
    ctx.check(validate_project(project) == [], "progetto valido prima della chiusura")

    from dbx.ui.project_runner import ProjectRunner

    project.settings["main_form"] = "form_clienti"
    runner = ProjectRunner(project, form_name="form_clienti", menu_name="principale")
    try:
        with (
            mock.patch.object(
                ReportPreviewDialog, "exec", lambda self: QDialog.DialogCode.Accepted
            ),
            mock.patch(
                "dbx.ui.project_runner.ScriptArgumentsDialog.exec",
                lambda self: QDialog.DialogCode.Accepted,
            ),
            mock.patch(
                "dbx.ui.project_runner.ScriptArgumentsDialog.values",
                lambda self: {"data_chiusura": "2026-03-31"},
            ),
        ):
            runner._dispatch("run_script", "chiusura_mensile")
        ctx.check(
            int(project.globals.get("ultimo_totale", 0)) == 3900,
            "chiusura avviata dal menu runtime",
        )
        ctx.capture(runner, "e2e-wf-chiusura-runner", (980, 720))
    finally:
        runner.close()

    second = ScriptEngine(project).run_named(
        "chiusura_mensile", params={"data_chiusura": "2026-04-30"}
    )
    ctx.check(second.error is None, "seconda chiusura mensile", second.error or "")
    project.save()

    closures = _table_rows(project, "chiusure", order="data")
    ctx.check(len(closures) == 2, "due chiusure registrate")
    ctx.check(
        [row["totale"] for row in closures] == [3900.5, 3900.5],
        "totali delle chiusure",
    )
    ctx.check([row["numero"] for row in closures] == [3, 3], "fatture conteggiate per chiusura")

    from dbx.ui.report_preview import build_pages

    pages = build_pages(project, report)
    text = " ".join(op.text for page in pages for op in page.ops)
    ctx.check("Totale da sollecitare: 3.900,50" in text, "totale dei solleciti nel report")
    ctx.check(text.count("Manutenzione") >= 1, "dettaglio dei solleciti")
    pdf = export_pdf(pages, ctx.work / "solleciti.pdf", "Solleciti")
    ctx.check(pdf.stat().st_size > 1000, "PDF dei solleciti")

    label_pages = render_labels_for_project(project, label)
    label_text = " ".join(op.text for page in label_pages for op in page.ops if op.kind == "text")
    for name in ("Alfa Srl", "Beta Studio"):
        ctx.check(name in label_text, f"sollecito per {name}")
    ctx.check("Gamma snc" not in label_text, "nessun sollecito per il cliente in regola")
    label_pdf = export_pdf(label_pages, ctx.work / "etichette_solleciti.pdf", "Solleciti")
    ctx.check(label_pdf.stat().st_size > 1000, "PDF delle etichette di sollecito")

    preview = ReportPreviewDialog(project, report)
    try:
        ctx.check(preview.pages, "anteprima del report solleciti")
        ctx.capture(preview, "e2e-wf-chiusura-preview", (940, 800))
    finally:
        preview.close()

    project.backup(reason="chiusura-mensile")
    backup = compact_database(project)
    ctx.check(backup is not None and Path(backup).exists(), "backup e compattazione dopo la chiusura")
    ctx.check(check_database(project) == "ok", "database integro dopo la compattazione")

    reopened = _reopen(ctx, project)
    ctx.check(len(_table_rows(reopened, "chiusure")) == 2, "chiusure persistite al riavvio")
    ctx.check(reopened.globals.get("ultima_chiusura") == "2026-04-30", "ultima chiusura persistita")
    ctx.check(
        len(run_query(reopened, QuerySpec.from_project(reopened, "solleciti"))) == 3,
        "query solleciti disponibile dopo il riavvio",
    )
    ctx.check(validate_project(reopened) == [], "progetto chiuso in modo valido")


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    title: str
    function: Callable[[HarnessContext], None]


SCENARIOS: list[ScenarioDefinition] = [
    ScenarioDefinition("environment", "Ambiente, versioni e progetto demo", scenario_environment),
    ScenarioDefinition("project_tables", "Tabelle, tipi, indici, FK, calcoli e CRUD", scenario_project_tables),
    ScenarioDefinition("search_csv", "Find mode, sostituzione, ricerche salvate e CSV", scenario_search_csv),
    ScenarioDefinition("queries_crosstab", "Query, aggregati, QBE, risultati e Crosstab", scenario_queries_crosstab),
    ScenarioDefinition("forms_runtime", "Form runtime, eventi, vista Lista e portali", scenario_forms_runtime),
    ScenarioDefinition("reports_labels", "Report, grafici, PDF, etichette e mail merge", scenario_reports_labels),
    ScenarioDefinition("scripts_automation", "Script, parametri, globali e transazioni", scenario_scripts_automation),
    ScenarioDefinition("maintenance", "Rinomina, duplicazione, backup e compattazione", scenario_maintenance),
    ScenarioDefinition("ui_designers", "Shell MDI, Navigator, designer, esperti e temi", scenario_ui_designers),
    ScenarioDefinition("runner_build", "Menu runtime, Project Runner e build", scenario_runner_build),
    ScenarioDefinition(
        "workflow_nuova_applicazione",
        "Workflow: dalla tabella vuota alla distribuzione",
        scenario_workflow_nuova_applicazione,
    ),
    ScenarioDefinition(
        "workflow_sportello",
        "Workflow: giornata allo sportello tra ricerca, incasso e stampa",
        scenario_workflow_sportello,
    ),
    ScenarioDefinition(
        "workflow_import_bonifica",
        "Workflow: import archivio, bonifica e mailing",
        scenario_workflow_import_bonifica,
    ),
    ScenarioDefinition(
        "workflow_chiusura_mensile",
        "Workflow: chiusura mensile, solleciti e riapertura",
        scenario_workflow_chiusura_mensile,
    ),
]


__all__ = [
    "HarnessContext",
    "ScenarioDefinition",
    "ScenarioFailure",
    "SCENARIOS",
]
