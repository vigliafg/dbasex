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
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.project import CATEGORY_LABELS, Project
from . import design, icons
from .menu import DescriptiveMenu, add_entry

# Categorie nello stesso ordine del Navigator originale. L'ultimo campo indica
# se la categoria è utilizzabile; quelle non disponibili restano visibili e
# disabilitate, con tooltip esplicativo.
NAV_CATEGORIES = [
    ("all", "Tutti", "elenco", True),
    ("tables", "Database", "database", True),
    ("queries", "Query", "cerca", True),
    ("forms", "Form", "form", True),
    ("reports", "Report", "report", True),
    ("labels", "Etichette", "etichetta", True),
    ("menus", "Menu", "menu", True),
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
    "tables": "database",
    "queries": "cerca",
    "forms": "form",
    "reports": "report",
    "labels": "etichetta",
    "scripts": "script",
    "menus": "menu",
}

FILTERS = [
    ("Tutti i file (*.*)", "all"),
    ("Database (*.table.json)", "tables"),
    ("Query (*.query.json)", "queries"),
    ("Form (*.form.json)", "forms"),
    ("Report (*.report.json)", "reports"),
    ("Etichette (*.label.json)", "labels"),
    ("Programmi (*.script.json)", "scripts"),
    ("Menu (*.menu.json)", "menus"),
]


class Navigator(QWidget):
    """Navigator a due zone: pulsanti di categoria a sinistra, elenco oggetti a destra."""

    open_object = pyqtSignal(str, str)
    run_object = pyqtSignal(str, str)
    new_object = pyqtSignal(str)
    new_expert = pyqtSignal(str)
    delete_object = pyqtSignal(str, str)
    duplicate_object = pyqtSignal(str, str)
    structure_object = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigator")
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
        column.setFixedWidth(64)
        column_outer = QVBoxLayout(column)
        column_outer.setContentsMargins(0, 0, 0, 0)
        column_outer.setSpacing(0)
        self.category_scroll = QScrollArea(column)
        self.category_scroll.setObjectName("nav_categories_scroll")
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.category_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.category_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        category_body = QWidget()
        category_body.setObjectName("nav_categories_body")
        column_layout = QVBoxLayout(category_body)
        column_layout.setContentsMargins(4, 6, 4, 6)
        column_layout.setSpacing(2)
        for key, label, glyph, available in NAV_CATEGORIES:
            button = QToolButton(column)
            color = design.category_color(key) if available else design.palette()["disabled"]
            button.setIcon(icons.icon(glyph, color))
            button.setIconSize(QSize(22, 22))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setCheckable(True)
            button.setFixedHeight(38)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setProperty("nav_category", key)
            button.setAccessibleName(label)
            if available:
                button.setToolTip(f"Mostra {label}")
                button.clicked.connect(
                    lambda _checked=False, k=key: self.set_category(k)
                )
            else:
                button.setEnabled(False)
                button.setToolTip(f"{label}: non disponibile in dBX 0.2")
            column_layout.addWidget(button)
            self._buttons[key] = button
        column_layout.addStretch(1)
        self.category_scroll.setWidget(category_body)
        column_outer.addWidget(self.category_scroll)
        outer.addWidget(column)

        ordered = [self._buttons[key] for key in SELECTABLE_CATEGORIES if key in self._buttons]
        for first, second in zip(ordered, ordered[1:]):
            self.setTabOrder(first, second)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 6, 6, 6)
        right_layout.setSpacing(4)

        directory_row = QHBoxLayout()
        directory_row.addWidget(QLabel("Dir."))
        self.directory_edit = QLineEdit()
        self.directory_edit.setMinimumWidth(40)
        self.directory_edit.setReadOnly(True)
        self.directory_edit.setPlaceholderText("(nessun progetto)")
        self.directory_edit.setToolTip("Cartella del progetto corrente")
        self.directory_edit.setAccessibleName("Directory corrente del progetto")
        directory_row.addWidget(self.directory_edit, 1)
        browse = QToolButton()
        browse.setText("…")
        browse.setToolTip("Apri la cartella del progetto")
        browse.clicked.connect(self._open_directory)
        directory_row.addWidget(browse)
        right_layout.addLayout(directory_row)

        self.filter_combo = QComboBox()
        self.filter_combo.setMinimumWidth(70)
        self.filter_combo.setAccessibleName("Filtro dei file")
        for text, data in FILTERS:
            self.filter_combo.addItem(text, data)
        self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        right_layout.addWidget(self.filter_combo)

        self.list_header = QLabel("Oggetti")
        self.list_header.setObjectName("nav_header")
        right_layout.addWidget(self.list_header)

        self.list = QListWidget()
        self.list.setMinimumWidth(70)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setAccessibleName("Oggetti del progetto")
        self.list.setAlternatingRowColors(False)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        # itemActivated copre già il doppio clic e Invio: collegare anche
        # itemDoubleClicked farebbe partire due volte la stessa azione.
        self.list.itemActivated.connect(self._activate)
        self.list.setToolTip("Doppio clic per aprire, tasto destro per le azioni")
        right_layout.addWidget(self.list, 1)

        self.hint = QLabel("Seleziona una categoria per iniziare.")
        self.hint.setWordWrap(True)
        self.hint.setMinimumWidth(60)
        self.hint.setObjectName("nav_hint")

        right_layout.addWidget(self.hint)
        outer.addWidget(right, 1)

        if ordered:
            self.setTabOrder(ordered[-1], self.directory_edit)
        self.setTabOrder(self.directory_edit, self.filter_combo)
        self.setTabOrder(self.filter_combo, self.list)

        self.setMinimumWidth(200)
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
            untitled = QListWidgetItem(
                icons.icon(CATEGORY_ICONS[category], design.category_color(category)),
                "[Untitled]",
            )
            untitled.setData(Qt.ItemDataRole.UserRole, f"new:{category}")
            untitled.setToolTip(
                f"Nuovo oggetto — {NAV_LABELS.get(category, CATEGORY_LABELS.get(category, category))}"
            )
            self.list.addItem(untitled)
            for name in self.project.names(category):
                item = QListWidgetItem(
                    icons.icon(CATEGORY_ICONS[category], design.category_color(category)),
                    name,
                )
                item.setData(Qt.ItemDataRole.UserRole, f"{category}:{name}")
                item.setToolTip(
                    f"{NAV_LABELS.get(category, category)} — doppio clic per aprire"
                )
                self.list.addItem(item)
                count += 1
        if self.category == "all":
            self.list_header.setText(f"Oggetti ({count})")
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
        menu = DescriptiveMenu(self)

        def add(category: str, description: str, slot) -> None:
            glyph = CATEGORY_ICONS.get(category, "nuovo")
            action = icons.make_action(
                f"Nuovo in {NAV_LABELS.get(category, category)}", glyph, menu
            )
            action.triggered.connect(slot)
            add_entry(menu, action, description)

        def add_expert(category: str) -> None:
            labels = {
                "tables": "Tabella con esperto…",
                "queries": "Query con esperto…",
                "forms": "Form con esperto…",
                "reports": "Report con esperto…",
            }
            action = icons.make_action(labels.get(category, "Nuovo con esperto…"), "esperto", menu)
            action.triggered.connect(
                lambda _checked=False, c=category: self.new_expert.emit(c)
            )
            add_entry(menu, action, f"Crea {NAV_LABELS.get(category, category).lower()} con una procedura guidata")

        if item is None:
            for category in AVAILABLE_CATEGORIES:
                add(
                    category,
                    f"Crea un nuovo oggetto nella categoria {NAV_LABELS.get(category, category)}",
                    lambda _checked=False, c=category: self.new_object.emit(c),
                )
            menu.addSeparator()
            for category in ("tables", "queries", "forms", "reports"):
                add_expert(category)
        else:
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, str) and data.startswith("new:"):
                category = data.split(":", 1)[1]
                add(
                    category,
                    f"Crea un nuovo oggetto in {NAV_LABELS.get(category, category)}",
                    lambda _checked=False, c=category: self.new_object.emit(c),
                )
                if category in ("tables", "queries", "forms", "reports"):
                    add_expert(category)
            elif isinstance(data, str) and ":" in data:
                category, name = data.split(":", 1)
                open_action = icons.make_action("Apri / modifica", "apri", menu)
                open_action.triggered.connect(
                    lambda _checked=False, c=category, n=name: self.open_object.emit(c, n)
                )
                add_entry(menu, open_action, "Apri l'oggetto nel designer o nella vista dati")
                if category == "tables":
                    structure = icons.make_action("Progetta tabella…", "database", menu)
                    structure.triggered.connect(lambda _checked=False, n=name: self.structure_object.emit(n))
                    add_entry(menu, structure, "Modifica campi, indici e relazioni nel Database Editor")
                if category in ("tables", "queries", "forms", "reports", "labels", "scripts"):
                    run = icons.make_action("Esegui", "esegui", menu)
                    run.triggered.connect(
                        lambda _checked=False, c=category, n=name: self.run_object.emit(c, n)
                    )
                    add_entry(menu, run, "Esegui l'oggetto con i dati reali")
                duplicate = icons.make_action("Duplica…", "copia", menu)
                duplicate.triggered.connect(
                    lambda _checked=False, c=category, n=name: self.duplicate_object.emit(c, n)
                )
                add_entry(menu, duplicate, "Crea una copia dell'oggetto con un nuovo nome")
                menu.addSeparator()
                delete = icons.make_action("Elimina", "elimina", menu)
                delete.triggered.connect(
                    lambda _checked=False, c=category, n=name: self.delete_object.emit(c, n)
                )
                add_entry(menu, delete, "Elimina l'oggetto dal progetto")
            menu.addSeparator()
            refresh = icons.make_action("Aggiorna", "aggiorna", menu)
            refresh.triggered.connect(self.refresh)
            add_entry(menu, refresh, "Ricarica l'elenco degli oggetti")
        menu.exec(self.list.viewport().mapToGlobal(position))
