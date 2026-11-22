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
from ..core.expressions import Expression, ExpressionError
from .rowset import Rowset, RowsetError

__all__ = [
    "ACTIONS",
    "ScriptEngine",
    "ScriptError",
    "NullUI",
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
    "message": {"label": "Messaggio", "params": [("text", "Testo", "expr")]},
    "status": {"label": "Messaggio di stato", "params": [("text", "Testo", "expr")]},
    "ask": {
        "label": "Chiedi un valore",
        "params": [("prompt", "Domanda", "expr"), ("variable", "Salva in variabile", "var")],
    },
    "set": {
        "label": "Imposta variabile",
        "params": [("variable", "Variabile", "var"), ("expr", "Espressione", "expr")],
    },
    "if": {"label": "Se…Altrimenti", "params": [("expr", "Condizione", "expr")]},
    "foreach": {
        "label": "Ripeti per ogni record",
        "params": [("table", "Tabella", "table"), ("filter", "Filtro SQL (facoltativo)", "text")],
    },
    "confirm": {"label": "Chiedi conferma", "params": [("text", "Domanda", "expr")]},
    "open_form": {"label": "Apri form", "params": [("form", "Form", "form")]},
    "print_report": {"label": "Stampa report", "params": [("report", "Report", "report")]},
    "export_csv": {
        "label": "Esporta CSV",
        "params": [
            ("table", "Tabella", "table"),
            ("filter", "Filtro SQL (facoltativo)", "text"),
            ("path", "File di destinazione", "file"),
        ],
    },
    "sql": {"label": "Esegui SQL", "params": [("statement", "Istruzione SQL", "text")]},
    "call": {"label": "Chiama script", "params": [("script", "Script", "script")]},
}

BLOCK_ACTIONS = ("if", "foreach", "confirm")
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

    def print_report(self, name: str) -> None:  # noqa: D102
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
        self.log: list[str] = []
        self.max_steps = max_steps
        self._executed = 0
        self._record: dict[str, Any] = {}
        self._current_table: str = ""
        self._depth = 0
        self._stop = False

    # ------------------------------------------------------------------ utils
    def _log(self, message: str) -> None:
        self.log.append(message)

    def _eval(self, source: str, record: dict[str, Any] | None = None) -> Any:
        context = dict(self._record)
        if record:
            context.update(record)
        try:
            return Expression(source).evaluate(context, self.variables, self._current_table or None)
        except ExpressionError as exc:
            raise ScriptError(str(exc)) from exc

    def _interpolate(self, text: Any) -> str:
        """Testo per l'utente: espressione se valida, altrimenti sostituzione :var e [campo]."""
        source = "" if text is None else str(text)
        if not source:
            return ""
        try:
            value = Expression(source).evaluate(self._record, self.variables, self._current_table or None)
            return "" if value is None else str(value)
        except ExpressionError:
            pass

        def replace_variable(match: re.Match[str]) -> str:
            name = match.group(1)
            for key, value in self.variables.items():
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
        result = re.sub(r"\[([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)?)\]", replace_field, result)
        return result

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

    # -------------------------------------------------------------- esecuzione
    def run(self, steps: Iterable[dict[str, Any]], record: dict[str, Any] | None = None) -> ScriptResult:
        self.log = []
        self._executed = 0
        self._stop = False
        self._depth = 0
        self._record = dict(record or {})
        error: str | None = None
        try:
            self._run_steps(list(steps))
        except ScriptAborted:
            self._log("Script interrotto dall'utente")
        except ScriptError as exc:
            error = str(exc)
            self._log(f"ERRORE: {exc}")
        return ScriptResult(log=list(self.log), variables=dict(self.variables), error=error)

    def run_named(self, name: str, record: dict[str, Any] | None = None) -> ScriptResult:
        artifact = self.project.artifact("scripts", name)
        if artifact is None:
            raise ScriptError(f"Script sconosciuto: {name}")
        return self.run(artifact.get("steps", []), record)

    def _run_steps(self, steps: list[dict[str, Any]]) -> None:
        for step in steps:
            if self._stop:
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
        where = str(params.get("filter") or "")
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
        rows = self._rows(table_name, str(params.get("filter") or ""))
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
        else:
            lines.append(f"{pad}# azione sconosciuta: {action}")
    return "\n".join(line for line in lines if line.strip())


_TOKEN_SPLIT = re.compile(r"\s+")


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
            expr = text[3:].strip()
            then_steps, index = _parse_block(lines, index + 1, ("ELSE", "ENDIF"))
            step = {"action": "if", "params": {"expr": expr}, "then": then_steps, "else": []}
            if index < len(lines) and lines[index][1].strip().upper() == "ELSE":
                else_steps, index = _parse_block(lines, index + 1, ("ENDIF",))
                step["else"] = else_steps
            if index >= len(lines):
                raise ScriptError(f"IF alla riga {line_no} senza ENDIF")
            index += 1
            steps.append(step)
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
