"""Form Designer a tre zone: palette, anteprima live e inspector (D2–D5).

Schema ripreso da dBASE 5.5: a sinistra la palette dei controlli e dei campi,
al centro la superficie di disegno con righelli e griglia di punti, a destra
l'Object Inspector con le schede Proprietà / Eventi / Metodi.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import (
    BUTTON_ACTIONS,
    CONTROL_KINDS,
    FIELD_KINDS,
    FormControl,
    FormPage,
    FormSpec,
)
from ..core.metadata import new_id
from ..core.project import Project, ProjectError
from ..runtime.form_runtime import FormPreviewDialog
from ..ui import icons
from ..ui.widgets import PropertyEditor

SNAP = 4
RULER = 18

TOOL_ICONS = {
    "label": "testo",
    "field": "campo",
    "memo": "testo",
    "checkbox": "ok",
    "combo": "elenco",
    "number": "campo",
    "date": "data",
    "button": "pulsante",
    "grid": "tabella",
    "line": "linea",
    "rect": "riquadro",
    "image": "immagine",
}

PALETTE_ORDER = (
    "label",
    "field",
    "memo",
    "checkbox",
    "combo",
    "number",
    "date",
    "button",
    "grid",
    "line",
    "rect",
    "image",
)


# ------------------------------------------------------------------ anteprima
def _preview_widget(control: FormControl, spec: FormSpec, project: Project) -> QWidget:
    """Widget reale, non interattivo, che mostra il controllo come nel runtime."""
    kind = control.kind
    if kind == "label":
        widget: QWidget = QLabel(control.text or "Etichetta")
    elif kind == "memo":
        widget = QPlainTextEdit()
    elif kind == "checkbox":
        widget = QCheckBox(control.text or "Casella")
    elif kind == "combo":
        combo = QComboBox()
        combo.addItem(control.field or "(campo)", None)
        widget = combo
    elif kind == "number":
        spin = QSpinBox()
        spin.setRange(-2_000_000_000, 2_000_000_000)
        widget = spin
    elif kind == "date":
        edit = QLineEdit()
        edit.setPlaceholderText("gg/mm/aaaa")
        widget = edit
    elif kind == "button":
        widget = QPushButton(control.text or "Pulsante")
    elif kind == "grid":
        grid = QTableWidget(2, 3)
        table = project.table(control.table) if control.table else None
        if table is not None:
            headers = [field.display_name() for field in table.fields][:3]
            grid.setColumnCount(len(headers) or 1)
            grid.setHorizontalHeaderLabels(headers or [control.table])
            for row in range(2):
                for column, field in enumerate(table.fields[:3]):
                    grid.setItem(row, column, QTableWidgetItem("…"))
        grid.verticalHeader().setVisible(False)
        widget = grid
    elif kind == "line":
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        widget = line
    elif kind == "rect":
        rect = QFrame()
        rect.setFrameShape(QFrame.Shape.StyledPanel)
        widget = rect
    elif kind == "image":
        image = QLabel("Immagine")
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setStyleSheet("border: 1px dashed palette(mid); color: palette(mid);")
        widget = image
    else:
        text = QLineEdit()
        text.setPlaceholderText(control.field or "campo")
        widget = text
    if kind in FIELD_KINDS and not isinstance(widget, (QCheckBox, QComboBox, QSpinBox)):
        widget.setPlaceholderText(control.field or "campo")
    widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    font = QFont()
    font.setPointSize(max(6, control.font_size - 1))
    font.setBold(control.bold)
    widget.setFont(font)
    return widget


class Ruler(QWidget):
    """Righello in unità dBASE (1 unità = 8 px), tacche ogni 5, etichette ogni 10."""

    def __init__(self, horizontal: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.horizontal = horizontal
        self.setFixedHeight(RULER) if horizontal else self.setFixedWidth(RULER)
        self.setStyleSheet("background: palette(window);")

    def paintEvent(self, event) -> None:  # noqa: D102
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#eceee9"))
        painter.setPen(QPen(QColor("#8b938a"), 1))
        length = self.width() if self.horizontal else self.height()
        for step in range(0, length, 8):
            unit = step // 8
            if unit % 10 == 0:
                tick = RULER
                if self.horizontal:
                    painter.drawText(step + 2, RULER - 3, str(unit))
                else:
                    painter.drawText(1, step + 10, str(unit))
            elif unit % 5 == 0:
                tick = RULER // 2
            else:
                tick = RULER // 4
            if self.horizontal:
                painter.drawLine(step, RULER - tick, step, RULER)
            else:
                painter.drawLine(RULER - tick, step, RULER, step)
        painter.setPen(QPen(QColor("#b9bfb3"), 1))
        painter.drawLine(0, RULER - 1, length, RULER - 1) if self.horizontal else painter.drawLine(
            RULER - 1, 0, RULER - 1, length
        )


class FormCanvas(QWidget):
    """Superficie di disegno con griglia di punti, controlli live e selezione."""

    control_selected = pyqtSignal(str)
    control_changed = pyqtSignal(str)
    tool_used = pyqtSignal(int, int)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec: FormSpec | None = None
        self.page: FormPage | None = None
        self.selected: str | None = None
        self.tool = "pointer"
        self.widgets: dict[str, QWidget] = {}
        self._dragging = False
        self._offset = QPoint()
        self.show_grid = True
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("background: #fbfbf8;")

    # ------------------------------------------------------------------ build
    def load(self, spec: FormSpec, page_index: int) -> None:
        self.spec = spec
        self.page = spec.pages[max(0, min(page_index, len(spec.pages) - 1))]
        self.setFixedSize(spec.width, spec.height)
        self._rebuild()

    def _rebuild(self) -> None:
        for widget in self.widgets.values():
            widget.setParent(None)
            widget.deleteLater()
        self.widgets = {}
        if self.page is None or self.spec is None:
            return
        for control in self.page.controls:
            widget = _preview_widget(control, self.spec, self.project)
            widget.setParent(self)
            widget.setGeometry(control.x, control.y, max(8, control.w), max(8, control.h))
            widget.show()
            self.widgets[control.id] = widget
        self.update()

    def refresh_control(self, control: FormControl) -> None:
        widget = self.widgets.get(control.id)
        if widget is None:
            self._rebuild()
            return
        widget.setGeometry(control.x, control.y, max(8, control.w), max(8, control.h))
        if control.kind == "label" and isinstance(widget, QLabel):
            widget.setText(control.text)
        if control.kind == "button" and isinstance(widget, QPushButton):
            widget.setText(control.text)
        font = widget.font()
        font.setPointSize(max(6, control.font_size - 1))
        font.setBold(control.bold)
        widget.setFont(font)
        self.update()

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event) -> None:  # noqa: D102
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#fbfbf8"))
        if self.show_grid:
            painter.setPen(QPen(QColor("#ccd1c6"), 1))
            for x in range(0, self.width(), SNAP):
                for y in range(0, self.height(), SNAP):
                    painter.drawPoint(x, y)
        if self.page is not None:
            control = next((c for c in self.page.controls if c.id == self.selected), None)
            if control is not None:
                painter.setPen(QPen(QColor("#2f6f4f"), 1, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRect(control.x - 1, control.y - 1, max(4, control.w) + 1, max(4, control.h) + 1))
                painter.setPen(QPen(QColor("#2f6f4f"), 1))
                painter.setBrush(QColor("#ffffff"))
                for x in (control.x - 4, control.x + control.w // 2 - 2, control.x + control.w - 4):
                    for y in (control.y - 4, control.y + control.h // 2 - 2, control.y + control.h - 4):
                        painter.drawRect(QRect(x, y, 5, 5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#b9bfb3"), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    # ------------------------------------------------------------------ mouse
    def _hit(self, point: QPoint) -> FormControl | None:
        if self.page is None:
            return None
        for control in reversed(self.page.controls):
            if QRect(control.x, control.y, max(8, control.w), max(8, control.h)).contains(point):
                return control
        return None

    def mousePressEvent(self, event) -> None:  # noqa: D102
        if event.button() != Qt.MouseButton.LeftButton or self.page is None:
            return
        point = event.position().toPoint()
        if self.tool != "pointer":
            self.tool_used.emit(point.x(), point.y())
            return
        control = self._hit(point)
        if control is None:
            self.selected = None
            self.update()
            return
        self.selected = control.id
        self._dragging = True
        self._offset = point - QPoint(control.x, control.y)
        self.control_selected.emit(control.id)
        self.update()
        self.setFocus()

    def mouseMoveEvent(self, event) -> None:  # noqa: D102
        if not self._dragging or self.page is None:
            return
        control = next((c for c in self.page.controls if c.id == self.selected), None)
        if control is None:
            return
        point = event.position().toPoint() - self._offset
        x = max(0, min(self.width() - control.w, (point.x() // SNAP) * SNAP))
        y = max(0, min(self.height() - control.h, (point.y() // SNAP) * SNAP))
        control.x, control.y = x, y
        self.refresh_control(control)
        self.control_changed.emit(control.id)

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102
        self._dragging = False

    def keyPressEvent(self, event) -> None:  # noqa: D102
        if self.page is None:
            return
        control = next((c for c in self.page.controls if c.id == self.selected), None)
        if control is None:
            super().keyPressEvent(event)
            return
        step = SNAP if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        deltas = {
            Qt.Key.Key_Left: (-step, 0),
            Qt.Key.Key_Right: (step, 0),
            Qt.Key.Key_Up: (0, -step),
            Qt.Key.Key_Down: (0, step),
        }
        if event.key() in deltas:
            dx, dy = deltas[event.key()]
            control.x = max(0, control.x + dx)
            control.y = max(0, control.y + dy)
            self.refresh_control(control)
            self.control_changed.emit(control.id)
            return
        super().keyPressEvent(event)


class PalettePanel(QWidget):
    """Palette dei controlli con Pointer e strumenti, più l'elenco dei campi."""

    tool_selected = pyqtSignal(str)
    field_activated = pyqtSignal(str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self._section("Controls"))
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        pointer = icons.make_button("Pointer", "puntatore", lambda: self.tool_selected.emit("pointer"), self)
        pointer.setCheckable(True)
        pointer.setChecked(True)
        pointer.setStyleSheet("text-align: left;")
        self.group.addButton(pointer)
        layout.addWidget(pointer)
        for kind in PALETTE_ORDER:
            button = icons.make_button(
                CONTROL_KINDS[kind].upper(),
                TOOL_ICONS.get(kind, "campo"),
                lambda _checked=False, k=kind: self.tool_selected.emit(k),
                self,
            )
            button.setCheckable(True)
            button.setStyleSheet("text-align: left;")
            self.group.addButton(button)
            layout.addWidget(button)
        layout.addSpacing(6)
        layout.addWidget(self._section("Field"))
        self.fields = QListWidget()
        self.fields.setIconSize(icons.ICON_SIZE)
        self.fields.itemDoubleClicked.connect(
            lambda item: self.field_activated.emit(str(item.data(Qt.ItemDataRole.UserRole)))
        )
        layout.addWidget(self.fields, 1)
        layout.addWidget(QLabel("Doppio clic su un campo per inserirlo nel form."))
        self.setFixedWidth(190)

    def _section(self, title: str) -> QLabel:
        label = QLabel(title)
        label.setStyleSheet("font-weight: 600; padding: 2px 0;")
        return label

    def set_table(self, table_name: str) -> None:
        self.fields.clear()
        table = self.project.table(table_name)
        if table is None:
            return
        for field in table.fields:
            item = QListWidgetItem(icons.icon("campo"), field.display_name())
            item.setData(Qt.ItemDataRole.UserRole, field.name)
            item.setToolTip(f"{field.name} · {field.type}")
            self.fields.addItem(item)


class InspectorPanel(QWidget):
    """Object Inspector: combo oggetto in alto e schede Proprietà/Eventi/Metodi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.object_combo = QComboBox()
        self.object_combo.setToolTip("Oggetto ispezionato")
        layout.addWidget(self.object_combo)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.editor = PropertyEditor()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.editor)
        self.tabs.addTab(scroll, "Proprietà")
        self.events = QListWidget()
        self.tabs.addTab(self.events, "Eventi")
        self.methods = QListWidget()
        self.tabs.addTab(self.methods, "Metodi")
        self.setMinimumWidth(270)

    def show_properties(self, specs, events: list[str], methods: list[str]) -> None:
        self.editor.set_properties(specs)
        self.events.clear()
        for text in events:
            self.events.addItem(text)
        self.methods.clear()
        for text in methods:
            self.methods.addItem(text)


METHODS = [
    "first() — primo record",
    "previous() — record precedente",
    "next() — record successivo",
    "last() — ultimo record",
    "new() — nuovo record",
    "save() — salva il record corrente",
    "delete() — elimina il record corrente",
    "close() — chiude il form",
]


class FormBuilderDialog(QDialog):
    """Form Designer: palette a sinistra, anteprima live al centro, proprietà a destra."""

    def __init__(self, project: Project, spec: FormSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.table = project.table(spec.table)
        self.selected: FormControl | None = None
        self.tool = "pointer"
        self.setWindowTitle(f"Form Designer ({spec.caption or spec.name})")
        self.resize(1160, 760)
        self._build_ui()
        self._load_page(0)
        self._select_object(None)

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Page:"))
        self.page_combo = QComboBox()
        for index, page in enumerate(self.spec.pages):
            self.page_combo.addItem(page.caption or f"Pagina {index + 1}", index)
        self.page_combo.currentIndexChanged.connect(self._on_page_changed)
        bar.addWidget(self.page_combo)
        bar.addWidget(icons.make_button("Nuova pagina", "nuovo", self.add_page, self))
        bar.addSpacing(12)
        self.grid_button = icons.make_button("Griglia", "tabella", self.toggle_grid, self, checkable=True)
        self.grid_button.setChecked(True)
        bar.addWidget(self.grid_button)
        bar.addWidget(icons.make_button("Elimina controllo", "elimina", self.remove_control, self))
        bar.addStretch(1)
        bar.addWidget(icons.make_button("Anteprima", "anteprima", self.preview, self))
        layout.addLayout(bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter, 1)

        self.palette = PalettePanel(self.project)
        self.palette.tool_selected.connect(self._on_tool_selected)
        self.palette.field_activated.connect(self.add_field_control)
        self.palette.set_table(self.spec.table)
        self.splitter.addWidget(self.palette)

        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.setSpacing(0)
        ruler_row = QHBoxLayout()
        ruler_row.setSpacing(0)
        ruler_row.addSpacing(RULER)
        self.h_ruler = Ruler(True)
        ruler_row.addWidget(self.h_ruler, 1)
        centre_layout.addLayout(ruler_row)
        canvas_row = QHBoxLayout()
        canvas_row.setSpacing(0)
        self.v_ruler = Ruler(False)
        canvas_row.addWidget(self.v_ruler)
        self.canvas = FormCanvas(self.project)
        self.canvas.control_selected.connect(self._on_control_selected)
        self.canvas.control_changed.connect(lambda _id: self._refresh_status())
        self.canvas.tool_used.connect(self._place_control)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        canvas_row.addWidget(scroll, 1)
        centre_layout.addLayout(canvas_row, 1)
        self.splitter.addWidget(centre)

        self.inspector = InspectorPanel()
        self.inspector.object_combo.activated.connect(self._on_object_combo)
        self.inspector.editor.changed.connect(self._on_property_changed)
        self.splitter.addWidget(self.inspector)
        self.splitter.setSizes([190, 660, 300])

        status_row = QHBoxLayout()
        self.status_labels: dict[str, QLabel] = {}
        for key in ("Object", "Page", "Top", "Left", "Height", "Width"):
            label = QLabel(f"{key}: —")
            self.status_labels[key] = label
            status_row.addWidget(label)
            status_row.addSpacing(10)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        buttons = icons.dialog_buttons("Salva", "Annulla")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------------------------------------------------------------- pagine
    def current_page(self) -> FormPage:
        index = self.page_combo.currentData() if self.page_combo.count() else 0
        return self.spec.pages[max(0, int(index or 0))]

    def _load_page(self, index: int) -> None:
        self.canvas.load(self.spec, index)
        self.selected = None
        self._refresh_objects()
        self._select_object(None)

    def _on_page_changed(self, _index: int) -> None:
        self._load_page(max(0, int(self.page_combo.currentData() or 0)))

    def add_page(self) -> None:
        caption, ok = QInputDialog.getText(self, "Nuova pagina", "Titolo della scheda:")
        if not ok:
            return
        self.spec.pages.append(FormPage(caption=caption or f"Pagina {len(self.spec.pages) + 1}"))
        self.page_combo.addItem(caption or f"Pagina {len(self.spec.pages)}", len(self.spec.pages) - 1)
        self.page_combo.setCurrentIndex(self.page_combo.count() - 1)

    def toggle_grid(self, checked: bool) -> None:
        self.canvas.show_grid = checked
        self.canvas.update()

    # ------------------------------------------------------------ palette/tool
    def _on_tool_selected(self, tool: str) -> None:
        self.tool = tool
        self.canvas.tool = tool
        self.canvas.setCursor(
            Qt.CursorShape.ArrowCursor if tool == "pointer" else Qt.CursorShape.CrossCursor
        )

    def _place_control(self, x: int, y: int) -> None:
        kind = self.tool
        self.add_control(kind, x, y)
        pointer = self.palette.group.buttons()[0]
        pointer.setChecked(True)
        self._on_tool_selected("pointer")

    def _control_name(self, control: FormControl) -> str:
        base = CONTROL_KINDS.get(control.kind, control.kind).lower().replace(" ", "")
        return f"form.{base}{self.current_page().controls.index(control) + 1}"

    def add_control(self, kind: str, x: int = 20, y: int = 20) -> None:
        default_field = ""
        if kind in FIELD_KINDS and self.table and self.table.fields:
            existing = {c.field for c in self.current_page().controls}
            default_field = next(
                (f.name for f in self.table.fields if f.name not in existing), self.table.fields[0].name
            )
        control = FormControl(
            id=new_id(),
            kind=kind,
            field=default_field,
            text=BUTTON_ACTIONS.get("save", "") if kind == "button" else "",
            x=(x // SNAP) * SNAP,
            y=(y // SNAP) * SNAP,
            w=260 if kind == "grid" else 180,
            h=120 if kind == "grid" else 24,
            table=self.table.name if kind == "grid" and self.table else "",
        )
        if kind == "button":
            control.action = "save"
            control.text = "Salva"
        if kind == "label":
            control.text = "Etichetta"
        self.current_page().controls.append(control)
        self.canvas._rebuild()
        self._refresh_objects()
        self._on_control_selected(control.id)

    def add_field_control(self, field_name: str) -> None:
        kind = "field"
        field = self.table.field(field_name) if self.table else None
        if field is not None:
            if field.type == "memo":
                kind = "memo"
            elif field.type in ("integer", "decimal"):
                kind = "number"
            elif field.type == "boolean":
                kind = "checkbox"
            elif field.type == "date":
                kind = "date"
            elif field.lookup:
                kind = "combo"
        used = self.current_page().controls
        y = 8 + 28 * len([c for c in used if c.kind in FIELD_KINDS])
        self.add_control(kind, 176, min(y, max(8, self.spec.height - 40)))
        if self.selected is not None:
            self.selected.field = field_name
            if field is not None and self.selected.kind == "combo" and field.lookup:
                self.selected.lookup = field.lookup
            self.canvas.refresh_control(self.selected)
            self._on_control_selected(self.selected.id)

    def remove_control(self) -> None:
        if self.selected is None:
            return
        page = self.current_page()
        page.controls = [c for c in page.controls if c.id != self.selected.id]
        self.selected = None
        self.canvas.load(self.spec, int(self.page_combo.currentData() or 0))
        self._refresh_objects()
        self._select_object(None)

    # --------------------------------------------------------------- oggetto
    def _refresh_objects(self) -> None:
        combo = self.inspector.object_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(f"form — {self.spec.name}", None)
        for control in self.current_page().controls:
            combo.addItem(self._control_name(control), control.id)
        combo.blockSignals(False)

    def _on_object_combo(self, index: int) -> None:
        control_id = self.inspector.object_combo.itemData(index)
        self.canvas.selected = control_id
        self.canvas.update()
        self._select_object(control_id)

    def _select_object(self, control_id: str | None) -> None:
        if control_id is None:
            self.selected = None
            self.canvas.selected = None
            self.canvas.update()
            self.inspector.tabs.setTabText(0, "Form")
            self.inspector.show_properties(
                [
                    ("name", "Nome", "text", self.spec.name, None),
                    ("caption", "Didascalia", "text", self.spec.caption, None),
                    ("width", "Larghezza", "int", self.spec.width, None),
                    ("height", "Altezza", "int", self.spec.height, None),
                    ("order", "Ordine", "text", self.spec.order, None),
                ],
                ["onOpen — all'apertura del form", "onClose — alla chiusura"],
                ["form.save() · form.close() · record.next()"],
            )
            self._refresh_status()
            return
        control = next((c for c in self.current_page().controls if c.id == control_id), None)
        if control is None:
            return
        self.selected = control
        self.canvas.selected = control.id
        self.inspector.tabs.setTabText(0, "Proprietà")
        field_choices = [("", "(nessuno)")] + [
            (f.name, f.display_name()) for f in (self.table.fields if self.table else [])
        ]
        table_choices = [("", "(nessuna)")] + [(name, name) for name in self.project.names("tables")]
        action_choices = [(key, label) for key, label in BUTTON_ACTIONS.items()]
        action_choices += [(f"script:{n}", f"Script: {n}") for n in self.project.names("scripts")]
        action_choices += [(f"report:{n}", f"Report: {n}") for n in self.project.names("reports")]
        self.inspector.show_properties(
            [
                ("kind", "Tipo", "choice", control.kind, [(k, v) for k, v in CONTROL_KINDS.items()]),
                ("field", "Campo", "choice", control.field, field_choices),
                ("text", "Testo", "text", control.text, None),
                ("x", "Left", "int", control.x, None),
                ("y", "Top", "int", control.y, None),
                ("w", "Width", "int", control.w, None),
                ("h", "Height", "int", control.h, None),
                ("font_size", "Font size", "int", control.font_size, None),
                ("bold", "Font bold", "bool", control.bold, None),
                (
                    "align",
                    "Allineamento",
                    "choice",
                    control.align,
                    [("left", "Sinistra"), ("center", "Centro"), ("right", "Destra")],
                ),
                ("action", "Azione", "choice", control.action, action_choices),
                ("table", "Tabella sottomaschera", "choice", control.table, table_choices),
                ("link_parent", "Campo padre", "text", control.link_parent, None),
                ("link_child", "Campo figlio", "text", control.link_child, None),
            ],
            [
                f"onClick — azione attuale: {control.action}",
                "onEnter — all'ingresso nel controllo",
                "onExit — all'uscita dal controllo",
            ],
            ["control.setFocus() · control.value · control.refresh()"],
        )
        self._refresh_status()

    def _on_control_selected(self, control_id: str) -> None:
        self._select_object(control_id)
        for index in range(self.inspector.object_combo.count()):
            if self.inspector.object_combo.itemData(index) == control_id:
                self.inspector.object_combo.setCurrentIndex(index)
                break

    def _refresh_status(self) -> None:
        control = self.selected
        values = {
            "Object": self._control_name(control) if control else "form",
            "Page": str((self.page_combo.currentData() or 0) + 1),
            "Top": f"{control.y / 8:.2f}" if control else "—",
            "Left": f"{control.x / 8:.2f}" if control else "—",
            "Height": f"{control.h / 8:.2f}" if control else "—",
            "Width": f"{control.w / 8:.2f}" if control else "—",
        }
        for key, value in values.items():
            self.status_labels[key].setText(f"{key}: {value}")

    # ------------------------------------------------------------- proprietà
    def _on_property_changed(self, key: str, value: Any) -> None:
        if self.selected is None:
            if key in ("name", "caption", "order"):
                setattr(self.spec, key, str(value))
                self.setWindowTitle(f"Form Designer ({self.spec.caption or self.spec.name})")
            elif key in ("width", "height"):
                setattr(self.spec, key, max(120, int(value)))
                self.canvas.load(self.spec, int(self.page_combo.currentData() or 0))
                self.canvas.selected = None
            return
        setattr(self.selected, key, value)
        if key == "kind" and self.selected.kind == "grid" and self.table:
            self.selected.table = self.table.name
        self.canvas.refresh_control(self.selected)
        self._refresh_status()
        if key == "kind":
            self.canvas._rebuild()

    # ------------------------------------------------------------------ azioni
    def preview(self) -> None:
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Form non valido", "\n".join(errors))
            return
        dialog = FormPreviewDialog(self.project, self.spec, self)
        dialog.exec()

    def save(self) -> None:
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Form non valido", "\n".join(errors))
            return
        try:
            self.project.put_object("forms", self.spec.to_dict(), previous_name=self.spec.name)
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return
        self.accept()
