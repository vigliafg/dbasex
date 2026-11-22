"""MiniScript Builder: catalogo azioni, albero, testo e prova (F1–F6)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import FormSpec
from ..core.project import Project, ProjectError
from ..ui import icons
from ..runtime.form_runtime import FormPreviewDialog
from ..runtime.script_engine import (
    ACTIONS,
    NullUI,
    ScriptEngine,
    count_steps,
    from_text,
    new_step,
    to_text,
)


class QtScriptUI(NullUI):
    """Adatta le azioni script ai dialoghi Qt."""

    def __init__(self, project: Project, parent: QWidget) -> None:
        self.project = project
        self.parent = parent

    def message(self, text: str) -> None:
        QMessageBox.information(self.parent, "Script", text)

    def status(self, text: str) -> None:
        window = self.parent.window()
        status = getattr(window, "statusBar", None)
        if callable(status):
            status().showMessage(text, 4000)

    def confirm(self, text: str) -> bool:
        return (
            QMessageBox.question(self.parent, "Conferma", text)
            == QMessageBox.StandardButton.Yes
        )

    def ask(self, prompt: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self.parent, "Script", prompt, text=default)
        return text if ok else None

    def open_form(self, name: str) -> None:
        artifact = self.project.artifact("forms", name)
        if artifact:
            dialog = FormPreviewDialog(self.project, FormSpec.from_dict(artifact), self.parent)
            dialog.exec()

    def print_report(self, name: str) -> None:
        from ..ui.report_preview import ReportPreviewDialog

        dialog = ReportPreviewDialog(self.project, name, self.parent)
        dialog.exec()


class ActionDialog(QDialog):
    """Parametri di una singola azione."""

    def __init__(self, action: str, params: dict[str, Any], project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.action = action
        self.project = project
        self.editors: dict[str, QWidget] = {}
        self.setWindowTitle(f"Azione — {ACTIONS[action]['label']}")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        for key, label, kind in ACTIONS[action]["params"]:
            widget = self._make_editor(kind, str(params.get(key, "")))
            self.editors[key] = widget
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        icons.style_button_box(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(520, 180)

    def _make_editor(self, kind: str, value: str) -> QWidget:
        if kind in ("table", "form", "report", "script"):
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")
            for name in self.project.names({"table": "tables", "form": "forms", "report": "reports", "script": "scripts"}[kind]):
                combo.addItem(name)
            index = combo.findText(value)
            combo.setCurrentIndex(max(0, index))
            return combo
        if kind == "file":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(value)
            browse = QPushButton("…")
            browse.clicked.connect(lambda: self._browse(edit))
            row.addWidget(edit, 1)
            row.addWidget(browse)
            container._edit = edit  # type: ignore[attr-defined]
            return container
        edit = QLineEdit(value)
        if kind == "var":
            edit.setPlaceholderText("nome_variabile")
        return edit

    def _browse(self, edit: QLineEdit) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "File di destinazione", edit.text(), "CSV (*.csv)")
        if path:
            edit.setText(path)

    def params(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, _label, kind in ACTIONS[self.action]["params"]:
            widget = self.editors[key]
            if isinstance(widget, QComboBox):
                result[key] = widget.currentText().strip()
            elif isinstance(widget, QLineEdit):
                result[key] = widget.text().strip()
            else:
                edit = getattr(widget, "_edit", None)
                result[key] = edit.text().strip() if edit is not None else ""
        return result


def _find_container(steps: list[dict[str, Any]], target: dict[str, Any]):
    for index, step in enumerate(steps):
        if step is target:
            return steps, index
        for key in ("then", "else", "steps"):
            child = step.get(key)
            if isinstance(child, list):
                found = _find_container(child, target)
                if found:
                    return found
    return None


class ScriptBuilderDialog(QDialog):
    """Editor a elenco con vista testuale bidirezionale."""

    def __init__(self, project: Project, artifact: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.name = str(artifact.get("name", "script"))
        self.steps: list[dict[str, Any]] = list(artifact.get("steps", []))
        self.setWindowTitle(f"MiniScript Builder — {self.name}")
        self.resize(880, 680)
        self._build_ui()
        self._rebuild_tree()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit(self.name)
        header.addWidget(self.name_edit, 1)
        layout.addLayout(header)

        bar = QHBoxLayout()
        add = icons.make_button("Aggiungi azione", "nuovo", self.add_action, self)
        edit = icons.make_button("Modifica", "modifica", self.edit_action, self)
        remove = icons.make_button("Elimina", "elimina", self.remove_action, self)
        up = icons.make_button("Sposta su", "su", lambda: self.move_action(-1), self)
        down = icons.make_button("Sposta giù", "giu", lambda: self.move_action(1), self)
        run = icons.make_button("Esegui", "esegui", self.run_script, self)
        for button in (add, edit, remove, up, down, run):
            bar.addWidget(button)
        bar.addStretch(1)
        layout.addLayout(bar)

        from PyQt6.QtWidgets import QTabWidget

        self.tabs = QTabWidget()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Azione", "Parametri"])
        self.tree.setColumnWidth(0, 240)
        self.tree.itemDoubleClicked.connect(lambda _item, _col: self.edit_action())
        self.tabs.addTab(self.tree, "Azioni")
        self.text_view = QPlainTextEdit()
        self.text_view.setStyleSheet("font-family: monospace;")
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.addWidget(self.text_view, 1)
        text_bar = QHBoxLayout()
        to_text_button = icons.make_button("Dal testo alle azioni", "ok", self.apply_text, self)
        from_text_button = icons.make_button("Rigenera testo", "aggiorna", self.refresh_text, self)
        text_bar.addWidget(to_text_button)
        text_bar.addWidget(from_text_button)
        text_bar.addStretch(1)
        text_layout.addLayout(text_bar)
        self.tabs.addTab(text_container, "Sorgente")
        layout.addWidget(self.tabs, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        layout.addWidget(self.log)

        buttons = QDialogButtonBox()
        buttons.addButton("Salva", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Annulla", QDialogButtonBox.ButtonRole.RejectRole)
        icons.style_button_box(buttons)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ albero
    def _rebuild_tree(self, select: dict[str, Any] | None = None) -> None:
        self.tree.clear()
        item = self._add_steps(None, self.steps, select)
        if item is not None:
            self.tree.setCurrentItem(item)

    def _add_steps(self, parent: QTreeWidgetItem | None, steps: list[dict[str, Any]], select: dict[str, Any] | None) -> QTreeWidgetItem | None:
        selected_item = None
        for step in steps:
            label = ACTIONS.get(step.get("action", ""), {}).get("label", str(step.get("action")))
            params = ", ".join(f"{k}={v}" for k, v in (step.get("params") or {}).items())
            item = QTreeWidgetItem([label, params])
            item.setData(0, Qt.ItemDataRole.UserRole, step)
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            if step is select:
                selected_item = item
            for key in ("then", "else", "steps"):
                child_steps = step.get(key)
                if isinstance(child_steps, list):
                    self._add_steps(item, child_steps, select)
        if parent is not None and parent.childCount():
            parent.setExpanded(True)
        return selected_item

    def _selected_step(self) -> dict[str, Any] | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    # ---------------------------------------------------------------- azioni
    def add_action(self) -> None:
        keys = list(ACTIONS)
        labels = [ACTIONS[k]["label"] for k in keys]
        label, ok = QInputDialog.getItem(self, "Nuova azione", "Scegli l'azione:", labels, 0, False)
        if not ok:
            return
        action = keys[labels.index(label)]
        dialog = ActionDialog(action, {}, self.project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        step = new_step(action, **dialog.params())
        selected = self._selected_step()
        if selected is not None:
            block_key = "then" if selected.get("action") == "if" else "steps"
            if selected.get("action") in ("if", "foreach", "confirm"):
                selected.setdefault(block_key, []).append(step)
            else:
                found = _find_container(self.steps, selected)
                if found:
                    found[0].insert(found[1] + 1, step)
                else:
                    self.steps.append(step)
        else:
            self.steps.append(step)
        self._rebuild_tree(select=step)

    def edit_action(self) -> None:
        step = self._selected_step()
        if step is None:
            return
        action = step.get("action", "")
        if action not in ACTIONS:
            return
        dialog = ActionDialog(action, step.get("params") or {}, self.project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        step["params"] = dialog.params()
        self._rebuild_tree(select=step)

    def remove_action(self) -> None:
        step = self._selected_step()
        if step is None:
            return
        found = _find_container(self.steps, step)
        if found:
            found[0].pop(found[1])
            self._rebuild_tree()

    def move_action(self, delta: int) -> None:
        step = self._selected_step()
        if step is None:
            return
        found = _find_container(self.steps, step)
        if not found:
            return
        container, index = found
        target = index + delta
        if 0 <= target < len(container):
            container[index], container[target] = container[target], container[index]
            self._rebuild_tree(select=step)

    # ------------------------------------------------------------------ testo
    def refresh_text(self) -> None:
        self.text_view.setPlainText(to_text(self.steps))

    def apply_text(self) -> None:
        try:
            self.steps = from_text(self.text_view.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "Testo non valido", str(exc))
            return
        self._rebuild_tree()
        self.log.appendPlainText(f"Importate {count_steps(self.steps)} azioni dal testo")

    # ------------------------------------------------------------------ esecuzione
    def run_script(self) -> None:
        ui = QtScriptUI(self.project, self)
        engine = ScriptEngine(self.project, ui)
        result = engine.run(self.steps)
        self.log.clear()
        for line in result.log:
            self.log.appendPlainText(line)
        if result.error:
            self.log.appendPlainText(f"ERRORE: {result.error}")

    # ------------------------------------------------------------------ salvataggio
    def save(self) -> None:
        name = self.name_edit.text().strip() or self.name
        artifact = {"name": name, "steps": self.steps}
        try:
            self.project.put_object("scripts", artifact, previous_name=self.name)
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return
        self.name = name
        self.accept()
