"""Evidenziazione degli errori di validazione nella UI (token del tema)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QWidget

from . import design


def error_brush() -> QColor:
    """Sfondo di errore derivato dal token del tema (mai un colore fisso)."""
    color = QColor(design.palette().get("error", "#be123c"))
    color.setAlpha(46)
    return color


def mark_error(widget: QWidget | QTableWidgetItem, message: str = "") -> None:
    """Evidenzia un widget o una cella con il colore d'errore del tema."""
    if isinstance(widget, QTableWidgetItem):
        widget.setBackground(error_brush())
        if message:
            widget.setToolTip(message)
        return
    widget.setProperty("state", "error")
    if message:
        widget.setToolTip(message)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


def clear_error(widget: QWidget | QTableWidgetItem) -> None:
    """Rimuove l'evidenziazione di errore."""
    if isinstance(widget, QTableWidgetItem):
        widget.setBackground(QColor(Qt.GlobalColor.transparent))
        return
    widget.setProperty("state", "")
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


__all__ = ["error_brush", "mark_error", "clear_error"]
