"""Selettore visuale dei passi script (0.4/O5).

Mostra il catalogo `ACTIONS` raggruppato per categoria, con filtro e
descrizione. Non cambia il comportamento del motore: sceglie soltanto quale
azione aprire nell'editor dei parametri.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..runtime.script_engine import ACTIONS, actions_by_category
from ..ui import icons


class StepPickerDialog(QDialog):
    """Elenco categorizzato delle azioni disponibili."""

    action_chosen = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Aggiungi azione")
        self.resize(560, 480)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Cerca per nome, categoria o descrizione…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Catalogo azioni script")
        self.tree.itemSelectionChanged.connect(self._on_selection)
        self.tree.itemDoubleClicked.connect(lambda _item, _column: self.accept())
        layout.addWidget(self.tree, 1)

        self.description_label = QLabel("")
        self.description_label.setObjectName("nav_hint")
        self.description_label.setWordWrap(True)
        self.description_label.setMinimumHeight(64)
        layout.addWidget(self.description_label)

        self.buttons = icons.dialog_buttons("Aggiungi", "Annulla")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.ok_button = self.buttons.buttons()[0] if self.buttons.buttons() else None
        if self.ok_button is not None:
            self.ok_button.setEnabled(False)
        layout.addWidget(self.buttons)

        self._populate()
        first = self._first_action_item()
        if first is not None:
            self.tree.setCurrentItem(first)

    # ------------------------------------------------------------------ dati
    def _populate(self) -> None:
        self.tree.clear()
        for category, keys in actions_by_category().items():
            parent = QTreeWidgetItem([category])
            parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            parent.setData(0, Qt.ItemDataRole.UserRole, ("category", category))
            self.tree.addTopLevelItem(parent)
            for key in keys:
                definition = ACTIONS[key]
                label = str(definition.get("label", key))
                item = QTreeWidgetItem([label])
                item.setData(0, Qt.ItemDataRole.UserRole, ("action", key))
                item.setToolTip(
                    0,
                    f"{label} — {definition.get('description', '')}",
                )
                item.setData(0, Qt.ItemDataRole.UserRole + 1, key)
                parent.addChild(item)
            parent.setExpanded(True)

    def _first_action_item(self) -> QTreeWidgetItem | None:
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            if parent.childCount():
                return parent.child(0)
        return None

    def _all_action_items(self) -> list[QTreeWidgetItem]:
        result: list[QTreeWidgetItem] = []
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            for child_index in range(parent.childCount()):
                result.append(parent.child(child_index))
        return result

    def _apply_filter(self, text: str) -> None:
        needle = str(text or "").strip().lower()
        for index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(index)
            visible = False
            for child_index in range(parent.childCount()):
                item = parent.child(child_index)
                key = str((item.data(0, Qt.ItemDataRole.UserRole) or ("", ""))[1])
                definition = ACTIONS.get(key, {})
                haystack = " ".join(
                    (
                        str(item.text(0)),
                        str(parent.text(0)),
                        str(definition.get("description", "")),
                        key,
                    )
                ).lower()
                match = not needle or needle in haystack
                item.setHidden(not match)
                visible = visible or match
            parent.setHidden(not visible)
        current = self.tree.currentItem()
        if current is not None and current.isHidden():
            first = next(
                (item for item in self._all_action_items() if not item.isHidden()),
                None,
            )
            self.tree.setCurrentItem(first)

    # ------------------------------------------------------------------ stato
    def selected_action(self) -> str:
        item = self.tree.currentItem()
        if item is None:
            return ""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and len(data) == 2 and data[0] == "action":
            return str(data[1])
        return ""

    def select_action(self, key: str) -> None:
        """Seleziona programmaticamente un'azione (usato dai test)."""
        for item in self._all_action_items():
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, tuple) and data[-1] == key:
                self.filter_edit.clear()
                self.tree.setCurrentItem(item)
                return

    def _on_selection(self) -> None:
        key = self.selected_action()
        definition = ACTIONS.get(key, {})
        if key:
            params = ", ".join(
                f"{label}" for _name, label, _kind in definition.get("params", [])
            )
            self.description_label.setText(
                f"<b>{definition.get('label', key)}</b> · "
                f"{definition.get('category', '')}<br>"
                f"{definition.get('description', '')}<br>"
                f"<i>Parametri:</i> {params or 'nessuno'}"
            )
            self.action_chosen.emit(key)
        else:
            self.description_label.setText("Scegli un'azione dall'elenco.")
        if self.ok_button is not None:
            self.ok_button.setEnabled(bool(key))

    def accept(self) -> None:
        if not self.selected_action():
            return
        super().accept()


__all__ = ["StepPickerDialog"]
