"""Navigator del progetto nello schema di dBASE: colonna categorie + elenco file (A4, G1)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.project import CATEGORY_LABELS, Project
from . import icons

# Categorie mostrate nella colonna del Navigator, nello stesso ordine del dBASE originale.
NAV_CATEGORIES = [
    ("all", "Tutti", "elenco"),
    ("tables", "Tabelle", "tabella"),
    ("forms", "Form", "form"),
    ("reports", "Report", "report"),
    ("scripts", "Programmi", "script"),
    ("menus", "Menu", "menu"),
]

CATEGORY_ICONS = {
    "tables": "tabella",
    "forms": "form",
    "reports": "report",
    "scripts": "script",
    "menus": "menu",
}


class Navigator(QWidget):
    """Navigator a due zone: pulsanti di categoria a sinistra, elenco oggetti a destra."""

    open_object = pyqtSignal(str, str)
    run_object = pyqtSignal(str, str)
    new_object = pyqtSignal(str)
    delete_object = pyqtSignal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self.category = "all"
        self._buttons: dict[str, QPushButton] = {}
        self._build_ui()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        column = QFrame()
        column.setObjectName("nav_categories")
        column.setFixedWidth(134)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(4, 6, 4, 6)
        column_layout.setSpacing(2)
        for key, label, glyph in NAV_CATEGORIES:
            button = icons.make_button(label, glyph, lambda _checked=False, k=key: self.set_category(k), self)
            button.setCheckable(True)
            button.setProperty("nav_category", key)
            button.setStyleSheet("text-align: left;")
            column_layout.addWidget(button)
            self._buttons[key] = button
        column_layout.addStretch(1)
        outer.addWidget(column)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        directory_row = QHBoxLayout()
        directory_row.addWidget(QLabel("Directory corrente:"))
        self.directory_edit = QLineEdit()
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setPlaceholderText("(nessun progetto)")
        directory_row.addWidget(self.directory_edit, 1)
        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Apri la cartella del progetto")
        browse.clicked.connect(self._open_directory)
        directory_row.addWidget(browse)
        right_layout.addLayout(directory_row)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Tutti i file (*.*)", "all")
        self.filter_combo.addItem("Tabelle (*.dbf)", "tables")
        self.filter_combo.addItem("Form (*.form)", "forms")
        self.filter_combo.addItem("Report (*.rep)", "reports")
        self.filter_combo.addItem("Programmi (*.pro)", "scripts")
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        right_layout.addWidget(self.filter_combo)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(False)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.itemDoubleClicked.connect(self._activate)
        self.list.itemActivated.connect(self._activate)
        self.list.setToolTip("Doppio clic per aprire, tasto destro per le azioni")
        right_layout.addWidget(self.list, 1)

        self.hint = QLabel("Seleziona una categoria per iniziare.")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: palette(mid);")
        right_layout.addWidget(self.hint)
        outer.addWidget(right, 1)

        self.set_category("all")

    # --------------------------------------------------------------- progetto
    def set_project(self, project: Project | None) -> None:
        self.project = project
        self.refresh()

    def set_category(self, category: str) -> None:
        self.category = category
        for key, button in self._buttons.items():
            button.setChecked(key == category)
        index = self.filter_combo.findData(category)
        if index >= 0 and self.filter_combo.currentIndex() != index:
            self.filter_combo.blockSignals(True)
            self.filter_combo.setCurrentIndex(index)
            self.filter_combo.blockSignals(False)
        self.refresh()

    def _on_filter_changed(self, _index: int) -> None:
        data = self.filter_combo.currentData() or "all"
        if data != self.category:
            self.set_category(data)

    def refresh(self) -> None:
        self.list.clear()
        if self.project is None:
            self.directory_edit.clear()
            self.hint.setText("Nessun progetto aperto.")
            return
        self.directory_edit.setText(str(self.project.path))
        categories = list(CATEGORY_LABELS)
        if self.category != "all":
            categories = [self.category]
        count = 0
        for category in categories:
            if category not in CATEGORY_ICONS:
                continue
            untitled = QListWidgetItem(icons.icon(CATEGORY_ICONS[category]), f"[Nuovo {CATEGORY_LABELS[category]}]")
            untitled.setData(Qt.ItemDataRole.UserRole, f"new:{category}")
            untitled.setToolTip(f"Crea un nuovo oggetto in {CATEGORY_LABELS[category]}")
            self.list.addItem(untitled)
            for name in self.project.names(category):
                item = QListWidgetItem(icons.icon(CATEGORY_ICONS[category]), name)
                item.setData(Qt.ItemDataRole.UserRole, f"{category}:{name}")
                item.setToolTip(f"{CATEGORY_LABELS[category]} — doppio clic per aprire")
                self.list.addItem(item)
                count += 1
        if count:
            self.hint.setText(f"{count} oggetti in {CATEGORY_LABELS.get(self.category, 'tutte le categorie')}.")
        else:
            self.hint.setText("Nessun oggetto: usa una voce [Nuovo …] per creare.")

    def _open_directory(self) -> None:
        if self.project is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.project.path))))

    # ------------------------------------------------------------------ azioni
    def _activate(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, str):
            return
        if data.startswith("new:"):
            self.new_object.emit(data.split(":", 1)[1])
            return
        if ":" in data:
            category, name = data.split(":", 1)
            self.open_object.emit(category, name)

    def _context_menu(self, position) -> None:
        item = self.list.itemAt(position)
        menu = QMenu(self)
        if item is None:
            for category in CATEGORY_ICONS:
                menu.addAction(f"Nuovo in {CATEGORY_LABELS[category]}", lambda c=category: self.new_object.emit(c))
        else:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, str) and data.startswith("new:"):
                category = data.split(":", 1)[1]
                menu.addAction(f"Nuovo in {CATEGORY_LABELS.get(category, category)}", lambda: self.new_object.emit(category))
            elif isinstance(data, str) and ":" in data:
                category, name = data.split(":", 1)
                menu.addAction("Apri / modifica", lambda: self.open_object.emit(category, name))
                if category in ("tables", "forms", "reports", "scripts"):
                    menu.addAction("Esegui", lambda: self.run_object.emit(category, name))
                menu.addSeparator()
                menu.addAction("Elimina", lambda: self.delete_object.emit(category, name))
            menu.addSeparator()
            menu.addAction("Aggiorna", self.refresh)
        menu.exec(self.list.viewport().mapToGlobal(position))
