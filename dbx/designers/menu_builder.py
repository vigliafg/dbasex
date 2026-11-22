"""Menu Designer: albero voci/separatori, azioni tipizzate e anteprima (O6)."""

from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.project import Project, ProjectError
from ..ui import icons

MENU_ACTIONS = {
    "open_form": "Apri form",
    "open_report": "Apri report",
    "run_script": "Esegui script",
    "separator": "Separatore",
    "quit": "Esci",
}

TARGET_CATEGORY = {
    "open_form": "forms",
    "open_report": "reports",
    "run_script": "scripts",
}


class MenuBuilderWidget(QWidget):
    """Menu Designer con albero, proprietà tipizzate e anteprima del menu."""

    saved = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, project: Project, artifact: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("menu_designer")
        self.project = project
        self.name = str(artifact.get("name", "principale"))
        self.items: list[dict[str, Any]] = [copy.deepcopy(item) for item in artifact.get("items", [])]
        self._saved_state = copy.deepcopy(self.items)
        self._saved_name = self.name
        self._loading = False
        self.setWindowTitle(f"Menu Designer ({self.name})")
        self.resize(860, 560)
        self._build_ui()
        self._rebuild_tree()
        self._rebuild_preview()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel("Nome menu:"))
        self.name_edit = QLineEdit(self.name)
        self.name_edit.setPlaceholderText("nome_menu")
        self.name_edit.textChanged.connect(self._on_name_changed)
        header.addWidget(self.name_edit, 1)
        layout.addLayout(header)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        for text, glyph, slot, tip in (
            ("Aggiungi voce", "nuovo", self.add_item, "Aggiungi una voce di menu"),
            ("Separatore", "linea", self.add_separator, "Aggiungi un separatore"),
            ("Elimina", "elimina", self.remove_item, "Rimuovi la voce"),
            ("Sposta su", "su", lambda: self.move_item(-1), "Sposta la voce su"),
            ("Sposta giù", "giu", lambda: self.move_item(1), "Sposta la voce giù"),
        ):
            bar.addWidget(icons.make_button(text, glyph, slot, self, tip))
        bar.addStretch(1)
        bar.addWidget(icons.make_button("Salva", "salva", self.save, self, "Salva il menu (Ctrl+S)"))
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setAccessibleName("Voci del menu")
        self.tree.setHeaderLabels(["Voce", "Azione", "Destinazione"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 120)
        self.tree.itemSelectionChanged.connect(self._on_selection)
        self.tree.itemDoubleClicked.connect(lambda _item, _col: self.name_edit.setFocus())
        splitter.addWidget(self.tree)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        properties = QFrame()
        properties.setObjectName("menu_properties")
        form = QFormLayout(properties)
        form.setContentsMargins(8, 8, 8, 8)
        self.label_edit = QLineEdit()
        self.label_edit.textEdited.connect(self._on_property_edited)
        form.addRow("Voce", self.label_edit)
        self.action_combo = QComboBox()
        for key, text in MENU_ACTIONS.items():
            self.action_combo.addItem(text, key)
        self.action_combo.currentIndexChanged.connect(self._on_action_changed)
        form.addRow("Azione", self.action_combo)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        self.target_combo.currentTextChanged.connect(self._on_property_edited)
        form.addRow("Destinazione", self.target_combo)
        right_layout.addWidget(properties)

        preview_frame = QFrame()
        preview_frame.setObjectName("menu_preview")
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(6, 6, 6, 6)
        preview_layout.addWidget(QLabel("Anteprima"))
        self.preview_bar = QMenuBar()
        self.preview_bar.setAccessibleName("Anteprima del menu")
        preview_layout.addWidget(self.preview_bar)
        preview_layout.addStretch(1)
        self.preview_state = QLabel("")
        self.preview_state.setObjectName("nav_hint")
        self.preview_state.setWordWrap(True)
        preview_layout.addWidget(self.preview_state)
        right_layout.addWidget(preview_frame, 1)
        splitter.addWidget(right)
        splitter.setSizes([500, 320])
        layout.addWidget(splitter, 1)

        self.setStyleSheet(
            "#menu_properties, #menu_preview { border: 1px solid palette(mid); }"
        )
        self._shortcuts = []
        shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.save)
        self._shortcuts.append(shortcut)

    # ------------------------------------------------------------------ albero
    def _rebuild_tree(self, select: int | None = None) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        for index, item in enumerate(self.items):
            action = str(item.get("action", ""))
            label = str(item.get("label", ""))
            if action == "separator":
                row = QTreeWidgetItem(["— separatore —", "Separatore", ""])
            else:
                row = QTreeWidgetItem(
                    [
                        label,
                        MENU_ACTIONS.get(action, action),
                        str(item.get("target", "")),
                    ]
                )
            row.setData(0, Qt.ItemDataRole.UserRole, index)
            self.tree.addTopLevelItem(row)
        self.tree.blockSignals(False)
        if self.items:
            index = 0 if select is None else max(0, min(select, len(self.items) - 1))
            self.tree.setCurrentItem(self.tree.topLevelItem(index))
        else:
            self._show_properties(None)

    def _selected_item(self) -> dict[str, Any] | None:
        row = self.tree.currentItem()
        if row is None:
            return None
        index = row.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(index, int) or not (0 <= index < len(self.items)):
            return None
        return self.items[index]

    def _selected_index(self) -> int:
        item = self._selected_item()
        if item is None:
            return -1
        for index, candidate in enumerate(self.items):
            if candidate is item:
                return index
        return -1

    # -------------------------------------------------------------- proprietà
    def _on_selection(self) -> None:
        self._show_properties(self._selected_item())

    def _show_properties(self, item: dict[str, Any] | None) -> None:
        self._loading = True
        separator = item is None or item.get("action") == "separator"
        self.label_edit.setEnabled(item is not None and not separator)
        self.action_combo.setEnabled(item is not None)
        self.target_combo.setEnabled(item is not None and str(item.get("action", "")) in TARGET_CATEGORY)
        if item is None:
            self.label_edit.clear()
            self.target_combo.clear()
            self._loading = False
            return
        action = str(item.get("action", "open_form"))
        self.label_edit.setText(str(item.get("label", "")))
        self.action_combo.setCurrentIndex(max(0, self.action_combo.findData(action)))
        self._reload_targets(action, str(item.get("target", "")))
        self._loading = False

    def _reload_targets(self, action: str, value: str = "") -> None:
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        category = TARGET_CATEGORY.get(action)
        if category is not None:
            self.target_combo.addItem("")
            for name in self.project.names(category):
                self.target_combo.addItem(name)
        if value:
            index = self.target_combo.findText(value)
            if index < 0:
                self.target_combo.addItem(value)
                index = self.target_combo.count() - 1
            self.target_combo.setCurrentIndex(index)
        elif self.target_combo.count():
            self.target_combo.setCurrentIndex(0)
        self.target_combo.blockSignals(False)

    def _on_action_changed(self, _index: int) -> None:
        if self._loading:
            return
        item = self._selected_item()
        if item is None:
            return
        action = str(self.action_combo.currentData() or "open_form")
        item["action"] = action
        if action == "separator":
            item["label"] = ""
            item["target"] = ""
        self._loading = True
        self._reload_targets(action, str(item.get("target", "")))
        self.label_edit.setEnabled(action != "separator")
        self.target_combo.setEnabled(action in TARGET_CATEGORY)
        self._loading = False
        self._refresh_row(item)
        self._rebuild_preview()

    def _on_property_edited(self, _text: str = "") -> None:
        if self._loading:
            return
        item = self._selected_item()
        if item is None:
            return
        item["label"] = self.label_edit.text()
        item["target"] = self.target_combo.currentText().strip()
        self._refresh_row(item)
        self._rebuild_preview()

    def _refresh_row(self, item: dict[str, Any]) -> None:
        index = self._selected_index()
        if index < 0:
            return
        row = self.tree.topLevelItem(index)
        if row is None:
            return
        if item.get("action") == "separator":
            row.setText(0, "— separatore —")
            row.setText(1, "Separatore")
            row.setText(2, "")
        else:
            row.setText(0, str(item.get("label", "")))
            row.setText(1, MENU_ACTIONS.get(str(item.get("action")), str(item.get("action"))))
            row.setText(2, str(item.get("target", "")))

    # ------------------------------------------------------------------ azioni
    def add_item(self) -> None:
        item = {"label": "Nuova voce", "action": "open_form", "target": ""}
        self.items.append(item)
        self._rebuild_tree(select=len(self.items) - 1)
        self._show_properties(item)
        self._rebuild_preview()
        self.status_message.emit("Voce aggiunta")

    def add_separator(self) -> None:
        item = {"label": "", "action": "separator", "target": ""}
        self.items.append(item)
        self._rebuild_tree(select=len(self.items) - 1)
        self._rebuild_preview()
        self.status_message.emit("Separatore aggiunto")

    def remove_item(self) -> None:
        index = self._selected_index()
        if index < 0:
            return
        self.items.pop(index)
        self._rebuild_tree(select=min(index, len(self.items) - 1) if self.items else None)
        self._rebuild_preview()

    def move_item(self, delta: int) -> None:
        index = self._selected_index()
        target = index + delta
        if index < 0 or not (0 <= target < len(self.items)):
            return
        self.items[index], self.items[target] = self.items[target], self.items[index]
        self._rebuild_tree(select=target)
        self._rebuild_preview()

    # --------------------------------------------------------------- anteprima
    def _rebuild_preview(self) -> None:
        self.preview_bar.clear()
        menu = self.preview_bar.addMenu(self.name or "Menu")
        visible = 0
        for item in self.items:
            action = str(item.get("action", ""))
            if action == "separator":
                menu.addSeparator()
                continue
            label = str(item.get("label", "") or "(senza titolo)")
            entry = menu.addAction(label)
            entry.setEnabled(False)
            visible += 1
        self.preview_state.setText(
            f"{visible} voci visibili · {len(self.items)} elementi totali"
        )

    def _on_name_changed(self, text: str) -> None:
        self.name = text.strip() or self.name
        self.setWindowTitle(f"Menu Designer ({self.name})")
        self._rebuild_preview()

    # ------------------------------------------------------------------ salvataggio
    def is_dirty(self) -> bool:
        return self.items != self._saved_state or self.name != self._saved_name

    def save(self) -> bool:
        name = self.name_edit.text().strip() or self.name
        items = [copy.deepcopy(item) for item in self.items]
        try:
            self.project.put_object(
                "menus", {"name": name, "items": items}, previous_name=self.name
            )
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self.name = name
        self._saved_name = name
        self._saved_state = copy.deepcopy(items)
        self.saved.emit(name)
        self.status_message.emit(f"Menu {name} salvato")
        return True


# Compatibilità con il nome storico usato da smoke, test e capture.
MenuBuilderDialog = MenuBuilderWidget
