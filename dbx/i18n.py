"""Stringhe dell'interfaccia (A2).

Tutte le etichette principali passano da `tr`, così l'estrazione per una futura
traduzione non richiede di toccare i widget. Il dizionario è in italiano: per
altre lingue basta aggiungere una tabella e chiamare `set_language`.
"""

from __future__ import annotations

_IT: dict[str, str] = {}
_TABLES: dict[str, dict[str, str]] = {"it": _IT}
_current = "it"


def set_language(code: str) -> None:
    global _current
    if code in _TABLES:
        _current = code


def tr(text: str, **kwargs: object) -> str:
    table = _TABLES.get(_current, {})
    result = table.get(text, text)
    return result.format(**kwargs) if kwargs else result
