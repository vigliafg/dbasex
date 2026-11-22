"""Form Designer a tre zone: palette, superficie con righelli, Object Inspector (O4).

Struttura ripresa da dBASE 5.5: a sinistra le palette ``Controls`` e ``Field``,
al centro la superficie di disegno con griglia di punti e righelli, a destra
l'Inspector con le schede Proprietà / Eventi / Metodi. Il designer è un
``QWidget`` ospitato nell'area MDI, non un dialog modale.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.form_model import (
    BUTTON_ACTIONS,
    CONTROL_EVENTS,
    CONTROL_KINDS,
    FIELD_KINDS,
    FORM_EVENTS,
    FormControl,
    FormPage,
    FormSpec,
)
from ..core.metadata import new_id
from ..core.project import Project, ProjectError
from ..ui import design, icons
from ..ui.widgets import PropertyInspector

SNAP = design.METRICS.grid_step
RULER = design.METRICS.ruler_size
HANDLE = 6
MIN_CONTROL = 16

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

# Nomi compatti delle classi nella palette Controls.
PALETTE_LABELS = {
    "label": "TEXT",
    "field": "ENTRYFIELD",
    "memo": "MEMO",
    "checkbox": "CHECKBOX",
    "combo": "COMBOBOX",
    "number": "SPINBOX",
    "date": "DATEFIELD",
    "button": "BUTTON",
    "grid": "GRID",
    "line": "LINE",
    "rect": "RECT",
    "image": "IMAGE",
}

# Pulsanti dBASE della palette Controls: nome originale, icona, azione runtime, testo.
BUTTON_OBJECTS = (
    ("OKBUTTON", "ok", "save", "OK"),
    ("CLOSEBUTTON", "chiudi", "close", "Chiudi"),
    ("CANCELBUTTON", "annulla", "cancel", "Annulla"),
    ("HELPBUTTON", "aiuto", "help", "?"),
    ("NOBUTTON", "annulla", "cancel", "No"),
    ("NEXTBUTTON", "successivo", "next", "Succ."),
    ("PREVBUTTON", "precedente", "previous", "Prec."),
    ("INFOBUTTON", "aiuto", "info", "Info"),
    ("TOOLBUTTON", "impostazioni", "none", "Strumento"),
    ("REPORTBUTTON", "report", "report:", "Report"),
    ("BROWSEBUTTON", "tabella", "browse", "Browse"),
    ("NEXTRECORD", "successivo", "next", "Succ. rec."),
    ("PREVRECORD", "precedente", "previous", "Prec. rec."),
    ("ADDRECORD", "nuovo", "new", "Nuovo rec."),
)
BUTTON_SPECS = {name: (glyph, action, text) for name, glyph, action, text in BUTTON_OBJECTS}

METHOD_HELP = (
    ("first", "Va al primo record", ""),
    ("previous", "Record precedente", ""),
    ("next", "Record successivo", ""),
    ("last", "Ultimo record", ""),
    ("new", "Nuovo record", ""),
    ("save", "Salva il record corrente", ""),
    ("delete", "Elimina il record corrente", ""),
    ("close", "Chiude il form", ""),
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
                for column, _field in enumerate(table.fields[:3]):
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
    if control.backcolor or control.forecolor:
        widget.setStyleSheet(
            f"background: {control.backcolor or 'transparent'};"
            f"color: {control.forecolor or 'inherit'};"
        )
    font = QFont()
    if control.font_name:
        font.setFamily(control.font_name)
    font.setPointSize(max(6, control.font_size - 1))
    font.setBold(control.bold)
    widget.setFont(font)
    return widget


def _tokens() -> dict[str, str]:
    """Token del tema attivo, non del tema predefinito."""
    app = QApplication.instance()
    name = app.property("dbx_theme") if app is not None else None
    return design.palette(name if isinstance(name, str) else None)


# --------------------------------------------------------------------- righelli
class Ruler(QWidget):
    """Righello in unità dBASE (1 unità = 8 px), tacche ogni 5, etichette ogni 10."""

    def __init__(self, horizontal: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.horizontal = horizontal
        self.offset = 0
        if horizontal:
            self.setFixedHeight(RULER)
        else:
            self.setFixedWidth(RULER)

    def set_offset(self, value: int) -> None:
        if value != self.offset:
            self.offset = int(value)
            self.update()

    def paintEvent(self, event) -> None:  # noqa: D102 - API Qt
        palette = _tokens()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(palette["ruler_bg"]))
        painter.setPen(QPen(QColor(palette["ruler_text"]), 1))
        length = self.width() if self.horizontal else self.height()
        start = -(self.offset % SNAP)
        for step in range(start, length, SNAP):
            if step < 0:
                continue
            unit = (step + self.offset) // SNAP
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
        painter.setPen(QPen(QColor(palette["panel_shadow"]), 1))
        if self.horizontal:
            painter.drawLine(0, RULER - 1, length, RULER - 1)
        else:
            painter.drawLine(RULER - 1, 0, RULER - 1, length)


class SelectionOverlay(QWidget):
    """Disegna bordo di selezione e maniglie sopra ai controlli di anteprima."""

    def __init__(self, canvas: "FormCanvas") -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        palette = _tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen = QPen(QColor(palette["focus"]), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for control in self.canvas.selected_controls():
            painter.drawRect(control.x, control.y, max(8, control.w) + 1, max(8, control.h) + 1)
        selected = self.canvas.selected_controls()
        if len(selected) == 1:
            control = selected[0]
            painter.setPen(QPen(QColor(palette["focus"]), 1))
            painter.setBrush(QColor(palette["workspace"]))
            for _name, x, y in self.canvas.handle_points(control):
                painter.drawRect(x - HANDLE // 2, y - HANDLE // 2, HANDLE, HANDLE)
            painter.setBrush(Qt.BrushStyle.NoBrush)


# ----------------------------------------------------------------------- canvas
class FormCanvas(QWidget):
    """Superficie di disegno: griglia di punti, selezione multipla, move e resize."""

    selection_changed = pyqtSignal(list)
    geometry_changed = pyqtSignal()
    edit_started = pyqtSignal()
    delete_requested = pyqtSignal()
    tool_used = pyqtSignal(int, int)
    field_dropped = pyqtSignal(str, int, int)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec: FormSpec | None = None
        self.page_index = 0
        self.page: FormPage | None = None
        self.selection: list[str] = []
        self.tool = "pointer"
        self.widgets: dict[str, QWidget] = {}
        self.show_grid = True
        self._mode: str | None = None
        self._resize_handle = ""
        self._press = QPoint()
        self._start_rects: dict[str, QRect] = {}
        self._start_rect = QRect()
        self.overlay = SelectionOverlay(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.setStyleSheet("background: %s;" % _tokens()["workspace"])

    # ------------------------------------------------------------------ build
    def load(self, spec: FormSpec, page_index: int) -> None:
        self.spec = spec
        self.page_index = max(0, min(page_index, len(spec.pages) - 1))
        self.page = spec.pages[self.page_index]
        self.setFixedSize(spec.width, spec.height)
        self.setStyleSheet("background: %s;" % (spec.backcolor or _tokens()["workspace"]))
        self.selection = [item for item in self.selection if self.control(item) is not None]
        self._rebuild()

    def control(self, control_id: str) -> FormControl | None:
        if self.page is None:
            return None
        return next((c for c in self.page.controls if c.id == control_id), None)

    def selected_controls(self) -> list[FormControl]:
        return [c for c in (self.control(item) for item in self.selection) if c is not None]

    def primary(self) -> FormControl | None:
        selected = self.selected_controls()
        return selected[-1] if selected else None

    def set_selection(self, ids: list[str], notify: bool = True) -> None:
        self.selection = [item for item in ids if self.control(item) is not None]
        self._raise_overlay()
        self.update()
        if notify:
            self.selection_changed.emit(list(self.selection))

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
        self.overlay.setGeometry(self.rect())
        self._raise_overlay()
        self.update()

    def _raise_overlay(self) -> None:
        self.overlay.setGeometry(self.rect())
        self.overlay.raise_()

    def sync_control(self, control: FormControl) -> None:
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
        if control.font_name:
            font.setFamily(control.font_name)
        font.setPointSize(max(6, control.font_size - 1))
        font.setBold(control.bold)
        widget.setFont(font)
        self._raise_overlay()
        self.update()

    def sync_all(self) -> None:
        self._rebuild()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.setCursor(
            Qt.CursorShape.ArrowCursor if tool == "pointer" else Qt.CursorShape.CrossCursor
        )

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event) -> None:  # noqa: D102 - API Qt
        palette = _tokens()
        painter = QPainter(self)
        background = (self.spec.backcolor if self.spec else "") or palette["workspace"]
        painter.fillRect(self.rect(), QColor(background))
        if self.show_grid:
            painter.setPen(QPen(QColor(palette["grid_dot"]), 1))
            for x in range(0, self.width(), SNAP):
                for y in range(0, self.height(), SNAP):
                    painter.drawPoint(x, y)
        painter.setPen(QPen(QColor(palette["panel_shadow"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

    # ------------------------------------------------------------- maniglie
    @staticmethod
    def handle_points(control: FormControl) -> list[tuple[str, int, int]]:
        left, top = control.x, control.y
        right, bottom = control.x + max(8, control.w), control.y + max(8, control.h)
        middle_x, middle_y = (left + right) // 2, (top + bottom) // 2
        return [
            ("nw", left, top),
            ("n", middle_x, top),
            ("ne", right, top),
            ("e", right, middle_y),
            ("se", right, bottom),
            ("s", middle_x, bottom),
            ("sw", left, bottom),
            ("w", left, middle_y),
        ]

    def _handle_at(self, point: QPoint) -> tuple[str, FormControl] | None:
        selected = self.selected_controls()
        if len(selected) != 1:
            return None
        control = selected[0]
        for name, x, y in self.handle_points(control):
            if abs(point.x() - x) <= HANDLE and abs(point.y() - y) <= HANDLE:
                return name, control
        return None

    def _hit(self, point: QPoint) -> FormControl | None:
        if self.page is None:
            return None
        for control in reversed(self.page.controls):
            if QRect(control.x, control.y, max(8, control.w), max(8, control.h)).contains(point):
                return control
        return None

    @staticmethod
    def _snap(value: int) -> int:
        return int(round(value / SNAP)) * SNAP

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() != Qt.MouseButton.LeftButton or self.page is None:
            return
        point = event.position().toPoint()
        if self.tool != "pointer":
            self.tool_used.emit(self._snap(point.x()), self._snap(point.y()))
            return
        handle = self._handle_at(point)
        if handle is not None:
            name, control = handle
            self.edit_started.emit()
            self._mode = "resize"
            self._resize_handle = name
            self._press = point
            self._start_rect = QRect(control.x, control.y, control.w, control.h)
            self.setFocus()
            return
        control = self._hit(point)
        if control is None:
            self.set_selection([])
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            ids = list(self.selection)
            if control.id in ids:
                ids.remove(control.id)
            else:
                ids.append(control.id)
            self.set_selection(ids)
            return
        if control.id not in self.selection:
            self.set_selection([control.id])
        self.edit_started.emit()
        self._mode = "move"
        self._press = point
        self._start_rects = {
            item.id: QRect(item.x, item.y, item.w, item.h) for item in self.selected_controls()
        }
        self.setFocus()

    def mouseMoveEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self._mode is None or self.page is None:
            return
        point = event.position().toPoint()
        if self._mode == "move":
            dx = self._snap(point.x() - self._press.x())
            dy = self._snap(point.y() - self._press.y())
            changed = False
            for control in self.selected_controls():
                start = self._start_rects.get(control.id)
                if start is None:
                    continue
                x = max(0, min(self.width() - max(MIN_CONTROL, start.width()), start.x() + dx))
                y = max(0, min(self.height() - max(MIN_CONTROL, start.height()), start.y() + dy))
                x, y = self._snap(x), self._snap(y)
                if (x, y) != (control.x, control.y):
                    control.x, control.y = x, y
                    changed = True
                    self.sync_control(control)
            if changed:
                self.geometry_changed.emit()
            return
        if self._mode == "resize":
            control = self.primary()
            if control is None:
                return
            left = self._start_rect.x()
            top = self._start_rect.y()
            width = self._start_rect.width()
            height = self._start_rect.height()
            dx = self._snap(point.x() - self._press.x())
            dy = self._snap(point.y() - self._press.y())
            handle = self._resize_handle
            if "w" in handle and "e" not in handle:
                left += dx
                width -= dx
            if "e" in handle:
                width += dx
            if "n" in handle and "s" not in handle:
                top += dy
                height -= dy
            if "s" in handle:
                height += dy
            if width < MIN_CONTROL:
                if "w" in handle:
                    left -= MIN_CONTROL - width
                width = MIN_CONTROL
            if height < MIN_CONTROL:
                if "n" in handle:
                    top -= MIN_CONTROL - height
                height = MIN_CONTROL
            left = max(0, min(left, self.width() - MIN_CONTROL))
            top = max(0, min(top, self.height() - MIN_CONTROL))
            width = min(width, self.width() - left)
            height = min(height, self.height() - top)
            control.x, control.y = left, top
            control.w, control.h = width, height
            self.sync_control(control)
            self.geometry_changed.emit()

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102 - API Qt
        self._mode = None
        self._resize_handle = ""

    # ------------------------------------------------------------- tastiera
    def keyPressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self.page is None:
            return
        selected = self.selected_controls()
        if not selected:
            super().keyPressEvent(event)
            return
        step = 1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else SNAP
        deltas = {
            Qt.Key.Key_Left: (-step, 0),
            Qt.Key.Key_Right: (step, 0),
            Qt.Key.Key_Up: (0, -step),
            Qt.Key.Key_Down: (0, step),
        }
        if event.key() in deltas:
            self.edit_started.emit()
            dx, dy = deltas[event.key()]
            for control in selected:
                control.x = max(0, min(self.width() - control.w, control.x + dx))
                control.y = max(0, min(self.height() - control.h, control.y + dy))
                self.sync_control(control)
            self.geometry_changed.emit()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            return
        if event.key() == Qt.Key.Key_Escape:
            self.set_tool("pointer")
            return
        super().keyPressEvent(event)

    # --------------------------------------------------------------- drag/drop
    def dragEnterEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.mimeData().hasFormat("application/x-dbx-field"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.mimeData().hasFormat("application/x-dbx-field"):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: D102 - API Qt
        if not event.mimeData().hasFormat("application/x-dbx-field"):
            return
        field_name = bytes(event.mimeData().data("application/x-dbx-field")).decode("utf-8")
        point = event.position().toPoint()
        self.field_dropped.emit(field_name, self._snap(point.x()), self._snap(point.y()))
        event.acceptProposedAction()


# ---------------------------------------------------------------------- palette
class FieldList(QListWidget):
    """Elenco dei campi trascinabile sulla superficie del form."""

    MIME = "application/x-dbx-field"

    def mimeTypes(self) -> list[str]:  # noqa: N802 - API Qt
        return [self.MIME]

    def mimeData(self, items) -> "QMimeData":  # noqa: N802 - API Qt
        from PyQt6.QtCore import QMimeData

        data = QMimeData()
        if items:
            name = str(items[0].data(Qt.ItemDataRole.UserRole) or "")
            data.setData(self.MIME, name.encode("utf-8"))
        return data


class PalettePanel(QWidget):
    """Palette Controls (Standard/Custom) e Field, in stile dBASE."""

    tool_selected = pyqtSignal(str)
    button_selected = pyqtSignal(str)
    field_activated = pyqtSignal(str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.tool_buttons: dict[str, QToolButton] = {}
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(4)
        upper_layout.addWidget(self._section("Controls"))

        self.control_tabs = QTabWidget()
        standard = QWidget()
        standard_layout = QGridLayout(standard)
        standard_layout.setContentsMargins(2, 2, 2, 2)
        standard_layout.setHorizontalSpacing(2)
        standard_layout.setVerticalSpacing(2)
        pointer = self._tool_button("Pointer", "pointer", "puntatore", standard)
        pointer.setCheckable(True)
        pointer.setChecked(True)
        standard_layout.addWidget(pointer, 0, 0)
        position = 1
        for kind in PALETTE_ORDER:
            button = self._tool_button(
                PALETTE_LABELS.get(kind, kind.upper()), kind, TOOL_ICONS.get(kind, "campo"), standard
            )
            standard_layout.addWidget(button, position // 2, position % 2)
            position += 1
        self.control_tabs.addTab(standard, "Standard")

        custom = QWidget()
        custom_layout = QVBoxLayout(custom)
        custom_layout.setContentsMargins(6, 6, 6, 6)
        hint = QLabel(
            "I controlli personalizzati non sono disponibili in dBX 0.2.\n"
            "Usa i controlli Standard o i pulsanti dBASE."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        custom_layout.addWidget(hint)
        custom_layout.addStretch(1)
        self.control_tabs.addTab(custom, "Custom")
        upper_layout.addWidget(self.control_tabs)

        upper_layout.addWidget(self._section("Button"))
        buttons = QWidget()
        button_layout = QGridLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setHorizontalSpacing(2)
        button_layout.setVerticalSpacing(2)
        for index, (name, glyph, _action, _text) in enumerate(BUTTON_OBJECTS):
            button = QToolButton()
            button.setText(name)
            button.setIcon(icons.icon(glyph))
            button.setIconSize(icons.ICON_SIZE)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setCheckable(True)
            button.setFixedHeight(26)
            button.setStyleSheet("font-size: 9px;")
            button.setToolTip(f"Inserisci {name}")
            button.clicked.connect(
                lambda _checked=False, n=name: self.button_selected.emit(n)
            )
            button_layout.addWidget(button, index // 2, index % 2)
            self.group.addButton(button)
            self.tool_buttons[name] = button
        upper_layout.addWidget(buttons)
        upper_layout.addStretch(1)

        upper_scroll = QScrollArea()
        upper_scroll.setWidgetResizable(True)
        upper_scroll.setFrameShape(QFrame.Shape.NoFrame)
        upper_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        upper_scroll.setWidget(upper)

        field_box = QWidget()
        field_layout = QVBoxLayout(field_box)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(4)
        field_layout.addWidget(self._section("Field"))

        self.fields = FieldList()
        self.fields.setIconSize(icons.ICON_SIZE)
        self.fields.setDragEnabled(True)
        self.fields.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.fields.itemDoubleClicked.connect(
            lambda item: self.field_activated.emit(str(item.data(Qt.ItemDataRole.UserRole)))
        )
        self.fields.itemActivated.connect(
            lambda item: self.field_activated.emit(str(item.data(Qt.ItemDataRole.UserRole)))
        )
        field_layout.addWidget(self.fields, 1)
        hint = QLabel("Doppio clic o trascina un campo sul form.")
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        field_layout.addWidget(hint)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(upper_scroll)
        splitter.addWidget(field_box)
        splitter.setSizes([560, 130])
        layout.addWidget(splitter, 1)
        self.setMinimumWidth(240)

    def _tool_button(
        self, text: str, key: str, glyph: str, parent: QWidget | None = None
    ) -> QToolButton:
        button = QToolButton(parent or self)
        button.setText(text)
        button.setIcon(icons.icon(glyph))
        button.setIconSize(icons.ICON_SIZE)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setCheckable(True)
        button.setFixedHeight(26)
        button.setStyleSheet("font-size: 9px;")
        button.setToolTip(f"Inserisci {text}")
        button.clicked.connect(lambda _checked=False, k=key: self.tool_selected.emit(k))
        self.group.addButton(button)
        self.tool_buttons[key] = button
        return button

    def _section(self, title: str) -> QLabel:
        label = QLabel(title)
        label.setObjectName("palette_section")
        return label

    def select_pointer(self) -> None:
        button = self.tool_buttons.get("pointer")
        if button is not None:
            button.setChecked(True)

    def set_table(self, table_name: str) -> None:
        self.fields.clear()
        table = self.project.table(table_name)
        if table is None:
            return
        for field in table.fields:
            item = QListWidgetItem(icons.icon("campo"), field.display_name())
            item.setData(Qt.ItemDataRole.UserRole, field.name)
            item.setData(Qt.ItemDataRole.UserRole + 1, field.type)
            item.setToolTip(f"{field.name} · {field.type}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            self.fields.addItem(item)


# ----------------------------------------------------------------- storia undo
class DesignerHistory:
    """Cronologia locale del designer basata su snapshot JSON del form."""

    def __init__(self, limit: int = 100) -> None:
        self.limit = limit
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def push(self, state: dict[str, Any]) -> None:
        self._undo.append(copy.deepcopy(state))
        if len(self._undo) > self.limit:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self) -> dict[str, Any] | None:
        if not self._undo:
            return None
        return self._undo.pop()

    def redo(self, state: dict[str, Any]) -> dict[str, Any] | None:
        self._undo.append(copy.deepcopy(state))
        if not self._redo:
            return None
        return self._redo.pop()

    def remember(self, state: dict[str, Any]) -> None:
        self._redo.append(copy.deepcopy(state))

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)


# -------------------------------------------------------------------- designer
class FormDesignerWidget(QWidget):
    """Form Designer a tre zone, ospitato nell'area MDI."""

    saved = pyqtSignal(str)
    preview_requested = pyqtSignal(object)
    status_message = pyqtSignal(str)

    def __init__(self, project: Project, spec: FormSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.table = project.table(spec.table)
        self.clipboard: list[dict[str, Any]] = []
        self.page_index = 0
        self.tool = "pointer"
        self.pending_button = ""
        self.history = DesignerHistory()
        self.preview_handler: Callable[[FormSpec], None] | None = None
        self._saved_state = copy.deepcopy(spec.to_dict())
        self._stored_name = spec.name
        self._loading = False
        self._page_loading = False
        self.setWindowTitle(f"Form Designer ({spec.caption or spec.name})")
        self.resize(1160, 760)
        self._build_ui()
        self._load_page(0)
        self._select([])

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(2)
        top.addWidget(QLabel("Pages:"))
        self.page_bar = QTabBar()
        self.page_bar.setExpanding(False)
        self.page_bar.setDrawBase(False)
        self.page_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.page_bar.customContextMenuRequested.connect(self._page_context_menu)
        self.page_bar.currentChanged.connect(self._on_page_tab_changed)
        self.page_bar.setToolTip("Tasto destro per rinominare o eliminare la pagina")
        top.addWidget(self.page_bar, 0)
        top.addWidget(icons.make_button("", "nuovo", self.add_page, self, "Nuova pagina"))
        top.addWidget(icons.make_button("", "modifica", self.rename_page, self, "Rinomina pagina"))
        top.addWidget(icons.make_button("", "elimina", self.remove_page, self, "Elimina pagina"))
        top.addSpacing(8)
        for glyph, slot, tip in (
            ("taglia", self.cut_selection, "Taglia (Ctrl+X)"),
            ("copia", self.copy_selection, "Copia (Ctrl+C)"),
            ("incolla", self.paste_clipboard, "Incolla (Ctrl+V)"),
            ("copia", self.duplicate_selection, "Duplica (Ctrl+D)"),
            ("elimina", self.remove_selected, "Elimina (Canc)"),
        ):
            top.addWidget(icons.make_button("", glyph, slot, self, tip))
        top.addSpacing(8)
        self.undo_button = icons.make_button("", "undo", self.undo, self, "Annulla (Ctrl+Z)")
        self.redo_button = icons.make_button("", "redo", self.redo, self, "Ripeti (Ctrl+Y)")
        top.addWidget(self.undo_button)
        top.addWidget(self.redo_button)
        top.addSpacing(8)
        top.addWidget(
            icons.make_button(
                "", "allinea", self.align_selection, self, "Allinea a sinistra i controlli selezionati"
            )
        )
        top.addWidget(
            icons.make_button(
                "",
                "distribuisci",
                self.distribute_selection,
                self,
                "Distribuisci orizzontalmente i controlli selezionati",
            )
        )
        self.zorder_button = QToolButton()
        self.zorder_button.setIcon(icons.icon("finestra"))
        self.zorder_button.setIconSize(icons.ICON_SIZE)
        self.zorder_button.setToolTip("Porta avanti/indietro e allineamento")
        self.zorder_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        zorder_menu = QMenu(self.zorder_button)
        zorder_menu.addAction("Porta in primo piano", self.bring_to_front)
        zorder_menu.addAction("Porta sullo sfondo", self.send_to_back)
        align_menu = zorder_menu.addMenu("Allinea")
        for label, mode in (
            ("Sinistra", "left"),
            ("Destra", "right"),
            ("Centro", "center"),
            ("Alto", "top"),
            ("Basso", "bottom"),
            ("Centro verticale", "middle"),
        ):
            align_menu.addAction(label, lambda m=mode: self.align_selection(m))
        distribute_menu = zorder_menu.addMenu("Distribuisci")
        distribute_menu.addAction("Orizzontalmente", lambda: self.distribute_selection("horizontal"))
        distribute_menu.addAction("Verticalmente", lambda: self.distribute_selection("vertical"))
        self.zorder_button.setMenu(zorder_menu)
        top.addWidget(self.zorder_button)
        top.addStretch(1)
        self.grid_button = icons.make_button(
            "", "tabella", self.toggle_grid, self, "Mostra la griglia di punti", checkable=True
        )
        self.grid_button.setChecked(True)
        top.addWidget(self.grid_button)
        top.addWidget(
            icons.make_button("", "anteprima", self.preview, self, "Esegui il form in anteprima")
        )
        top.addWidget(icons.make_button("", "salva", self.save, self, "Salva il form"))
        layout.addLayout(top)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter, 1)

        self.palette = PalettePanel(self.project)
        self.palette.tool_selected.connect(self._on_tool_selected)
        self.palette.button_selected.connect(self._on_button_selected)
        self.palette.field_activated.connect(self.add_field_control)
        self.palette.set_table(self.spec.table)
        self.splitter.addWidget(self.palette)

        self.splitter.addWidget(self._build_centre())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        self.object_combo = QComboBox()
        self.object_combo.setToolTip("Oggetto ispezionato (form oppure controllo)")
        self.object_combo.activated.connect(self._on_object_combo)
        right_layout.addWidget(self.object_combo)
        self.inspector = PropertyInspector()
        self.inspector.setMinimumWidth(250)
        self.inspector.property_changed.connect(self._on_property_changed)
        self.inspector.event_changed.connect(self._on_event_changed)
        self.inspector.method_changed.connect(self._on_method_changed)
        right_layout.addWidget(self.inspector, 1)
        self.splitter.addWidget(right)
        self.splitter.setSizes([240, 600, 320])

        self.status_labels: dict[str, QLabel] = {}
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        for key in ("Object", "Page", "Top", "Left", "Height", "Width"):
            label = QLabel(f"{key}: —")
            self.status_labels[key] = label
            status_row.addWidget(label)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        self._install_shortcuts()

    def _build_centre(self) -> QWidget:
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
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.geometry_changed.connect(self._on_geometry_changed)
        self.canvas.edit_started.connect(self._push_undo)
        self.canvas.tool_used.connect(self._place_control)
        self.canvas.field_dropped.connect(self._on_field_dropped)
        self.canvas.delete_requested.connect(self.remove_selected)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.scroll.setStyleSheet("QScrollArea { background: %s; }" % _tokens()["window_bg"])
        self.scroll.horizontalScrollBar().valueChanged.connect(self.h_ruler.set_offset)
        self.scroll.verticalScrollBar().valueChanged.connect(self.v_ruler.set_offset)
        canvas_row.addWidget(self.scroll, 1)
        centre_layout.addLayout(canvas_row, 1)
        return centre

    def _install_shortcuts(self) -> None:
        self._shortcuts: list[QShortcut] = []
        shortcuts = {
            "Ctrl+X": self.cut_selection,
            "Ctrl+C": self.copy_selection,
            "Ctrl+V": self.paste_clipboard,
            "Ctrl+D": self.duplicate_selection,
            "Ctrl+Z": self.undo,
            "Ctrl+Y": self.redo,
            "Ctrl+Shift+Z": self.redo,
            "Ctrl+S": self.save,
        }
        for sequence, slot in shortcuts.items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    # ---------------------------------------------------------------- pagine
    def current_page(self) -> FormPage:
        return self.spec.pages[max(0, min(self.page_index, len(self.spec.pages) - 1))]

    def _sync_page_bar(self) -> None:
        self._page_loading = True
        while self.page_bar.count() > len(self.spec.pages):
            self.page_bar.removeTab(self.page_bar.count() - 1)
        while self.page_bar.count() < len(self.spec.pages):
            self.page_bar.addTab(self.spec.pages[self.page_bar.count()].caption or f"Pagina {self.page_bar.count() + 1}")
        for index, page in enumerate(self.spec.pages):
            self.page_bar.setTabText(index, page.caption or f"Pagina {index + 1}")
        self.page_bar.setCurrentIndex(max(0, min(self.page_index, len(self.spec.pages) - 1)))
        self._page_loading = False

    def _load_page(self, index: int) -> None:
        self.page_index = max(0, min(index, len(self.spec.pages) - 1))
        self.canvas.load(self.spec, self.page_index)
        self.canvas.set_selection([], notify=False)
        self._sync_page_bar()
        self._refresh_objects()
        self._select([])

    def _on_page_tab_changed(self, index: int) -> None:
        if self._page_loading or index < 0:
            return
        self._load_page(index)

    def add_page(self) -> None:
        caption, ok = QInputDialog.getText(
            self, "Nuova pagina", "Titolo della scheda:", text=f"Pagina {len(self.spec.pages) + 1}"
        )
        if not ok:
            return
        self._push_undo()
        self.spec.pages.append(FormPage(caption=caption or f"Pagina {len(self.spec.pages) + 1}"))
        self._load_page(len(self.spec.pages) - 1)
        self._mark_dirty()

    def rename_page(self) -> None:
        page = self.current_page()
        caption, ok = QInputDialog.getText(
            self, "Rinomina pagina", "Titolo della scheda:", text=page.caption
        )
        if not ok:
            return
        self._push_undo()
        page.caption = caption or page.caption
        self._sync_page_bar()
        self._mark_dirty()

    def remove_page(self) -> None:
        if len(self.spec.pages) <= 1:
            QMessageBox.information(self, "Pagine", "Il form deve conservare almeno una pagina.")
            return
        page = self.current_page()
        if page.controls:
            answer = QMessageBox.question(
                self,
                "Elimina pagina",
                f"La pagina «{page.caption}» contiene {len(page.controls)} controlli.\nEliminarla?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._push_undo()
        del self.spec.pages[self.page_index]
        self._load_page(min(self.page_index, len(self.spec.pages) - 1))
        self._mark_dirty()

    def _page_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Nuova pagina", self.add_page)
        menu.addAction("Rinomina pagina", self.rename_page)
        menu.addAction("Elimina pagina", self.remove_page)
        menu.exec(self.page_bar.mapToGlobal(position))

    def toggle_grid(self, checked: bool) -> None:
        self.canvas.show_grid = checked
        self.canvas.update()

    # ---------------------------------------------------------- palette e tool
    def _on_tool_selected(self, tool: str) -> None:
        self.tool = tool
        self.pending_button = ""
        self.canvas.set_tool(tool)

    def _on_button_selected(self, name: str) -> None:
        self.pending_button = name
        self.tool = "button"
        self.canvas.set_tool("button")

    def _place_control(self, x: int, y: int) -> None:
        kind = self.tool
        button = self.pending_button
        self.add_control(kind, x, y, button=button)
        self.palette.select_pointer()
        self._on_tool_selected("pointer")

    def control_name(self, control: FormControl) -> str:
        return self.spec.control_object_name(control)

    # ------------------------------------------------------------------ campi
    def _field_kind(self, field_name: str) -> str:
        field = self.table.field(field_name) if self.table else None
        if field is None:
            return "field"
        if field.type == "memo":
            return "memo"
        if field.type in ("integer", "decimal"):
            return "number"
        if field.type == "boolean":
            return "checkbox"
        if field.type == "date":
            return "date"
        if field.lookup:
            return "combo"
        return "field"

    def add_field_control(self, field_name: str, x: int | None = None, y: int | None = None) -> None:
        field = self.table.field(field_name) if self.table else None
        if field is None:
            return
        page = self.current_page()
        used = [c for c in page.controls if c.kind in FIELD_KINDS]
        if x is None or y is None:
            x = 176
            y = 8 + 32 * len(used)
        y = min(max(SNAP, y), max(SNAP, self.spec.height - 40))
        self._push_undo()
        label = FormControl(
            id=new_id(),
            kind="label",
            text=field.display_name(),
            x=max(0, x - 150),
            y=y + 3,
            w=140,
            h=20,
        )
        kind = self._field_kind(field_name)
        control = FormControl(
            id=new_id(),
            kind=kind,
            field=field_name,
            x=x,
            y=y,
            w=300,
            h=52 if kind == "memo" else 24,
            lookup=field.lookup,
        )
        page.controls.extend([label, control])
        self.canvas._rebuild()
        self._refresh_objects()
        self._select([control.id])
        self._mark_dirty()

    def _on_field_dropped(self, field_name: str, x: int, y: int) -> None:
        self.add_field_control(field_name, x=x, y=y)

    def add_control(
        self,
        kind: str,
        x: int = 20,
        y: int = 20,
        *,
        button: str = "",
        field_name: str = "",
    ) -> FormControl | None:
        if kind not in CONTROL_KINDS:
            return None
        self._push_undo()
        default_field = field_name
        if kind in FIELD_KINDS and not default_field and self.table and self.table.fields:
            existing = {c.field for c in self.current_page().controls}
            default_field = next(
                (
                    f.name
                    for f in self.table.fields
                    if f.name not in existing
                ),
                self.table.fields[0].name,
            )
        text = ""
        action = "save"
        if kind == "button":
            if button and button in BUTTON_SPECS:
                _glyph, action, text = BUTTON_SPECS[button]
                if action == "report:":
                    reports = self.project.names("reports")
                    action = f"report:{reports[0]}" if reports else "none"
                if action == "script:":
                    scripts = self.project.names("scripts")
                    action = f"script:{scripts[0]}" if scripts else "none"
            else:
                text = "Pulsante"
        if kind == "label":
            text = "Etichetta"
        control = FormControl(
            id=new_id(),
            kind=kind,
            field=default_field,
            text=text,
            action=action,
            x=max(0, (x // SNAP) * SNAP),
            y=max(0, (y // SNAP) * SNAP),
            w=320 if kind == "grid" else 180,
            h=140 if kind == "grid" else 24,
            table=self.table.name if kind == "grid" and self.table else "",
        )
        self.current_page().controls.append(control)
        self.canvas._rebuild()
        self._refresh_objects()
        self._select([control.id])
        self._mark_dirty()
        return control

    # -------------------------------------------------------------- selezione
    def selected_controls(self) -> list[FormControl]:
        return self.canvas.selected_controls()

    def _on_selection_changed(self, ids: list[str]) -> None:
        self._select(ids, refresh_objects=False)

    def _on_geometry_changed(self) -> None:
        self._refresh_status()
        self._mark_dirty()

    def _select(self, ids: list[str], refresh_objects: bool = True) -> None:
        self.canvas.set_selection(ids, notify=False)
        if refresh_objects:
            self._sync_combo()
        selected = self.selected_controls()
        if len(selected) == 1:
            self._show_control(selected[0])
        elif len(selected) > 1:
            self._show_multi(selected)
        else:
            self._show_form()
        self._refresh_status()

    def _sync_combo(self) -> None:
        combo = self.object_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(f"form — {self.spec.name}", None)
        for control in self.current_page().controls:
            combo.addItem(self.control_name(control), control.id)
        combo.blockSignals(False)
        selected = self.selected_controls()
        if len(selected) == 1:
            index = combo.findData(selected[0].id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _on_object_combo(self, index: int) -> None:
        control_id = self.object_combo.itemData(index)
        self._select([] if control_id is None else [str(control_id)])

    # ------------------------------------------------------------- inspector
    def _field_choices(self) -> list[tuple[str, str]]:
        choices = [("", "(nessuno)")]
        for field in (self.table.fields if self.table else []):
            choices.append((field.name, field.display_name()))
        return choices

    def _table_choices(self) -> list[tuple[str, str]]:
        return [("", "(nessuna)")] + [(name, name) for name in self.project.names("tables")]

    def _action_choices(self) -> list[tuple[str, str]]:
        choices = [(key, label) for key, label in BUTTON_ACTIONS.items()]
        choices += [("cancel", "Annulla modifiche"), ("help", "Aiuto"), ("info", "Info record")]
        choices += [("browse", "Apri Browse"), ("none", "(nessuna azione)")]
        choices += [(f"script:{n}", f"Script: {n}") for n in self.project.names("scripts")]
        choices += [(f"report:{n}", f"Report: {n}") for n in self.project.names("reports")]
        return choices

    def _show_form(self) -> None:
        self.inspector.set_properties(
            [
                (
                    "• Form",
                    [
                        ("name", "Name", "text", self.spec.name, None),
                        ("caption", "Caption", "text", self.spec.caption, None),
                        ("width", "Width", "int", self.spec.width, None),
                        ("height", "Height", "int", self.spec.height, None),
                        ("order", "Order", "text", self.spec.order, None),
                        ("backcolor", "BackColor", "text", self.spec.backcolor, None),
                        ("forecolor", "ForeColor", "text", self.spec.forecolor, None),
                    ],
                ),
                (
                    "• Data",
                    [
                        (
                            "table",
                            "Table",
                            "choice",
                            self.spec.table,
                            self._table_choices(),
                        ),
                    ],
                ),
            ]
        )
        self._show_events(None)
        self._show_methods(None)

    def _show_control(self, control: FormControl) -> None:
        self.inspector.set_properties(
            [
                (
                    "• Font Properties",
                    [
                        ("font_size", "FontSize", "int", control.font_size, None),
                        ("font_name", "FontName", "text", control.font_name, None),
                        ("bold", "FontBold", "bool", control.bold, None),
                    ],
                ),
                (
                    "• Geometry",
                    [
                        ("x", "Left", "int", control.x, None),
                        ("y", "Top", "int", control.y, None),
                        ("w", "Width", "int", control.w, None),
                        ("h", "Height", "int", control.h, None),
                    ],
                ),
                (
                    "• Data",
                    [
                        (
                            "kind",
                            "Class",
                            "choice",
                            control.kind,
                            [(key, value) for key, value in CONTROL_KINDS.items()],
                        ),
                        ("field", "Field", "choice", control.field, self._field_choices()),
                        ("text", "Text", "text", control.text, None),
                        ("lookup", "Lookup", "text", control.lookup, None),
                        ("table", "ChildTable", "choice", control.table, self._table_choices()),
                        ("link_parent", "LinkParent", "text", control.link_parent, None),
                        ("link_child", "LinkChild", "text", control.link_child, None),
                        ("backcolor", "BackColor", "text", control.backcolor, None),
                        ("forecolor", "ForeColor", "text", control.forecolor, None),
                    ],
                ),
                (
                    "• Behavior",
                    [
                        ("action", "Action", "choice", control.action, self._action_choices()),
                    ],
                ),
                (
                    "• Layout",
                    [
                        (
                            "align",
                            "Align",
                            "choice",
                            control.align,
                            [("left", "Sinistra"), ("center", "Centro"), ("right", "Destra")],
                        ),
                    ],
                ),
            ]
        )
        self._show_events(control)
        self._show_methods(control)

    def _show_multi(self, controls: list[FormControl]) -> None:
        self.inspector.set_properties(
            [
                (
                    "• Selection",
                    [
                        ("count", "Oggetti", "ro", len(controls), None),
                        ("top", "Top", "ro", min(c.y for c in controls), None),
                        ("left", "Left", "ro", min(c.x for c in controls), None),
                    ],
                )
            ]
        )
        self.inspector.set_events([])
        self.inspector.set_methods([])

    EVENT_LABELS = {
        "onClick": "al clic",
        "onEnter": "all'ingresso",
        "onExit": "all'uscita",
        "onOpen": "all'apertura del form",
        "onClose": "alla chiusura del form",
    }

    def _show_events(self, control: FormControl | None) -> None:
        names = CONTROL_EVENTS if control is not None else FORM_EVENTS
        source = control.events if control is not None else self.spec.events
        self.inspector.set_events(
            [(name, self.EVENT_LABELS.get(name, ""), source.get(name, "")) for name in names]
        )

    def _show_methods(self, control: FormControl | None) -> None:
        if control is None:
            rows = [
                ("save", "salva il form", self.spec.methods.get("save", "")),
                ("close", "chiude il form", self.spec.methods.get("close", "")),
            ]
        else:
            rows = [
                (name, description, control.methods.get(name, ""))
                for name, description, _empty in METHOD_HELP
            ]
        self.inspector.set_methods(rows)

    def _on_property_changed(self, key: str, value: Any) -> None:
        selected = self.selected_controls()
        if not selected:
            self._push_undo()
            if key == "table":
                self.spec.table = str(value or "")
                self.table = self.project.table(self.spec.table)
                self.palette.set_table(self.spec.table)
            elif key in ("width", "height"):
                setattr(self.spec, key, max(120, int(value)))
                self.canvas.load(self.spec, self.page_index)
            elif key in ("backcolor", "forecolor"):
                setattr(self.spec, key, str(value))
                self.canvas.load(self.spec, self.page_index)
            else:
                setattr(self.spec, key, str(value))
            self.setWindowTitle(f"Form Designer ({self.spec.caption or self.spec.name})")
            self._mark_dirty()
            self._refresh_status()
            return
        self._push_undo()
        for control in selected:
            if key in ("x", "y"):
                value = max(0, int(value))
            elif key in ("w", "h"):
                value = max(MIN_CONTROL, int(value))
            elif key == "font_size":
                value = max(6, int(value))
            setattr(control, key, value)
            if key == "kind" and control.kind == "grid" and self.table:
                control.table = self.table.name
        if key in ("x", "y", "w", "h", "font_size", "bold", "text", "backcolor", "forecolor"):
            for control in selected:
                self.canvas.sync_control(control)
        if key == "kind":
            self.canvas._rebuild()
            self._refresh_objects()
        self._mark_dirty()
        self._refresh_status()

    def _on_event_changed(self, name: str, action: str) -> None:
        self._push_undo()
        selected = self.selected_controls()
        if len(selected) == 1:
            if action.strip():
                selected[0].events[name] = action.strip()
            else:
                selected[0].events.pop(name, None)
        elif not selected:
            if action.strip():
                self.spec.events[name] = action.strip()
            else:
                self.spec.events.pop(name, None)
        self._mark_dirty()

    def _on_method_changed(self, name: str, body: str) -> None:
        self._push_undo()
        selected = self.selected_controls()
        target = selected[0].methods if len(selected) == 1 else self.spec.methods
        if body.strip():
            target[name] = body
        else:
            target.pop(name, None)
        self._mark_dirty()

    # ------------------------------------------------------------- comandi
    def _push_undo(self) -> None:
        if getattr(self, "_in_undo", False):
            return
        self.history.push(self.spec.to_dict())
        self._refresh_history_actions()

    def undo(self) -> None:
        state = self.history.undo()
        if state is None:
            self._refresh_history_actions()
            return
        self.history.remember(self.spec.to_dict())
        self._restore(state)
        self._refresh_history_actions()

    def redo(self) -> None:
        state = self.history.redo(self.spec.to_dict())
        if state is None:
            self._refresh_history_actions()
            return
        self._restore(state)
        self._refresh_history_actions()

    def _restore(self, state: dict[str, Any]) -> None:
        self._in_undo = True
        try:
            self.spec = FormSpec.from_dict(state)
            self.table = self.project.table(self.spec.table)
            self.canvas.selection = []
            self._load_page(min(self.page_index, len(self.spec.pages) - 1))
            self.palette.set_table(self.spec.table)
        finally:
            self._in_undo = False
        self._mark_dirty()

    def _refresh_history_actions(self) -> None:
        self.undo_button.setEnabled(self.history.can_undo)
        self.redo_button.setEnabled(self.history.can_redo)

    def copy_selection(self) -> None:
        selected = self.selected_controls()
        if not selected:
            return
        self.clipboard = [copy.deepcopy(control.to_dict()) for control in selected]
        self.status_message.emit(f"Copiati {len(self.clipboard)} oggetti")

    def cut_selection(self) -> None:
        if not self.selected_controls():
            return
        self.copy_selection()
        self.remove_selected()

    def paste_clipboard(self) -> None:
        if not self.clipboard:
            return
        self._push_undo()
        page = self.current_page()
        pasted: list[FormControl] = []
        for data in self.clipboard:
            control = FormControl.from_dict(data)
            control.id = new_id()
            control.x = min(max(0, control.x + SNAP), max(0, self.spec.width - control.w))
            control.y = min(max(0, control.y + SNAP), max(0, self.spec.height - control.h))
            page.controls.append(control)
            pasted.append(control)
        self.canvas._rebuild()
        self._refresh_objects()
        self._select([c.id for c in pasted])
        self._mark_dirty()

    def duplicate_selection(self) -> None:
        selected = self.selected_controls()
        if not selected:
            return
        self.clipboard = [copy.deepcopy(control.to_dict()) for control in selected]
        self.paste_clipboard()

    def remove_selected(self) -> None:
        selected = self.selected_controls()
        if not selected:
            return
        self._push_undo()
        ids = {control.id for control in selected}
        page = self.current_page()
        page.controls = [c for c in page.controls if c.id not in ids]
        self.canvas.selection = []
        self.canvas._rebuild()
        self._refresh_objects()
        self._select([])
        self._mark_dirty()

    def delete_key(self) -> None:
        self.remove_selected()

    def _move_z(self, delta: int) -> None:
        selected = self.selected_controls()
        if not selected:
            return
        self._push_undo()
        page = self.current_page()
        ids = {control.id for control in selected}
        moving = [c for c in page.controls if c.id in ids]
        rest = [c for c in page.controls if c.id not in ids]
        if delta > 0:
            page.controls = rest + moving
        else:
            page.controls = moving + rest
        self.canvas._rebuild()
        self._mark_dirty()

    def bring_to_front(self) -> None:
        self._move_z(1)

    def send_to_back(self) -> None:
        self._move_z(-1)

    def align_selection(self, mode: str = "left") -> None:
        selected = self.selected_controls()
        if len(selected) < 2:
            self.status_message.emit("Seleziona almeno due controlli per allineare")
            return
        self._push_undo()
        if mode in ("left", "right", "center"):
            if mode == "left":
                target = min(c.x for c in selected)
            elif mode == "right":
                target = max(c.x + c.w for c in selected)
            else:
                target = sum(c.x + c.w // 2 for c in selected) // len(selected)
            for control in selected:
                if mode == "left":
                    control.x = target
                elif mode == "right":
                    control.x = target - control.w
                else:
                    control.x = max(0, target - control.w // 2)
        else:
            if mode == "top":
                target = min(c.y for c in selected)
            elif mode == "bottom":
                target = max(c.y + c.h for c in selected)
            else:
                target = sum(c.y + c.h // 2 for c in selected) // len(selected)
            for control in selected:
                if mode == "top":
                    control.y = target
                elif mode == "bottom":
                    control.y = target - control.h
                else:
                    control.y = max(0, target - control.h // 2)
        for control in selected:
            self.canvas.sync_control(control)
        self._mark_dirty()
        self._refresh_status()

    def distribute_selection(self, mode: str = "horizontal") -> None:
        selected = self.selected_controls()
        if len(selected) < 3:
            self.status_message.emit("Seleziona almeno tre controlli per distribuire")
            return
        self._push_undo()
        if mode == "horizontal":
            ordered = sorted(selected, key=lambda c: c.x)
            first, last = ordered[0], ordered[-1]
            span = (last.x + last.w) - first.x
            used = sum(c.w for c in ordered)
            gap = (span - used) / max(1, len(ordered) - 1)
            cursor = first.x
            for control in ordered:
                control.x = int(round(cursor))
                cursor += control.w + gap
        else:
            ordered = sorted(selected, key=lambda c: c.y)
            first, last = ordered[0], ordered[-1]
            span = (last.y + last.h) - first.y
            used = sum(c.h for c in ordered)
            gap = (span - used) / max(1, len(ordered) - 1)
            cursor = first.y
            for control in ordered:
                control.y = int(round(cursor))
                cursor += control.h + gap
        for control in selected:
            self.canvas.sync_control(control)
        self._mark_dirty()
        self._refresh_status()

    # -------------------------------------------------------------- stato/dirty
    def _refresh_objects(self) -> None:
        self._sync_combo()

    def _refresh_status(self) -> None:
        selected = self.selected_controls()
        control = selected[0] if len(selected) == 1 else None
        if control is not None:
            obj = self.control_name(control)
        elif selected:
            obj = f"{len(selected)} oggetti"
        else:
            obj = "form"
        values = {
            "Object": obj,
            "Page": str(self.page_index + 1),
            "Top": f"{control.y / SNAP:.2f}" if control else "—",
            "Left": f"{control.x / SNAP:.2f}" if control else "—",
            "Height": f"{control.h / SNAP:.2f}" if control else "—",
            "Width": f"{control.w / SNAP:.2f}" if control else "—",
        }
        for key, value in values.items():
            self.status_labels[key].setText(f"{key}: {value}")

    def _mark_dirty(self) -> None:
        self._refresh_status()
        self._refresh_history_actions()

    def is_dirty(self) -> bool:
        return self.spec.to_dict() != self._saved_state

    # ------------------------------------------------------------------ azioni
    def preview(self) -> None:
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Form non valido", "\n".join(errors))
            return
        if self.preview_handler is not None:
            self.preview_handler(self.spec)
            return
        self.preview_requested.emit(self.spec)

    def save(self) -> bool:
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Form non valido", "\n".join(errors))
            return False
        try:
            self.project.put_object(
                "forms", self.spec.to_dict(), previous_name=getattr(self, "_stored_name", self.spec.name)
            )
            self._stored_name = self.spec.name
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self._saved_state = copy.deepcopy(self.spec.to_dict())
        self.history.clear()
        self._refresh_history_actions()
        self.saved.emit(self.spec.name)
        self.status_message.emit(f"Form {self.spec.name} salvato")
        return True


# Compatibilità con il nome storico usato da smoke, test e capture.
FormBuilderDialog = FormDesignerWidget
