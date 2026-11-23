"""Adattamento delle finestre dBX allo spazio disponibile sullo schermo.

Le finestre nascono con dimensioni pensate per un desktop ampio; su portatili
e schermi piccoli vanno ridotte e riposizionate senza superare l'area utile.
Le dimensioni qui sono in pixel logici Qt, quindi il calcolo resta corretto
anche con il ridimensionamento HiDPI.
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QDialog, QWidget

DEFAULT_MARGIN = 12
MIN_WINDOW_WIDTH = 360
MIN_WINDOW_HEIGHT = 240
_ORIGINAL_EXEC = None


def available_geometry(widget: QWidget | None = None) -> QRect:
    """Area utile dello schermo su cui si trova (o si aprirà) la finestra."""
    screen = widget.screen() if widget is not None else None
    if screen is None:
        screen = QGuiApplication.primaryScreen()
    if screen is None:  # pragma: no cover - ambiente senza schermo
        return QRect(0, 0, 1024, 768)
    return screen.availableGeometry()


def fit_to_available(
    widget: QWidget,
    *,
    margin: int = DEFAULT_MARGIN,
    move: bool = True,
) -> QSize:
    """Riduce ``widget`` entro lo schermo e lo riporta dentro l'area utile.

    Non ingrandisce mai una finestra più piccola del massimo disponibile.
    Restituisce la dimensione effettiva richiesta.
    """
    area = available_geometry(widget)
    max_width = max(MIN_WINDOW_WIDTH, area.width() - margin * 2)
    max_height = max(MIN_WINDOW_HEIGHT, area.height() - margin * 2)
    current = widget.size()
    target = QSize(min(current.width(), max_width), min(current.height(), max_height))
    if target != current:
        widget.resize(target)
    if move:
        frame = widget.frameGeometry()
        if not area.contains(frame):
            left = area.left() + margin
            top = area.top() + margin
            right = area.right() - margin - frame.width() + 1
            bottom = area.bottom() - margin - frame.height() + 1
            x = min(max(frame.left(), left), max(left, right))
            y = min(max(frame.top(), top), max(top, bottom))
            widget.move(x, y)
    return target


def install_dialog_fit() -> None:
    """Adatta automaticamente ogni ``QDialog`` aperto in modo modale.

    L'aggancio avviene prima di ``exec()``, quando il dialogo non è ancora
    visibile: è il punto più sicuro per cambiarne la geometria. Un filtro
    globale sugli eventi ``Show`` è stato scartato perché interferiva con la
    distruzione degli oggetti Qt a fine sessione.
    """
    global _ORIGINAL_EXEC
    if _ORIGINAL_EXEC is not None:
        return
    original = QDialog.exec

    def fit_exec(self: QDialog) -> int:
        if not self.isMaximized() and not self.isFullScreen():
            fit_to_available(self)
        return original(self)

    QDialog.exec = fit_exec  # type: ignore[method-assign]
    _ORIGINAL_EXEC = original


__all__ = [
    "DEFAULT_MARGIN",
    "available_geometry",
    "fit_to_available",
    "install_dialog_fit",
]
