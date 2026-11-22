"""Runtime dei form: costruzione widget, navigazione e CRUD (D6, D7)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QPixmap

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.form_model import FIELD_KINDS, FormControl, FormSpec
from ..core.metadata import Table
from ..ui import icons
from .rowset import Rowset, RowsetError


class FieldBinder:
    """Collega un widget al campo di una tabella."""

    def __init__(self, control: FormControl, widget: QWidget, table: Table | None) -> None:
        self.control = control
        self.widget = widget
        self.field = table.field(control.field) if table else None

    def set_value(self, value: Any) -> None:
        widget = self.widget
        if isinstance(widget, QLineEdit):
            widget.setText("" if value is None else T.format_value(value, self.field.type, self.field.fmt) if self.field else str(value))
        elif isinstance(widget, QPlainTextEdit):
            widget.setPlainText("" if value is None else str(value))
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value or 0))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value or 0))
        elif isinstance(widget, QComboBox):
            index = widget.findData(value)
            if index < 0:
                index = widget.findText("" if value is None else str(value))
            widget.setCurrentIndex(index if index >= 0 else -1)
        elif isinstance(widget, QDateEdit):
            if value:
                widget.setDate(value if hasattr(value, "year") else widget.date())

    def get_value(self) -> Any:
        widget = self.widget
        if isinstance(widget, QLineEdit):
            if self.field is None:
                return widget.text()
            return T.parse_input(widget.text(), self.field.type)
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QComboBox):
            return widget.currentData()
        if isinstance(widget, QDateEdit):
            return widget.date().toString("yyyy-MM-dd")
        return None


class FormRuntime(QWidget):
    """Form eseguibile: una pagina per scheda, navigazione e salvataggio."""

    def __init__(self, project, spec: FormSpec, record_id: int | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.table = project.require_table(spec.table)
        self.rowset = Rowset(project.db, self.table).open(order=spec.order or "")
        self.binders: list[FieldBinder] = []
        self.buttons: list[tuple[QPushButton, str]] = []
        self.grids: list[tuple[QTableWidget, FormControl]] = []
        self._new = False
        self._status = QLabel("")
        self._toolbar = QHBoxLayout()
        self._pages = QTabWidget()
        self._build_ui()
        if record_id is not None:
            for index, row in enumerate(self.rowset.rows()):
                if row.get(INTERNAL_ID) == record_id:
                    self.rowset.goto(index)
                    break
        elif self.rowset.current is None and self.rowset.count():
            self.rowset.first()
        self.load_current()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(self._toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._pages)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._status)
        self.setWindowTitle(self.spec.caption or self.spec.name)
        for page in self.spec.pages:
            surface = QWidget()
            surface.setFixedSize(self.spec.width, self.spec.height)
            self._pages.addTab(surface, page.caption or "Dati")
            for control in page.controls:
                self._add_control(surface, control)
        self._add_nav_buttons()

    def _add_nav_buttons(self) -> None:
        for caption, action, glyph, tip in (
            ("Primo", "first", "primo", "Primo record"),
            ("Prec.", "previous", "precedente", "Record precedente"),
            ("Succ.", "next", "successivo", "Record successivo"),
            ("Ultimo", "last", "ultimo", "Ultimo record"),
            ("Nuovo", "new", "nuovo", "Nuovo record"),
            ("Salva", "save", "salva", "Salva il record"),
            ("Elimina", "delete", "elimina", "Elimina il record"),
        ):
            button = icons.make_button(
                caption, glyph, lambda _checked=False, a=action: self.perform(a), self, tip
            )
            button.setAutoDefault(False)
            self._toolbar.addWidget(button)
        self._toolbar.addStretch(1)
        close = icons.make_button("Chiudi", "chiudi", self._close, self)
        self._toolbar.addWidget(close)

    def _add_control(self, surface: QWidget, control: FormControl) -> None:
        kind = control.kind
        widget: QWidget | None = None
        if kind == "label":
            widget = QLabel(control.text)
            if control.bold:
                font = widget.font()
                font.setBold(True)
                font.setPointSize(control.font_size)
                widget.setFont(font)
        elif kind in ("field", "memo", "date"):
            widget = QPlainTextEdit() if kind == "memo" else QLineEdit()
            if kind == "date":
                widget.setPlaceholderText("AAAA-MM-GG oppure GG/MM/AAAA")
            binder = FieldBinder(control, widget, self.table)
            self.binders.append(binder)
        elif kind == "checkbox":
            widget = QCheckBox(control.text)
            binder = FieldBinder(control, widget, self.table)
            self.binders.append(binder)
        elif kind == "number":
            field = self.table.field(control.field)
            if field is not None and field.type == T.INTEGER:
                widget = QSpinBox()
                widget.setRange(-2_000_000_000, 2_000_000_000)
            else:
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(2)
            binder = FieldBinder(control, widget, self.table)
            self.binders.append(binder)
        elif kind == "combo":
            widget = QComboBox()
            self._populate_combo(widget, control)
            binder = FieldBinder(control, widget, self.table)
            self.binders.append(binder)
        elif kind == "button":
            button = QPushButton(control.text or "…")
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, a=control.action: self.perform(a))
            widget = button
        elif kind == "grid":
            grid = QTableWidget()
            widget = grid
            self.grids.append((grid, control))
        elif kind == "line":
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            widget = line
        elif kind == "rect":
            rect = QFrame()
            rect.setFrameShape(QFrame.Shape.StyledPanel)
            widget = rect
        elif kind == "image":
            label = QLabel()
            if control.text and control.text.startswith("/"):
                pixmap = QPixmap(control.text)
                if not pixmap.isNull():
                    label.setPixmap(pixmap.scaled(control.w, control.h, Qt.AspectRatioMode.KeepAspectRatio))
            widget = label
        if widget is None:
            return
        widget.setParent(surface)
        widget.setGeometry(control.x, control.y, max(8, control.w), max(8, control.h))
        if control.kind in FIELD_KINDS and not isinstance(widget, QComboBox):
            font = widget.font()
            font.setBold(control.bold)
            font.setPointSize(max(6, control.font_size))
            widget.setFont(font)
        widget.show()

    def _populate_combo(self, combo: QComboBox, control: FormControl) -> None:
        combo.clear()
        combo.addItem("", None)
        if not control.lookup or "." not in control.lookup:
            return
        table_name, field_name = control.lookup.split(".", 1)
        table = self.project.table(table_name)
        if table is None:
            return
        display = table.field(field_name)
        if display is None:
            return
        for row in self.project.db.query(f'SELECT * FROM "{table.name}" ORDER BY "{display.name}"'):
            combo.addItem(str(row[display.name]), row[display.name])

    # ------------------------------------------------------------- load/save
    def load_current(self) -> None:
        record = self.rowset.current
        for binder in self.binders:
            binder.set_value(record.get(binder.control.field) if record else None)
        self._refresh_grids(record)
        self._update_status()

    def _refresh_grids(self, record: dict[str, Any] | None) -> None:
        for grid, control in self.grids:
            child = self.project.table(control.table)
            grid.clear()
            if child is None:
                continue
            grid.setColumnCount(len(child.fields))
            grid.setHorizontalHeaderLabels([f.display_name() for f in child.fields])
            rows: list[dict[str, Any]] = []
            if record is not None and control.link_parent:
                value = record.get(control.link_parent)
                if value is None:
                    rows = []
                else:
                    rows = Rowset(self.project.db, child).open(
                        where=f'"{control.link_child or control.link_parent}" = ?', params=(value,)
                    ).rows()
            grid.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, field in enumerate(child.fields):
                    item = QTableWidgetItem(T.format_value(row.get(field.name), field.type, field.fmt))
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    grid.setItem(r, c, item)
            grid.resizeColumnsToContents()

    def collect(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        record = self.rowset.current or {}
        if not self._new and record.get(INTERNAL_ID) is not None:
            values[INTERNAL_ID] = record[INTERNAL_ID]
        for binder in self.binders:
            values[binder.control.field] = binder.get_value()
        return values

    def save(self) -> bool:
        try:
            record_id = self.rowset.save(self.collect())
        except RowsetError as exc:
            QMessageBox.warning(self, "Salvataggio non riuscito", str(exc))
            return False
        self._new = False
        self._select_record(record_id)
        self.load_current()
        self._status.setText("Record salvato")
        return True

    def _select_record(self, record_id: int) -> None:
        for index, row in enumerate(self.rowset.rows()):
            if row.get(INTERNAL_ID) == record_id:
                self.rowset.goto(index)
                return

    def perform(self, action: str) -> None:
        if action == "new":
            self._new = True
            blank = self.rowset.new_record()
            for binder in self.binders:
                binder.set_value(blank.get(binder.control.field))
            self._refresh_grids(None)
            self._status.setText("Nuovo record: compila e salva")
            return
        if action == "save":
            self.save()
            return
        if action == "delete":
            if self.rowset.current is None:
                return
            answer = QMessageBox.question(self, "Elimina", "Eliminare il record corrente?")
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                self.rowset.delete()
            except RowsetError as exc:
                QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
                return
            self.rowset.first()
            self.load_current()
            self._status.setText("Record eliminato")
            return
        if action in ("first", "previous", "next", "last"):
            self._new = False
            getattr(self.rowset, action)()
            self.load_current()
            return
        if action == "close":
            self._close()
            return
        if action.startswith("script:"):
            self._run_script(action.split(":", 1)[1])
            return
        if action.startswith("report:"):
            self._print_report(action.split(":", 1)[1])
            return

    def _run_script(self, name: str) -> None:
        from .script_engine import ScriptEngine

        engine = ScriptEngine(self.project)
        result = engine.run_named(name, self.rowset.current)
        if result.error:
            QMessageBox.warning(self, "Script", result.error)
        else:
            self._status.setText("Script eseguito")

    def _print_report(self, name: str) -> None:
        from ..ui.report_preview import ReportPreviewDialog

        dialog = ReportPreviewDialog(self.project, name, self)
        dialog.exec()

    def _close(self) -> None:
        window = self.window()
        if isinstance(window, QDialog):
            window.accept()
        else:
            window.close()

    def _update_status(self) -> None:
        position = self.rowset.index + 1 if self.rowset.current else 0
        total = max(self.rowset.count(), len(self.rowset))
        self._status.setText(f"Record {position} di {total}")


class FormPreviewDialog(QDialog):
    """Anteprima live di un form con dati reali (D11)."""

    def __init__(self, project, spec: FormSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Anteprima — {spec.caption or spec.name}")
        layout = QVBoxLayout(self)
        self.runtime = FormRuntime(project, spec, parent=self)
        layout.addWidget(self.runtime)
        self.resize(760, 620)
