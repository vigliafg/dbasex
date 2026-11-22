"""Menu Designer minimale: voci e azioni (G2)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.project import Project, ProjectError

MENU_ACTIONS = {
    "open_form": "Apri form",
    "open_report": "Apri report",
    "run_script": "Esegui script",
    "separator": "Separatore",
    "quit": "Esci",
}


class MenuBuilderDialog(QDialog):
    def __init__(self, project: Project, artifact: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.name = str(artifact.get("name", "principale"))
        self.items = [dict(item) for item in artifact.get("items", [])]
        self.setWindowTitle(f"Menu Designer — {self.name}")
        self.resize(720, 480)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Nome menu:"))
        self.name_edit = QLineEdit(self.name)
        header.addWidget(self.name_edit, 1)
        layout.addLayout(header)
        self.grid = QTableWidget(0, 3)
        self.grid.setHorizontalHeaderLabels(["Voce", "Azione", "Destinazione"])
        self.grid.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.grid, 1)
        bar = QHBoxLayout()
        from ..ui import icons

        add = icons.make_button("Aggiungi voce", "nuovo", parent=self)
        add.clicked.connect(self.add_item)
        remove = icons.make_button("Rimuovi voce", "elimina", parent=self)
        remove.clicked.connect(lambda: self.grid.removeRow(self.grid.currentRow()) if self.grid.currentRow() >= 0 else None)
        bar.addWidget(add)
        bar.addWidget(remove)
        bar.addStretch(1)
        layout.addLayout(bar)
        buttons = QDialogButtonBox()
        buttons.addButton("Salva", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Annulla", QDialogButtonBox.ButtonRole.RejectRole)
        icons.style_button_box(buttons)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self) -> None:
        for item in self.items:
            self._add_row(item.get("label", ""), item.get("action", "open_form"), item.get("target", ""))

    def _add_row(self, label: str, action: str, target: str) -> None:
        row = self.grid.rowCount()
        self.grid.insertRow(row)
        self.grid.setItem(row, 0, QTableWidgetItem(label))
        combo = QComboBox()
        for key, text in MENU_ACTIONS.items():
            combo.addItem(text, key)
        combo.setCurrentIndex(max(0, combo.findData(action)))
        self.grid.setCellWidget(row, 1, combo)
        self.grid.setItem(row, 2, QTableWidgetItem(target))

    def add_item(self) -> None:
        self._add_row("Nuova voce", "open_form", "")

    def save(self) -> None:
        items: list[dict[str, Any]] = []
        for row in range(self.grid.rowCount()):
            label = self.grid.item(row, 0).text().strip() if self.grid.item(row, 0) else ""
            combo = self.grid.cellWidget(row, 1)
            action = combo.currentData() if isinstance(combo, QComboBox) else "open_form"
            target = self.grid.item(row, 2).text().strip() if self.grid.item(row, 2) else ""
            if label:
                items.append({"label": label, "action": action, "target": target})
        name = self.name_edit.text().strip() or self.name
        try:
            self.project.put_object("menus", {"name": name, "items": items}, previous_name=self.name)
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return
        self.name = name
        self.accept()
