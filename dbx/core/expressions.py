"""Motore di espressioni condiviso da form, report, script e validazioni.

Sostituisce l'Expression Builder di dBASE: la sintassi è quella classica
(`[tabella.campo]`, `:variabile`, `.AND.`, `IIF(...)`), l'esecuzione avviene su
un AST Python validato con whitelist di nodi e funzioni: nessun `eval` libero.
"""

from __future__ import annotations

import ast
import re
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterable

__all__ = ["Expression", "ExpressionError", "evaluate", "rewrite", "FUNCTIONS"]


class ExpressionError(ValueError):
    """Errore di sintassi o di valutazione di un'espressione."""


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DOT_KEYWORD = re.compile(r"\.(AND|OR|NOT|T|F|NULL)\.", re.IGNORECASE)

_DOT_MAP = {
    "AND": " and ",
    "OR": " or ",
    "NOT": " not ",
    "T": " True ",
    "F": " False ",
    "NULL": " None ",
}


def rewrite(source: str) -> tuple[str, set[str], set[str]]:
    """Traduce la sintassi dBASE-ish in espressione Python.

    Restituisce (sorgente Python, campi referenziati, variabili referenziate).
    """
    if source is None:
        return "", set(), set()
    text = str(source)
    out: list[str] = []
    fields: set[str] = set()
    variables: set[str] = set()
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in ("'", '"'):
            quote = ch
            j = i + 1
            buf = [quote]
            closed = False
            while j < n:
                c = text[j]
                if c == "\\" and j + 1 < n:
                    buf.append(text[j : j + 2])
                    j += 2
                    continue
                if c == quote:
                    if j + 1 < n and text[j + 1] == quote:
                        buf.append(quote)
                        j += 2
                        continue
                    closed = True
                    break
                buf.append(c)
                j += 1
            if not closed:
                raise ExpressionError(f"Stringa non terminata in: {text}")
            buf.append(quote)
            out.append("".join(buf))
            i = j + 1
            continue
        if ch == "[":
            j = text.find("]", i + 1)
            if j < 0:
                raise ExpressionError(f"Riferimento di campo non terminato in: {text}")
            ref = text[i + 1 : j].strip()
            if not ref:
                raise ExpressionError("Riferimento di campo vuoto: []")
            if "." in ref:
                table_name, field_name = ref.split(".", 1)
            else:
                table_name, field_name = "", ref
            fields.add(ref.lower())
            out.append(f"_F({table_name.strip()!r}, {field_name.strip()!r})")
            i = j + 1
            continue
        if ch == ":":
            match = _IDENT.match(text, i + 1)
            if not match:
                raise ExpressionError(f"Variabile non valida dopo ':' in: {text}")
            name = match.group(0)
            variables.add(name.lower())
            out.append(f"_V({name!r})")
            i = match.end()
            continue
        if ch == ".":
            match = _DOT_KEYWORD.match(text, i)
            if match:
                out.append(_DOT_MAP[match.group(1).upper()])
                i = match.end()
                continue
            out.append(ch)
            i += 1
            continue
        two = text[i : i + 2]
        if two in ("<=", ">=", "!=", "=="):
            out.append(two)
            i += 2
            continue
        if two == "<>":
            out.append("!=")
            i += 2
            continue
        if ch == "=":
            out.append("==")
            i += 1
            continue
        if ch == "&":
            out.append(" + ")
            i += 1
            continue
        if ch.isdigit() or (ch == "." and i + 1 < n and text[i + 1].isdigit()):
            j = i
            while j < n and (text[j].isdigit() or text[j] == "."):
                j += 1
            out.append(text[i:j])
            i = j
            continue
        if ch.isalpha() or ch == "_":
            match = _IDENT.match(text, i)
            assert match is not None
            word = match.group(0)
            low = word.lower()
            if low in ("and", "or", "not"):
                out.append(f" {low} ")
            elif low == "true":
                out.append(" True ")
            elif low == "false":
                out.append(" False ")
            elif low in ("null", "none"):
                out.append(" None ")
            else:
                out.append(word)
            i = match.end()
            continue
        out.append(ch)
        i += 1
    return "".join(out), fields, variables


# --------------------------------------------------------------------------- #
# Funzioni disponibili nelle espressioni
# --------------------------------------------------------------------------- #


def _s(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _n(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(str(value).replace(",", "."))


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _s(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[: len(fmt) + 4].strip(), fmt).date()
        except ValueError:
            continue
    raise ExpressionError(f"Data non valida: {value!r}")


def _f_upper(value: Any) -> str:
    return _s(value).upper()


def _f_lower(value: Any) -> str:
    return _s(value).lower()


def _f_proper(value: Any) -> str:
    return _s(value).title()


def _f_trim(value: Any) -> str:
    return _s(value).strip()


def _f_ltrim(value: Any) -> str:
    return _s(value).lstrip()


def _f_rtrim(value: Any) -> str:
    return _s(value).rstrip()


def _f_len(value: Any) -> int:
    return len(_s(value))


def _f_left(value: Any, count: Any) -> str:
    return _s(value)[: int(_n(count))]


def _f_right(value: Any, count: Any) -> str:
    count_i = int(_n(count))
    if count_i <= 0:
        return ""
    return _s(value)[-count_i:]


def _f_substr(value: Any, start: Any, length: Any = None) -> str:
    text = _s(value)
    start_i = int(_n(start)) - 1
    if start_i < 0:
        start_i = 0
    if length is None:
        return text[start_i:]
    return text[start_i : start_i + int(_n(length))]


def _f_replace(value: Any, old: Any, new: Any) -> str:
    return _s(value).replace(_s(old), _s(new))


def _f_instr(haystack: Any, needle: Any) -> int:
    return _s(haystack).find(_s(needle)) + 1


def _f_str(value: Any, length: Any = 10, decimals: Any = 0) -> str:
    number = _n(value)
    if decimals:
        return f"{number:.{int(_n(decimals))}f}".rjust(int(_n(length)))
    return str(int(number)).rjust(int(_n(length)))


def _f_val(value: Any) -> float:
    try:
        return _n(value)
    except ValueError:
        return 0.0


def _f_round(value: Any, decimals: Any = 0) -> float:
    return round(_n(value), int(_n(decimals)))


def _f_mod(a: Any, b: Any) -> float:
    divisor = _n(b)
    if divisor == 0:
        raise ExpressionError("Divisione per zero in MOD()")
    return _n(a) % divisor


def _f_today() -> date:
    return date.today()


def _f_now() -> datetime:
    return datetime.now()


def _f_date(year: Any, month: Any, day: Any) -> date:
    return date(int(_n(year)), int(_n(month)), int(_n(day)))


def _f_year(value: Any) -> int:
    return _as_date(value).year


def _f_month(value: Any) -> int:
    return _as_date(value).month


def _f_day(value: Any) -> int:
    return _as_date(value).day


def _f_dateadd(value: Any, days: Any) -> date:
    return _as_date(value) + timedelta(days=int(_n(days)))


def _f_iif(condition: Any, if_true: Any, if_false: Any) -> Any:
    return if_true if condition else if_false


def _f_isnull(value: Any) -> bool:
    return value is None or value == ""


def _f_nvl(value: Any, fallback: Any) -> Any:
    return fallback if value is None or value == "" else value


def _f_empty(value: Any) -> bool:
    return value is None or value == "" or value == 0


def _f_concat(*values: Any) -> str:
    return "".join(_s(v) for v in values)


FUNCTIONS: dict[str, Callable[..., Any]] = {
    "UPPER": _f_upper,
    "MAIUSC": _f_upper,
    "LOWER": _f_lower,
    "MINUSC": _f_lower,
    "PROPER": _f_proper,
    "TRIM": _f_trim,
    "ALLTRIM": _f_trim,
    "LTRIM": _f_ltrim,
    "RTRIM": _f_rtrim,
    "LEN": _f_len,
    "LUNG": _f_len,
    "LEFT": _f_left,
    "RIGHT": _f_right,
    "SUBSTR": _f_substr,
    "MID": _f_substr,
    "REPLACE": _f_replace,
    "INSTR": _f_instr,
    "STR": _f_str,
    "VAL": _f_val,
    "INT": lambda v: int(_n(v)),
    "ABS": lambda v: abs(_n(v)),
    "ROUND": _f_round,
    "MOD": _f_mod,
    "MIN": lambda *vs: min(_n(v) for v in vs),
    "MAX": lambda *vs: max(_n(v) for v in vs),
    "TODAY": _f_today,
    "DATE": _f_today,
    "NOW": _f_now,
    "YEAR": _f_year,
    "MONTH": _f_month,
    "DAY": _f_day,
    "DATEADD": _f_dateadd,
    "IIF": _f_iif,
    "IF": _f_iif,
    "ISNULL": _f_isnull,
    "NVL": _f_nvl,
    "EMPTY": _f_empty,
    "CONCAT": _f_concat,
    "SQR": lambda v: _n(v) ** 0.5,
    "SQRT": lambda v: _n(v) ** 0.5,
}

_ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.IfExp,
    ast.List,
    ast.Tuple,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.keyword,
)

_SAFE_NAMES = {"_F", "_V", "True", "False", "None", "and", "or", "not"}


class _Validator(ast.NodeVisitor):
    def __init__(self, function_names: set[str]) -> None:
        self.function_names = function_names

    def generic_visit(self, node: ast.AST) -> None:  # noqa: D102
        if not isinstance(node, _ALLOWED_NODES):
            raise ExpressionError(f"Costrutto non consentito: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: D102
        allowed_calls = self.function_names | {"_F", "_V"}
        if not isinstance(node.func, ast.Name) or node.func.id not in allowed_calls:
            raise ExpressionError("Solo le funzioni dBX sono ammesse nelle espressioni")
        if node.keywords:
            raise ExpressionError("Argomenti con nome non supportati")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:  # noqa: D102
        if node.id not in self.function_names and node.id not in _SAFE_NAMES:
            raise ExpressionError(f"Nome non consentito: {node.id}")


class Expression:
    """Espressione compilata, riutilizzabile su molti record."""

    def __init__(self, source: str | None) -> None:
        self.source = "" if source is None else str(source).strip()
        self.fields: set[str] = set()
        self.variables: set[str] = set()
        self._code: Any = None
        if self.source:
            python_source, fields, variables = rewrite(self.source)
            self.fields = fields
            self.variables = variables
            try:
                # La parentesi neutralizza spazi iniziali prodotti dai token .T./.AND.
                tree = ast.parse("(" + python_source.strip() + ")", mode="eval")
            except SyntaxError as exc:
                raise ExpressionError(f"Espressione non valida: {self.source}") from exc
            _Validator(set(FUNCTIONS)).visit(tree)
            self._code = compile(tree, "<dbx-expression>", "eval")

    def __bool__(self) -> bool:
        return bool(self.source)

    def __repr__(self) -> str:  # pragma: no cover - diagnostica
        return f"Expression({self.source!r})"

    def evaluate(
        self,
        record: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        table: str | None = None,
    ) -> Any:
        if not self.source:
            return None
        values = record or {}
        vars_ = variables or {}
        lowered = {str(k).lower(): v for k, v in values.items()}

        def field(table_name: str, field_name: str) -> Any:
            candidates: list[str] = []
            if table_name:
                candidates.append(f"{table_name}.{field_name}")
            candidates.append(field_name)
            if table and not table_name:
                candidates.insert(0, f"{table}.{field_name}")
            for key in candidates:
                if key in values:
                    return values[key]
            for key in candidates:
                if key.lower() in lowered:
                    return lowered[key.lower()]
            return None

        def variable(name: str) -> Any:
            if name in vars_:
                return vars_[name]
            low = {str(k).lower(): v for k, v in vars_.items()}
            if name.lower() in low:
                return low[name.lower()]
            raise ExpressionError(f"Variabile non definita: :{name}")

        scope: dict[str, Any] = {"_F": field, "_V": variable}
        for name, func in FUNCTIONS.items():
            scope[name] = func
            scope[name.lower()] = func
        try:
            return eval(self._code, {"__builtins__": {}}, scope)  # noqa: S307 - AST validato
        except ExpressionError:
            raise
        except ZeroDivisionError as exc:
            raise ExpressionError(f"Divisione per zero in: {self.source}") from exc
        except Exception as exc:  # pragma: no cover - messaggi utente
            raise ExpressionError(f"Errore nella espressione {self.source!r}: {exc}") from exc

    def truth(
        self,
        record: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        table: str | None = None,
    ) -> bool:
        return bool(self.evaluate(record, variables, table))


def evaluate(
    source: str,
    record: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    table: str | None = None,
) -> Any:
    """Scorciatoia: compila e valuta una singola espressione."""
    return Expression(source).evaluate(record, variables, table)
