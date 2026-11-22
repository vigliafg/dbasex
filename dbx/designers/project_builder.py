"""Validazione del progetto e build distribuibile (G5, G6)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import FormSpec, form_references
from ..core.metadata import validate_project_tables
from ..core.project import Project
from ..runtime.report_engine import ReportSpec
from ..runtime.script_engine import ACTIONS


class BuildError(RuntimeError):
    """Errore di build o di validazione bloccante."""


def validate_project(project: Project) -> list[str]:
    """Controlla struttura, riferimenti incrociati e oggetti mancanti."""
    errors: list[str] = []
    tables = project.tables()
    errors.extend(validate_project_tables(tables.values()))
    table_names = {name.lower() for name in tables}
    form_names = {name.lower() for name in project.names("forms")}
    report_names = {name.lower() for name in project.names("reports")}
    script_names = {name.lower() for name in project.names("scripts")}

    for name, artifact in project.objects["forms"].items():
        spec = FormSpec.from_dict(artifact)
        for error in spec.validate():
            errors.append(f"Form {name}: {error}")
        for table in form_references(spec):
            if table and table.lower() not in table_names:
                errors.append(f"Form {name}: tabella inesistente {table}")

    for name, artifact in project.objects["reports"].items():
        spec = ReportSpec.from_dict(artifact)
        for error in spec.validate():
            errors.append(f"Report {name}: {error}")
        if spec.table and spec.table.lower() not in table_names:
            errors.append(f"Report {name}: tabella inesistente {spec.table}")

    for name, artifact in project.objects["scripts"].items():
        for error in _validate_steps(artifact.get("steps", []), table_names, form_names, report_names, script_names):
            errors.append(f"Script {name}: {error}")

    for name, artifact in project.objects["menus"].items():
        for item in artifact.get("items", []):
            action = item.get("action")
            target = str(item.get("target", "")).lower()
            if action == "open_form" and target and target not in form_names:
                errors.append(f"Menu {name}: form inesistente {item.get('target')}")
            if action == "open_report" and target and target not in report_names:
                errors.append(f"Menu {name}: report inesistente {item.get('target')}")
            if action == "run_script" and target and target not in script_names:
                errors.append(f"Menu {name}: script inesistente {item.get('target')}")

    main_form = str(project.settings.get("main_form", "")).lower()
    if main_form and main_form not in form_names:
        errors.append(f"Form principale inesistente: {project.settings.get('main_form')}")
    return errors


def _validate_steps(
    steps: list[dict[str, Any]],
    table_names: set[str],
    form_names: set[str],
    report_names: set[str],
    script_names: set[str],
) -> list[str]:
    errors: list[str] = []
    for step in steps:
        action = step.get("action")
        params = step.get("params") or {}
        if action not in ACTIONS:
            errors.append(f"azione sconosciuta {action}")
            continue
        if action in ("open_form",) and str(params.get("form", "")).lower() not in form_names:
            errors.append(f"form inesistente {params.get('form')}")
        if action == "print_report" and str(params.get("report", "")).lower() not in report_names:
            errors.append(f"report inesistente {params.get('report')}")
        if action in ("foreach", "export_csv"):
            table_name = str(params.get("table", "")).lower()
            if table_name and table_name not in table_names:
                errors.append(f"tabella inesistente {params.get('table')}")
        if action == "call" and str(params.get("script", "")).lower() not in script_names:
            errors.append(f"script inesistente {params.get('script')}")
        for key in ("then", "else", "steps"):
            child = step.get(key)
            if isinstance(child, list):
                errors.extend(_validate_steps(child, table_names, form_names, report_names, script_names))
    return errors


def build_project(project: Project, target: Path, make_zip: bool = True) -> Path:
    """Copia artefatti e dati in una cartella distribuibile (+ zip)."""
    errors = validate_project(project)
    if errors:
        raise BuildError("Validazione non superata:\n" + "\n".join(errors))
    project.save()
    base = Path(target) / project.name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    shutil.copytree(project.objects_path, base / "objects")
    base.joinpath("data").mkdir()
    project.db.con.commit()
    if project.database_file.exists():
        shutil.copy2(project.database_file, base / "data" / project.database_file.name)
    shutil.copy2(project.manifest_path, base / "project.dbx.json")
    (base / "LEGGIMI.txt").write_text(
        "Applicazione dBX\n\n"
        f"Progetto: {project.name}\n"
        "Avvio: apri il progetto con dBX (File > Apri progetto) oppure esegui\n"
        f"  dbx \"{base / 'project.dbx.json'}\"\n",
        encoding="utf-8",
    )
    if not make_zip:
        return base
    archive = Path(target) / f"{project.name}.dbx.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(base.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(base))
    return archive


def package_with_pyinstaller(project: Project, target: Path) -> Path:
    """Crea un eseguibile con PyInstaller, se installato (G7)."""
    import shutil as _shutil
    import subprocess
    import sys

    if _shutil.which("pyinstaller") is None:
        raise BuildError(
            "PyInstaller non è installato. Installa con 'pip install pyinstaller' oppure distribuisci il progetto con il build zip."
        )
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    project_path = project.manifest_path
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        f"dbx_{project.name}",
        "--distpath",
        str(target),
        "--workpath",
        str(target / ".build"),
        "--specpath",
        str(target / ".build"),
        str(Path(__file__).resolve().parents[2] / "run_dbx.py"),
        "--",
        str(project_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise BuildError(result.stderr[-2000:] or "PyInstaller non riuscito")
    return target / f"dbx_{project.name}"


# --------------------------------------------------------------------------- #
# Project Editor (O6)
# --------------------------------------------------------------------------- #
CATEGORY_LABELS = {
    "tables": "Tabelle",
    "forms": "Form",
    "reports": "Report",
    "scripts": "Programmi",
    "menus": "Menu",
}


class ProjectEditorWidget(QWidget):
    """Project Editor: oggetti, impostazioni, validazione e build distribuibile."""

    open_object = pyqtSignal(str, str)
    saved = pyqtSignal()
    status_message = pyqtSignal(str)

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("project_editor")
        self.project = project
        self.setWindowTitle(f"Project Editor ({project.name})")
        self.resize(900, 620)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(QLabel(f"Progetto: {self.project.name}"))
        self.path_label = QLabel(str(self.project.path))
        self.path_label.setObjectName("nav_hint")
        header.addWidget(self.path_label, 1)
        layout.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setAccessibleName("Oggetti del progetto")
        self.tree.setHeaderLabels(["Oggetto", "Tipo"])
        self.tree.setColumnWidth(0, 240)
        self.tree.itemDoubleClicked.connect(self._activate)
        splitter.addWidget(self.tree)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(6)

        settings = QWidget()
        form = QFormLayout(settings)
        form.setContentsMargins(0, 0, 0, 0)
        self.title_edit = QLineEdit(str(self.project.settings.get("title", self.project.caption)))
        form.addRow("Titolo applicazione", self.title_edit)
        self.form_combo = QComboBox()
        self.form_combo.addItem("(nessuno)", "")
        form.addRow("Form principale", self.form_combo)
        self.menu_combo = QComboBox()
        self.menu_combo.addItem("(nessuno)", "")
        form.addRow("Menu principale", self.menu_combo)
        right_layout.addWidget(settings)
        save_settings = QPushButton("Salva impostazioni")
        save_settings.clicked.connect(self.save_settings)
        right_layout.addWidget(save_settings)

        right_layout.addWidget(QLabel("Validazione"))
        self.validation = QPlainTextEdit()
        self.validation.setReadOnly(True)
        self.validation.setFixedHeight(130)
        right_layout.addWidget(self.validation)
        validate = QPushButton("Valida progetto")
        validate.clicked.connect(self.validate_now)
        right_layout.addWidget(validate)

        right_layout.addWidget(QLabel("Build distribuibile"))
        build_row = QHBoxLayout()
        self.destination_edit = QLineEdit()
        self.destination_edit.setPlaceholderText("Cartella di destinazione")
        build_row.addWidget(self.destination_edit, 1)
        browse = QPushButton("…")
        browse.clicked.connect(self.choose_destination)
        build_row.addWidget(browse)
        right_layout.addLayout(build_row)
        build_button = QPushButton("Build distribuibile…")
        build_button.clicked.connect(self.build)
        right_layout.addWidget(build_button)
        right_layout.addStretch(1)
        splitter.addWidget(right)
        splitter.setSizes([430, 430])
        layout.addWidget(splitter, 1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("nav_hint")
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------ dati
    def refresh(self) -> None:
        self.tree.clear()
        for category, label in CATEGORY_LABELS.items():
            names = self.project.names(category)
            parent = QTreeWidgetItem([f"{label} ({len(names)})", ""])
            parent.setData(0, Qt.ItemDataRole.UserRole, ("", ""))
            self.tree.addTopLevelItem(parent)
            for name in names:
                child = QTreeWidgetItem([name, label])
                child.setData(0, Qt.ItemDataRole.UserRole, (category, name))
                parent.addChild(child)
            parent.setExpanded(True)
        self.path_label.setText(str(self.project.path))
        self.form_combo.clear()
        self.form_combo.addItem("(nessuno)", "")
        for name in self.project.names("forms"):
            self.form_combo.addItem(name, name)
        index = self.form_combo.findData(str(self.project.settings.get("main_form", "")))
        self.form_combo.setCurrentIndex(max(0, index))
        self.menu_combo.clear()
        self.menu_combo.addItem("(nessuno)", "")
        for name in self.project.names("menus"):
            self.menu_combo.addItem(name, name)
        index = self.menu_combo.findData(str(self.project.settings.get("main_menu", "")))
        self.menu_combo.setCurrentIndex(max(0, index))
        self.validate_now()

    def _activate(self, item, _column: int) -> None:
        category, name = item.data(0, Qt.ItemDataRole.UserRole) or ("", "")
        if category and name:
            self.open_object.emit(str(category), str(name))

    # -------------------------------------------------------------- impostazioni
    def save_settings(self) -> None:
        self.project.settings["title"] = self.title_edit.text().strip()
        self.project.settings["main_form"] = str(self.form_combo.currentData() or "")
        self.project.settings["main_menu"] = str(self.menu_combo.currentData() or "")
        try:
            self.project.save()
        except OSError as exc:
            QMessageBox.warning(self, "Salvataggio non riuscito", str(exc))
            return
        self.saved.emit()
        self.status_message.emit("Impostazioni del progetto salvate")
        self.status_label.setText("Impostazioni salvate")

    def is_dirty(self) -> bool:
        settings = self.project.settings
        return (
            self.title_edit.text().strip() != str(settings.get("title", self.project.caption))
            or str(self.form_combo.currentData() or "") != str(settings.get("main_form", ""))
            or str(self.menu_combo.currentData() or "") != str(settings.get("main_menu", ""))
        )

    # ------------------------------------------------------------------ azioni
    def validate_now(self) -> list[str]:
        errors = validate_project(self.project)
        if errors:
            self.validation.setPlainText("\n".join(errors))
            self.status_label.setText(f"{len(errors)} problemi rilevati")
        else:
            self.validation.setPlainText("Nessun problema rilevato.")
            self.status_label.setText("Progetto valido")
        return errors

    def choose_destination(self) -> str:
        folder = QFileDialog.getExistingDirectory(
            self, "Cartella di destinazione del build", self.destination_edit.text()
        )
        if folder:
            self.destination_edit.setText(folder)
        return folder

    def build(self) -> Path | None:
        folder = self.destination_edit.text().strip()
        if not folder:
            folder = self.choose_destination()
        if not folder:
            return None
        try:
            target = build_project(self.project, Path(folder))
        except BuildError as exc:
            QMessageBox.warning(self, "Build non riuscita", str(exc))
            self.status_label.setText("Build non riuscita")
            return None
        self.status_message.emit(f"Build creata: {target.name}")
        self.status_label.setText(f"Build creata: {target}")
        return target
