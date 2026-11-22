"""Navigator del progetto nello schema di dBASE: colonna categorie + elenco file (A4, G1)."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
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
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.project import CATEGORY_LABELS, Project
from . import icons

# Categorie nello stesso ordine del Navigator originale. L'ultimo campo indica
# se la categoria è utilizzabile in dBX 0.2; quelle non disponibili restano
# visibili e disabilitate, con tooltip esplicativo.
NAV_CATEGORIES = [
    ("all", "Tutti", "elenco", True),
    ("tables", "Tabelle", "tabella", True),
    ("queries", "Query", "cerca", False),
    ("forms", "Form", "form", True),
    ("reports", "Report", "report", True),
    ("menus", "Menu", "menu", True),
    ("labels", "Etichette", "stampa", False),
    ("scripts", "Programmi", "script", True),
    ("images", "Immagini", "immagine", False),
    ("sounds", "Suoni", "esegui", False),
    ("catalogs", "Cataloghi", "elenco", False),
    ("custom", "Personalizzati", "impostazioni", False),
]

NAV_LABELS = {key: label for key, label, _glyph, _available in NAV_CATEGORIES}
AVAILABLE_CATEGORIES = [
    key for key, _label, _glyph, available in NAV_CATEGORIES if available and key != "all"
]
SELECTABLE_CATEGORIES = ["all", *AVAILABLE_CATEGORIES]

CATEGORY_ICONS = {
    "tables": "tabella",
    "forms": "form",
    "reports": "report",
    "scripts": "script",
    "menus": "menu",
}

FILTERS = [
    ("Tutti i file (*.*)", "all"),
    ("Tabelle (*.table.json)", "tables"),
    ("Form (*.form.json)", "forms"),
    ("Report (*.report.json)", "reports"),
    ("Programmi (*.script.json)", "scripts"),
    ("Menu (*.menu.json)", "menus"),
]


class Navigator(QWidget):
    """Navigator a due zone: pulsanti di categoria a sinistra, elenco oggetti a destra."""

    open_object = pyqtSignal(str, str)
    run_object = pyqtSignal(str, str)
    new_object = pyqtSignal(str)
    delete_object = pyqtSignal(str, str)
    structure_object = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self.category = "all"
        self._buttons: dict[str, QToolButton] = {}
        self._build_ui()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        column = QFrame()
        column.setObjectName("nav_categories")
        column.setFixedWidth(122)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(4, 6, 4, 6)
        column_layout.setSpacing(2)
        for key, label, glyph, available in NAV_CATEGORIES:
            button = QToolButton(column)
            button.setText(label)
            button.setIcon(icons.icon(glyph))
            button.setIconSize(QSize(20, 20))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setCheckable(True)
            button.setFixedHeight(46)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setProperty("nav_category", key)
            if available:
                button.setToolTip(f"Mostra {label.lower()}")
                button.clicked.connect(
                    lambda _checked=False, k=key: self.set_category(k)
                )
            else:
                button.setEnabled(False)
                button.setToolTip(f"{label}: non disponibile in dBX 0.2")
            column_layout.addWidget(button)
            self._buttons[key] = button
        column_layout.addStretch(1)
        outer.addWidget(column)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        directory_row = QHBoxLayout()
        directory_row.addWidget(QLabel("Directory corrente"))
        self.directory_edit = QLineEdit()
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setPlaceholderText("(nessun progetto)")
        self.directory_edit.setToolTip("Cartella del progetto corrente")
        directory_row.addWidget(self.directory_edit, 1)
        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Apri la cartella del progetto")
        browse.clicked.connect(self._open_directory)
        directory_row.addWidget(browse)
        right_layout.addLayout(directory_row)

        self.filter_combo = QComboBox()
        for text, data in FILTERS:
            self.filter_combo.addItem(text, data)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        right_layout.addWidget(self.filter_combo)

        self.list_header = QLabel("Oggetti del progetto")
        self.list_header.setObjectName("nav_header")
        right_layout.addWidget(self.list_header)

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
        self.hint.setObjectName("nav_hint")
        right_layout.addWidget(self.hint)
        outer.addWidget(right, 1)

        self.set_category("all")

    # --------------------------------------------------------------- progetto
    def set_project(self, project: Project | None) -> None:
        self.project = project
        self.refresh()

    def set_category(self, category: str) -> None:
        if category not in SELECTABLE_CATEGORIES:
            return
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
            self.list_header.setText("Oggetti del progetto")
            self.hint.setText("Nessun progetto aperto.")
            return
        self.directory_edit.setText(str(self.project.path))
        self.directory_edit.setCursorPosition(0)
        categories = (
            AVAILABLE_CATEGORIES if self.category == "all" else [self.category]
        )
        count = 0
        for category in categories:
            if category not in CATEGORY_ICONS:
                continue
            untitled = QListWidgetItem(icons.icon(CATEGORY_ICONS[category]), "[Untitled]")
            untitled.setData(Qt.ItemDataRole.UserRole, f"new:{category}")
            untitled.setToolTip(
                f"Nuovo oggetto — {NAV_LABELS.get(category, CATEGORY_LABELS.get(category, category))}"
            )
            self.list.addItem(untitled)
            for name in self.project.names(category):
                item = QListWidgetItem(icons.icon(CATEGORY_ICONS[category]), name)
                item.setData(Qt.ItemDataRole.UserRole, f"{category}:{name}")
                item.setToolTip(
                    f"{NAV_LABELS.get(category, category)} — doppio clic per aprire"
                )
                self.list.addItem(item)
                count += 1
        if self.category == "all":
            self.list_header.setText(f"Oggetti del progetto ({count})")
        else:
            self.list_header.setText(f"{NAV_LABELS.get(self.category, self.category)} ({count})")
        if count:
            where = (
                "nel progetto"
                if self.category == "all"
                else f"in {NAV_LABELS.get(self.category, self.category)}"
            )
            self.hint.setText(f"{count} oggetti {where}.")
        elif self.category == "all":
            self.hint.setText("Progetto vuoto: apri una categoria e usa [Untitled].")
        else:
            self.hint.setText(
                f"Nessun oggetto in {NAV_LABELS.get(self.category, self.category)}: "
                "doppio clic su [Untitled] per crearlo."
            )

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
            for category in AVAILABLE_CATEGORIES:
                label = NAV_LABELS.get(category, CATEGORY_LABELS.get(category, category))
                menu.addAction(
                    f"Nuovo in {label}",
                    lambda c=category: self.new_object.emit(c),
                )
        else:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, str) and data.startswith("new:"):
                category = data.split(":", 1)[1]
                label = NAV_LABELS.get(category, CATEGORY_LABELS.get(category, category))
                menu.addAction(
                    f"Nuovo in {label}", lambda c=category: self.new_object.emit(c)
                )
            elif isinstance(data, str) and ":" in data:
                category, name = data.split(":", 1)
                menu.addAction("Apri / modifica", lambda: self.open_object.emit(category, name))
                if category == "tables":
                    menu.addAction("Struttura…", lambda: self.structure_object.emit(name))
                if category in ("tables", "forms", "reports", "scripts"):
                    menu.addAction("Esegui", lambda: self.run_object.emit(category, name))
                menu.addSeparator()
                menu.addAction("Elimina", lambda: self.delete_object.emit(category, name))
            menu.addSeparator()
            menu.addAction("Aggiorna", self.refresh)
        menu.exec(self.list.viewport().mapToGlobal(position))
