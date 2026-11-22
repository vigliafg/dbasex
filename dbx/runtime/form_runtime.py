"""Runtime dei form: costruzione widget, navigazione, CRUD ed eventi (D6, D7).

Gli eventi non sono un linguaggio di scripting: il valore di ``onClick``,
``onEnter``, ``onExit``, ``onOpen`` e ``onClose`` è un'azione singola dello
stesso dispatcher usato dai pulsanti (``save``, ``next``, ``script:nome``,
``report:nome``, ``message:testo``, ...). Un evento vuoto lascia attiva
l'azione predefinita del controllo; un evento valorizzato la sostituisce.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
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

from ..core import types as T
from ..core.ddl import INTERNAL_ID
from ..core.form_model import FIELD_KINDS, FormControl, FormSpec
from ..core.metadata import Table
from ..core.query_engine import QueryError, query_table, run_query
from ..core.query_model import QuerySpec
from ..ui import icons
from .query_rowset import QueryRowset
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
            if value is None:
                widget.clear()
            elif self.field is not None:
                widget.setText(T.format_value(value, self.field.type, self.field.fmt))
            else:
                widget.setText(str(value))
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
            if value and hasattr(value, "year"):
                widget.setDate(value)

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


class FormScriptUI:
    """Adattatore minimale tra ScriptEngine e il runtime del form."""

    def __init__(self, runtime: "FormRuntime") -> None:
        self.runtime = runtime
        self.project = runtime.project
        self.parent = runtime

    def message(self, text: str) -> None:
        QMessageBox.information(self.parent, "Script", text)

    def status(self, text: str) -> None:
        self.runtime._status.setText(text)

    def confirm(self, text: str) -> bool:
        return (
            QMessageBox.question(self.parent, "Conferma", text)
            == QMessageBox.StandardButton.Yes
        )

    def ask(self, prompt: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self.parent, "Script", prompt, text=default)
        return text if ok else None

    def custom_dialog(self, title: str, message: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self.parent, title or "dBX", message, text=default)
        return text if ok else None

    def open_form(self, name: str) -> None:
        artifact = self.project.artifact("forms", name)
        if artifact:
            dialog = FormPreviewDialog(
                self.project, FormSpec.from_dict(artifact), self.parent
            )
            dialog.exec()

    def open_query(self, name: str) -> None:
        window = self.parent.window()
        opener = getattr(window, "open_query_results", None)
        if callable(opener):
            opener(name)
            return
        self.runtime._status.setText(f"Query {name}: apri i risultati dal Navigator")

    def open_report(self, name: str) -> None:
        self.runtime._print_report(name)

    def print_report(self, name: str) -> None:
        self.runtime._print_report(name)

    def beep(self) -> None:
        QApplication.beep()

    def refresh(self) -> None:
        if self.runtime.read_only:
            return
        try:
            self.runtime.rowset.refresh()
            self.runtime.load_current()
        except RowsetError:
            return


class FormRuntime(QWidget):
    """Form eseguibile: una pagina per scheda, navigazione, CRUD ed eventi."""

    def __init__(
        self,
        project,
        spec: FormSpec,
        record_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("form_runtime")
        self.project = project
        self.spec = spec
        self.read_only = spec.source_type == "query"
        if self.read_only:
            query_spec = QuerySpec.from_project(project, spec.query)
            if query_spec is None:
                raise ValueError(f"Query del form inesistente: {spec.query}")
            try:
                self.table = query_table(project, spec.query)
                result = run_query(project, query_spec)
            except QueryError as exc:
                raise ValueError(f"Query del form non valida: {exc}") from exc
            self.rowset = QueryRowset(result, order=spec.order or "")
        else:
            self.table = project.require_table(spec.table)
            self.rowset = Rowset(project.db, self.table).open(order=spec.order or "")
        self.binders: list[FieldBinder] = []
        self.buttons: list[tuple[QPushButton, str]] = []
        self.grids: list[tuple[QTableWidget, FormControl]] = []
        self.event_log: list[str] = []
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
        self._run_form_event("onOpen")

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(self._toolbar)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._pages)
        layout.addWidget(scroll, 1)
        self._status.setObjectName("runtime_status")
        layout.addWidget(self._status)
        self.setWindowTitle(self.spec.caption or self.spec.name)
        for page in self.spec.pages:
            surface = QWidget()
            surface.setFixedSize(self.spec.width, self.spec.height)
            if self.spec.backcolor:
                surface.setStyleSheet(f"background: {self.spec.backcolor};")
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
            if self.read_only and action in ("new", "save", "delete"):
                button.setEnabled(False)
                button.setToolTip("Form su query: sorgente in sola lettura")
            self._toolbar.addWidget(button)
        self._toolbar.addStretch(1)
        close = icons.make_button("Chiudi", "chiudi", self._close, self, "Chiude il form")
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
            self._bind(control, widget)
        elif kind == "checkbox":
            widget = QCheckBox(control.text)
            self._bind(control, widget)
        elif kind == "number":
            field = self.table.field(control.field)
            if field is not None and field.type == T.INTEGER:
                widget = QSpinBox()
                widget.setRange(-2_000_000_000, 2_000_000_000)
            else:
                widget = QDoubleSpinBox()
                widget.setRange(-1e12, 1e12)
                widget.setDecimals(2)
            self._bind(control, widget)
        elif kind == "combo":
            widget = QComboBox()
            self._populate_combo(widget, control)
            self._bind(control, widget)
        elif kind == "button":
            button = QPushButton(control.text or "…")
            button.setAutoDefault(False)
            button.clicked.connect(lambda _checked=False, c=control: self._activate_button(c))
            if self.read_only and control.action in ("new", "save", "delete"):
                button.setEnabled(False)
                button.setToolTip("Form su query: sorgente in sola lettura")
            widget = button
            self.buttons.append((button, control.id))
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
                    label.setPixmap(
                        pixmap.scaled(control.w, control.h, Qt.AspectRatioMode.KeepAspectRatio)
                    )
            widget = label
        if widget is None:
            return
        if control.kind in FIELD_KINDS:
            bound = self.table.field(control.field)
            if bound is not None and not bound.stored:
                if hasattr(widget, "setReadOnly"):
                    widget.setReadOnly(True)
                else:
                    widget.setEnabled(False)
                widget.setToolTip("Campo calcolato: valore non modificabile")
        widget.setParent(surface)
        widget.setGeometry(control.x, control.y, max(8, control.w), max(8, control.h))
        if control.backcolor or control.forecolor:
            widget.setStyleSheet(
                f"background: {control.backcolor or 'transparent'};"
                f"color: {control.forecolor or 'inherit'};"
            )
        if control.kind in FIELD_KINDS and not isinstance(widget, QComboBox):
            font = widget.font()
            if control.font_name:
                font.setFamily(control.font_name)
            font.setBold(control.bold)
            font.setPointSize(max(6, control.font_size))
            widget.setFont(font)
        if control.events.get("onEnter") or control.events.get("onExit"):
            widget.installEventFilter(self)
        widget.show()

    def _bind(self, control: FormControl, widget: QWidget) -> None:
        self.binders.append(FieldBinder(control, widget, self.table))

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
        for row in self.project.db.query(
            f'SELECT * FROM "{table.name}" ORDER BY "{display.name}"'
        ):
            combo.addItem(str(row[display.name]), row[display.name])

    # ------------------------------------------------------------------ eventi
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802 - API Qt
        control = self._control_for_widget(obj)
        if control is not None:
            if event.type() == QEvent.Type.Enter:
                self._run_control_event(control, "onEnter")
            elif event.type() == QEvent.Type.Leave:
                self._run_control_event(control, "onExit")
        return super().eventFilter(obj, event)

    def _control_for_widget(self, obj: QObject) -> FormControl | None:
        for binder in self.binders:
            if binder.widget is obj:
                return binder.control
        return None

    def _run_control_event(self, control: FormControl, name: str) -> bool:
        action = str(control.events.get(name, "")).strip()
        if not action:
            return False
        try:
            self.perform(action)
        except Exception as exc:  # pragma: no cover - difensivo
            self._event_error(control, name, exc)
        return True

    def _run_form_event(self, name: str) -> None:
        action = str(self.spec.events.get(name, "")).strip()
        if not action:
            return
        try:
            self.perform(action)
        except Exception as exc:  # pragma: no cover - difensivo
            self.event_log.append(f"{name}: {exc}")
            self._status.setText(f"Errore evento {name}: {exc}")

    def _activate_button(self, control: FormControl) -> None:
        """Un ``onClick`` valorizzato sostituisce l'azione predefinita del pulsante."""
        if self._run_control_event(control, "onClick"):
            return
        self.perform(control.action)

    def _event_error(self, control: FormControl, name: str, exc: Exception) -> None:
        message = f"{self.spec.control_object_name(control)}.{name}: {exc}"
        self.event_log.append(message)
        self._status.setText(f"Errore evento — {message}")

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
                if value is not None:
                    rows = Rowset(self.project.db, child).open(
                        where=f'"{control.link_child or control.link_parent}" = ?',
                        params=(value,),
                    ).rows()
            grid.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, field in enumerate(child.fields):
                    item = QTableWidgetItem(
                        T.format_value(row.get(field.name), field.type, field.fmt)
                    )
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
        if self.read_only:
            self._status.setText("Form in sola lettura: la sorgente è una query")
            return False
        try:
            record_id = self.rowset.save(self.collect())
        except RowsetError as exc:
            self._status.setText(f"Salvataggio non riuscito: {exc}")
            QMessageBox.warning(self, "Salvataggio non riuscito", str(exc))
            return False
        self._new = False
        self._select_record(record_id)
        self.load_current()
        self._status.setText(f"Record salvato · {self._position_text()}")
        return True

    def _select_record(self, record_id: int) -> None:
        for index, row in enumerate(self.rowset.rows()):
            if row.get(INTERNAL_ID) == record_id:
                self.rowset.goto(index)
                return

    # --------------------------------------------------------------- azioni
    def perform(self, action: str) -> None:
        action = (action or "").strip()
        if not action or action == "none":
            return
        if self.read_only and action in ("new", "save", "delete"):
            self._status.setText("Form in sola lettura: la sorgente è una query")
            return
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
        if action == "cancel":
            self._new = False
            self.load_current()
            self._status.setText("Modifiche annullate")
            return
        if action == "delete":
            self.delete_current()
            return
        if action in ("first", "previous", "next", "last"):
            self._new = False
            getattr(self.rowset, action)()
            self.load_current()
            return
        if action == "close":
            self._close()
            return
        if action == "help":
            QMessageBox.information(
                self,
                "Aiuto",
                "Naviga con Primo/Prec./Succ./Ultimo, crea record con Nuovo, "
                "conferma con Salva e rimuovi con Elimina.",
            )
            self._status.setText("Aiuto mostrato")
            return
        if action == "info":
            record = self.rowset.current or {}
            detail = "\n".join(f"{key}: {value!r}" for key, value in record.items())
            QMessageBox.information(self, "Record corrente", detail or "Nessun record")
            return
        if action == "browse":
            self._browse()
            return
        if action.startswith("script:"):
            self._run_script(action.split(":", 1)[1])
            return
        if action.startswith("report:"):
            self._print_report(action.split(":", 1)[1])
            return
        if action.startswith("message:"):
            text = action.split(":", 1)[1] or "Messaggio"
            self._status.setText(text)
            QMessageBox.information(self, "Form", text)
            return
        self._status.setText(f"Azione sconosciuta: {action}")
        self.event_log.append(f"azione sconosciuta: {action}")

    def delete_current(self) -> None:
        if self.read_only:
            self._status.setText("Form in sola lettura: la sorgente è una query")
            return
        if self.rowset.current is None:
            self._status.setText("Nessun record da eliminare")
            return
        answer = QMessageBox.question(self, "Elimina", "Eliminare il record corrente?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.rowset.delete()
        except RowsetError as exc:
            self._status.setText(f"Eliminazione non riuscita: {exc}")
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self.rowset.first()
        self.load_current()
        self._status.setText(f"Record eliminato · {self._position_text()}")

    def _run_script(self, name: str) -> None:
        from .script_engine import ScriptEngine

        engine = ScriptEngine(self.project, FormScriptUI(self))
        result = engine.run_named(name, self.rowset.current)
        try:
            if not self.read_only:
                self.rowset.refresh()
                self.load_current()
        except RowsetError:
            pass
        if result.error:
            self.event_log.append(f"script {name}: {result.error}")
            self._status.setText(f"Script non eseguito: {result.error}")
            QMessageBox.warning(self, "Script", result.error)
        else:
            self._status.setText(f"Script {name} eseguito")

    def _print_report(self, name: str) -> None:
        from ..ui.report_preview import ReportPreviewDialog

        try:
            dialog = ReportPreviewDialog(self.project, name)
        except ValueError as exc:
            self._status.setText(f"Report non disponibile: {exc}")
            QMessageBox.warning(self, "Report", str(exc))
            return
        handler = getattr(self, "report_handler", None)
        if callable(handler):
            handler(dialog)
        else:
            dialog.exec()

    def _browse(self) -> None:
        handler = getattr(self, "browse_handler", None)
        if callable(handler):
            handler(self.spec.table)
            return
        self._status.setText("Browse: apri la tabella dal Navigator")

    def _close(self) -> None:
        self._run_form_event("onClose")
        window = self.window()
        if isinstance(window, QDialog):
            window.accept()
        else:
            window.close()

    # ------------------------------------------------------------------ stato
    def _position_text(self) -> str:
        position = self.rowset.index + 1 if self.rowset.current else 0
        total = max(self.rowset.count(), len(self.rowset))
        return f"Record {position} di {total}"

    def _update_status(self) -> None:
        suffix = " · sola lettura" if self.read_only else ""
        self._status.setText(f"{self._position_text()}{suffix}")


class FormPreviewDialog(QDialog):
    """Anteprima di un form con dati reali (D11).

    La finestra principale apre il runtime direttamente nell'area MDI; questo
    wrapper resta per i test, il capture e gli script che lavorano fuori dall'MDI.
    """

    def __init__(self, project, spec: FormSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Anteprima — {spec.caption or spec.name}")
        layout = QVBoxLayout(self)
        self.runtime = FormRuntime(project, spec, parent=self)
        layout.addWidget(self.runtime)
        self.resize(760, 620)
