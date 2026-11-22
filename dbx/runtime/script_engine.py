"""MiniScript: catalogo azioni, interprete e forma testuale (F1, F4, F6).

Le azioni sono dizionari concatenabili:

    {"action": "message", "params": {"text": "Ciao"}}

I blocchi (if/else, foreach, confirm) contengono figli in `then` / `else` /
`steps`. La forma testuale permette il montaggio bidirezionale (two-way).
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Iterable

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.expressions import Expression, ExpressionError
from .rowset import Rowset, RowsetError

__all__ = [
    "ACTIONS",
    "ACTION_CATEGORIES",
    "actions_by_category",
    "ScriptEngine",
    "ScriptError",
    "NullUI",
    "parameter_values",
    "script_parameters",
    "to_text",
    "from_text",
    "new_step",
]


class ScriptError(RuntimeError):
    """Errore di esecuzione o di parsing di uno script."""


class ScriptAborted(Exception):
    """Lo script è stato interrotto dall'utente."""


# (chiave, etichetta, tipo: text|expr|var|table|form|report|file)
ACTIONS: dict[str, dict[str, Any]] = {
    "message": {
        "label": "Messaggio",
        "category": "Interfaccia",
        "description": "Mostra un messaggio all'utente.",
        "params": [("text", "Testo", "expr")],
    },
    "status": {
        "label": "Messaggio di stato",
        "category": "Interfaccia",
        "description": "Aggiorna il messaggio nella barra di stato.",
        "params": [("text", "Testo", "expr")],
    },
    "ask": {
        "label": "Chiedi un valore",
        "category": "Variabili",
        "description": "Chiede un valore e lo salva in una variabile.",
        "params": [("prompt", "Domanda", "expr"), ("variable", "Salva in variabile", "var")],
    },
    "set": {
        "label": "Imposta variabile",
        "category": "Variabili",
        "description": "Assegna il risultato di un'espressione a una variabile.",
        "params": [("variable", "Variabile", "var"), ("expr", "Espressione", "expr")],
    },
    "set_global": {
        "label": "Imposta variabile globale",
        "category": "Variabili",
        "description": "Salva un valore nel progetto, disponibile anche agli altri script.",
        "params": [
            ("variable", "Variabile globale", "var"),
            ("expr", "Espressione", "expr"),
        ],
    },
    "unset_global": {
        "label": "Cancella variabile globale",
        "category": "Variabili",
        "description": "Rimuove una variabile globale salvata nel progetto.",
        "params": [("variable", "Variabile globale", "var")],
    },
    "if": {
        "label": "Se…Altrimenti",
        "category": "Controllo",
        "description": "Esegue i passi del ramo Then o Else secondo la condizione.",
        "params": [("expr", "Condizione", "expr")],
    },
    "foreach": {
        "label": "Ripeti per ogni record",
        "category": "Record",
        "description": "Ripete i passi per ogni record della tabella indicata.",
        "params": [("table", "Tabella", "table"), ("filter", "Filtro SQL (facoltativo)", "text")],
    },
    "confirm": {
        "label": "Chiedi conferma",
        "category": "Interfaccia",
        "description": "Chiede conferma prima di eseguire i passi contenuti.",
        "params": [("text", "Domanda", "expr")],
    },
    "open_form": {
        "label": "Apri form",
        "category": "Navigazione",
        "description": "Apre un form del progetto.",
        "params": [("form", "Form", "form")],
    },
    "print_report": {
        "label": "Stampa report",
        "category": "Stampa/File",
        "description": "Apre l'anteprima di stampa di un report.",
        "params": [("report", "Report", "report")],
    },
    "export_csv": {
        "label": "Esporta CSV",
        "category": "Stampa/File",
        "description": "Esporta in CSV i record della tabella, con filtro facoltativo.",
        "params": [
            ("table", "Tabella", "table"),
            ("filter", "Filtro SQL (facoltativo)", "text"),
            ("path", "File di destinazione", "file"),
        ],
    },
    "sql": {
        "label": "Esegui SQL",
        "category": "Avanzate",
        "description": "Esegue un'istruzione SQL controllata dal motore.",
        "params": [("statement", "Istruzione SQL", "text")],
    },
    "call": {
        "label": "Chiama script",
        "category": "Script",
        "description": "Esegue un altro script del progetto.",
        "params": [("script", "Script", "script")],
    },
    "comment": {
        "label": "Commento",
        "category": "Controllo",
        "description": "Aggiunge una nota allo script senza eseguire nulla.",
        "params": [("text", "Testo", "text")],
    },
    "loop": {
        "label": "Ciclo",
        "category": "Controllo",
        "description": "Ripete i passi finché non viene interrotto o termina lo script.",
        "params": [],
    },
    "exit_loop_if": {
        "label": "Esci dal ciclo se",
        "category": "Controllo",
        "description": "Interrompe il ciclo corrente quando la condizione è vera.",
        "params": [("expr", "Condizione", "expr")],
    },
    "exit_script": {
        "label": "Termina script",
        "category": "Controllo",
        "description": "Interrompe subito lo script senza messaggi.",
        "params": [],
    },
    "halt": {
        "label": "Arresta script",
        "category": "Controllo",
        "description": "Interrompe lo script e mostra un messaggio facoltativo.",
        "params": [("message", "Messaggio", "expr")],
    },
    "select_table": {
        "label": "Seleziona tabella",
        "category": "Ricerche",
        "description": "Apre la tabella con filtro e ordinamento e posiziona il primo record.",
        "params": [
            ("table", "Tabella", "table"),
            ("filter", "Filtro SQL (facoltativo)", "text"),
            ("order", "Ordinamento SQL (facoltativo)", "text"),
        ],
    },
    "go_record": {
        "label": "Vai al record",
        "category": "Navigazione",
        "description": "Sposta il cursore sul primo, precedente, successivo, ultimo o numero indicato.",
        "params": [("mode", "Modalità", "mode"), ("number", "Numero record", "text")],
    },
    "set_field": {
        "label": "Imposta campo",
        "category": "Dati",
        "description": "Calcola un'espressione e la scrive subito nel campo del record corrente.",
        "params": [("field", "Campo", "text"), ("expr", "Espressione", "expr")],
    },
    "new_record": {
        "label": "Nuovo record",
        "category": "Record",
        "description": "Inserisce un record con i valori predefiniti e lo rende corrente.",
        "params": [("table", "Tabella (facoltativa)", "table")],
    },
    "duplicate_record": {
        "label": "Duplica record",
        "category": "Record",
        "description": "Copia il record corrente e posiziona il cursore sulla copia.",
        "params": [],
    },
    "delete_record": {
        "label": "Elimina record",
        "category": "Record",
        "description": "Elimina il record corrente, con conferma facoltativa.",
        "params": [("confirm", "Chiedi conferma", "text")],
    },
    "commit_record": {
        "label": "Conferma record",
        "category": "Record",
        "description": "Ricarica il record corrente dopo le scritture immediate.",
        "params": [],
    },
    "begin_transaction": {
        "label": "Avvia transazione",
        "category": "Dati",
        "description": "Apre una transazione esplicita per raggruppare più scritture.",
        "params": [],
    },
    "commit_transaction": {
        "label": "Conferma transazione",
        "category": "Dati",
        "description": "Conferma definitivamente le scritture della transazione aperta.",
        "params": [],
    },
    "rollback_transaction": {
        "label": "Annulla transazione",
        "category": "Dati",
        "description": "Annulla tutte le scritture della transazione aperta.",
        "params": [],
    },
    "revert_record": {
        "label": "Ripristina record",
        "category": "Record",
        "description": "Ricarica il record corrente dal database, annullando le modifiche in memoria.",
        "params": [],
    },
    "open_query": {
        "label": "Apri query",
        "category": "Navigazione",
        "description": "Apre i risultati di una query salvata.",
        "params": [("query", "Query", "query")],
    },
    "open_report": {
        "label": "Apri report",
        "category": "Navigazione",
        "description": "Apre l'anteprima di un report.",
        "params": [("report", "Report", "report")],
    },
    "custom_dialog": {
        "label": "Dialogo personalizzato",
        "category": "Interfaccia",
        "description": "Chiede un valore con titolo e messaggio e lo salva in una variabile.",
        "params": [
            ("title", "Titolo", "text"),
            ("message", "Messaggio", "expr"),
            ("variable", "Salva in variabile", "var"),
        ],
    },
    "beep": {
        "label": "Segnale acustico",
        "category": "Interfaccia",
        "description": "Emette il segnale acustico di sistema.",
        "params": [],
    },
}

ACTION_CATEGORIES = (
    "Controllo",
    "Navigazione",
    "Dati",
    "Record",
    "Ricerche",
    "Interfaccia",
    "Stampa/File",
    "Script",
    "Variabili",
    "Avanzate",
)


def actions_by_category() -> dict[str, list[str]]:
    """Azioni raggruppate per categoria, nell'ordine dichiarato dal catalogo."""
    buckets: dict[str, list[str]] = {name: [] for name in ACTION_CATEGORIES}
    for key, definition in ACTIONS.items():
        category = str(definition.get("category", "Avanzate"))
        buckets.setdefault(category, []).append(key)
    return {name: keys for name, keys in buckets.items() if keys}


BLOCK_ACTIONS = ("if", "foreach", "confirm", "loop")
GO_RECORD_MODES = ("first", "previous", "next", "last", "number")
_READ_ONLY_PREFIXES = ("SELECT", "WITH", "PRAGMA")
_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE")
_FORBIDDEN_PREFIXES = ("DROP", "ALTER", "CREATE", "ATTACH", "DETACH", "TRUNCATE")


def new_step(action: str, **params: Any) -> dict[str, Any]:
    if action not in ACTIONS:
        raise ScriptError(f"Azione sconosciuta: {action}")
    step: dict[str, Any] = {"action": action, "params": dict(params)}
    if action == "if":
        step["then"] = []
        step["else"] = []
    elif action in BLOCK_ACTIONS:
        step["steps"] = []
    return step


PARAM_NAME = re.compile(r"^[A-Za-z_]\w*$")


def script_parameters(artifact: dict[str, Any] | None) -> list[dict[str, str]]:
    """Parametri dichiarati da uno script: nome, etichetta e valore predefinito.

    Accetta sia la forma completa ``{"name", "label", "default"}`` sia una
    semplice lista di nomi, così gli script 0.8 restano validi.
    """
    if not isinstance(artifact, dict):
        return []
    raw = artifact.get("params") or []
    if not isinstance(raw, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for entry in raw:
        if isinstance(entry, str):
            name, label, default = entry.strip(), entry.strip(), ""
        elif isinstance(entry, dict):
            name = str(entry.get("name") or "").strip()
            label = str(entry.get("label") or name).strip() or name
            default = "" if entry.get("default") is None else str(entry.get("default"))
        else:
            continue
        if not PARAM_NAME.match(name):
            raise ScriptError(f"Nome di parametro non valido: {name!r}")
        key = name.lower()
        if key in seen:
            raise ScriptError(f"Parametro duplicato: {name}")
        seen.add(key)
        result.append({"name": name, "label": label, "default": default})
    return result


def parameter_values(
    artifact: dict[str, Any] | None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Valori iniziali dei parametri: predefiniti più eventuali sostituzioni."""
    values: dict[str, Any] = {
        entry["name"]: entry["default"] for entry in script_parameters(artifact)
    }
    for key, value in (overrides or {}).items():
        name = str(key).lstrip(":")
        values[name] = value
    return values


class NullUI:
    """Interfaccia utente silenziosa per test e build headless."""

    def message(self, text: str) -> None:  # noqa: D102
        pass

    def status(self, text: str) -> None:  # noqa: D102
        pass

    def confirm(self, text: str) -> bool:  # noqa: D102
        return True

    def ask(self, prompt: str, default: str = "") -> str | None:  # noqa: D102
        return default

    def open_form(self, name: str) -> None:  # noqa: D102
        pass

    def open_query(self, name: str) -> None:  # noqa: D102
        pass

    def open_report(self, name: str) -> None:  # noqa: D102
        pass

    def print_report(self, name: str) -> None:  # noqa: D102
        pass

    def custom_dialog(self, title: str, message: str, default: str = "") -> str | None:  # noqa: D102
        return default

    def beep(self) -> None:  # noqa: D102
        pass

    def refresh(self) -> None:  # noqa: D102
        pass


@dataclass
class ScriptResult:
    log: list[str] = dc_field(default_factory=list)
    variables: dict[str, Any] = dc_field(default_factory=dict)
    error: str | None = None


class ScriptEngine:
    """Esegue gli script di progetto; UI iniettabile per test/headless."""

    def __init__(
        self,
        project,
        ui: Any | None = None,
        variables: dict[str, Any] | None = None,
        max_steps: int = 20000,
    ) -> None:
        self.project = project
        self.ui = ui or NullUI()
        self.variables: dict[str, Any] = dict(variables or {})
        self.globals: dict[str, Any] = dict(getattr(project, "globals", {}) or {})
        self.log: list[str] = []
        self.max_steps = max_steps
        self._executed = 0
        self._record: dict[str, Any] = {}
        self._current_table: str = ""
        self._rowset: Rowset | None = None
        self._loop_flags: list[bool] = []
        self._depth = 0
        self._stop = False
        self._in_transaction = False
        self._globals_dirty = False

    # ------------------------------------------------------------------ utils
    def _log(self, message: str) -> None:
        self.log.append(message)

    def _scope(self) -> dict[str, Any]:
        """Variabili locali sopra le globali: il locale ha la precedenza."""
        return {**self.globals, **self.variables}

    def _eval(self, source: str, record: dict[str, Any] | None = None) -> Any:
        context = dict(self._record)
        if record:
            context.update(record)
        try:
            return Expression(source).evaluate(
                context, self._scope(), self._current_table or None
            )
        except ExpressionError as exc:
            raise ScriptError(str(exc)) from exc

    def _interpolate(self, text: Any) -> str:
        """Testo per l'utente: espressione se valida, altrimenti sostituzione :var e [campo]."""
        source = "" if text is None else str(text)
        if not source:
            return ""
        scope = self._scope()
        try:
            value = Expression(source).evaluate(
                self._record, scope, self._current_table or None
            )
            return "" if value is None else str(value)
        except ExpressionError:
            return self._substitute(source)

    def _substitute(self, text: Any) -> str:
        """Sostituisce solo ``:variabile`` e ``[campo]``, senza valutare il testo.

        Serve per filtri e ordinamenti SQL, dove un'espressione valida non deve
        essere trasformata nel suo risultato booleano.
        """
        source = "" if text is None else str(text)
        if not source:
            return ""
        scope = self._scope()

        def replace_variable(match: re.Match[str]) -> str:
            name = match.group(1)
            for key, value in scope.items():
                if str(key).lower() == name.lower():
                    return str(value)
            return match.group(0)

        def replace_field(match: re.Match[str]) -> str:
            name = match.group(1)
            value = self._record.get(name)
            if value is None:
                lowered = {k.lower(): v for k, v in self._record.items()}
                value = lowered.get(name.lower())
            return "" if value is None else str(value)

        result = re.sub(r":([A-Za-z_]\w*)", replace_variable, source)
        return re.sub(r"\[([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\]", replace_field, result)

    def _tick(self) -> None:
        self._executed += 1
        if self._executed > self.max_steps:
            raise ScriptError("Limite di azioni superato: possibile ciclo infinito")

    def _rows(self, table_name: str, where: str = "") -> list[dict[str, Any]]:
        table = self.project.table(table_name)
        if table is None:
            raise ScriptError(f"Tabella sconosciuta: {table_name}")
        try:
            return Rowset(self.project.db, table).open(where=where or "").rows()
        except RowsetError as exc:
            raise ScriptError(str(exc)) from exc

    # ------------------------------------------------------------- cursore dati
    def _open_cursor(self, table_name: str, where: str = "", order: str = "") -> Rowset:
        table = self.project.table(table_name)
        if table is None:
            raise ScriptError(f"Tabella sconosciuta: {table_name}")
        rowset = Rowset(self.project.db, table)
        try:
            rowset.open(where=where or "", order=order or "")
        except RowsetError as exc:
            raise ScriptError(str(exc)) from exc
        self._rowset = rowset
        self._current_table = table.name
        self._sync_record()
        return rowset

    def _require_cursor(self) -> Rowset:
        if self._rowset is None:
            raise ScriptError("Nessuna tabella selezionata: usa SELECT TABLE prima")
        return self._rowset

    def _sync_record(self) -> None:
        if self._rowset is None:
            self._record = {}
            return
        current = self._rowset.current
        self._record = dict(current) if current else {}

    def _current_id(self) -> int:
        record_id = self._record.get(INTERNAL_ID)
        if record_id in (None, "", 0):
            raise ScriptError("Nessun record corrente")
        return int(record_id)

    def _position_log(self) -> str:
        rowset = self._require_cursor()
        position = rowset.index + 1 if rowset.current else 0
        return f"Record {position} di {len(rowset)}"

    def _refresh_ui(self) -> None:
        self.ui.refresh()

    # -------------------------------------------------------------- esecuzione
    def run(
        self,
        steps: Iterable[dict[str, Any]],
        record: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ScriptResult:
        self.log = []
        self._executed = 0
        self._stop = False
        self._depth = 0
        self._loop_flags = []
        self._rowset = None
        self._record = dict(record or {})
        self._in_transaction = False
        self._globals_dirty = False
        if params:
            for key, value in params.items():
                self.variables[str(key).lstrip(":")] = value
        error: str | None = None
        try:
            self._run_steps(list(steps))
        except ScriptAborted:
            self._log("Script interrotto dall'utente")
        except ScriptError as exc:
            error = str(exc)
            self._log(f"ERRORE: {exc}")
        finally:
            if self._in_transaction:
                self._in_transaction = False
                try:
                    self.project.db.con.execute("ROLLBACK")
                    self._log("Transazione aperta annullata automaticamente")
                except Exception as exc:  # pragma: no cover - difensivo
                    self._log(f"Rollback automatico non riuscito: {exc}")
            if self._globals_dirty:
                self._save_globals()
        return ScriptResult(log=list(self.log), variables=dict(self.variables), error=error)

    def run_named(
        self,
        name: str,
        record: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> ScriptResult:
        artifact = self.project.artifact("scripts", name)
        if artifact is None:
            raise ScriptError(f"Script sconosciuto: {name}")
        values = parameter_values(artifact, params)
        return self.run(artifact.get("steps", []), record, values)

    def _save_globals(self) -> None:
        self._globals_dirty = False
        try:
            current = self.project.globals
            current.clear()
            current.update(self.globals)
            self.project.save()
        except Exception as exc:  # pragma: no cover - difensivo
            self._log(f"Variabili globali non salvate: {exc}")

    def _run_steps(self, steps: list[dict[str, Any]]) -> None:
        for step in steps:
            if self._stop:
                return
            if self._loop_flags and self._loop_flags[-1]:
                return
            self._tick()
            self._execute(step)

    def _execute(self, step: dict[str, Any]) -> None:
        action = str(step.get("action", ""))
        params = step.get("params") or {}
        handler = getattr(self, f"_do_{action}", None)
        if handler is None:
            raise ScriptError(f"Azione non implementata: {action}")
        handler(params, step)

    # ------------------------------------------------------------------ azioni
    def _do_message(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        text = self._interpolate(params.get("text", ""))
        self._log(text)
        self.ui.message(text)

    def _do_status(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        text = self._interpolate(params.get("text", ""))
        self._log(text)
        self.ui.status(text)

    def _do_ask(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        prompt = self._interpolate(params.get("prompt", ""))
        variable = str(params.get("variable") or "risposta")
        value = self.ui.ask(prompt, str(self.variables.get(variable, "")))
        if value is None:
            raise ScriptAborted()
        self.variables[variable] = value
        self._log(f":{variable} = {value!r}")

    def _do_set(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        variable = str(params.get("variable") or "").lstrip(":")
        if not variable:
            raise ScriptError("Variabile mancante nell'azione 'set'")
        self.variables[variable] = self._eval(str(params.get("expr", "")))
        self._log(f":{variable} = {self.variables[variable]!r}")

    def _do_set_global(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        variable = str(params.get("variable") or "").lstrip(":")
        if not variable:
            raise ScriptError("Variabile globale mancante nell'azione 'set_global'")
        value = self._eval(str(params.get("expr", "")))
        self.project.set_global(variable, value)
        self.globals[variable] = self.project.globals[variable]
        self.variables.pop(variable, None)
        self._globals_dirty = True
        self._log(f"globale :{variable} = {self.globals[variable]!r}")

    def _do_unset_global(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        variable = str(params.get("variable") or "").lstrip(":")
        if not variable:
            raise ScriptError("Variabile globale mancante nell'azione 'unset_global'")
        self.globals.pop(variable, None)
        self.project.unset_global(variable)
        self._globals_dirty = True
        self._log(f"globale :{variable} cancellata")

    def _do_if(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        condition = bool(self._eval(str(params.get("expr", ""))))
        branch = step.get("then", step.get("steps", [])) if condition else step.get("else", [])
        self._run_steps(list(branch or []))

    def _do_confirm(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        text = self._interpolate(params.get("text", ""))
        if self.ui.confirm(text):
            self._run_steps(list(step.get("steps", [])))
        else:
            self._log("Operazione annullata")

    def _do_foreach(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        table_name = str(params.get("table") or "")
        where = self._substitute(str(params.get("filter") or ""))
        rows = self._rows(table_name, where)
        previous_record = self._record
        previous_table = self._current_table
        self._current_table = table_name
        table = self.project.require_table(table_name)
        try:
            for row in rows:
                self._record = {f.name: row.get(f.name) for f in table.fields}
                self._run_steps(list(step.get("steps", [])))
        finally:
            self._record = previous_record
            self._current_table = previous_table

    def _do_open_form(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        name = str(params.get("form") or "")
        if self.project.artifact("forms", name) is None:
            raise ScriptError(f"Form sconosciuto: {name}")
        self._log(f"Apri form {name}")
        self.ui.open_form(name)

    def _do_print_report(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        name = str(params.get("report") or "")
        if self.project.artifact("reports", name) is None:
            raise ScriptError(f"Report sconosciuto: {name}")
        self._log(f"Stampa report {name}")
        self.ui.print_report(name)

    def _do_export_csv(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        from ..io.csv_io import CsvError, export_rows

        table_name = str(params.get("table") or "")
        table = self.project.table(table_name)
        if table is None:
            raise ScriptError(f"Tabella sconosciuta: {table_name}")
        rows = self._rows(table_name, self._substitute(str(params.get("filter") or "")))
        path = self._interpolate(params.get("path", ""))
        if not path:
            raise ScriptError("Percorso di destinazione mancante per l'export CSV")
        try:
            export_rows(path, table.field_names, rows, table=table)
        except CsvError as exc:
            raise ScriptError(str(exc)) from exc
        self._log(f"Esportati {len(rows)} record in {path}")

    def _do_sql(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        statement = str(params.get("statement") or "").strip()
        if not statement:
            raise ScriptError("Istruzione SQL vuota")
        head = statement.split(None, 1)[0].upper()
        if head in _FORBIDDEN_PREFIXES:
            raise ScriptError(
                "Le azioni script non possono modificare la struttura del database (usa il Table Builder)"
            )
        try:
            if head in _READ_ONLY_PREFIXES or head not in _WRITE_PREFIXES:
                rows = self.project.db.query(statement)
                self._log(f"SQL: {len(rows)} righe")
            else:
                cursor = self.project.db.execute(statement)
                self._log(f"SQL: {cursor.rowcount} righe modificate")
        except Exception as exc:
            raise ScriptError(f"SQL non riuscito: {exc}") from exc
        self.ui.refresh()

    def _do_call(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        name = str(params.get("script") or "")
        artifact = self.project.artifact("scripts", name)
        if artifact is None:
            raise ScriptError(f"Script sconosciuto: {name}")
        if self._depth >= 12:
            raise ScriptError("Troppe chiamate annidate tra script")
        self._depth += 1
        try:
            self._run_steps(list(artifact.get("steps", [])))
        finally:
            self._depth -= 1

    # ------------------------------------------------------ controllo e testo
    def _do_comment(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        return

    def _do_loop(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        body = list(step.get("steps", []))
        self._loop_flags.append(False)
        try:
            while not self._stop and not self._loop_flags[-1]:
                self._tick()
                self._run_steps(body)
        finally:
            self._loop_flags.pop()

    def _do_exit_loop_if(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        if not self._loop_flags:
            raise ScriptError("EXIT LOOP IF è valido solo dentro un ciclo")
        if bool(self._eval(str(params.get("expr", "")))):
            self._loop_flags[-1] = True
            self._log("Uscita dal ciclo")

    def _do_exit_script(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        self._stop = True
        self._log("Script terminato")

    def _do_halt(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        message = self._interpolate(params.get("message", ""))
        self._stop = True
        self._log(f"Script interrotto: {message}" if message else "Script interrotto")
        if message:
            self.ui.message(message)

    # -------------------------------------------------------------- dati/record
    def _do_select_table(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        table_name = str(params.get("table") or "")
        if not table_name:
            raise ScriptError("Tabella mancante in SELECT TABLE")
        rowset = self._open_cursor(
            table_name,
            where=self._substitute(str(params.get("filter") or "")),
            order=self._substitute(str(params.get("order") or "")),
        )
        self._log(f"Tabella {rowset.table.name}: {len(rowset)} record · {self._position_log()}")
        self._refresh_ui()

    def _do_go_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        mode = str(params.get("mode") or "first").strip().lower()
        aliases = {
            "primo": "first",
            "precedente": "previous",
            "prev": "previous",
            "successivo": "next",
            "ultimo": "last",
            "numero": "number",
            "goto": "number",
        }
        mode = aliases.get(mode, mode)
        if mode == "first":
            rowset.first()
        elif mode == "previous":
            rowset.previous()
        elif mode == "next":
            rowset.next()
        elif mode == "last":
            rowset.last()
        elif mode == "number":
            try:
                number = int(str(params.get("number") or "0"))
            except (TypeError, ValueError) as exc:
                raise ScriptError("Numero di record non valido") from exc
            if number < 1:
                raise ScriptError("Il numero di record parte da 1")
            rowset.goto(number - 1)
        else:
            raise ScriptError(f"Modalità GO RECORD non valida: {mode}")
        self._sync_record()
        self._log(self._position_log())
        self._refresh_ui()

    def _do_set_field(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        record_id = self._current_id()
        field_name = str(params.get("field") or "").strip()
        if "." in field_name:
            table_name, field_name = field_name.split(".", 1)
            if table_name.lower() != rowset.table.name.lower():
                raise ScriptError(
                    f"SET FIELD lavora sulla tabella corrente {rowset.table.name}, non su {table_name}"
                )
        field_obj = rowset.table.field(field_name)
        if field_obj is None:
            raise ScriptError(f"Campo sconosciuto in SET FIELD: {field_name}")
        if not field_obj.stored:
            raise ScriptError(f"Il campo calcolato {field_name} non è modificabile")
        expression = str(params.get("expr") or "").strip()
        if not expression:
            raise ScriptError("Espressione mancante in SET FIELD")
        value = self._eval(expression)
        values = dict(self._record)
        values[field_name] = value
        try:
            rowset.update(record_id, values)
        except RowsetError as exc:
            raise ScriptError(str(exc)) from exc
        self._sync_record()
        self._log(f"{rowset.table.name}.{field_name} = {value!r}")
        self._refresh_ui()

    def _do_new_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        table_name = str(params.get("table") or "")
        if table_name and (
            self._rowset is None
            or self._rowset.table.name.lower() != table_name.lower()
        ):
            self._open_cursor(table_name)
        rowset = self._require_cursor()
        record = rowset.new_record()
        try:
            record_id = rowset.insert(record)
        except RowsetError as exc:
            raise ScriptError(f"Nuovo record non inserito: {exc}") from exc
        rowset.refresh()
        rowset.find(INTERNAL_ID, record_id)
        self._sync_record()
        self._log(f"Nuovo record in {rowset.table.name} · {self._position_log()}")
        self._refresh_ui()

    def _do_duplicate_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        self._current_id()
        values = {key: value for key, value in self._record.items() if key != INTERNAL_ID}
        try:
            record_id = rowset.insert(values)
        except RowsetError as exc:
            raise ScriptError(f"Duplicazione non riuscita: {exc}") from exc
        rowset.refresh()
        rowset.find(INTERNAL_ID, record_id)
        self._sync_record()
        self._log(f"Record duplicato · {self._position_log()}")
        self._refresh_ui()

    def _do_delete_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        self._current_id()
        confirm = str(params.get("confirm") or "").strip().lower()
        if confirm not in ("no", "false", "0", "off"):
            if not self.ui.confirm("Eliminare il record corrente?"):
                self._log("Eliminazione annullata")
                return
        try:
            rowset.delete()
        except RowsetError as exc:
            raise ScriptError(f"Eliminazione non riuscita: {exc}") from exc
        rowset.refresh()
        self._sync_record()
        self._log(f"Record eliminato · {self._position_log()}")
        self._refresh_ui()

    def _do_commit_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        rowset.refresh()
        self._sync_record()
        self._log(f"Record confermato · {self._position_log()}")
        self._refresh_ui()

    # ------------------------------------------------------------ transazioni
    def _do_begin_transaction(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        if self._in_transaction:
            raise ScriptError("Transazione già aperta")
        try:
            self.project.db.con.execute("BEGIN")
        except Exception as exc:
            raise ScriptError(f"Transazione non avviata: {exc}") from exc
        self._in_transaction = True
        self._log("Transazione avviata")

    def _do_commit_transaction(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        if not self._in_transaction:
            raise ScriptError("Nessuna transazione aperta da confermare")
        try:
            self.project.db.con.execute("COMMIT")
        except Exception as exc:
            raise ScriptError(f"Transazione non confermata: {exc}") from exc
        finally:
            self._in_transaction = False
        self._log("Transazione confermata")
        self._refresh_ui()

    def _do_rollback_transaction(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        if not self._in_transaction:
            raise ScriptError("Nessuna transazione aperta da annullare")
        try:
            self.project.db.con.execute("ROLLBACK")
        except Exception as exc:
            raise ScriptError(f"Transazione non annullata: {exc}") from exc
        finally:
            self._in_transaction = False
        if self._rowset is not None:
            try:
                self._rowset.refresh()
                self._sync_record()
            except RowsetError:
                pass
        self._log("Transazione annullata")
        self._refresh_ui()

    def _do_revert_record(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        rowset = self._require_cursor()
        rowset.refresh()
        self._sync_record()
        self._log(f"Record ripristinato · {self._position_log()}")
        self._refresh_ui()

    # ------------------------------------------------------- finestre e servizi
    def _do_open_query(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        name = str(params.get("query") or "")
        if self.project.artifact("queries", name) is None:
            raise ScriptError(f"Query sconosciuta: {name}")
        self._log(f"Apri query {name}")
        self.ui.open_query(name)

    def _do_open_report(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        name = str(params.get("report") or "")
        if self.project.artifact("reports", name) is None:
            raise ScriptError(f"Report sconosciuto: {name}")
        self._log(f"Apri report {name}")
        self.ui.open_report(name)

    def _do_custom_dialog(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        title = self._interpolate(params.get("title", "")) or "dBX"
        message = self._interpolate(params.get("message", ""))
        variable = str(params.get("variable") or "").lstrip(":")
        default = str(self.variables.get(variable, "")) if variable else ""
        value = self.ui.custom_dialog(title, message, default)
        if value is None:
            self._log("Dialogo annullato")
            return
        if variable:
            self.variables[variable] = value
            self._log(f":{variable} = {value!r}")
        else:
            self._log(f"Dialogo: {value!r}")

    def _do_beep(self, params: dict[str, Any], step: dict[str, Any]) -> None:
        self.ui.beep()


# --------------------------------------------------------------------------- #
# Forma testuale (two-way)
# --------------------------------------------------------------------------- #


def _quote(text: str) -> str:
    return '"' + str(text).replace('"', '""') + '"'


def _unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
        quote = text[0]
        return text[1:-1].replace(quote * 2, quote)
    return text


def to_text(steps: Iterable[dict[str, Any]], indent: int = 0) -> str:
    lines: list[str] = []
    pad = "  " * indent
    for step in steps:
        action = step.get("action", "")
        params = step.get("params") or {}
        if action == "message":
            lines.append(f"{pad}MESSAGE {_quote(params.get('text', ''))}")
        elif action == "status":
            lines.append(f"{pad}STATUS {_quote(params.get('text', ''))}")
        elif action == "ask":
            lines.append(
                f"{pad}ASK {_quote(params.get('prompt', ''))} INTO :{params.get('variable', 'risposta')}"
            )
        elif action == "set":
            lines.append(f"{pad}SET :{params.get('variable', '')} = {params.get('expr', '')}")
        elif action == "set_global":
            lines.append(
                f"{pad}SET GLOBAL :{params.get('variable', '')} = {params.get('expr', '')}"
            )
        elif action == "unset_global":
            lines.append(f"{pad}CLEAR GLOBAL :{params.get('variable', '')}")
        elif action == "if":
            lines.append(f"{pad}IF {params.get('expr', '')}")
            lines.append(to_text(step.get("then", step.get("steps", [])), indent + 1))
            if step.get("else"):
                lines.append(f"{pad}ELSE")
                lines.append(to_text(step.get("else", []), indent + 1))
            lines.append(f"{pad}ENDIF")
        elif action == "confirm":
            lines.append(f"{pad}CONFIRM {_quote(params.get('text', ''))}")
            lines.append(to_text(step.get("steps", []), indent + 1))
            lines.append(f"{pad}ENDCONFIRM")
        elif action == "foreach":
            where = f" WHERE {params.get('filter')}" if params.get("filter") else ""
            lines.append(f"{pad}FOR EACH {params.get('table', '')}{where}")
            lines.append(to_text(step.get("steps", []), indent + 1))
            lines.append(f"{pad}ENDFOR")
        elif action == "open_form":
            lines.append(f"{pad}OPEN FORM {params.get('form', '')}")
        elif action == "print_report":
            lines.append(f"{pad}PRINT REPORT {params.get('report', '')}")
        elif action == "export_csv":
            where = f" WHERE {params.get('filter')}" if params.get("filter") else ""
            lines.append(f"{pad}EXPORT CSV {params.get('table', '')}{where} TO {_quote(params.get('path', ''))}")
        elif action == "sql":
            lines.append(f"{pad}SQL {params.get('statement', '')}")
        elif action == "call":
            lines.append(f"{pad}CALL {params.get('script', '')}")
        elif action == "comment":
            lines.append(f"{pad}COMMENT {_quote(params.get('text', ''))}")
        elif action == "loop":
            lines.append(f"{pad}LOOP")
            lines.append(to_text(step.get("steps", []), indent + 1))
            lines.append(f"{pad}ENDLOOP")
        elif action == "exit_loop_if":
            lines.append(f"{pad}EXIT LOOP IF {params.get('expr', '')}")
        elif action == "exit_script":
            lines.append(f"{pad}EXIT SCRIPT")
        elif action == "halt":
            message = str(params.get("message") or "")
            lines.append(f"{pad}HALT {_quote(message)}" if message else f"{pad}HALT")
        elif action == "select_table":
            where = f" WHERE {params.get('filter')}" if params.get("filter") else ""
            order = f" ORDER BY {params.get('order')}" if params.get("order") else ""
            lines.append(f"{pad}SELECT TABLE {params.get('table', '')}{where}{order}")
        elif action == "go_record":
            mode = str(params.get("mode") or "first")
            number = f" {params.get('number')}" if mode == "number" else ""
            lines.append(f"{pad}GO RECORD {mode}{number}")
        elif action == "set_field":
            lines.append(
                f"{pad}SET FIELD {params.get('field', '')} = {params.get('expr', '')}"
            )
        elif action == "new_record":
            table = str(params.get("table") or "")
            lines.append(f"{pad}NEW RECORD {table}" if table else f"{pad}NEW RECORD")
        elif action == "duplicate_record":
            lines.append(f"{pad}DUPLICATE RECORD")
        elif action == "delete_record":
            confirm = str(params.get("confirm") or "").strip().lower()
            suffix = " NOCONFIRM" if confirm in ("no", "false", "0", "off") else ""
            lines.append(f"{pad}DELETE RECORD{suffix}")
        elif action == "commit_record":
            lines.append(f"{pad}COMMIT RECORD")
        elif action == "begin_transaction":
            lines.append(f"{pad}BEGIN TRANSACTION")
        elif action == "commit_transaction":
            lines.append(f"{pad}COMMIT TRANSACTION")
        elif action == "rollback_transaction":
            lines.append(f"{pad}ROLLBACK TRANSACTION")
        elif action == "revert_record":
            lines.append(f"{pad}REVERT RECORD")
        elif action == "open_query":
            lines.append(f"{pad}OPEN QUERY {params.get('query', '')}")
        elif action == "open_report":
            lines.append(f"{pad}OPEN REPORT {params.get('report', '')}")
        elif action == "custom_dialog":
            variable = str(params.get("variable") or "")
            into = f" INTO :{variable}" if variable else ""
            lines.append(
                f"{pad}CUSTOM DIALOG {_quote(params.get('title', ''))} "
                f"{_quote(params.get('message', ''))}{into}"
            )
        elif action == "beep":
            lines.append(f"{pad}BEEP")
        else:
            lines.append(f"{pad}# azione sconosciuta: {action}")
    return "\n".join(line for line in lines if line.strip())


_TOKEN_SPLIT = re.compile(r"\s+")


def _parse_if(
    lines: list[tuple[int, str]], index: int, line_no: int, expr: str
) -> tuple[dict[str, Any], int]:
    """Legge un IF, incluso ``ELSE IF`` come IF annidato nell'ELSE."""
    then_steps, index = _parse_block(lines, index + 1, ("ELSE", "ELSEIF", "ENDIF"))
    step: dict[str, Any] = {
        "action": "if",
        "params": {"expr": expr},
        "then": then_steps,
        "else": [],
    }
    if index < len(lines):
        current = lines[index][1].strip()
        upper = current.upper()
        if upper == "ELSE":
            else_steps, index = _parse_block(lines, index + 1, ("ENDIF",))
            step["else"] = else_steps
        elif upper.startswith("ELSE IF ") or upper.startswith("ELSEIF "):
            nested_expr = current[8:].strip() if upper.startswith("ELSE IF ") else current[7:].strip()
            nested, index = _parse_if(lines, index, line_no, nested_expr)
            step["else"] = [nested]
            # L'ENDIF del nested chiude anche l'IF esterno.
            return step, index
    if index >= len(lines):
        raise ScriptError(f"IF alla riga {line_no} senza ENDIF")
    if lines[index][1].strip().upper() != "ENDIF":
        raise ScriptError(f"IF alla riga {line_no} senza ENDIF")
    return step, index + 1


def _parse_block(lines: list[tuple[int, str]], index: int, terminators: tuple[str, ...]) -> tuple[list[dict[str, Any]], int]:
    steps: list[dict[str, Any]] = []
    while index < len(lines):
        _, raw = lines[index]
        keyword = raw.split()[0].upper()
        if keyword in terminators:
            return steps, index
        line_no, text = lines[index]
        upper = text.upper()
        if upper.startswith("IF "):
            step, index = _parse_if(lines, index, line_no, text[3:].strip())
            steps.append(step)
            continue
        if upper == "LOOP":
            body, index = _parse_block(lines, index + 1, ("ENDLOOP",))
            if index >= len(lines):
                raise ScriptError(f"LOOP alla riga {line_no} senza ENDLOOP")
            index += 1
            steps.append({"action": "loop", "params": {}, "steps": body})
            continue
        if upper.startswith("FOR EACH "):
            rest = text[9:].strip()
            where = ""
            match = re.split(r"\s+WHERE\s+", rest, maxsplit=1, flags=re.IGNORECASE)
            table_name = match[0].strip()
            if len(match) > 1:
                where = match[1].strip()
            body, index = _parse_block(lines, index + 1, ("ENDFOR",))
            if index >= len(lines):
                raise ScriptError(f"FOR EACH alla riga {line_no} senza ENDFOR")
            index += 1
            steps.append(
                {
                    "action": "foreach",
                    "params": {"table": table_name, "filter": where},
                    "steps": body,
                }
            )
            continue
        if upper.startswith("CONFIRM "):
            text_value = _unquote(text[8:].strip())
            body, index = _parse_block(lines, index + 1, ("ENDCONFIRM",))
            if index >= len(lines):
                raise ScriptError(f"CONFIRM alla riga {line_no} senza ENDCONFIRM")
            index += 1
            steps.append({"action": "confirm", "params": {"text": text_value}, "steps": body})
            continue
        steps.append(_parse_line(text, line_no))
        index += 1
    return steps, index


def _parse_line(text: str, line_no: int) -> dict[str, Any]:
    upper = text.upper()
    if upper.startswith("COMMENT "):
        return {"action": "comment", "params": {"text": _unquote(text[8:])}}
    if upper.startswith("SET GLOBAL "):
        rest = text[11:].strip()
        match = re.match(r"^:(\w+)\s*=\s*(.+)$", rest)
        if not match:
            raise ScriptError(
                f"SET GLOBAL malformato alla riga {line_no}: usa SET GLOBAL :var = espressione"
            )
        return {
            "action": "set_global",
            "params": {"variable": match.group(1), "expr": match.group(2).strip()},
        }
    if upper.startswith("CLEAR GLOBAL "):
        rest = text[13:].strip()
        match = re.match(r"^:?(\w+)$", rest)
        if not match:
            raise ScriptError(
                f"CLEAR GLOBAL malformato alla riga {line_no}: usa CLEAR GLOBAL :var"
            )
        return {"action": "unset_global", "params": {"variable": match.group(1)}}
    if upper.startswith("SET FIELD "):
        rest = text[10:].strip()
        match = re.match(
            r"^([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\s*=\s*(.+)$", rest
        )
        if not match:
            raise ScriptError(
                f"SET FIELD malformato alla riga {line_no}: usa SET FIELD campo = espressione"
            )
        return {
            "action": "set_field",
            "params": {"field": match.group(1), "expr": match.group(2).strip()},
        }
    if upper.startswith("SELECT TABLE "):
        rest = text[13:].strip()
        match = re.match(
            r"^(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+))?$",
            rest,
            re.IGNORECASE,
        )
        if not match:
            raise ScriptError(f"SELECT TABLE malformato alla riga {line_no}")
        return {
            "action": "select_table",
            "params": {
                "table": match.group(1),
                "filter": (match.group(2) or "").strip(),
                "order": (match.group(3) or "").strip(),
            },
        }
    if upper.startswith("GO RECORD "):
        rest = text[10:].strip()
        match = re.match(r"^(\w+)(?:\s+(\d+))?$", rest)
        if not match:
            raise ScriptError(f"GO RECORD malformato alla riga {line_no}")
        return {
            "action": "go_record",
            "params": {"mode": match.group(1).lower(), "number": match.group(2) or ""},
        }
    if upper.startswith("NEW RECORD"):
        rest = text[10:].strip()
        return {"action": "new_record", "params": {"table": rest}}
    if upper.startswith("DUPLICATE RECORD"):
        return {"action": "duplicate_record", "params": {}}
    if upper.startswith("DELETE RECORD"):
        rest = text[13:].strip().upper()
        return {
            "action": "delete_record",
            "params": {"confirm": "no" if rest == "NOCONFIRM" else ""},
        }
    if upper.startswith("BEGIN TRANSACTION"):
        return {"action": "begin_transaction", "params": {}}
    if upper.startswith("COMMIT TRANSACTION"):
        return {"action": "commit_transaction", "params": {}}
    if upper.startswith("ROLLBACK TRANSACTION"):
        return {"action": "rollback_transaction", "params": {}}
    if upper.startswith("COMMIT RECORD"):
        return {"action": "commit_record", "params": {}}
    if upper.startswith("REVERT RECORD"):
        return {"action": "revert_record", "params": {}}
    if upper.startswith("EXIT LOOP IF "):
        return {"action": "exit_loop_if", "params": {"expr": text[13:].strip()}}
    if upper.startswith("EXIT SCRIPT"):
        return {"action": "exit_script", "params": {}}
    if upper.startswith("HALT"):
        rest = text[4:].strip()
        return {"action": "halt", "params": {"message": _unquote(rest)}}
    if upper.startswith("OPEN QUERY "):
        return {"action": "open_query", "params": {"query": text[11:].strip()}}
    if upper.startswith("OPEN REPORT "):
        return {"action": "open_report", "params": {"report": text[12:].strip()}}
    if upper.startswith("CUSTOM DIALOG "):
        rest = text[14:].strip()
        match = re.match(
            r'^("(?:[^"]|"")*")\s+("(?:[^"]|"")*")(?:\s+INTO\s+:(\w+))?$',
            rest,
        )
        if not match:
            raise ScriptError(
                f"CUSTOM DIALOG malformato alla riga {line_no}: usa CUSTOM DIALOG \"titolo\" \"messaggio\" INTO :var"
            )
        return {
            "action": "custom_dialog",
            "params": {
                "title": _unquote(match.group(1)),
                "message": _unquote(match.group(2)),
                "variable": match.group(3) or "",
            },
        }
    if upper.strip() == "BEEP":
        return {"action": "beep", "params": {}}
    if upper.startswith("MESSAGE "):
        return {"action": "message", "params": {"text": _unquote(text[8:])}}
    if upper.startswith("STATUS "):
        return {"action": "status", "params": {"text": _unquote(text[7:])}}
    if upper.startswith("ASK "):
        rest = text[4:].strip()
        match = re.match(r"^(.*)\s+INTO\s+:(\w+)$", rest, re.IGNORECASE)
        if not match:
            raise ScriptError(f"ASK malformato alla riga {line_no}: usa ASK \"domanda\" INTO :var")
        return {"action": "ask", "params": {"prompt": _unquote(match.group(1)), "variable": match.group(2)}}
    if upper.startswith("SET "):
        rest = text[4:].strip()
        match = re.match(r"^:(\w+)\s*=\s*(.+)$", rest)
        if not match:
            raise ScriptError(f"SET malformato alla riga {line_no}: usa SET :var = espressione")
        return {"action": "set", "params": {"variable": match.group(1), "expr": match.group(2).strip()}}
    if upper.startswith("OPEN FORM "):
        return {"action": "open_form", "params": {"form": text[10:].strip()}}
    if upper.startswith("PRINT REPORT "):
        return {"action": "print_report", "params": {"report": text[13:].strip()}}
    if upper.startswith("EXPORT CSV "):
        rest = text[11:].strip()
        match = re.match(r"^(.*)\s+TO\s+(.+)$", rest, re.IGNORECASE)
        if not match:
            raise ScriptError(f"EXPORT CSV malformato alla riga {line_no}: usa ... TO \"file\"")
        source = match.group(1).strip()
        parts = re.split(r"\s+WHERE\s+", source, maxsplit=1, flags=re.IGNORECASE)
        return {
            "action": "export_csv",
            "params": {
                "table": parts[0].strip(),
                "filter": parts[1].strip() if len(parts) > 1 else "",
                "path": _unquote(match.group(2)),
            },
        }
    if upper.startswith("SQL "):
        return {"action": "sql", "params": {"statement": text[4:].strip()}}
    if upper.startswith("CALL "):
        return {"action": "call", "params": {"script": text[5:].strip()}}
    raise ScriptError(f"Riga {line_no} non riconosciuta: {text}")


def from_text(text: str) -> list[dict[str, Any]]:
    lines: list[tuple[int, str]] = []
    for number, raw in enumerate(str(text).splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append((number, stripped))
    steps, index = _parse_block(lines, 0, ())
    if index < len(lines):
        raise ScriptError(f"Blocco non chiuso alla riga {lines[index][0]}")
    return steps


def count_steps(steps: Iterable[dict[str, Any]]) -> int:
    total = 0
    for step in steps:
        total += 1
        total += count_steps(step.get("then", []))
        total += count_steps(step.get("else", []))
        total += count_steps(step.get("steps", []))
    return total
