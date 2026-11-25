"""Area documenti di dBX: schede orizzontali al posto delle sottofinestre MDI.

Ogni editor occupa tutta l'area a destra del Navigator. Le schede mostrano
icona, titolo e pulsante di chiusura; l'attivazione avviene con un clic
sull'etichetta o dal menu Finestra. I ``QDialog`` legacy passano da
:class:`DialogEditor`, che li rende contenuti scorrevoli di una scheda.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons


class DialogEditor(QWidget):
    """Adapter che ospita un ``QDialog`` legacy dentro una scheda."""

    finished = pyqtSignal()

    def __init__(self, dialog: QDialog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.dialog = dialog
        self._preferred = QSize()
        self._notified = False
        self.setObjectName("dialog_editor")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
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
        dialog.windowTitleChanged.connect(self._on_dialog_title)
        self.setWindowTitle(dialog.windowTitle())

    def _on_dialog_title(self, title: str) -> None:
        self.setWindowTitle(title)
        host = self.parentWidget()
        while host is not None and not isinstance(host, EditorHost):
            host = host.parentWidget()
        if host is not None:
            host.set_title_for_widget(self, title)

    def sizeHint(self) -> QSize:  # noqa: N802 - API Qt
        if self._preferred.isValid():
            return self._preferred
        return super().sizeHint()

    def set_preferred_size(self, size: QSize) -> None:
        """Dimensione richiesta dal dialogo, usata solo come suggerimento."""
        self._preferred = QSize(size)
        self.updateGeometry()

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


class EditorTab:
    """Handle di una scheda: mantiene l'API usata dai chiamanti."""

    def __init__(self, host: "EditorHost", key: str, title: str, widget: QWidget) -> None:
        self.host = host
        self._key = key
        self._title = title
        self._widget = widget

    def property(self, name: str) -> Any:
        return self._key if name == "dbx_key" else self._widget.property(name)

    def setProperty(self, name: str, value: Any) -> None:  # noqa: N802 - API Qt
        if name == "dbx_key":
            self._key = str(value)
        self._widget.setProperty(name, value)

    def widget(self) -> QWidget:
        return self._widget

    def windowTitle(self) -> str:  # noqa: N802 - API Qt
        return self._title

    def setWindowTitle(self, title: str) -> None:  # noqa: N802 - API Qt
        self._title = title
        self.host.set_title_for_widget(self._widget, title)

    def close(self) -> bool:
        return self.host.close_tab(self)

    def isMaximized(self) -> bool:  # noqa: N802 - API Qt
        return False

    def isMinimized(self) -> bool:  # noqa: N802 - API Qt
        return False


class EditorHost(QWidget):
    """Gestisce le schede dei documenti, la loro attivazione e la chiusura."""

    activated = pyqtSignal(object)
    closed = pyqtSignal()
    opened = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("editor_host")
        self._items: list[EditorTab] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("editor_tabs")
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tabs.currentChanged.connect(self._on_current_changed)
        layout.addWidget(self.tabs)

    # ------------------------------------------------------------------ lettura
    def windows(self) -> list[EditorTab]:
        return list(self._items)

    def find(self, key: str) -> EditorTab | None:
        return next((item for item in self._items if item._key == key), None)

    def current(self) -> EditorTab | None:
        widget = self.tabs.currentWidget()
        if widget is None:
            return None
        return next((item for item in self._items if item.widget() is widget), None)

    def current_editor(self) -> QWidget | None:
        tab = self.current()
        return tab.widget() if tab is not None else None

    # ------------------------------------------------------------------ apertura
    def open(
        self,
        key: str,
        title: str,
        widget: QWidget,
        *,
        icon: QIcon | None = None,
        size: QSize | None = None,
    ) -> EditorTab:
        """Apre ``widget`` in una scheda, oppure attiva quella esistente."""
        existing = self.find(key)
        if existing is not None:
            self.activate(existing)
            return existing
        widget.setProperty("dbx_key", key)
        if not widget.windowTitle():
            widget.setWindowTitle(title)
        tab = EditorTab(self, key, title, widget)
        self._items.append(tab)
        index = self.tabs.addTab(
            widget,
            icon if icon is not None else icons.icon("finestra"),
            title,
        )
        self.tabs.setTabToolTip(index, title)
        self.tabs.setCurrentIndex(index)
        self.opened.emit(tab)
        return tab

    def open_dialog(
        self,
        key: str,
        dialog: QDialog,
        *,
        title: str | None = None,
        icon: QIcon | None = None,
        size: QSize | None = None,
    ) -> EditorTab:
        """Apre un ``QDialog`` legacy attraverso :class:`DialogEditor`."""
        page = DialogEditor(dialog, self)
        tab = self.open(key, title or dialog.windowTitle() or "Finestra", page, icon=icon, size=size)
        page.finished.connect(lambda: self.remove(key))
        return tab

    def focus_tab_bar(self) -> None:
        """Porta il focus sull'etichetta della scheda corrente."""
        self.tabs.tabBar().setFocus(Qt.FocusReason.OtherFocusReason)

    # ------------------------------------------------------------------ comandi
    def activate(self, tab: EditorTab) -> None:
        if tab in self._items:
            self.tabs.setCurrentWidget(tab.widget())

    def set_title_for_widget(self, widget: QWidget, title: str) -> None:
        index = self.tabs.indexOf(widget)
        if index >= 0:
            self.tabs.setTabText(index, title)
            self.tabs.setTabToolTip(index, title)
        for item in self._items:
            if item.widget() is widget:
                item._title = title

    def close_tab(self, tab: EditorTab | None) -> bool:
        if tab is None or tab not in self._items:
            return False
        if not self._confirm_close(tab):
            return False
        return self._remove(tab)

    def remove(self, key: str) -> None:
        tab = self.find(key)
        if tab is not None:
            self._remove(tab)

    def close_current(self) -> None:
        self.close_tab(self.current())

    def close_all(self) -> None:
        for tab in list(self._items):
            if not self.close_tab(tab):
                continue

    # ------------------------------------------------------------------ interni
    def _confirm_close(self, tab: EditorTab) -> bool:
        if not editor_dirty(tab.widget()):
            return True
        answer = QMessageBox.question(
            self,
            "Modifiche non salvate",
            f"«{tab.windowTitle()}» contiene modifiche non salvate.\nChiudere comunque?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def _remove(self, tab: EditorTab) -> bool:
        if tab not in self._items:
            return False
        index = self.tabs.indexOf(tab.widget())
        if index >= 0:
            self.tabs.removeTab(index)
        self._items.remove(tab)
        tab.widget().deleteLater()
        self.closed.emit()
        return True

    def _on_tab_close_requested(self, index: int) -> None:
        widget = self.tabs.widget(index)
        tab = next((item for item in self._items if item.widget() is widget), None)
        self.close_tab(tab)

    def _on_current_changed(self, _index: int) -> None:
        tab = self.current()
        self.activated.emit(tab.widget() if tab is not None else None)


__all__ = [
    "DialogEditor",
    "EditorHost",
    "EditorTab",
    "editor_dirty",
    "editor_title",
    "editor_widget",
]
