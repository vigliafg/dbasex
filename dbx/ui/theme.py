"""Applicazione dei temi dBX.

Il QSS è generato dai token di :mod:`dbx.ui.design`; qui resta solo il
bootstrap Qt e il refresh delle icone.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from . import design, icons


def apply_theme(app: QApplication, name: str | None = None) -> str:
    """Applica il tema richiesto e restituisce il nome normalizzato."""
    resolved = design.normalize_theme(name)
    app.setStyleSheet(design.qss(resolved))
    icons.set_theme(resolved)
    icons.refresh_all(app)
    return resolved
