"""Integrazione Qt delle regole di input: validatore di maschera e maiuscole."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QValidator
from PyQt6.QtWidgets import QLineEdit, QWidget

from .input_rules import InputRules


class MaskValidator(QValidator):
    """Accetta solo i caratteri previsti dalla maschera, anche parziale."""

    def __init__(self, mask: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mask = str(mask or "")

    def validate(self, text: str, pos: int):  # noqa: N802 - API Qt
        if not self.mask:
            return QValidator.State.Acceptable, text, pos
        if len(text) > len(self.mask):
            return QValidator.State.Invalid, text, pos
        for index, char in enumerate(text):
            if not InputRules.accepts(self.mask[index], char):
                return QValidator.State.Invalid, text, pos
        state = (
            QValidator.State.Acceptable
            if len(text) == len(self.mask)
            else QValidator.State.Intermediate
        )
        return state, text, pos


def attach_input_rules(editor: QLineEdit, field, on_complete=None) -> None:
    """Applica maschera e maiuscole a una ``QLineEdit``.

    ``on_complete`` viene chiamato una sola volta quando il testo raggiunge la
    lunghezza della maschera o del campo (auto-advance).
    """
    if field is None:
        return
    mask = str(getattr(field, "mask", "") or "")
    if mask:
        editor.setValidator(MaskValidator(mask, editor))
        if not editor.placeholderText():
            editor.setPlaceholderText(InputRules.placeholder(mask))
    mode = str(getattr(field, "case_mode", "") or "")
    if not mask and not mode:
        return
    editor.setProperty("_input_complete", False)
    # Timer figlio dell'editor: se l'editor viene distrutto, il timer sparisce
    # con lui e il callback di auto-advance non tocca oggetti Qt già liberati.
    timer = QTimer(editor)
    timer.setSingleShot(True)
    timer.setInterval(0)
    if on_complete is not None:
        timer.timeout.connect(on_complete)

    def _changed(text: str) -> None:
        if mode:
            shaped = InputRules.apply_case(text, mode)
            if shaped != text:
                cursor = editor.cursorPosition()
                editor.blockSignals(True)
                editor.setText(shaped)
                editor.setCursorPosition(min(cursor, len(shaped)))
                editor.blockSignals(False)
        complete = InputRules.is_complete(field, editor.text())
        if complete and not editor.property("_input_complete"):
            editor.setProperty("_input_complete", True)
            if on_complete is not None:
                timer.start()
        elif not complete:
            editor.setProperty("_input_complete", False)

    editor.textChanged.connect(_changed)


__all__ = ["MaskValidator", "attach_input_rules"]
