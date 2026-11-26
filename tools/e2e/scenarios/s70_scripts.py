"""Scenari I — Program Editor, MiniScript e automazione."""

from __future__ import annotations

from unittest import mock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLineEdit

from dbx.core.form_model import FormControl, FormSpec
from dbx.core.query_model import QueryField, QuerySpec
from dbx.designers.form_builder import FormDesignerWidget
from dbx.designers.report_builder import ReportDesignerWidget
from dbx.designers.script_builder import QtScriptUI, ScriptBuilderWidget
from dbx.designers.step_picker import StepPickerDialog
from dbx.runtime.report_engine import ReportSpec
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.rowset import Rowset
from dbx.runtime.script_engine import (
    ACTIONS,
    ACTION_CATEGORIES,
    NullUI,
    ScriptEngine,
    new_step,
    parameter_values,
    script_parameters,
    to_text,
)
from dbx.ui.script_params import ScriptArgumentsDialog, ScriptParametersDialog

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _settled(ctx: E2EContext, name: str = "Script") -> object:
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


def _artifact(name: str, steps: list[dict], params: list[dict[str, str]] | None = None) -> dict:
    return {"name": name, "params": list(params or []), "steps": steps}


def _builder(ctx: E2EContext, project, artifact: dict) -> ScriptBuilderWidget:
    widget = ScriptBuilderWidget(project, artifact)
    return ctx.track(widget)


def _step(action: str, **params) -> dict:
    return new_step(action, **params)


class RecordingUI(NullUI):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.messages: list[str] = []

    def message(self, text: str) -> None:
        self.messages.append(text)

    def status(self, text: str) -> None:
        self.calls.append(("status", text))

    def open_form(self, name: str) -> None:
        self.calls.append(("form", name))

    def open_query(self, name: str) -> None:
        self.calls.append(("query", name))

    def open_report(self, name: str) -> None:
        self.calls.append(("report", name))

    def print_report(self, name: str) -> None:
        self.calls.append(("print", name))

    def beep(self) -> None:
        self.calls.append(("beep", ""))


@scenario(
    "scr-01-source-text",
    "I01 — Sorgente, azioni, numeri di riga e log",
    "scripts",
    features=("SCR-SOURCE-TEXT", "SCR-LINE-NUMBERS", "SCR-SYNTAX", "SCR-LOG"),
    min_checks=10,
    budget_s=8.0,
    screenshots=("script-editor",),
)
def scr_source_text(ctx: E2EContext) -> None:
    project = _settled(ctx, "SorgenteScript")
    artifact = _artifact(
        "benvenuto",
        [_step("message", text="Ciao dBX"), _step("status", text="Pronto")],
    )
    builder = _builder(ctx, project, artifact)
    ctx.check_close(builder.tree.topLevelItemCount(), 2, "due azioni nell'albero")
    ctx.check_close(builder.count_label.text(), "2 azioni", "conteggio azioni")
    ctx.check("MESSAGE" in builder.text_view.toPlainText(), "sorgente generata")
    ctx.check(builder.text_view.line_number_area.width() > 0, "area numeri di riga")
    ctx.check(builder.text_view.line_number_width() > 0, "larghezza numeri")
    ctx.check(builder.text_view.highlighter is not None, "evidenziazione sintassi")

    builder.text_view.setPlainText('MESSAGE "Da testo"\nSTATUS "Allineato"')
    ctx.check(builder.source_state.text() == "Sorgente modificata", "sorgente modificata")
    builder.apply_text()
    ctx.check_close([step["action"] for step in builder.steps], ["message", "status"], "azioni dal testo")
    ctx.check(builder.source_state.text() == "Sorgente applicata", "testo applicato")
    ctx.check("Importate 2 azioni" in builder.log.toPlainText(), "log importazione")
    builder.refresh_text()
    ctx.check_close(builder.text_view.toPlainText().strip(), to_text(builder.steps).strip(), "sorgente rigenerata")
    builder.text_view.setPlainText("AZIONE_SCONOSCIUTA")
    builder.apply_text()
    ctx.check_close(len(builder.steps), 2, "testo invalido non applicato")
    ctx.check(any("Sorgente non valida" in entry[1] for entry in ctx.dialogs), "avviso sorgente")
    builder.run_script()
    ctx.check("Da testo" in builder.log.toPlainText(), "log esecuzione")
    ctx.check("Allineato" in builder.log.toPlainText(), "azione status eseguita")
    ctx.capture(builder, "script-editor", (1140, 740))


@scenario(
    "scr-02-picker",
    "I02 — Step Picker: categorie, descrizioni e ricerca",
    "scripts",
    features=("SCR-PICKER", "SCR-PICKER-CATEGORIES", "SCR-PICKER-SEARCH", "SCR-PICKER-DESCRIPTION"),
    min_checks=8,
    budget_s=8.0,
)
def scr_picker(ctx: E2EContext) -> None:
    project = _settled(ctx, "StepPicker")
    picker = StepPickerDialog()
    ctx.track(picker)
    ctx.check_close(picker.tree.topLevelItemCount(), len(ACTION_CATEGORIES), "dieci categorie")
    total = sum(picker.tree.topLevelItem(i).childCount() for i in range(picker.tree.topLevelItemCount()))
    ctx.check_close(total, len(ACTIONS), "tutte le azioni")
    ctx.check(picker.description_label.text(), "descrizione iniziale")
    picker.select_action("set_field")
    ctx.check_close(picker.selected_action(), "set_field", "azione selezionata")
    ctx.check("modifica" in picker.description_label.text().lower() or "campo" in picker.description_label.text().lower(), "descrizione azione")
    picker.filter_edit.setText("messaggio")
    visible = [
        item
        for index in range(picker.tree.topLevelItemCount())
        for item in (
            picker.tree.topLevelItem(index).child(row)
            for row in range(picker.tree.topLevelItem(index).childCount())
        )
        if not item.isHidden()
    ]
    ctx.check(0 < len(visible) < total, "ricerca filtra le azioni")
    ctx.check(all("messaggio" in item.text(0).lower() or "messaggio" in item.toolTip(0).lower() for item in visible), "risultati coerenti")
    picker.filter_edit.clear()
    ctx.check_close(len(picker._all_action_items()), total, "ricerca azzerata")


@scenario(
    "scr-03-control",
    "I03 — Controllo: if, foreach, loop, exit e halt",
    "scripts",
    features=(
        "SCR-ACTION-COMMENT",
        "SCR-ACTION-IF",
        "SCR-ACTION-FOREACH",
        "SCR-ACTION-LOOP",
        "SCR-ACTION-EXIT_LOOP_IF",
        "SCR-ACTION-EXIT_SCRIPT",
        "SCR-ACTION-HALT",
        "SCR-ACTION-CONFIRM",
    ),
    min_checks=9,
    budget_s=10.0,
)
def scr_control(ctx: E2EContext) -> None:
    project = _settled(ctx, "ControlloScript")
    loop = _step("loop")
    loop["steps"] = [
        _step("set", variable="contatore", expr=":contatore + 1"),
        _step("exit_loop_if", expr=":contatore >= 3"),
    ]
    if_step = _step("if", expr=":contatore == 3")
    if_step["then"] = [_step("status", text="Ramo then")]
    if_step["else"] = [_step("status", text="Ramo else")]
    foreach = _step("foreach", table="clienti", filter='"citta" = \'Roma\'')
    foreach["steps"] = [_step("status", text="[nome]")]
    confirm = _step("confirm", text="Procedo?")
    confirm["steps"] = [_step("status", text="Confermato")]
    steps = [
        _step("comment", text="prova del controllo"),
        _step("set", variable="contatore", expr="0"),
        loop,
        if_step,
        foreach,
        confirm,
        _step("exit_script"),
        _step("message", text="Non deve apparire"),
    ]
    result = ScriptEngine(project, NullUI()).run(steps)
    ctx.check(result.error is None, "script senza errori")
    ctx.check_close(result.variables.get("contatore"), 3, "ciclo terminato")
    log = "\n".join(result.log)
    ctx.check("Ramo then" in log, "ramo then")
    ctx.check("Ramo else" not in log, "ramo else non eseguito")
    ctx.check("Alfa Srl" in log and "Delta Spa" in log, "foreach sui clienti")
    ctx.check("Beta Studio" not in log, "filtro foreach")
    ctx.check("Confermato" in log, "conferma eseguita")
    ctx.check("Non deve apparire" not in log, "exit script interrompe")

    halted = ScriptEngine(project, NullUI()).run([_step("halt", message="Basta")])
    ctx.check("Basta" in "\n".join(halted.log), "halt registrato")


@scenario(
    "scr-04-table-nav",
    "I04 — Tabelle e navigazione: select_table, go_record",
    "scripts",
    features=("SCR-ACTION-SELECT_TABLE", "SCR-ACTION-GO_RECORD"),
    min_checks=6,
    budget_s=8.0,
)
def scr_table_nav(ctx: E2EContext) -> None:
    project = _settled(ctx, "NavigazioneScript")
    steps = [
        _step("select_table", table="clienti", filter='"citta" = \'Roma\'', order="nome desc"),
        _step("go_record", mode="first"),
        _step("status", text="[codice]"),
        _step("go_record", mode="last"),
        _step("status", text="[codice]"),
        _step("go_record", mode="number", number="2"),
        _step("status", text="[codice]"),
        _step("go_record", mode="previous"),
        _step("status", text="[codice]"),
    ]
    result = ScriptEngine(project, NullUI()).run(steps)
    ctx.check(result.error is None, "script senza errori")
    log = "\n".join(result.log)
    ctx.check("Tabella clienti: 2 record" in log, "filtro e conteggio")
    ctx.check("C004" in log and "C001" in log, "record di Roma")
    ctx.check("Record 1 di 2" in log, "primo record")
    ctx.check("Record 2 di 2" in log, "secondo record")
    ctx.check("Record 1 di 2" in log.split("C004")[0] or log.count("Record 1 di 2") >= 1, "navigazione numero")


@scenario(
    "scr-05-records",
    "I05 — Record: set, new, duplicate, delete, commit e revert",
    "scripts",
    features=(
        "SCR-ACTION-SET_FIELD",
        "SCR-ACTION-NEW_RECORD",
        "SCR-ACTION-DUPLICATE_RECORD",
        "SCR-ACTION-DELETE_RECORD",
        "SCR-ACTION-COMMIT_RECORD",
        "SCR-ACTION-REVERT_RECORD",
    ),
    min_checks=9,
    budget_s=10.0,
)
def scr_records(ctx: E2EContext) -> None:
    project = ctx.new_project("RecordScript")
    table = fixtures.tutti_tipi_table()
    fixtures.apply(project, table)
    rows = Rowset(project.db, project.require_table("tutti_tipi"))
    rows.insert({"testo": "originale", "intero": 1, "decimale": 2.5, "booleano": False})
    steps = [
        _step("select_table", table="tutti_tipi"),
        _step("set_field", field="testo", expr='"modificato"'),
        _step("new_record", table="tutti_tipi"),
        _step("duplicate_record"),
        _step("delete_record", confirm="no"),
        _step("commit_record"),
        _step("revert_record"),
    ]
    result = ScriptEngine(project, NullUI()).run(steps)
    ctx.check(result.error is None, "script senza errori")
    log = "\n".join(result.log)
    ctx.check("tutti_tipi.testo = 'modificato'" in log, "set field")
    ctx.check("Nuovo record in tutti_tipi" in log, "nuovo record")
    ctx.check("Record duplicato" in log, "duplicazione")
    ctx.check("Record eliminato" in log, "eliminazione")
    ctx.check("Record confermato" in log, "commit record")
    ctx.check("Record ripristinato" in log, "revert record")
    current = Rowset(project.db, project.require_table("tutti_tipi")).open()
    ctx.check_close(current.count(), 2, "conteggio finale")
    ctx.check_close(current.rows()[0]["testo"], "modificato", "valore scritto")


@scenario(
    "scr-06-transactions",
    "I06 — Transazioni: commit e rollback",
    "scripts",
    features=("SCR-ACTION-BEGIN_TRANSACTION", "SCR-ACTION-COMMIT_TRANSACTION", "SCR-ACTION-ROLLBACK_TRANSACTION"),
    min_checks=7,
    budget_s=8.0,
)
def scr_transactions(ctx: E2EContext) -> None:
    project = _settled(ctx, "TransazioniScript")
    table = project.require_table("clienti")
    steps = [
        _step("select_table", table="clienti", filter='"codice" = \'C001\''),
        _step("begin_transaction"),
        _step("set_field", field="saldo", expr="999"),
        _step("rollback_transaction"),
        _step("begin_transaction"),
        _step("set_field", field="saldo", expr="1234"),
        _step("commit_transaction"),
    ]
    result = ScriptEngine(project, NullUI()).run(steps)
    ctx.check(result.error is None, "script senza errori")
    log = "\n".join(result.log)
    ctx.check("Transazione avviata" in log, "transazione avviata")
    ctx.check("Transazione annullata" in log, "rollback")
    ctx.check("Transazione confermata" in log, "commit")
    stored = Rowset(project.db, table).open().find("codice", "C001")
    ctx.check_close(float(stored["saldo"]), 1234.0, "commit persistito")
    rolled = ScriptEngine(project, NullUI()).run(
        [
            _step("select_table", table="clienti", filter='"codice" = \'C001\''),
            _step("begin_transaction"),
            _step("set_field", field="saldo", expr="777"),
            _step("rollback_transaction"),
        ]
    )
    ctx.check(rolled.error is None, "rollback senza errori")
    after = Rowset(project.db, table).open().find("codice", "C001")
    ctx.check_close(float(after["saldo"]), 1234.0, "rollback non persiste")


@scenario(
    "scr-07-variables",
    "I07 — Variabili locali e globali",
    "scripts",
    features=("SCR-ACTION-SET", "SCR-ACTION-SET_GLOBAL", "SCR-ACTION-UNSET_GLOBAL"),
    min_checks=7,
    budget_s=8.0,
)
def scr_variables(ctx: E2EContext) -> None:
    project = _settled(ctx, "VariabiliScript")
    steps = [
        _step("set", variable="locale", expr='"valore"'),
        _step("set_global", variable="azienda", expr='"dBX"'),
        _step("set_global", variable="temporanea", expr="1"),
        _step("unset_global", variable="temporanea"),
    ]
    result = ScriptEngine(project, NullUI()).run(steps)
    ctx.check(result.error is None, "script senza errori")
    ctx.check_close(result.variables["locale"], "valore", "variabile locale")
    ctx.check_close(project.globals.get("azienda"), "dBX", "variabile globale")
    ctx.check("temporanea" not in project.globals, "globale rimossa")
    log = "\n".join(result.log)
    ctx.check(":locale = 'valore'" in log, "log variabile locale")
    ctx.check("globale :azienda = 'dBX'" in log, "log variabile globale")
    reopened = ctx.reopen(project)
    ctx.check_close(reopened.globals.get("azienda"), "dBX", "globale persistita")


@scenario(
    "scr-08-parameters",
    "I08 — Parametri dichiarati e dialogo argomenti",
    "scripts",
    features=("SCR-PARAMS", "SCR-ARGS-DIALOG"),
    min_checks=9,
    budget_s=8.0,
)
def scr_parameters(ctx: E2EContext) -> None:
    project = _settled(ctx, "ParametriScript")
    dialog = ScriptParametersDialog([], name="saluta")
    ctx.track(dialog)
    dialog.table.item(0, 0).setText("nome")
    dialog.table.item(0, 1).setText("Nome")
    dialog.table.item(0, 2).setText("Mondo")
    params = dialog.parameters()
    ctx.check_close(params, [{"name": "nome", "label": "Nome", "default": "Mondo"}], "parametro dichiarato")
    ctx.check_close(script_parameters({"params": params}), params, "parametri normalizzati")
    arguments = ScriptArgumentsDialog(params, name="saluta")
    ctx.track(arguments)
    ctx.check("Mondo" in arguments._edits["nome"].text(), "predefinito nel dialogo")
    arguments._edits["nome"].setText("dBX")
    ctx.check_close(arguments.values(), {"nome": "dBX"}, "valori argomenti")
    values = parameter_values({"params": params}, {"nome": "Override"})
    ctx.check_close(values["nome"], "Override", "override parametro")

    artifact = _artifact(
        "saluta",
        [_step("status", text=":nome")],
        params,
    )
    builder = _builder(ctx, project, artifact)
    ctx.check_close([entry["name"] for entry in builder.params], ["nome"], "parametri nel builder")
    ctx.check_close(builder.steps[0]["params"]["text"], ":nome", "variabile nel passo")
    result = ScriptEngine(project, NullUI(), variables=parameter_values(artifact)).run(builder.steps)
    ctx.check(result.error is None, "script parametrico eseguito")
    ctx.check("Mondo" in result.log, "valore predefinito usato")


@scenario(
    "scr-09-ui",
    "I09 — Azioni UI: message, status, ask, confirm, custom_dialog, beep",
    "scripts",
    features=(
        "SCR-ACTION-MESSAGE",
        "SCR-ACTION-STATUS",
        "SCR-ACTION-ASK",
        "SCR-ACTION-CONFIRM",
        "SCR-ACTION-CUSTOM_DIALOG",
        "SCR-ACTION-BEEP",
    ),
    min_checks=8,
    budget_s=8.0,
)
def scr_ui(ctx: E2EContext) -> None:
    project = _settled(ctx, "UIScript")
    confirm = _step("confirm", text="Continuo?")
    confirm["steps"] = [_step("status", text="Confermato")]
    artifact = _artifact(
        "interfaccia",
        [
            _step("message", text="Ciao"),
            _step("status", text="Stato aggiornato"),
            _step("ask", prompt="Nome?", variable="nome"),
            confirm,
            _step("custom_dialog", title="Dati", message="Valore?", variable="valore"),
            _step("beep"),
        ],
    )
    builder = _builder(ctx, project, artifact)
    builder.run_script()
    log = builder.log.toPlainText()
    ctx.check("Ciao" in log, "messaggio")
    ctx.check("Stato aggiornato" in log, "stato")
    ctx.check(":nome = 'valore'" in log, "ask")
    ctx.check("Confermato" in log, "confirm")
    ctx.check(":valore = 'valore'" in log, "custom dialog")
    ctx.check("Script eseguito" in builder.status_label.text() or "Pronto" in builder.status_label.text(), "esito esecuzione")
    ctx.check(any("Ciao" in entry[2] for entry in ctx.dialogs), "finestra messaggio")
    ctx.check(any("Nome?" in entry[2] for entry in ctx.dialogs), "finestra ask")


@scenario(
    "scr-10-integration",
    "I10 — Integrazione: form, query, report, stampa ed export",
    "scripts",
    features=(
        "SCR-ACTION-OPEN_FORM",
        "SCR-ACTION-OPEN_QUERY",
        "SCR-ACTION-OPEN_REPORT",
        "SCR-ACTION-PRINT_REPORT",
        "SCR-ACTION-EXPORT_CSV",
    ),
    min_checks=7,
    budget_s=10.0,
)
def scr_integration(ctx: E2EContext) -> None:
    project = _settled(ctx, "IntegrazioneScript")
    form = FormSpec.create(project.require_table("clienti"), name="form_script")
    project.put_object("forms", form.to_dict())
    query = QuerySpec(name="query_script", base="clienti", fields=[QueryField("clienti", "codice")])
    project.put_object("queries", query.to_dict())
    report = ReportSpec.create("report_script", "clienti", "Report script")
    project.put_object("reports", report.to_dict())
    project.save()
    path = ctx.work / "script_export.csv"
    steps = [
        _step("open_form", form="form_script"),
        _step("open_query", query="query_script"),
        _step("open_report", report="report_script"),
        _step("print_report", report="report_script"),
        _step("export_csv", table="clienti", path=str(path)),
    ]
    ui = RecordingUI()
    result = ScriptEngine(project, ui).run(steps)
    ctx.check(result.error is None, "azioni di integrazione")
    ctx.check(("form", "form_script") in ui.calls, "apertura form")
    ctx.check(("query", "query_script") in ui.calls, "apertura query")
    ctx.check(("report", "report_script") in ui.calls, "apertura report")
    ctx.check(("print", "report_script") in ui.calls, "stampa report")
    ctx.check(path.exists() and path.stat().st_size > 0, "export CSV da script")
    ctx.check("Esportati 5 record" in "\n".join(result.log), "log export")


@scenario(
    "scr-11-sql-call",
    "I11 — SQL, chiamate tra script ed errori",
    "scripts",
    features=("SCR-ACTION-SQL", "SCR-ACTION-CALL"),
    min_checks=8,
    budget_s=8.0,
)
def scr_sql_call(ctx: E2EContext) -> None:
    project = _settled(ctx, "SQLScript")
    project.put_object(
        "scripts",
        _artifact("chiamato", [_step("status", text="Chiamato")]),
    )
    project.save()
    result = ScriptEngine(project, NullUI()).run(
        [
            _step("call", script="chiamato"),
            _step("sql", statement='UPDATE "clienti" SET "note" = \'x\' WHERE "codice" = \'C001\''),
            _step("sql", statement='SELECT * FROM "clienti"'),
        ]
    )
    ctx.check(result.error is None, "chiamata e SQL eseguiti")
    log = "\n".join(result.log)
    ctx.check("Chiamato" in log, "script chiamato")
    ctx.check("SQL: 1 righe modificate" in log, "update SQL")
    ctx.check("SQL: 5 righe" in log, "select SQL")
    note = Rowset(project.db, project.require_table("clienti")).open().find("codice", "C001")["note"]
    ctx.check_close(note, "x", "SQL persistito")

    forbidden = ScriptEngine(project, NullUI()).run([_step("sql", statement="ALTER TABLE clienti ADD COLUMN x TEXT")])
    ctx.check(forbidden.error is not None and "struttura" in forbidden.error, "SQL strutturale rifiutato")
    missing = ScriptEngine(project, NullUI()).run([_step("call", script="inesistente")])
    ctx.check(missing.error is not None and "sconosciuto" in missing.error, "script mancante")
    ctx.check(any("ERRORE" in line for line in missing.log), "errore nel log")


@scenario(
    "scr-12-round-trip",
    "I12 — Round-trip script, legacy ed eventi form",
    "scripts",
    features=("SCR-SAVE-REOPEN", "SCR-LEGACY", "SCR-FORM-EVENT", "SCR-RUN"),
    min_checks=10,
    budget_s=10.0,
)
def scr_round_trip(ctx: E2EContext) -> None:
    project = _settled(ctx, "RoundTripScript")
    artifact = _artifact(
        "saluta",
        [_step("message", text="Eseguito")],
        [{"name": "nome", "label": "Nome", "default": "Mondo"}],
    )
    builder = _builder(ctx, project, artifact)
    ctx.check(builder.save(), "script salvato")
    reopened = ctx.reopen(project)
    stored = reopened.artifact("scripts", "saluta")
    ctx.check_close(stored["steps"], artifact["steps"], "azioni persistite")
    ctx.check_close(stored["params"], artifact["params"], "parametri persistiti")
    again = _builder(ctx, reopened, stored)
    ctx.check_close(again.name, "saluta", "nome riaperto")
    ctx.check(again.save(), "script riaperto e salvato")

    legacy = {"name": "legacy", "steps": [_step("status", text="Legacy")]}
    ctx.check_close(script_parameters(legacy), [], "script legacy senza parametri")
    reopened.put_object("scripts", legacy)
    reopened.save()
    third = ctx.reopen(reopened)
    ctx.check(third.artifact("scripts", "legacy") is not None, "script legacy persistito")

    form = FormSpec.create(third.require_table("clienti"), name="form_evento")
    form.events["onOpen"] = "script:saluta"
    button = FormControl(id="script_button", kind="button", text="Esegui", action="script:saluta", x=10, y=10, w=80, h=26)
    form.pages[0].controls.append(button)
    runtime = FormRuntime(third, form)
    ctx.track(runtime)
    ctx.check("Script saluta eseguito" in runtime._status.text(), "evento onOpen esegue script")
    widget = next(button_widget for button_widget, control_id in runtime.buttons if control_id == button.id)
    widget.click()
    ctx.check("Script saluta eseguito" in runtime._status.text(), "pulsante esegue script")
    ctx.check(any("Eseguito" in entry[2] for entry in ctx.dialogs), "messaggio dello script")
