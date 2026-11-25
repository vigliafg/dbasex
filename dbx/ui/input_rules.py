"""Regole di forma dell'input (riesporta il modulo puro di ``dbx.core``).

La logica vive in ``dbx.core.input_rules`` perché serve sia agli editor sia
alla manutenzione dei dati (``re_evaluate``). Questo modulo mantiene il punto
di import storico usato dalla UI.
"""

from ..core.input_rules import CASE_MODES, MASK_CHARS, InputRules

__all__ = ["CASE_MODES", "MASK_CHARS", "InputRules"]
