"""Icone disegnate a runtime e pulsanti con icona (H5).

Le icone sono disegnate con QPainter su una griglia 24×24, quindi non servono
file immagine né dipendenze esterne e il contrasto si adatta al tema.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap, QPolygonF
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QPushButton, QWidget

from . import design

ICON_SIZE = QSize(18, 18)

BUTTON_ACTION_ICONS = {
    "new": "nuovo",
    "save": "salva",
    "delete": "elimina",
    "first": "primo",
    "previous": "precedente",
    "next": "successivo",
    "last": "ultimo",
    "close": "chiudi",
}

_theme = design.DEFAULT_THEME
_cache: dict[tuple[str, str], QIcon] = {}


# --------------------------------------------------------------------- glifi
def _poly(painter: QPainter, *points: tuple[float, float]) -> None:
    painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in points]))


def _triangle(painter: QPainter, *points: tuple[float, float]) -> None:
    painter.setBrush(painter.pen().color())
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _nuovo(painter: QPainter) -> None:
    painter.drawLine(QPointF(12, 5), QPointF(12, 19))
    painter.drawLine(QPointF(5, 12), QPointF(19, 12))


def _apri(painter: QPainter) -> None:
    _poly(painter, (3, 19), (3, 6), (9, 6), (11, 9), (21, 9), (21, 19), (3, 19))


def _salva(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 4, 16, 16))
    painter.drawRect(QRectF(8.5, 4.5, 7, 5))
    painter.drawRect(QRectF(7, 13, 10, 6.5))


def _esporta(painter: QPainter) -> None:
    painter.drawLine(QPointF(12, 4), QPointF(12, 15))
    _poly(painter, (8, 11), (12, 15), (16, 11))
    painter.drawLine(QPointF(5, 19), QPointF(19, 19))


def _annulla(painter: QPainter) -> None:
    painter.drawLine(QPointF(7, 7), QPointF(17, 17))
    painter.drawLine(QPointF(17, 7), QPointF(7, 17))


def _ok(painter: QPainter) -> None:
    _poly(painter, (5, 13), (10, 18), (19, 6))


def _zoom_in(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(4, 4, 12, 12))
    painter.drawLine(QPointF(15, 15), QPointF(20, 20))
    painter.drawLine(QPointF(10, 6.5), QPointF(10, 13.5))
    painter.drawLine(QPointF(6.5, 10), QPointF(13.5, 10))


def _zoom_out(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(4, 4, 12, 12))
    painter.drawLine(QPointF(15, 15), QPointF(20, 20))
    painter.drawLine(QPointF(6.5, 10), QPointF(13.5, 10))


def _puntatore(painter: QPainter) -> None:
    _poly(painter, (6, 4), (18, 12), (12, 13), (15, 19), (12.5, 20.5), (9.5, 14.5), (5.5, 18), (6, 4))


def _elimina(painter: QPainter) -> None:
    painter.drawLine(QPointF(5, 7), QPointF(19, 7))
    painter.drawRect(QRectF(10, 4, 4, 3))
    _poly(painter, (7, 7), (8, 20), (16, 20), (17, 7))


def _su(painter: QPainter) -> None:
    painter.drawLine(QPointF(12, 20), QPointF(12, 5))
    _poly(painter, (6, 11), (12, 5), (18, 11))


def _giu(painter: QPainter) -> None:
    painter.drawLine(QPointF(12, 4), QPointF(12, 19))
    _poly(painter, (6, 13), (12, 19), (18, 13))


def _primo(painter: QPainter) -> None:
    painter.drawLine(QPointF(6, 5), QPointF(6, 19))
    _triangle(painter, (18, 5), (9, 12), (18, 19))


def _ultimo(painter: QPainter) -> None:
    painter.drawLine(QPointF(18, 5), QPointF(18, 19))
    _triangle(painter, (6, 5), (15, 12), (6, 19))


def _precedente(painter: QPainter) -> None:
    _triangle(painter, (17, 5), (8, 12), (17, 19))


def _successivo(painter: QPainter) -> None:
    _triangle(painter, (7, 5), (16, 12), (7, 19))


def _aggiorna(painter: QPainter) -> None:
    painter.drawArc(QRectF(5, 5, 14, 14), 45 * 16, 280 * 16)
    _triangle(painter, (15, 2.5), (20, 6), (14.5, 8))


def _anteprima(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(3, 7, 18, 10))
    painter.setBrush(painter.pen().color())
    painter.drawEllipse(QPointF(12, 12), 2.4, 2.4)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _stampa(painter: QPainter) -> None:
    painter.drawRect(QRectF(8, 3.5, 8, 5))
    painter.drawRect(QRectF(4, 8.5, 16, 8))
    painter.drawRect(QRectF(7, 14, 10, 6))


def _tabella(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 5, 16, 14))
    painter.drawLine(QPointF(9.5, 5), QPointF(9.5, 19))
    painter.drawLine(QPointF(14.5, 5), QPointF(14.5, 19))
    painter.drawLine(QPointF(4, 9.7), QPointF(20, 9.7))
    painter.drawLine(QPointF(4, 14.3), QPointF(20, 14.3))


def _form(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 3, 16, 18))
    painter.drawLine(QPointF(4, 9), QPointF(20, 9))
    painter.drawLine(QPointF(7, 13), QPointF(13, 13))
    painter.drawLine(QPointF(7, 17), QPointF(17, 17))


def _report(painter: QPainter) -> None:
    painter.drawRect(QRectF(6, 3, 12, 18))
    painter.drawLine(QPointF(9, 8), QPointF(15, 8))
    painter.drawLine(QPointF(9, 12), QPointF(15, 12))
    painter.drawLine(QPointF(9, 16), QPointF(13, 16))


def _script(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 3, 16, 18))
    _poly(painter, (9, 10), (12, 12.5), (9, 15))
    painter.drawLine(QPointF(13, 15.5), QPointF(16, 15.5))


def _menu(painter: QPainter) -> None:
    for y in (7, 12, 17):
        painter.setBrush(painter.pen().color())
        painter.drawEllipse(QPointF(6, y), 1.3, 1.3)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(10, y), QPointF(19, y))


def _elenco(painter: QPainter) -> None:
    for y in (7, 12, 17):
        painter.drawRect(QRectF(5, y - 1.4, 2.8, 2.8))
        painter.drawLine(QPointF(10, y), QPointF(19, y))


def _impostazioni(painter: QPainter) -> None:
    painter.drawEllipse(QPointF(12, 12), 4.6, 4.6)
    import math

    for step in range(8):
        angle = step * math.pi / 4
        inner = 6.4
        outer = 9.4
        painter.drawLine(
            QPointF(12 + inner * math.cos(angle), 12 + inner * math.sin(angle)),
            QPointF(12 + outer * math.cos(angle), 12 + outer * math.sin(angle)),
        )


def _esegui(painter: QPainter) -> None:
    _triangle(painter, (7, 4), (20, 12), (7, 20))


def _cerca(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(4, 4, 11, 11))
    painter.drawLine(QPointF(14.5, 14.5), QPointF(20, 20))


def _immagine(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 5, 18, 14))
    painter.drawEllipse(QPointF(8, 9.5), 1.6, 1.6)
    _poly(painter, (3, 17.5), (9, 11.5), (13, 15.5), (16, 12.5), (21, 17.5))


def _modifica(painter: QPainter) -> None:
    painter.drawLine(QPointF(6, 18), QPointF(17, 7))
    _poly(painter, (17, 7), (18, 4), (20, 6), (17, 7))
    painter.drawLine(QPointF(4, 20), QPointF(9, 20))


def _testo(painter: QPainter) -> None:
    painter.drawLine(QPointF(5, 7), QPointF(19, 7))
    painter.drawLine(QPointF(5, 12), QPointF(16, 12))
    painter.drawLine(QPointF(5, 17), QPointF(13, 17))


def _somma(painter: QPainter) -> None:
    _poly(painter, (17, 5), (7, 5), (14, 12), (7, 19), (17, 19))


def _linea(painter: QPainter) -> None:
    painter.drawLine(QPointF(5, 19), QPointF(19, 5))


def _riquadro(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 6, 16, 12))


def _pulsante(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3, 7, 18, 10), 3, 3)
    painter.drawLine(QPointF(8, 12), QPointF(16, 12))


def _campo(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 7, 18, 10))
    painter.drawLine(QPointF(7, 9), QPointF(7, 15))


def _data(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 5, 16, 15))
    painter.drawLine(QPointF(4, 10), QPointF(20, 10))
    painter.drawLine(QPointF(8, 3), QPointF(8, 7))
    painter.drawLine(QPointF(16, 3), QPointF(16, 7))
    for x in (8, 12, 16):
        painter.drawLine(QPointF(x - 1, 14), QPointF(x + 1, 14))


def _aiuto(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(4, 4, 16, 16))
    painter.drawLine(QPointF(12, 11), QPointF(12, 16))
    painter.setBrush(painter.pen().color())
    painter.drawEllipse(QPointF(12, 7.6), 0.9, 0.9)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def _chiudi(painter: QPainter) -> None:
    painter.drawRect(QRectF(4, 4, 10, 16))
    painter.drawLine(QPointF(13, 12), QPointF(21, 12))
    _poly(painter, (18, 9), (21, 12), (18, 15))


def _taglia(painter: QPainter) -> None:
    painter.drawEllipse(QRectF(3, 14, 6, 6))
    painter.drawEllipse(QRectF(15, 14, 6, 6))
    painter.drawLine(QPointF(8, 15), QPointF(17, 4))
    painter.drawLine(QPointF(16, 15), QPointF(7, 4))


def _copia(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 7, 12, 14))
    painter.drawRect(QRectF(9, 3, 12, 14))


def _incolla(painter: QPainter) -> None:
    painter.drawRect(QRectF(5, 5, 14, 16))
    painter.drawRect(QRectF(9, 3, 6, 4))
    painter.drawLine(QPointF(8, 12), QPointF(16, 12))
    painter.drawLine(QPointF(8, 16), QPointF(14, 16))


def _undo(painter: QPainter) -> None:
    _poly(painter, (18, 17), (18, 9), (8, 9))
    _triangle(painter, (3, 9), (9, 5), (9, 13))


def _redo(painter: QPainter) -> None:
    _poly(painter, (6, 17), (6, 9), (16, 9))
    _triangle(painter, (21, 9), (15, 5), (15, 13))


def _allinea(painter: QPainter) -> None:
    painter.drawLine(QPointF(4, 4), QPointF(4, 20))
    painter.drawLine(QPointF(7, 7), QPointF(20, 7))
    painter.drawLine(QPointF(7, 12), QPointF(16, 12))
    painter.drawLine(QPointF(7, 17), QPointF(19, 17))


def _distribuisci(painter: QPainter) -> None:
    painter.drawLine(QPointF(3, 5), QPointF(21, 5))
    painter.drawRect(QRectF(3, 9, 4, 10))
    painter.drawRect(QRectF(10, 9, 4, 10))
    painter.drawRect(QRectF(17, 9, 4, 10))


def _cascata(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 4, 13, 11))
    painter.drawRect(QRectF(8, 9, 13, 11))


def _affianca(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 4, 8, 16))
    painter.drawRect(QRectF(13, 4, 8, 16))


def _finestra(painter: QPainter) -> None:
    painter.drawRect(QRectF(3, 5, 18, 14))
    painter.drawLine(QPointF(3, 10), QPointF(21, 10))
    painter.setBrush(painter.pen().color())
    painter.drawRect(QRectF(18, 6.8, 2, 1.4))
    painter.setBrush(Qt.BrushStyle.NoBrush)


_GLYPHS: dict[str, Callable[[QPainter], None]] = {
    "nuovo": _nuovo,
    "zoom_in": _zoom_in,
    "zoom_out": _zoom_out,
    "puntatore": _puntatore,
    "apri": _apri,
    "salva": _salva,
    "esporta": _esporta,
    "annulla": _annulla,
    "ok": _ok,
    "elimina": _elimina,
    "su": _su,
    "giu": _giu,
    "primo": _primo,
    "ultimo": _ultimo,
    "precedente": _precedente,
    "successivo": _successivo,
    "aggiorna": _aggiorna,
    "anteprima": _anteprima,
    "stampa": _stampa,
    "tabella": _tabella,
    "form": _form,
    "report": _report,
    "script": _script,
    "menu": _menu,
    "elenco": _elenco,
    "impostazioni": _impostazioni,
    "esegui": _esegui,
    "cerca": _cerca,
    "immagine": _immagine,
    "modifica": _modifica,
    "testo": _testo,
    "somma": _somma,
    "linea": _linea,
    "riquadro": _riquadro,
    "pulsante": _pulsante,
    "campo": _campo,
    "data": _data,
    "aiuto": _aiuto,
    "chiudi": _chiudi,
    "taglia": _taglia,
    "copia": _copia,
    "incolla": _incolla,
    "undo": _undo,
    "redo": _redo,
    "allinea": _allinea,
    "distribuisci": _distribuisci,
    "cascata": _cascata,
    "affianca": _affianca,
    "finestra": _finestra,
}


# ------------------------------------------------------------------- API
def set_theme(name: str | None = None) -> None:
    """Imposta il tema corrente delle icone."""
    global _theme
    resolved = design.normalize_theme(name)
    if _theme != resolved:
        _theme = resolved
        _cache.clear()


def set_dark(dark: bool) -> None:
    """Compatibilità: seleziona il tema scuro o il default."""
    set_theme("dark" if dark else design.DEFAULT_THEME)


def _color() -> str:
    return design.icon_color(_theme)


def _pixmap(glyph: Callable[[QPainter], None], size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / 24.0, size / 24.0)
    pen = painter.pen()
    pen.setColor(QColor(_color()))
    pen.setWidthF(1.7)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    glyph(painter)
    painter.end()
    return pixmap


def icon(name: str) -> QIcon:
    """Icona per nome; nomi sconosciuti ricadono sul simbolo «nuovo»."""
    if QApplication.instance() is None:  # pragma: no cover - senza GUI
        return QIcon()
    key = (name, _theme)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    glyph = _GLYPHS.get(name) or _GLYPHS["nuovo"]
    result = QIcon()
    for size in (16, 20, 24, 32, 48):
        result.addPixmap(_pixmap(glyph, size))
    _cache[key] = result
    return result


def make_button(
    text: str,
    name: str,
    slot=None,
    parent: QWidget | None = None,
    tooltip: str | None = None,
    checkable: bool = False,
) -> QPushButton:
    """Pulsante con icona e nome, opzionalmente collegato a uno slot."""
    button = QPushButton(text, parent)
    button.setIcon(icon(name))
    button.setIconSize(ICON_SIZE)
    button.setProperty("dbx_icon", name)
    button.setCheckable(checkable)
    button.setAutoDefault(False)
    if tooltip:
        button.setToolTip(tooltip)
    if slot is not None:
        button.clicked.connect(slot)
    return button


def make_action(
    text: str,
    name: str | None,
    parent: QWidget,
    shortcut=None,
    tooltip: str | None = None,
    checkable: bool = False,
) -> QAction:
    """QAction con icona opzionale e nome, per menu e barre degli strumenti."""
    action = QAction(text, parent)
    if name:
        action.setIcon(icon(name))
        action.setProperty("dbx_icon", name)
    action.setCheckable(checkable)
    if shortcut:
        action.setShortcut(shortcut)
    action.setToolTip(tooltip or text)
    action.setStatusTip(tooltip or text)
    return action


def dialog_buttons(accept_text: str = "Salva", reject_text: str = "Annulla") -> QDialogButtonBox:
    """Barra Salva/Annulla con icone, in italiano."""
    box = QDialogButtonBox()
    accept = box.addButton(accept_text, QDialogButtonBox.ButtonRole.AcceptRole)
    accept.setIcon(icon("ok"))
    accept.setIconSize(ICON_SIZE)
    accept.setProperty("dbx_icon", "ok")
    accept.setDefault(True)
    reject = box.addButton(reject_text, QDialogButtonBox.ButtonRole.RejectRole)
    reject.setIcon(icon("annulla"))
    reject.setIconSize(ICON_SIZE)
    reject.setProperty("dbx_icon", "annulla")
    return box


def style_button_box(box: QDialogButtonBox) -> QDialogButtonBox:
    """Aggiunge le icone ai pulsanti standard di una QDialogButtonBox."""
    icons_by_role = {
        QDialogButtonBox.ButtonRole.AcceptRole: "ok",
        QDialogButtonBox.ButtonRole.YesRole: "ok",
        QDialogButtonBox.ButtonRole.ApplyRole: "ok",
        QDialogButtonBox.ButtonRole.RejectRole: "annulla",
        QDialogButtonBox.ButtonRole.NoRole: "annulla",
        QDialogButtonBox.ButtonRole.ResetRole: "aggiorna",
        QDialogButtonBox.ButtonRole.HelpRole: "aiuto",
    }
    for button in box.buttons():
        name = icons_by_role.get(box.buttonRole(button))
        if name:
            button.setIcon(icon(name))
            button.setIconSize(ICON_SIZE)
            button.setProperty("dbx_icon", name)
    return box


def refresh_all(app: QApplication) -> None:
    """Ridisegna icone di pulsanti e azioni dopo un cambio di tema."""
    _cache.clear()
    for widget in app.allWidgets():
        name = widget.property("dbx_icon")
        if isinstance(name, str) and name and isinstance(widget, QPushButton):
            widget.setIcon(icon(name))
        for action in widget.findChildren(QAction):
            action_name = action.property("dbx_icon")
            if isinstance(action_name, str) and action_name:
                action.setIcon(icon(action_name))
