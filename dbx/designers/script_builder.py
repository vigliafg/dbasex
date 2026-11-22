"""Program Editor MiniScript: azioni, sorgente con numeri di riga e prova (O6).

L'editor è un ``QWidget`` ospitato nell'area MDI. Azioni e forma testuale
restano bidirezionali: l'albero modifica i passi, il testo li rigenera e può
essere reimportato. Il pannello di destra mostra i parametri del passo scelto.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QShortcut,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QApplication,
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
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import FormSpec
from ..core.project import Project, ProjectError
from ..runtime.form_runtime import FormPreviewDialog
from ..runtime.script_engine import (
    ACTIONS,
    GO_RECORD_MODES,
    NullUI,
    ScriptEngine,
    count_steps,
    from_text,
    new_step,
    parameter_values,
    script_parameters,
    to_text,
)
from ..ui import design, icons
from ..ui.script_params import ScriptParametersDialog
from ..ui.widgets import PropertyInspector
from .step_picker import StepPickerDialog

KEYWORDS = (
    "MESSAGE",
    "STATUS",
    "ASK",
    "INTO",
    "SET",
    "FIELD",
    "IF",
    "THEN",
    "ELSE",
    "ELSEIF",
    "ENDIF",
    "CONFIRM",
    "ENDCONFIRM",
    "FOR",
    "EACH",
    "ENDFOR",
    "LOOP",
    "ENDLOOP",
    "EXIT",
    "HALT",
    "COMMENT",
    "SELECT",
    "TABLE",
    "WHERE",
    "ORDER",
    "BY",
    "GO",
    "RECORD",
    "NEW",
    "DUPLICATE",
    "DELETE",
    "NOCONFIRM",
    "COMMIT",
    "REVERT",
    "OPEN",
    "FORM",
    "QUERY",
    "REPORT",
    "PRINT",
    "EXPORT",
    "CSV",
    "TO",
    "SQL",
    "CALL",
    "CUSTOM",
    "DIALOG",
    "BEEP",
)


def _tokens() -> dict[str, str]:
    app = QApplication.instance()
    name = app.property("dbx_theme") if app is not None else None
    return design.palette(name if isinstance(name, str) else None)


class ScriptHighlighter(QSyntaxHighlighter):
    """Evidenzia parole chiave, stringhe, commenti e numeri del MiniScript."""

    def __init__(self, document) -> None:
        super().__init__(document)
        palette = _tokens()
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor(palette["accent"]))
        self.keyword_format.setFontWeight(QFont.Weight.Bold)
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor(palette["error"]))
        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor(palette["disabled"]))
        self.comment_format.setFontItalic(True)
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor(palette["accent"]))
        self.keyword_pattern = re.compile(
            r"\b(" + "|".join(KEYWORDS) + r")\b", re.IGNORECASE
        )
        self.string_pattern = re.compile(r'"(?:[^"]|"")*"')
        self.number_pattern = re.compile(r"\b\d+(?:[.,]\d+)?\b")

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - API Qt
        for match in self.keyword_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.keyword_format)
        for match in self.string_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_format)
        for match in self.number_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_format)
        comment = text.find("#")
        if comment >= 0:
            self.setFormat(comment, len(text) - comment, self.comment_format)


class LineNumberArea(QWidget):
    """Area dei numeri di riga del Program Editor."""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802 - API Qt
        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: D102 - API Qt
        self.editor.paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Editor di codice con numeri di riga, riga corrente e tab a 2 spazi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        font = QFont(design.CODE_FONT.family, int(design.CODE_FONT.size_pt))
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 2)
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_margins)
        self.updateRequest.connect(self._update_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_margins()
        self._highlight_current_line()
        self.highlighter = ScriptHighlighter(self.document())

    def line_number_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margins(self, *_args) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _update_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_margins()

    def resizeEvent(self, event) -> None:  # noqa: D102 - API Qt
        super().resizeEvent(event)
        box = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(box.left(), box.top(), self.line_number_width(), box.height())
        )

    def paint_line_numbers(self, event) -> None:
        palette = _tokens()
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(palette["panel"]))
        painter.setPen(QColor(palette["panel_shadow"]))
        painter.drawLine(
            self.line_number_area.width() - 1,
            event.rect().top(),
            self.line_number_area.width() - 1,
            event.rect().bottom(),
        )
        block = self.firstVisibleBlock()
        number = block.blockNumber() + 1
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        painter.setPen(QColor(palette["ruler_text"]))
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    4,
                    top,
                    self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    int(Qt.AlignmentFlag.AlignRight),
                    str(number),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            number += 1

    def _highlight_current_line(self) -> None:
        palette = _tokens()
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(palette["alternate_bg"]))
        selection.format.setProperty(
            QTextFormat.Property.FullWidthSelection,
            True,
        )
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


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

    def open_query(self, name: str) -> None:
        window = self.parent.window()
        opener = getattr(window, "open_query_results", None)
        if callable(opener):
            opener(name)
            return
        from ..ui.query_results import QueryResultsWidget

        dialog = QDialog(self.parent)
        dialog.setWindowTitle(f"Query Results — {name}")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(QueryResultsWidget(self.project, name, dialog))
        dialog.resize(900, 560)
        dialog.exec()

    def open_report(self, name: str) -> None:
        self.print_report(name)

    def custom_dialog(self, title: str, message: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self.parent, title or "dBX", message, text=default)
        return text if ok else None

    def beep(self) -> None:
        QApplication.beep()

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
        description = QLabel(str(ACTIONS[action].get("description", "")))
        description.setObjectName("nav_hint")
        description.setWordWrap(True)
        layout.addWidget(description)
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
        if kind == "mode":
            combo = QComboBox()
            labels = {
                "first": "Primo",
                "previous": "Precedente",
                "next": "Successivo",
                "last": "Ultimo",
                "number": "Numero",
            }
            for mode in GO_RECORD_MODES:
                combo.addItem(labels.get(mode, mode), mode)
            combo.setCurrentIndex(max(0, combo.findData(value)))
            return combo
        if kind in ("table", "form", "report", "script", "query"):
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")
            category = {
                "table": "tables",
                "form": "forms",
                "report": "reports",
                "script": "scripts",
                "query": "queries",
            }[kind]
            for name in self.project.names(category):
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
                data = widget.currentData()
                result[key] = (
                    str(data) if data is not None else widget.currentText().strip()
                )
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


class ScriptBuilderWidget(QWidget):
    """Program Editor MiniScript con albero azioni, sorgente e inspector."""

    saved = pyqtSignal(str)
    status_message = pyqtSignal(str)

    def __init__(self, project: Project, artifact: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("script_editor")
        self.project = project
        self.name = str(artifact.get("name", "script"))
        self.steps: list[dict[str, Any]] = copy.deepcopy(list(artifact.get("steps", [])))
        self.params: list[dict[str, str]] = script_parameters(artifact)
        self.selected_step: dict[str, Any] | None = None
        self._source_dirty = False
        self._loading = False
        self._saved_state = copy.deepcopy(self.steps)
        self._saved_params = copy.deepcopy(self.params)
        self._saved_name = self.name
        self.setWindowTitle(f"Program Editor ({self.name})")
        self.resize(1140, 740)
        self._build_ui()
        self._rebuild_tree()
        self.refresh_text()
        self._show_step_properties()
        self._refresh_actions()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit(self.name)
        self.name_edit.setPlaceholderText("nome_script")
        self.name_edit.textChanged.connect(self._on_name_changed)
        header.addWidget(self.name_edit, 1)
        self.source_state = QLabel("Sorgente allineata")
        self.source_state.setObjectName("nav_hint")
        header.addWidget(self.source_state)
        layout.addLayout(header)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        for text, glyph, slot, tip in (
            ("Aggiungi azione", "nuovo", self.add_action, "Aggiungi un passo"),
            ("Modifica", "modifica", self.edit_action, "Modifica i parametri del passo"),
            ("Elimina", "elimina", self.remove_action, "Rimuovi il passo"),
            ("Sposta su", "su", lambda: self.move_action(-1), "Sposta il passo su"),
            ("Sposta giù", "giu", lambda: self.move_action(1), "Sposta il passo giù"),
        ):
            bar.addWidget(icons.make_button(text, glyph, slot, self, tip))
        bar.addSpacing(8)
        bar.addWidget(icons.make_button("Esegui", "esegui", self.run_script, self, "Esegui lo script (F5)"))
        bar.addWidget(
            icons.make_button(
                "Parametri",
                "impostazioni",
                self.edit_parameters,
                self,
                "Dichiara i parametri dello script (:nome)",
            )
        )
        bar.addStretch(1)
        self.save_button = icons.make_button("Salva", "salva", self.save, self, "Salva lo script (Ctrl+S)")
        self.save_button.setEnabled(False)
        bar.addWidget(self.save_button)
        layout.addLayout(bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setAccessibleName("Azioni dello script")
        self.tree.setHeaderLabels(["Azione", "Parametri"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setAlternatingRowColors(False)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.tree.itemDoubleClicked.connect(lambda _item, _col: self.edit_action())
        self.splitter.addWidget(self.tree)

        centre = QSplitter(Qt.Orientation.Vertical)
        editor_box = QWidget()
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(2)
        self.text_view = CodeEditor()
        self.text_view.setAccessibleName("Sorgente MiniScript")
        self.text_view.textChanged.connect(self._on_source_changed)
        editor_layout.addWidget(self.text_view, 1)
        text_bar = QHBoxLayout()
        text_bar.setSpacing(2)
        text_bar.addWidget(
            icons.make_button("Dal testo alle azioni", "ok", self.apply_text, self, "Interpreta il sorgente")
        )
        text_bar.addWidget(
            icons.make_button("Rigenera sorgente", "aggiorna", self.refresh_text, self, "Rigenera il testo dalle azioni")
        )
        text_bar.addStretch(1)
        self.count_label = QLabel("")
        text_bar.addWidget(self.count_label)
        editor_layout.addLayout(text_bar)
        centre.addWidget(editor_box)

        self.log = QPlainTextEdit()
        self.log.setAccessibleName("Log di esecuzione")
        self.log.setReadOnly(True)
        self.log.setObjectName("script_log")
        self.log.setFixedHeight(150)
        self.log.setFont(QFont(design.CODE_FONT.family, int(design.CODE_FONT.size_pt)))
        self.log.setPlaceholderText("Log di esecuzione")
        centre.addWidget(self.log)
        centre.setSizes([520, 150])
        self.splitter.addWidget(centre)

        self.inspector = PropertyInspector()
        self.inspector.setMinimumWidth(250)
        self.inspector.property_changed.connect(self._on_property_changed)
        self.splitter.addWidget(self.inspector)
        self.splitter.setSizes([340, 540, 260])
        layout.addWidget(self.splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("nav_hint")
        layout.addWidget(self.status_label)
        self._install_shortcuts()

    def _install_shortcuts(self) -> None:
        self._shortcuts: list[QShortcut] = []
        for sequence, slot in (("Ctrl+S", self.save), ("F5", self.run_script)):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    # ------------------------------------------------------------------ albero
    def _rebuild_tree(self, select: dict[str, Any] | None = None) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        item = self._add_steps(None, self.steps, select)
        self.tree.blockSignals(False)
        if item is not None:
            self.tree.setCurrentItem(item)
        if self.tree.currentItem() is not None:
            self._on_tree_selection()
        self._refresh_actions()

    def _add_steps(
        self,
        parent: QTreeWidgetItem | None,
        steps: list[dict[str, Any]],
        select: dict[str, Any] | None,
        container_key: str = "",
        prefix: tuple[tuple[str, int], ...] = (),
    ) -> QTreeWidgetItem | None:
        selected_item = None
        for index, step in enumerate(steps):
            label = ACTIONS.get(step.get("action", ""), {}).get("label", str(step.get("action")))
            params = ", ".join(f"{key}={value}" for key, value in (step.get("params") or {}).items())
            item = QTreeWidgetItem([label, params])
            path = prefix + ((container_key, index),)
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            if parent is None:
                self.tree.addTopLevelItem(item)
            else:
                parent.addChild(item)
            if step is select:
                selected_item = item
            for child_key in ("then", "else", "steps"):
                child_steps = step.get(child_key)
                if isinstance(child_steps, list):
                    self._add_steps(item, child_steps, select, child_key, path)
        if parent is not None and parent.childCount():
            parent.setExpanded(True)
        return selected_item

    def _step_at(self, path: tuple[tuple[str, int], ...]) -> dict[str, Any] | None:
        container = self.steps
        step: dict[str, Any] | None = None
        for container_key, index in path:
            if container_key:
                if step is None:
                    return None
                container = step.setdefault(container_key, [])
            if not (0 <= index < len(container)):
                return None
            step = container[index]
        return step

    def _on_tree_selection(self) -> None:
        self.selected_step = self._selected_step()
        self._show_step_properties()
        self._refresh_actions()

    def _selected_step(self) -> dict[str, Any] | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(path, tuple):
            return None
        return self._step_at(path)

    # ------------------------------------------------------------- inspector
    def _param_options(self, kind: str) -> list[tuple[str, str]]:
        if kind == "mode":
            labels = {
                "first": "Primo",
                "previous": "Precedente",
                "next": "Successivo",
                "last": "Ultimo",
                "number": "Numero",
            }
            return [(mode, labels.get(mode, mode)) for mode in GO_RECORD_MODES]
        category = {
            "table": "tables",
            "form": "forms",
            "report": "reports",
            "script": "scripts",
            "query": "queries",
        }.get(kind)
        if category is None:
            return []
        return [(name, name) for name in self.project.names(category)]

    def _show_step_properties(self) -> None:
        step = self.selected_step
        if step is None:
            self.inspector.set_properties(
                [
                    (
                        "• Script",
                        [
                            ("name", "Name", "text", self.name, None),
                            ("steps", "Azioni", "ro", str(count_steps(self.steps)), None),
                            (
                                "params",
                                "Parametri",
                                "ro",
                                ", ".join(entry["name"] for entry in self.params)
                                or "(nessuno)",
                                None,
                            ),
                        ],
                    )
                ]
            )
            self.inspector.set_events([])
            self.inspector.set_methods([])
            return
        action = str(step.get("action", ""))
        definition = ACTIONS.get(
            action,
            {"label": action, "category": "", "description": "", "params": []},
        )
        params = step.get("params") or {}
        rows = [
            ("action", "Azione", "ro", definition.get("label", action), None),
            ("category", "Categoria", "ro", definition.get("category", ""), None),
            ("description", "Descrizione", "ro", definition.get("description", ""), None),
            ("label", "Blocchi", "ro", str(count_steps([step])), None),
        ]
        self._loading = True
        for key, label, kind in definition.get("params", []):
            value = str(params.get(key, ""))
            if kind in ("table", "form", "report", "script", "query", "mode"):
                rows.append((f"param:{key}", label, "choice", value, self._param_options(kind)))
            else:
                rows.append((f"param:{key}", label, "text", value, None))
        self.inspector.set_properties([("• Parameters", rows)])
        self.inspector.set_events([])
        self.inspector.set_methods([])
        self._loading = False

    def _on_property_changed(self, key: str, value: Any) -> None:
        if self._loading:
            return
        step = self.selected_step
        if step is None:
            if key == "name":
                self.name_edit.setText(str(value))
            return
        if not key.startswith("param:"):
            return
        param = key.split(":", 1)[1]
        step.setdefault("params", {})[param] = str(value)
        self._rebuild_tree(select=step)
        self.refresh_text()
        self.status_message.emit(f"Parametro {param} aggiornato")

    # --------------------------------------------------------------- comandi
    def _refresh_actions(self) -> None:
        has_selection = self.selected_step is not None
        self.save_button.setEnabled(self.is_dirty())
        self.count_label.setText(f"{count_steps(self.steps)} azioni")
        self.status_label.setText(
            "Sorgente modificata: applica le modifiche o rigenera"
            if self._source_dirty
            else "Pronto"
        )

    def _on_name_changed(self, text: str) -> None:
        self.name = text.strip() or self.name
        self.setWindowTitle(f"Program Editor ({self.name})")
        self._refresh_actions()

    def _on_source_changed(self) -> None:
        if self._loading:
            return
        self._source_dirty = True
        self.source_state.setText("Sorgente modificata")
        self._refresh_actions()

    def add_action(self) -> None:
        picker = StepPickerDialog(self)
        if picker.exec() != QDialog.DialogCode.Accepted:
            return
        action = picker.selected_action()
        if action not in ACTIONS:
            return
        dialog = ActionDialog(action, {}, self.project, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        step = new_step(action, **dialog.params())
        selected = self.selected_step
        if selected is not None:
            if selected.get("action") in ("if", "foreach", "confirm"):
                block_key = "then" if selected.get("action") == "if" else "steps"
                selected.setdefault(block_key, []).append(step)
            else:
                found = _find_container(self.steps, selected)
                if found:
                    found[0].insert(found[1] + 1, step)
                else:
                    self.steps.append(step)
        else:
            self.steps.append(step)
        self.selected_step = step
        self._rebuild_tree(select=step)
        self.refresh_text()
        self._refresh_actions()

    def edit_action(self) -> None:
        step = self.selected_step
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
        self.refresh_text()
        self._show_step_properties()

    def remove_action(self) -> None:
        step = self.selected_step
        if step is None:
            return
        found = _find_container(self.steps, step)
        if found:
            found[0].pop(found[1])
            self.selected_step = None
            self._rebuild_tree()
            self.refresh_text()
            self._show_step_properties()

    def move_action(self, delta: int) -> None:
        step = self.selected_step
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
            self.refresh_text()

    # ------------------------------------------------------------------ testo
    def refresh_text(self) -> None:
        self._loading = True
        self.text_view.setPlainText(to_text(self.steps))
        self._loading = False
        self._source_dirty = False
        self.source_state.setText("Sorgente allineata")
        self._refresh_actions()

    def apply_text(self) -> None:
        try:
            self.steps = from_text(self.text_view.toPlainText())
        except Exception as exc:
            QMessageBox.warning(self, "Sorgente non valida", str(exc))
            return
        self.selected_step = None
        self._rebuild_tree()
        self._show_step_properties()
        self._source_dirty = False
        self.source_state.setText("Sorgente applicata")
        self.log.appendPlainText(f"Importate {count_steps(self.steps)} azioni dal testo")
        self._refresh_actions()

    # ----------------------------------------------------------- esecuzione
    def edit_parameters(self) -> None:
        dialog = ScriptParametersDialog(self.params, self, self.name)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.params = dialog.parameters()
        self._show_step_properties()
        self._refresh_actions()
        self.status_message.emit(
            f"{len(self.params)} parametri dichiarati" if self.params else "Nessun parametro"
        )

    def run_script(self) -> None:
        if self._source_dirty:
            self.apply_text()
        ui = QtScriptUI(self.project, self)
        engine = ScriptEngine(self.project, ui)
        values = parameter_values({"params": self.params})
        result = engine.run(self.steps, params=values)
        self.log.clear()
        for line in result.log:
            self.log.appendPlainText(line)
        if result.error:
            self.log.appendPlainText(f"ERRORE: {result.error}")
            self.status_message.emit("Script non eseguito: controlla il log")
        else:
            self.status_message.emit("Script eseguito")
        self._refresh_actions()

    # ------------------------------------------------------------- salvataggio
    def is_dirty(self) -> bool:
        return (
            self.steps != self._saved_state
            or self.params != self._saved_params
            or self.name != self._saved_name
        )

    def save(self) -> bool:
        name = self.name_edit.text().strip() or self.name
        artifact = {"name": name, "params": copy.deepcopy(self.params), "steps": self.steps}
        try:
            self.project.put_object("scripts", artifact, previous_name=self.name)
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self.name = name
        self._saved_name = name
        self._saved_state = copy.deepcopy(self.steps)
        self._saved_params = copy.deepcopy(self.params)
        self._refresh_actions()
        self.saved.emit(name)
        self.status_message.emit(f"Script {name} salvato")
        return True


# Compatibilità con il nome storico usato da smoke, test e capture.
ScriptBuilderDialog = ScriptBuilderWidget
