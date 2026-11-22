"""Applicazione dei temi dBX.

Il QSS è generato dai token di :mod:`dbx.ui.design`; qui resta solo il
bootstrap Qt, la palette di sistema e il refresh delle icone.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from . import design, icons

_PALETTE_ROLES = {
    QPalette.ColorRole.Window: "window_bg",
    QPalette.ColorRole.WindowText: "text",
    QPalette.ColorRole.Base: "input_bg",
    QPalette.ColorRole.AlternateBase: "alternate_bg",
    QPalette.ColorRole.Text: "text",
    QPalette.ColorRole.Button: "button_bg",
    QPalette.ColorRole.ButtonText: "text",
    QPalette.ColorRole.Highlight: "selection_bg",
    QPalette.ColorRole.HighlightedText: "selection_text",
    QPalette.ColorRole.ToolTipBase: "tooltip_bg",
    QPalette.ColorRole.ToolTipText: "tooltip_text",
    QPalette.ColorRole.BrightText: "selection_text",
    QPalette.ColorRole.PlaceholderText: "disabled",
}


def apply_theme(app: QApplication, name: str | None = None) -> str:
    """Applica il tema richiesto e restituisce il nome normalizzato."""
    resolved = design.normalize_theme(name)
    app.setStyleSheet(design.qss(resolved))
    palette = design.palette(resolved)
    qt_palette = app.palette()
    for role, key in _PALETTE_ROLES.items():
        qt_palette.setColor(role, QColor(palette[key]))
    app.setPalette(qt_palette)
    icons.set_theme(resolved)
    icons.refresh_all(app)
    return resolved
