"""Host dei documenti MDI di dBX.

Il desktop usa un :class:`QMdiArea`: ogni documento è una
:class:`QMdiSubWindow`. I widget nativi vengono ospitati direttamente; i
``QDialog`` non ancora convertiti passano da :class:`DialogEditor`, un adapter
sottile che li rende figli di una sottofinestra.

L'interfaccia riconosciuta dagli editor è volutamente minima:

``windowTitle()``
    titolo della sottofinestra;
``is_dirty()`` oppure ``dirty``
    eventuali modifiche non salvate, usate alla chiusura;
``save()``, ``print_pages()``, ``set_zoom()``, ``align_selection()``
    metodi contestuali invocati dai comandi globali quando presenti.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QEvent, QObject, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QMdiArea,
    QMdiSubWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import icons

MIN_EDITOR_SIZE = QSize(480, 320)


class EditorSubWindow(QMdiSubWindow):
    """Sottofinestra MDI con una dimensione preferita stabile."""

    def __init__(self, preferred: QSize, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preferred = QSize(preferred)

    def sizeHint(self) -> QSize:  # noqa: N802 - API Qt
        if self._preferred.isValid():
            return self._preferred
        return super().sizeHint()


class DialogEditor(QWidget):
    """Adapter che ospita un ``QDialog`` legacy dentro una sottofinestra MDI."""

    finished = pyqtSignal()

    def __init__(self, dialog: QDialog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dialog = dialog
        self._preferred = QSize()
        self._notified = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Il dialogo conserva la sua dimensione minima, ma se la sottofinestra
        # è più piccola compaiono le barre di scorrimento: la shell non viene
        # forzata a crescere oltre lo schermo.
        self.scroll = QScrollArea(self)
        self.scroll.setObjectName("dialog_editor_scroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        self.scroll.setWidget(dialog)
        layout.addWidget(self.scroll)
        dialog.accepted.connect(self._notify_finished)
        dialog.rejected.connect(self._notify_finished)
        dialog.windowTitleChanged.connect(self.setWindowTitle)
        self.setWindowTitle(dialog.windowTitle())

    def set_preferred_size(self, size: QSize) -> None:
        """Dimensione richiesta alla sottofinestra MDI (usata come sizeHint)."""
        self._preferred = QSize(size)
        self.updateGeometry()

    def sizeHint(self) -> QSize:  # noqa: N802 - API Qt
        if self._preferred.isValid():
            return self._preferred
        return super().sizeHint()

    def _notify_finished(self) -> None:
        if self._notified:
            return
        self._notified = True
        self.finished.emit()

    def editor_dirty(self) -> bool:
        return editor_dirty(self.dialog)


def editor_widget(widget: QWidget | None) -> QWidget | None:
    """Restituisce il contenuto reale di un editor, scartando l'adapter."""
    if isinstance(widget, DialogEditor):
        return widget.dialog
    return widget


def editor_dirty(widget: QWidget | None) -> bool:
    """True se l'editor dichiara modifiche non salvate."""
    target = editor_widget(widget)
    if target is None:
        return False
    for name in ("is_dirty", "has_unsaved_changes"):
        checker = getattr(target, name, None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:  # pragma: no cover - difensivo
                return False
    value: Any = getattr(target, "dirty", False)
    if callable(value):
        try:
            return bool(value())
        except Exception:  # pragma: no cover - difensivo
            return False
    return bool(value)


def editor_title(widget: QWidget | None, fallback: str = "") -> str:
    target = editor_widget(widget)
    if target is None:
        return fallback
    return target.windowTitle() or fallback


class EditorHost(QObject):
    """Gestisce l'apertura, l'attivazione e la chiusura dei documenti MDI."""

    activated = pyqtSignal(object)
    closed = pyqtSignal()
    opened = pyqtSignal(object)

    def __init__(self, area: QMdiArea, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.area = area
        self.area.subWindowActivated.connect(self._on_activated)

    # ------------------------------------------------------------------ lettura
    def windows(self) -> list[QMdiSubWindow]:
        return [sub for sub in self.area.subWindowList() if sub.widget() is not None]

    def find(self, key: str) -> QMdiSubWindow | None:
        for sub in self.windows():
            if sub.property("dbx_key") == key:
                return sub
        return None

    def current(self) -> QMdiSubWindow | None:
        return self.area.activeSubWindow()

    def current_editor(self) -> QWidget | None:
        sub = self.current()
        if sub is None:
            return None
        return editor_widget(sub.widget())

    # ------------------------------------------------------------------ apertura
    def open(
        self,
        key: str,
        title: str,
        widget: QWidget,
        *,
        icon: QIcon | None = None,
        size: QSize | None = None,
    ) -> QMdiSubWindow:
        """Apre ``widget`` in una sottofinestra, oppure attiva quella esistente."""
        existing = self.find(key)
        if existing is not None:
            self.area.setActiveSubWindow(existing)
            return existing
        widget.setProperty("dbx_key", key)
        proposed = (size or widget.size()).expandedTo(MIN_EDITOR_SIZE)
        available = self.area.viewport().size()
        if available.isValid():
            proposed.setWidth(
                min(proposed.width(), max(MIN_EDITOR_SIZE.width(), available.width() - 24))
            )
            proposed.setHeight(
                min(proposed.height(), max(MIN_EDITOR_SIZE.height(), available.height() - 24))
            )
        setter = getattr(widget, "set_preferred_size", None)
        if callable(setter):
            setter(proposed)
        sub = EditorSubWindow(proposed, self.area)
        sub.setObjectName("editor_subwindow")
        sub.setWidget(widget)
        sub.setProperty("dbx_key", key)
        sub.setWindowTitle(title)
        sub.setWindowIcon(icon if icon is not None else icons.icon("finestra"))
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        sub.installEventFilter(self)
        sub.destroyed.connect(self._on_destroyed)
        self.area.addSubWindow(sub)
        sub.show()
        sub.resize(proposed)
        self.area.setActiveSubWindow(sub)
        self.opened.emit(sub)
        return sub

    def open_dialog(
        self,
        key: str,
        dialog: QDialog,
        *,
        title: str | None = None,
        icon: QIcon | None = None,
        size: QSize | None = None,
    ) -> QMdiSubWindow:
        """Apre un ``QDialog`` legacy attraverso :class:`DialogEditor`."""
        page = DialogEditor(dialog, self.area)
        sub = self.open(key, title or dialog.windowTitle() or "Finestra", page, icon=icon, size=size)
        page.finished.connect(lambda: self._close_if_open(sub))
        return sub

    # ------------------------------------------------------------------ chiusura
    def close(self, sub: QMdiSubWindow | None) -> None:
        if sub is not None:
            sub.close()

    def remove(self, key: str) -> None:
        """Rimuove subito il documento con quella chiave, senza attendere deleteLater."""
        sub = self.find(key)
        if sub is None:
            return
        self.area.removeSubWindow(sub)
        sub.close()
        sub.deleteLater()

    def close_current(self) -> None:
        self.area.closeActiveSubWindow()

    def close_all(self) -> None:
        for sub in list(self.windows()):
            sub.close()

    def cascade(self) -> None:
        self.area.cascadeSubWindows()

    def tile(self) -> None:
        self.area.tileSubWindows()

    # --------------------------------------------------------------------- eventi
    def _close_if_open(self, sub: QMdiSubWindow | None) -> None:
        if sub is not None and sub.isVisible():
            sub.close()

    def _on_activated(self, sub: QMdiSubWindow | None) -> None:
        self.activated.emit(sub.widget() if sub is not None else None)

    def _on_destroyed(self, *_args: Any) -> None:
        self.closed.emit()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 - API Qt
        if isinstance(obj, QMdiSubWindow) and event.type() == QEvent.Type.Close:
            widget = obj.widget()
            if widget is not None and editor_dirty(widget):
                answer = QMessageBox.question(
                    obj,
                    "Modifiche non salvate",
                    f"«{obj.windowTitle()}» contiene modifiche non salvate.\nChiudere comunque?",
                )
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return True
        return super().eventFilter(obj, event)
