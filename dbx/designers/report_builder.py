"""Report Designer: foglio a bande impilate in stile Crystal Reports (O5).

Un unico foglio mostra tutte le bande del report nell'ordine del modello,
etichettate a sinistra, con righello, griglia, controlli ridimensionabili e
delimitatori di banda trascinabili. Le due toolbar (standard e formattazione)
e i dialoghi Insert Field / Sort Order completano la finestra.
"""

from __future__ import annotations

import copy
from typing import Any

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..core.metadata import new_id, slugify
from ..core.project import Project, ProjectError
from ..runtime.report_engine import (
    BAND_LABELS,
    BAND_NAMES,
    CONTROL_KINDS,
    Control,
    ReportSpec,
    field_display_name,
)
from ..ui import design, icons
from ..ui.widgets import PropertyInspector

BASE_SCALE = 3.0  # px per mm a zoom 100%
GUTTER = 96
SNAP_MM = 0.5
MIN_CONTROL_MM = 2.0
MIN_BAND_MM = 4.0


def _tokens() -> dict[str, str]:
    app = QApplication.instance()
    name = app.property("dbx_theme") if app is not None else None
    return design.palette(name if isinstance(name, str) else None)


class ReportRuler(QWidget):
    """Righello orizzontale del foglio, tacche ogni 5 mm e etichette ogni 10."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.offset = 0
        self.scale = BASE_SCALE
        self.origin = 0
        self.setFixedHeight(design.METRICS.ruler_size)

    def set_metrics(self, scale: float, offset: int = 0) -> None:
        self.scale = scale
        self.offset = offset
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        palette = _tokens()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(palette["ruler_bg"]))
        painter.setPen(QPen(QColor(palette["ruler_text"]), 1))
        start = self.origin - self.offset
        step = 5 * self.scale
        index = 0
        x = start
        while x < self.width():
            if x >= 0:
                if index % 2 == 0:
                    painter.drawText(int(x) + 2, self.height() - 3, str(index * 5))
                    tick = self.height()
                else:
                    tick = self.height() // 2
                painter.drawLine(QPoint(int(x), self.height() - tick), QPoint(int(x), self.height()))
            x += step
            index += 1
        painter.setPen(QPen(QColor(palette["panel_shadow"]), 1))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)


class ReportCanvas(QWidget):
    """Foglio unico con bande impilate, selezione, resize e divider trascinabili."""

    selection_changed = pyqtSignal(object)
    geometry_changed = pyqtSignal()
    edit_started = pyqtSignal()
    delete_requested = pyqtSignal()
    band_changed = pyqtSignal(str)
    control_activated = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec: ReportSpec | None = None
        self.zoom_factor = 1.0
        self.selected: str | None = None
        self.active_band = "detail"
        self._mode: str | None = None
        self._handle = ""
        self._press = QPoint()
        self._start_rect = QRectF()
        self._start_band_height = 0.0
        self._offset_mm = (0.0, 0.0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------ misure
    @property
    def scale(self) -> float:
        return BASE_SCALE * self.zoom_factor

    def load(self, spec: ReportSpec) -> None:
        self.spec = spec
        self._resize()
        self.update()

    def set_zoom_factor(self, factor: float) -> None:
        self.zoom_factor = max(0.5, min(2.0, float(factor)))
        self._resize()
        self.update()

    def _resize(self) -> None:
        if self.spec is None:
            return
        width, height = self.spec.page_dimensions()
        self.setFixedSize(int(GUTTER + width * self.scale), int(height * self.scale))

    def band_height(self, name: str) -> float:
        assert self.spec is not None
        controls = self.spec.band(name)
        minimum = 0.0
        for control in controls:
            text_height = control.font_size * 0.45 if control.kind not in ("line", "rect", "image") else 0.0
            minimum = max(minimum, control.y + max(control.h, text_height))
        return max(MIN_BAND_MM, self.spec.band_height(name, minimum))

    def band_tops(self) -> list[tuple[str, float, float]]:
        """(nome, top px, altezza px) delle bande visibili, nell'ordine del modello."""
        if self.spec is None:
            return []
        result: list[tuple[str, float, float]] = []
        y = self.spec.margins["top"] * self.scale
        for name in self.spec.effective_band_order():
            if not self.spec.is_visible(name):
                continue
            height = self.band_height(name) * self.scale
            result.append((name, y, height))
            y += height
        return result

    def band_at(self, y: float) -> str | None:
        for name, top, height in self.band_tops():
            if top <= y <= top + height:
                return name
        return None

    def controls_of(self, band: str) -> list[Control]:
        assert self.spec is not None
        return self.spec.band(band)

    def control(self, control_id: str) -> tuple[str, Control] | None:
        if self.spec is None:
            return None
        for name in self.spec.effective_band_order():
            for control in self.spec.band(name):
                if control.id == control_id:
                    return name, control
        return None

    def control_rect(self, band: str, control: Control) -> QRectF:
        assert self.spec is not None
        top = dict((name, top) for name, top, _h in self.band_tops()).get(band, 0.0)
        left = GUTTER + (self.spec.margins["left"] + control.x) * self.scale
        return QRectF(
            left,
            top + control.y * self.scale,
            max(2.0, control.w * self.scale),
            max(2.0, control.h * self.scale),
        )

    @staticmethod
    def handles(rect: QRectF) -> list[tuple[str, QPoint]]:
        return [
            ("nw", rect.topLeft().toPoint()),
            ("n", QPoint(int(rect.center().x()), int(rect.top()))),
            ("ne", rect.topRight().toPoint()),
            ("e", QPoint(int(rect.right()), int(rect.center().y()))),
            ("se", rect.bottomRight().toPoint()),
            ("s", QPoint(int(rect.center().x()), int(rect.bottom()))),
            ("sw", rect.bottomLeft().toPoint()),
            ("w", QPoint(int(rect.left()), int(rect.center().y()))),
        ]

    def _handle_at(self, point: QPoint) -> str | None:
        found = self.control(self.selected) if self.selected else None
        if found is None:
            return None
        band, control = found
        for name, center in self.handles(self.control_rect(band, control)):
            if abs(point.x() - center.x()) <= 5 and abs(point.y() - center.y()) <= 5:
                return name
        return None

    def _hit_control(self, point: QPoint) -> tuple[str, Control] | None:
        position = QPointF(point)
        for name, top, height in self.band_tops():
            for control in reversed(self.spec.band(name) if self.spec else []):
                rect = self.control_rect(name, control)
                if rect.contains(position):
                    return name, control
        return None

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        palette = _tokens()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(palette["window_bg"]))
        if self.spec is None:
            return
        width_mm, height_mm = self.spec.page_dimensions()
        page = QRectF(GUTTER, 0, width_mm * self.scale, height_mm * self.scale)
        painter.fillRect(page, QColor(palette["workspace"]))
        painter.setPen(QPen(QColor(palette["panel_shadow"]), 1))
        painter.drawRect(page)

        left = page.left() + self.spec.margins["left"] * self.scale
        top = self.spec.margins["top"] * self.scale
        right = page.right() - self.spec.margins["right"] * self.scale
        bottom = page.bottom() - self.spec.margins["bottom"] * self.scale

        # Sfondi delle bande sotto la griglia, così i punti restano visibili.
        for name, band_top, band_height in self.band_tops():
            active = name == self.active_band
            painter.fillRect(
                QRectF(GUTTER, band_top, page.width(), band_height),
                QColor(
                    palette["report_band_active"]
                    if active
                    else palette["report_band"]
                ),
            )
            painter.fillRect(QRectF(0, band_top, GUTTER, band_height), QColor(palette["panel"]))

        painter.setPen(QPen(QColor(palette["grid_dot"]), 1, Qt.PenStyle.DotLine))
        grid = 5 * self.scale
        x = left
        while x <= right:
            painter.drawLine(QPoint(int(x), int(top)), QPoint(int(x), int(bottom)))
            x += grid
        y = top
        while y <= bottom:
            painter.drawLine(QPoint(int(left), int(y)), QPoint(int(right), int(y)))
            y += grid

        label_font = QFont()
        label_font.setPointSizeF(7.5)
        label_font.setBold(True)
        for name, band_top, band_height in self.band_tops():
            painter.setPen(QPen(QColor(palette["panel_shadow"]), 1, Qt.PenStyle.DashLine))
            painter.drawLine(
                QPoint(GUTTER, int(band_top + band_height)),
                QPoint(int(page.right()), int(band_top + band_height)),
            )
            painter.setPen(QPen(QColor(palette["ruler_text"]), 1))
            painter.setFont(label_font)
            painter.drawText(
                QRectF(4, band_top + 2, GUTTER - 8, band_height - 4),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                BAND_LABELS.get(name, name),
            )
            for control in self.spec.band(name):
                self._paint_control(painter, name, control)

        painter.setPen(QPen(QColor(palette["panel_shadow"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(left, top, right - left, bottom - top))

    def _paint_control(self, painter: QPainter, band: str, control: Control) -> None:
        palette = _tokens()
        rect = self.control_rect(band, control)
        selected = control.id == self.selected
        painter.setPen(QPen(QColor(palette["focus"] if selected else palette["panel_shadow"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        font = QFont()
        if control.font_name:
            font.setFamily(control.font_name)
        font.setPointSizeF(max(5.5, min(16.0, float(control.font_size) * 0.72)))
        font.setBold(control.bold)
        font.setItalic(control.italic)
        font.setUnderline(control.underline)
        painter.setFont(font)
        painter.setPen(QPen(QColor(palette["text"]), 1))
        if control.kind == "line":
            painter.drawLine(rect.topLeft(), rect.topRight())
        elif control.kind == "rect":
            painter.drawRect(rect)
        elif control.kind == "image":
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "Immagine")
        else:
            text = control.text or control.expr
            if control.kind == "field" and control.expr:
                text = field_display_name(self.spec.table if self.spec else "", control.expr)
            elif control.kind == "expr":
                text = f"= {control.expr}"
            elif control.kind == "total":
                text = f"{control.func}({control.expr})"
            flags = {
                "left": Qt.AlignmentFlag.AlignLeft,
                "center": Qt.AlignmentFlag.AlignHCenter,
                "right": Qt.AlignmentFlag.AlignRight,
            }.get(control.align, Qt.AlignmentFlag.AlignLeft)
            painter.drawText(
                rect.adjusted(1, 0, -1, 0),
                int(flags | Qt.AlignmentFlag.AlignVCenter),
                str(text),
            )
        if selected:
            painter.setPen(QPen(QColor(palette["focus"]), 1, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(-1, -1, 1, 1))
            painter.setPen(QPen(QColor(palette["focus"]), 1))
            painter.setBrush(QColor(palette["workspace"]))
            for _name, center in self.handles(rect):
                painter.drawRect(QRectF(center.x() - 2.5, center.y() - 2.5, 5, 5))
            painter.setBrush(Qt.BrushStyle.NoBrush)

    # ------------------------------------------------------------------ mouse
    def mousePressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() != Qt.MouseButton.LeftButton or self.spec is None:
            return
        point = event.position().toPoint()
        handle = self._handle_at(point)
        found = self.control(self.selected) if self.selected else None
        if handle is not None and found is not None:
            band, control = found
            self.edit_started.emit()
            self._mode = "resize"
            self._handle = handle
            self._press = point
            self._start_rect = self.control_rect(band, control)
            self.setFocus()
            return
        # Delimitatore di banda (gutter o bordo superiore della banda).
        for name, top, _height in self.band_tops():
            if abs(point.y() - top) <= 4 and point.x() < GUTTER:
                self.edit_started.emit()
                self._mode = "band"
                self._band = name
                self._press = point
                self._start_band_height = self.band_height(name)
                self.active_band = name
                self.band_changed.emit(name)
                self.setFocus()
                return
        hit = self._hit_control(point)
        if hit is None:
            band = self.band_at(point.y())
            if band is not None:
                self.active_band = band
                self.band_changed.emit(band)
            self.selected = None
            self.selection_changed.emit(None)
            self.update()
            return
        band, control = hit
        self.active_band = band
        self.selected = control.id
        self.band_changed.emit(band)
        self.selection_changed.emit(control.id)
        self.edit_started.emit()
        self._mode = "move"
        self._press = point
        rect = self.control_rect(band, control)
        self._offset_mm = (
            (point.x() - rect.left()) / self.scale,
            (point.y() - rect.top()) / self.scale,
        )
        self._start_rect = rect
        self.setFocus()
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self._mode is None or self.spec is None:
            return
        point = event.position().toPoint()
        if self._mode == "band":
            name = getattr(self, "_band", "")
            tops = {item[0]: item[1] for item in self.band_tops()}
            top = tops.get(name, 0.0)
            height_mm = max(MIN_BAND_MM, (point.y() - top) / self.scale)
            controls = self.spec.band(name)
            minimum = max((c.y + c.h for c in controls), default=MIN_BAND_MM)
            height_mm = max(minimum, round(height_mm / SNAP_MM) * SNAP_MM)
            self.spec.band_heights[name] = height_mm
            self._resize_after_band()
            self.band_changed.emit(name)
            self.geometry_changed.emit()
            return
        found = self.control(self.selected) if self.selected else None
        if found is None:
            return
        band, control = found
        if self._mode == "move":
            top = dict((name, top) for name, top, _h in self.band_tops()).get(band, 0.0)
            left = GUTTER + (self.spec.margins["left"]) * self.scale
            x_mm = (point.x() - left) / self.scale - self._offset_mm[0]
            y_mm = (point.y() - top) / self.scale - self._offset_mm[1]
            control.x = max(0.0, round(x_mm / SNAP_MM) * SNAP_MM)
            control.y = max(0.0, round(y_mm / SNAP_MM) * SNAP_MM)
            self.geometry_changed.emit()
            self.update()
            return
        if self._mode == "resize":
            dx = (point.x() - self._press.x()) / self.scale
            dy = (point.y() - self._press.y()) / self.scale
            left = self._start_rect.left()
            top = self._start_rect.top()
            width = self._start_rect.width()
            height = self._start_rect.height()
            handle = self._handle
            if "w" in handle and "e" not in handle:
                left += dx * self.scale
                width -= dx
            if "e" in handle:
                width += dx
            if "n" in handle and "s" not in handle:
                top += dy * self.scale
                height -= dy
            if "s" in handle:
                height += dy
            width = max(MIN_CONTROL_MM, round(width / SNAP_MM) * SNAP_MM)
            height = max(MIN_CONTROL_MM, round(height / SNAP_MM) * SNAP_MM)
            band_left = GUTTER + self.spec.margins["left"] * self.scale
            band_top = dict((name, top) for name, top, _h in self.band_tops()).get(band, 0.0)
            control.x = max(0.0, round((left - band_left) / self.scale / SNAP_MM) * SNAP_MM)
            control.y = max(0.0, round((top - band_top) / self.scale / SNAP_MM) * SNAP_MM)
            control.w = width
            control.h = height
            self.geometry_changed.emit()
            self.update()

    def _resize_after_band(self) -> None:
        self._resize()
        if self.parentWidget() is not None:
            self.parentWidget().updateGeometry()
        self.update()

    def mouseReleaseEvent(self, _event) -> None:  # noqa: D102 - API Qt
        self._mode = None
        self._handle = ""

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() != Qt.MouseButton.LeftButton or self.spec is None:
            return
        hit = self._hit_control(event.position().toPoint())
        if hit is not None:
            _band, control = hit
            self.selected = control.id
            self.selection_changed.emit(control.id)
            self.control_activated.emit(control.id)

    def keyPressEvent(self, event) -> None:  # noqa: D102 - API Qt
        found = self.control(self.selected) if self.selected else None
        if found is None:
            super().keyPressEvent(event)
            return
        _band, control = found
        step = 0.1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else SNAP_MM
        deltas = {
            Qt.Key.Key_Left: (-step, 0.0),
            Qt.Key.Key_Right: (step, 0.0),
            Qt.Key.Key_Up: (0.0, -step),
            Qt.Key.Key_Down: (0.0, step),
        }
        if event.key() in deltas:
            self.edit_started.emit()
            dx, dy = deltas[event.key()]
            control.x = max(0.0, round(control.x + dx, 2))
            control.y = max(0.0, round(control.y + dy, 2))
            self.geometry_changed.emit()
            self.update()
            return
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_requested.emit()
            return
        super().keyPressEvent(event)


# --------------------------------------------------------------------- dialoghi
class FieldDataDialog(QDialog):
    """``Browse Field Data…``: primi valori distinti del campo."""

    def __init__(self, project: Project, table: str, field: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Field Data — {field_display_name(table, field)}")
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        try:
            rows = project.db.query(
                f'SELECT DISTINCT "{field}" AS value FROM "{table}" '
                f'WHERE "{field}" IS NOT NULL LIMIT 50'
            )
        except Exception:  # pragma: no cover - difensivo
            rows = []
        for row in rows:
            self.list.addItem(str(row.get("value")))
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(lambda _b: self.accept())
        layout.addWidget(buttons)
        self.resize(360, 420)


class InsertFieldDialog(QDialog):
    """``Insert Database Field`` con elenco ``TABELLA->CAMPO``."""

    def __init__(self, project: Project, table: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.table = table
        self.setWindowTitle("Insert Database Field")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Campi di {table or '(nessuna tabella)'}"))
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        model = project.table(table) if table else None
        for field in (model.fields if model else []):
            item = QListWidgetItem(field_display_name(table, field.name))
            item.setData(Qt.ItemDataRole.UserRole, field.name)
            item.setToolTip(f"{field.type} · {field.display_name()}")
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        layout.addWidget(self.list, 1)
        row = QHBoxLayout()
        row.addWidget(icons.make_button("Insert", "ok", self.accept, self))
        browse = icons.make_button("Browse Field Data…", "elenco", self.browse_data, self)
        row.addWidget(browse)
        row.addStretch(1)
        done = icons.make_button("Done", "chiudi", self.reject, self)
        row.addWidget(done)
        layout.addLayout(row)
        self.resize(380, 460)

    def selected_field(self) -> str:
        item = self.list.currentItem()
        return str(item.data(Qt.ItemDataRole.UserRole)) if item is not None else ""

    def browse_data(self) -> None:
        field = self.selected_field()
        if field and self.table:
            FieldDataDialog(self.project, self.table, field, self).exec()


class EditTextDialog(QDialog):
    """``Edit Text Field``: testo, font, bordo e allineamento."""

    def __init__(self, control: Control, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Text Field")
        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit(control.text)
        self.text_edit.setFixedHeight(90)
        layout.addWidget(self.text_edit)
        row = QHBoxLayout()
        row.addWidget(QLabel("Corpo:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(4, 72)
        self.size_spin.setValue(control.font_size)
        row.addWidget(self.size_spin)
        self.border_check = QCheckBox("Bordo")
        self.border_check.setChecked(control.border)
        row.addWidget(self.border_check)
        self.align_combo = QComboBox()
        for label, key in (("Sinistra", "left"), ("Centro", "center"), ("Destra", "right")):
            self.align_combo.addItem(label, key)
        self.align_combo.setCurrentIndex(max(0, self.align_combo.findData(control.align)))
        row.addWidget(self.align_combo)
        row.addStretch(1)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(420, 240)

    def apply_to(self, control: Control) -> None:
        control.text = self.text_edit.toPlainText()
        control.font_size = int(self.size_spin.value())
        control.border = self.border_check.isChecked()
        control.align = str(self.align_combo.currentData() or "left")


class SortOrderDialog(QDialog):
    """``Record Sort Order``: campi disponibili, campi ordinati e direzione."""

    def __init__(
        self,
        project: Project,
        table: str,
        sort_fields: list[dict[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Record Sort Order")
        self.project = project
        self.table = table
        self._entries = [dict(entry) for entry in sort_fields]
        layout = QVBoxLayout(self)
        columns = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Report Fields"))
        self.available = QListWidget()
        model = project.table(table) if table else None
        for field in (model.fields if model else []):
            item = QListWidgetItem(field_display_name(table, field.name))
            item.setData(Qt.ItemDataRole.UserRole, field.name)
            self.available.addItem(item)
        left.addWidget(self.available)
        columns.addLayout(left)
        middle = QVBoxLayout()
        middle.addStretch(1)
        self.add_button = QPushButton("Add >")
        self.add_button.clicked.connect(self.add_selected)
        middle.addWidget(self.add_button)
        self.remove_button = QPushButton("< Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        middle.addWidget(self.remove_button)
        self.up_button = QPushButton("Su")
        self.up_button.clicked.connect(lambda: self.move_entry(-1))
        middle.addWidget(self.up_button)
        self.down_button = QPushButton("Giù")
        self.down_button.clicked.connect(lambda: self.move_entry(1))
        middle.addWidget(self.down_button)
        middle.addStretch(1)
        columns.addLayout(middle)
        right = QVBoxLayout()
        right.addWidget(QLabel("Sort Fields"))
        self.sorted = QListWidget()
        self.sorted.currentRowChanged.connect(self._sync_direction)
        right.addWidget(self.sorted)
        direction_row = QHBoxLayout()
        direction_row.addWidget(QLabel("Sort Direction:"))
        self.direction = QComboBox()
        self.direction.addItem("Ascending", "asc")
        self.direction.addItem("Descending", "desc")
        self.direction.currentIndexChanged.connect(self._apply_direction)
        direction_row.addWidget(self.direction)
        right.addLayout(direction_row)
        columns.addLayout(right)
        layout.addLayout(columns, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_sorted()
        self.resize(620, 460)

    def _refresh_sorted(self) -> None:
        self.sorted.blockSignals(True)
        self.sorted.clear()
        for entry in self._entries:
            direction = "A" if entry.get("direction", "asc") == "asc" else "D"
            label = field_display_name(self.table, entry["field"]) + f"  ({direction})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, dict(entry))
            self.sorted.addItem(item)
        self.sorted.blockSignals(False)
        if self.sorted.count():
            self.sorted.setCurrentRow(0)
            self._sync_direction(0)

    def _sync_direction(self, row: int) -> None:
        if not (0 <= row < len(self._entries)):
            return
        self.direction.blockSignals(True)
        self.direction.setCurrentIndex(
            max(0, self.direction.findData(self._entries[row].get("direction", "asc")))
        )
        self.direction.blockSignals(False)

    def _apply_direction(self, _index: int) -> None:
        row = self.sorted.currentRow()
        if 0 <= row < len(self._entries):
            self._entries[row]["direction"] = str(self.direction.currentData() or "asc")
            self._refresh_sorted()
            self.sorted.setCurrentRow(row)

    def add_selected(self) -> None:
        for item in self.available.selectedItems():
            field = str(item.data(Qt.ItemDataRole.UserRole))
            if any(entry["field"] == field for entry in self._entries):
                continue
            self._entries.append(
                {"field": field, "direction": str(self.direction.currentData() or "asc")}
            )
            self.available.takeItem(self.available.row(item))
        self._refresh_sorted()

    def remove_selected(self) -> None:
        row = self.sorted.currentRow()
        if not (0 <= row < len(self._entries)):
            return
        entry = self._entries.pop(row)
        item = QListWidgetItem(field_display_name(self.table, entry["field"]))
        item.setData(Qt.ItemDataRole.UserRole, entry["field"])
        self.available.addItem(item)
        self._refresh_sorted()

    def move_entry(self, delta: int) -> None:
        row = self.sorted.currentRow()
        target = row + delta
        if not (0 <= row < len(self._entries) and 0 <= target < len(self._entries)):
            return
        self._entries[row], self._entries[target] = self._entries[target], self._entries[row]
        self._refresh_sorted()
        self.sorted.setCurrentRow(target)

    def sort_fields(self) -> list[dict[str, str]]:
        return [dict(entry) for entry in self._entries]


class GroupDialog(QDialog):
    """``Insert Group`` minimo: campo e didascalia."""

    def __init__(self, project: Project, table: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Insert Group")
        layout = QVBoxLayout(self)
        form = QHBoxLayout()
        form.addWidget(QLabel("Campo:"))
        self.field_combo = QComboBox()
        model = project.table(table) if table else None
        for field in (model.fields if model else []):
            self.field_combo.addItem(field_display_name(table, field.name), field.name)
        form.addWidget(self.field_combo, 1)
        form.addWidget(QLabel("Didascalia:"))
        self.label_edit = QLineEdit()
        form.addWidget(self.label_edit, 1)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(460, 130)

    def group(self) -> dict[str, str]:
        return {
            "field": str(self.field_combo.currentData() or ""),
            "label": self.label_edit.text().strip(),
        }


class TotalDialog(QDialog):
    """``Insert Total`` minimo: campo, funzione, prefisso e banda."""

    def __init__(self, project: Project, table: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Total")
        layout = QVBoxLayout(self)
        grid = QHBoxLayout()
        grid.addWidget(QLabel("Campo:"))
        self.field_combo = QComboBox()
        model = project.table(table) if table else None
        for field in (model.fields if model else []):
            self.field_combo.addItem(field_display_name(table, field.name), field.name)
        grid.addWidget(self.field_combo, 1)
        grid.addWidget(QLabel("Funzione:"))
        self.func_combo = QComboBox()
        for label, key in (
            ("Somma", "sum"),
            ("Conteggio", "count"),
            ("Media", "avg"),
            ("Minimo", "min"),
            ("Massimo", "max"),
        ):
            self.func_combo.addItem(label, key)
        grid.addWidget(self.func_combo)
        layout.addLayout(grid)
        row = QHBoxLayout()
        row.addWidget(QLabel("Prefisso:"))
        self.label_edit = QLineEdit("Totale: ")
        row.addWidget(self.label_edit, 1)
        row.addWidget(QLabel("Banda:"))
        self.band_combo = QComboBox()
        self.band_combo.addItem("Summary", "summary")
        self.band_combo.addItem("Group footer", "group_footer")
        row.addWidget(self.band_combo)
        layout.addLayout(row)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(520, 170)

    def control(self) -> tuple[str, Control]:
        field = str(self.field_combo.currentData() or "")
        control = Control(
            id=new_id(),
            kind="total",
            x=100,
            y=0,
            w=40,
            h=6,
            expr=f"[{field}]" if field else "",
            label=self.label_edit.text(),
            func=str(self.func_combo.currentData() or "sum"),
            align="right",
        )
        return str(self.band_combo.currentData() or "summary"), control


# ------------------------------------------------------------------- designer
class ReportDesignerWidget(QWidget):
    """Report Designer a foglio unico, ospitato nell'area MDI."""

    saved = pyqtSignal(str)
    preview_requested = pyqtSignal(object)
    status_message = pyqtSignal(str)
    new_requested = pyqtSignal()
    open_requested = pyqtSignal()

    def __init__(self, project: Project, spec: ReportSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.original_name = spec.name
        self.selected_id: str | None = None
        self.active_band = "detail"
        self.preview_handler = None
        self._saved_state = copy.deepcopy(spec.to_dict())
        self._undo: list[dict[str, Any]] = []
        self._redo: list[dict[str, Any]] = []
        self._loading = False
        self.setWindowTitle(f"Report Designer ({spec.name})")
        self.resize(1180, 800)
        self._build_ui()
        self._load()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        header = QHBoxLayout()
        header.setSpacing(3)
        self.name_edit = QLineEdit(self.spec.name)
        self.name_edit.setPlaceholderText("nome_report")
        self.title_edit = QLineEdit(self.spec.title)
        self.title_edit.setPlaceholderText("Titolo")
        self.table_combo = QComboBox()
        for name in self.project.names("tables"):
            self.table_combo.addItem(name, name)
        self.table_combo.setCurrentIndex(max(0, self.table_combo.findData(self.spec.table)))
        self.filter_edit = QLineEdit(self.spec.filter)
        self.filter_edit.setPlaceholderText("Filtro SQL")
        self.order_edit = QLineEdit(self.spec.order)
        self.order_edit.setPlaceholderText("Ordine")
        for label, widget, stretch in (
            ("Nome:", self.name_edit, 2),
            ("Titolo:", self.title_edit, 3),
            ("Tabella:", self.table_combo, 2),
            ("Filtro:", self.filter_edit, 3),
            ("Ordine:", self.order_edit, 2),
        ):
            header.addWidget(QLabel(label))
            header.addWidget(widget, stretch)
        layout.addLayout(header)

        layout.addLayout(self._build_standard_toolbar())
        layout.addLayout(self._build_format_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.setSpacing(0)
        ruler_row = QHBoxLayout()
        ruler_row.setSpacing(0)
        ruler_row.addSpacing(GUTTER)
        self.ruler = ReportRuler()
        ruler_row.addWidget(self.ruler, 1)
        centre_layout.addLayout(ruler_row)

        self.canvas = ReportCanvas()
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self.canvas.geometry_changed.connect(self._on_geometry_changed)
        self.canvas.edit_started.connect(self._push_undo)
        self.canvas.delete_requested.connect(self.remove_control)
        self.canvas.band_changed.connect(self._on_band_changed)
        self.canvas.control_activated.connect(lambda _id: self.edit_text())
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.scroll.horizontalScrollBar().valueChanged.connect(self._sync_ruler)
        self.scroll.setStyleSheet(
            "QScrollArea { background: %s; }" % _tokens()["window_bg"]
        )
        centre_layout.addWidget(self.scroll, 1)
        splitter.addWidget(centre)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)
        self.inspector = PropertyInspector()
        self.inspector.setMinimumWidth(260)
        self.inspector.property_changed.connect(self._on_property_changed)
        right_layout.addWidget(self.inspector, 1)
        splitter.addWidget(right)
        splitter.setSizes([860, 300])
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("L:— R:— · Banda: Details · Zoom 100%")
        self.status_label.setObjectName("report_status")
        layout.addWidget(self.status_label)
        self._install_shortcuts()

    def _tool_button(self, text: str, tooltip: str, slot, *, checkable: bool = False) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setFixedHeight(24)
        button.clicked.connect(lambda _checked=False: slot())
        return button

    def _build_standard_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(2)
        bar.addWidget(icons.make_button("", "nuovo", self.new_requested.emit, self, "Nuovo report"))
        bar.addWidget(icons.make_button("", "apri", self.open_requested.emit, self, "Apri report…"))
        self.save_button = icons.make_button("", "salva", self.save, self, "Salva report")
        self.preview_button = icons.make_button("", "anteprima", self.preview, self, "Anteprima")
        self.print_button = icons.make_button("", "stampa", self.print_pages, self, "Stampa")
        for button in (self.save_button, self.preview_button, self.print_button):
            bar.addWidget(button)
        bar.addSpacing(6)
        for glyph, slot, tip in (
            ("taglia", self.cut_control, "Taglia controllo"),
            ("copia", self.copy_control, "Copia controllo"),
            ("incolla", self.paste_control, "Incolla controllo"),
        ):
            bar.addWidget(icons.make_button("", glyph, slot, self, tip))
        self.undo_button = icons.make_button("", "undo", self.undo, self, "Annulla")
        self.redo_button = icons.make_button("", "redo", self.redo, self, "Ripeti")
        bar.addWidget(self.undo_button)
        bar.addWidget(self.redo_button)
        bar.addSpacing(6)
        bar.addWidget(
            icons.make_button("Inserisci campo", "campo", self.insert_field, self, "Insert Database Field")
        )
        bar.addWidget(
            icons.make_button("Ordinamento", "elenco", self.edit_sort_order, self, "Record Sort Order")
        )
        bar.addWidget(icons.make_button("Testo", "testo", self.edit_text, self, "Edit Text Field"))
        bar.addWidget(icons.make_button("Totali", "somma", self.insert_total, self, "Insert Total"))
        bar.addWidget(icons.make_button("Gruppo", "tabella", self.insert_group, self, "Insert Group"))
        self.bands_button = QToolButton()
        self.bands_button.setText("Bande")
        self.bands_button.setIcon(icons.icon("form"))
        self.bands_button.setIconSize(icons.ICON_SIZE)
        self.bands_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.bands_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.bands_menu = QMenu(self.bands_button)
        self.bands_button.setMenu(self.bands_menu)
        bar.addWidget(self.bands_button)
        bar.addStretch(1)
        return bar

    def _build_format_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(2)
        bar.addWidget(QLabel("Font:"))
        self.font_combo = QComboBox()
        for family in (
            design.UI_FONT.family,
            "Segoe UI",
            "Noto Sans",
            "DejaVu Sans",
            "Times New Roman",
            "Courier New",
        ):
            self.font_combo.addItem(family, family)
        self.font_combo.setFixedWidth(120)
        self.font_combo.currentIndexChanged.connect(
            lambda _index: self.apply_format("font_name", str(self.font_combo.currentData() or ""))
        )
        bar.addWidget(self.font_combo)
        bar.addWidget(QLabel("Corpo:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(4, 72)
        self.font_spin.setValue(10)
        self.font_spin.setFixedWidth(58)
        self.font_spin.valueChanged.connect(lambda value: self.apply_format("font_size", int(value)))
        bar.addWidget(self.font_spin)
        self.bold_button = self._tool_button("B", "Grassetto", lambda: self.toggle_format("bold"), checkable=True)
        self.bold_button.setStyleSheet("font-weight: 700;")
        self.italic_button = self._tool_button("I", "Corsivo", lambda: self.toggle_format("italic"), checkable=True)
        self.italic_button.setStyleSheet("font-style: italic;")
        self.underline_button = self._tool_button("U", "Sottolineato", lambda: self.toggle_format("underline"), checkable=True)
        self.underline_button.setStyleSheet("text-decoration: underline;")
        for button in (self.bold_button, self.italic_button, self.underline_button):
            button.setFixedWidth(26)
            bar.addWidget(button)
        bar.addSpacing(6)
        self.align_buttons: dict[str, QToolButton] = {}
        for key, text, tip in (
            ("left", "Sx", "Allinea a sinistra"),
            ("center", "C", "Centra"),
            ("right", "Dx", "Allinea a destra"),
        ):
            button = self._tool_button(text, tip, lambda k=key: self.apply_format("align", k), checkable=True)
            button.setFixedWidth(28)
            self.align_buttons[key] = button
            bar.addWidget(button)
        bar.addSpacing(6)
        self.border_button = self._tool_button("Bordo", "Bordo", lambda: self.toggle_format("border"), checkable=True)
        bar.addWidget(self.border_button)
        self.align_button = QToolButton()
        self.align_button.setIcon(icons.icon("allinea"))
        self.align_button.setIconSize(icons.ICON_SIZE)
        self.align_button.setToolTip("Allinea il controllo nella banda")
        self.align_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        align_menu = QMenu(self.align_button)
        for label, mode in (
            ("Sinistra", "left"),
            ("Centro", "center"),
            ("Destra", "right"),
            ("Alto", "top"),
        ):
            align_menu.addAction(label, lambda m=mode: self.align_control(m))
        self.align_button.setMenu(align_menu)
        bar.addWidget(self.align_button)
        bar.addWidget(QLabel("Colore:"))
        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#rrggbb")
        self.color_edit.setFixedWidth(84)
        self.color_edit.editingFinished.connect(lambda: self.apply_format("color", self.color_edit.text().strip()))
        bar.addWidget(self.color_edit)
        bar.addStretch(1)
        bar.addWidget(QLabel("Zoom:"))
        self.zoom_combo = QComboBox()
        for percent in (50, 75, 100, 150, 200):
            self.zoom_combo.addItem(f"{percent}%", percent)
        self.zoom_combo.setCurrentIndex(2)
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        bar.addWidget(self.zoom_combo)
        return bar

    def _install_shortcuts(self) -> None:
        self._shortcuts: list[QShortcut] = []
        for sequence, slot in {
            "Ctrl+S": self.save,
            "Ctrl+Z": self.undo,
            "Ctrl+Y": self.redo,
            "Ctrl+C": self.copy_control,
            "Ctrl+X": self.cut_control,
            "Ctrl+V": self.paste_control,
        }.items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    # ------------------------------------------------------------------ stato
    def _load(self) -> None:
        self._loading = True
        self.name_edit.setText(self.spec.name)
        self.title_edit.setText(self.spec.title)
        self.filter_edit.setText(self.spec.filter)
        self.order_edit.setText(self.spec.order)
        index = self.table_combo.findData(self.spec.table)
        self.table_combo.setCurrentIndex(max(0, index))
        self._loading = False
        self.canvas.load(self.spec)
        self._sync_ruler()
        self._refresh_bands_menu()
        self.canvas.selected = None
        self._show_report_properties()
        self._refresh_history()
        self._refresh_status()

    def _apply_header(self) -> None:
        self.spec.name = self.name_edit.text().strip() or self.spec.name
        self.spec.title = self.title_edit.text()
        self.spec.table = str(self.table_combo.currentData() or self.spec.table)
        self.spec.filter = self.filter_edit.text().strip()
        self.spec.order = self.order_edit.text().strip()

    def current_control(self) -> tuple[str, Control] | None:
        return self.canvas.control(self.selected_id) if self.selected_id else None

    def _sync_ruler(self, *_args) -> None:
        self.ruler.set_metrics(self.canvas.scale, self.scroll.horizontalScrollBar().value())

    def _on_zoom_changed(self, _index: int) -> None:
        percent = int(self.zoom_combo.currentData() or 100)
        self.canvas.set_zoom_factor(percent / 100.0)
        self._sync_ruler()
        self._refresh_status()

    def _refresh_status(self) -> None:
        found = self.current_control()
        if found is not None:
            _band, control = found
            left = control.x / 25.4
            right = (control.x + control.w) / 25.4
            position = f"L:{left:.2f} R:{right:.2f}"
        else:
            position = "L:— R:—"
        zoom = int(round(self.canvas.zoom_factor * 100))
        self.status_label.setText(
            f"{position} · Banda: {BAND_LABELS.get(self.active_band, self.active_band)} · Zoom {zoom}%"
        )

    def _refresh_bands_menu(self) -> None:
        self.bands_menu.clear()
        for name in self.spec.effective_band_order():
            action = self.bands_menu.addAction(BAND_LABELS.get(name, name))
            action.setCheckable(True)
            action.setChecked(self.spec.is_visible(name))
            action.triggered.connect(
                lambda checked, band=name: self.set_band_visible(band, checked)
            )
        self.bands_menu.addSeparator()
        self.bands_menu.addAction("Mostra tutte le bande", self.show_all_bands)

    def set_band_visible(self, name: str, visible: bool) -> None:
        self._push_undo()
        self.spec.band_visible[name] = bool(visible)
        self.canvas.load(self.spec)
        self._refresh_status()

    def show_all_bands(self) -> None:
        self._push_undo()
        for name in BAND_NAMES:
            self.spec.band_visible[name] = True
        self.canvas.load(self.spec)
        self._refresh_status()

    # ------------------------------------------------------------- selezione
    def _on_selection_changed(self, control_id: object) -> None:
        self.selected_id = str(control_id) if control_id else None
        found = self.current_control()
        if found is None:
            self._show_report_properties()
        else:
            band, control = found
            self.active_band = band
            self._show_control(control)
        self._refresh_status()

    def _on_band_changed(self, band: str) -> None:
        self.active_band = band
        self._refresh_status()

    def _on_geometry_changed(self) -> None:
        found = self.current_control()
        if found is not None:
            _band, control = found
            self._loading = True
            for key, value in (("x", control.x), ("y", control.y), ("w", control.w), ("h", control.h)):
                item = self.inspector.item(key)
                if item is not None:
                    item.setText(1, self._format_float(value))
            self._loading = False
        self._refresh_status()

    @staticmethod
    def _format_float(value: float) -> str:
        text = f"{float(value):.2f}".rstrip("0").rstrip(".")
        return text or "0"

    def _show_report_properties(self) -> None:
        self.inspector.set_properties(
            [
                (
                    "• Report",
                    [
                        ("name", "Name", "text", self.spec.name, None),
                        ("title", "Title", "text", self.spec.title, None),
                        (
                            "table",
                            "Table",
                            "choice",
                            self.spec.table,
                            [(name, name) for name in self.project.names("tables")],
                        ),
                        (
                            "page_size",
                            "Page",
                            "choice",
                            self.spec.page_size,
                            [("A4", "A4"), ("Letter", "Letter")],
                        ),
                        (
                            "orientation",
                            "Orientation",
                            "choice",
                            self.spec.orientation,
                            [("portrait", "Verticale"), ("landscape", "Orizzontale")],
                        ),
                        ("filter", "Filter", "text", self.spec.filter, None),
                        ("order", "Order", "text", self.spec.order, None),
                    ],
                ),
                (
                    "• Groups",
                    [
                        ("groups", "Gruppi", "ro", ", ".join(g.get("field", "") for g in self.spec.effective_groups()) or "(nessuno)", None),
                        (
                            "sort_fields",
                            "Ordinamento",
                            "ro",
                            ", ".join(
                                f"{e.get('field')} {e.get('direction')}"
                                for e in self.spec.sort_fields
                            )
                            or "(nessuno)",
                            None,
                        ),
                    ],
                ),
            ]
        )
        self.inspector.set_events([])
        self.inspector.set_methods([])

    def _show_control(self, control: Control) -> None:
        self.inspector.set_properties(
            [
                (
                    "• Layout",
                    [
                        ("x", "Left (mm)", "float", control.x, None),
                        ("y", "Top (mm)", "float", control.y, None),
                        ("w", "Width (mm)", "float", control.w, None),
                        ("h", "Height (mm)", "float", control.h, None),
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
                            [(kind, kind) for kind in CONTROL_KINDS],
                        ),
                        ("text", "Text", "text", control.text, None),
                        ("expr", "Expression", "text", control.expr, None),
                        ("label", "Label", "text", control.label, None),
                        (
                            "func",
                            "Total",
                            "choice",
                            control.func,
                            [
                                ("sum", "Somma"),
                                ("count", "Conteggio"),
                                ("avg", "Media"),
                                ("min", "Minimo"),
                                ("max", "Massimo"),
                            ],
                        ),
                        ("fmt", "Format", "text", control.fmt, None),
                    ],
                ),
                (
                    "• Format",
                    [
                        ("font_name", "FontName", "text", control.font_name, None),
                        ("font_size", "FontSize", "int", control.font_size, None),
                        ("bold", "FontBold", "bool", control.bold, None),
                        ("italic", "FontItalic", "bool", control.italic, None),
                        ("underline", "FontUnderline", "bool", control.underline, None),
                        (
                            "align",
                            "Align",
                            "choice",
                            control.align,
                            [("left", "Sinistra"), ("center", "Centro"), ("right", "Destra")],
                        ),
                        ("border", "Border", "bool", control.border, None),
                        ("color", "Color", "text", control.color, None),
                        ("fill", "Fill", "text", control.fill, None),
                    ],
                ),
            ]
        )
        self._sync_format_buttons(control)

    def _sync_format_buttons(self, control: Control) -> None:
        self._loading = True
        font_index = self.font_combo.findData(control.font_name) if control.font_name else 0
        self.font_combo.setCurrentIndex(max(0, font_index))
        self.font_spin.setValue(int(control.font_size))
        self.bold_button.setChecked(bool(control.bold))
        self.italic_button.setChecked(bool(control.italic))
        self.underline_button.setChecked(bool(control.underline))
        self.border_button.setChecked(bool(control.border))
        for key, button in self.align_buttons.items():
            button.setChecked(key == control.align)
        self.color_edit.setText(control.color)
        self._loading = False

    def _on_property_changed(self, key: str, value: Any) -> None:
        found = self.current_control()
        if found is not None:
            self._push_undo()
            _band, control = found
            setattr(control, key, value)
            self.canvas.update()
            self._sync_format_buttons(control)
            self._refresh_status()
            return
        if key in ("name", "title", "table", "page_size", "orientation", "filter", "order"):
            self._push_undo()
            if key == "table":
                self.spec.table = str(value or "")
                index = self.table_combo.findData(self.spec.table)
                self.table_combo.blockSignals(True)
                self.table_combo.setCurrentIndex(max(0, index))
                self.table_combo.blockSignals(False)
            elif key in ("page_size", "orientation"):
                setattr(self.spec, key, str(value))
                self.canvas.load(self.spec)
            else:
                setattr(self.spec, key, str(value))
                if key == "name":
                    self.name_edit.setText(self.spec.name)
                elif key == "title":
                    self.title_edit.setText(self.spec.title)
                elif key == "filter":
                    self.filter_edit.setText(self.spec.filter)
                elif key == "order":
                    self.order_edit.setText(self.spec.order)
            self.setWindowTitle(f"Report Designer ({self.spec.name})")
            self._refresh_status()

    # ------------------------------------------------------------- formattazione
    def _selection_or_warn(self) -> Control | None:
        found = self.current_control()
        if found is None:
            self.status_message.emit("Seleziona un controllo sul foglio")
            return None
        return found[1]

    def apply_format(self, key: str, value: Any) -> None:
        if self._loading:
            return
        control = self._selection_or_warn()
        if control is None:
            return
        self._push_undo()
        setattr(control, key, value)
        self.canvas.update()
        self._sync_format_buttons(control)
        self.status_message.emit(f"{key} = {value}")

    def align_control(self, mode: str) -> None:
        control = self._selection_or_warn()
        if control is None:
            return
        self._push_undo()
        content_width = (
            self.spec.page_dimensions()[0]
            - float(self.spec.margins.get("left", 15))
            - float(self.spec.margins.get("right", 15))
        )
        if mode == "left":
            control.x = 0.0
        elif mode == "right":
            control.x = max(0.0, round(content_width - control.w, 2))
        elif mode == "center":
            control.x = max(0.0, round((content_width - control.w) / 2, 2))
        elif mode == "top":
            control.y = 0.0
        self.canvas.update()
        self._on_geometry_changed()
        self.status_message.emit(f"Allineato: {mode}")

    def toggle_format(self, key: str) -> None:
        control = self._selection_or_warn()
        if control is None:
            return
        self._push_undo()
        setattr(control, key, not bool(getattr(control, key)))
        button = getattr(self, f"{key}_button", None)
        if button is not None:
            button.setChecked(bool(getattr(control, key)))
        self.canvas.update()

    # ------------------------------------------------------------------ insert
    def _insert(self, band: str, control: Control) -> None:
        self._push_undo()
        self.spec.bands.setdefault(band, []).append(control)
        self.active_band = band
        self.canvas.load(self.spec)
        self.selected_id = control.id
        self.canvas.selected = control.id
        self._show_control(control)
        self.canvas.selection_changed.emit(control.id)
        self._refresh_status()

    def insert_field(self) -> None:
        self._apply_header()
        dialog = InsertFieldDialog(self.project, self.spec.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        field = dialog.selected_field()
        if not field:
            return
        control = Control(
            id=new_id(),
            kind="field",
            x=0.0,
            y=0.0,
            w=45.0,
            h=6.0,
            expr=field,
            font_size=10,
        )
        self._insert(self.active_band, control)

    def insert_total(self) -> None:
        self._apply_header()
        dialog = TotalDialog(self.project, self.spec.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        band, control = dialog.control()
        self._insert(band, control)

    def insert_group(self) -> None:
        self._apply_header()
        dialog = GroupDialog(self.project, self.spec.table, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        group = dialog.group()
        if not group.get("field"):
            return
        self._push_undo()
        self.spec.groups.append(group)
        self.spec.band_visible["group_header"] = True
        header_control = Control(
            id=new_id(),
            kind="field",
            x=0.0,
            y=0.0,
            w=60.0,
            h=6.0,
            expr=group["field"],
            bold=True,
        )
        self.spec.bands.setdefault("group_header", []).append(header_control)
        self.canvas.load(self.spec)
        self._refresh_bands_menu()
        self._show_report_properties()
        self.status_message.emit(f"Gruppo su {group['field']}")

    def edit_sort_order(self) -> None:
        self._apply_header()
        dialog = SortOrderDialog(self.project, self.spec.table, self.spec.sort_fields, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._push_undo()
        self.spec.sort_fields = dialog.sort_fields()
        self._show_report_properties()
        self.status_message.emit("Ordinamento aggiornato")

    # -------------------------------------------------------------- clipboard
    def copy_control(self) -> None:
        found = self.current_control()
        if found is None:
            return
        self._clipboard = copy.deepcopy(found[1].to_dict())
        self.status_message.emit("Controllo copiato")

    def cut_control(self) -> None:
        self.copy_control()
        self.remove_control()

    def paste_control(self) -> None:
        data = getattr(self, "_clipboard", None)
        if not data:
            return
        control = Control.from_dict(data)
        control.id = new_id()
        control.x += SNAP_MM
        control.y += SNAP_MM
        self._insert(self.active_band, control)

    def remove_control(self) -> None:
        found = self.current_control()
        if found is None:
            return
        band, control = found
        self._push_undo()
        self.spec.bands[band] = [c for c in self.spec.band(band) if c.id != control.id]
        self.selected_id = None
        self.canvas.selected = None
        self.canvas.load(self.spec)
        self._show_report_properties()
        self._refresh_status()

    def edit_text(self) -> None:
        found = self.current_control()
        if found is None:
            return
        _band, control = found
        dialog = EditTextDialog(control, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._push_undo()
        dialog.apply_to(control)
        self.canvas.update()
        self._show_control(control)

    # -------------------------------------------------------------- cronologia
    def _push_undo(self) -> None:
        if getattr(self, "_in_undo", False):
            return
        self._undo.append(copy.deepcopy(self.spec.to_dict()))
        if len(self._undo) > 80:
            self._undo.pop(0)
        self._redo.clear()
        self._refresh_history()

    def undo(self) -> None:
        if not self._undo:
            return
        state = self._undo.pop()
        self._redo.append(copy.deepcopy(self.spec.to_dict()))
        self._restore(state)

    def redo(self) -> None:
        if not self._redo:
            return
        state = self._redo.pop()
        self._undo.append(copy.deepcopy(self.spec.to_dict()))
        self._restore(state)

    def _restore(self, state: dict[str, Any]) -> None:
        self._in_undo = True
        try:
            self.spec = ReportSpec.from_dict(state)
            self.selected_id = None
            self._load()
        finally:
            self._in_undo = False
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.undo_button.setEnabled(bool(self._undo))
        self.redo_button.setEnabled(bool(self._redo))

    # ------------------------------------------------------------------ azioni
    def preview(self) -> None:
        self._apply_header()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Report non valido", "\n".join(errors))
            return
        if self.preview_handler is not None:
            self.preview_handler(self.spec)
            return
        self.preview_requested.emit(self.spec)

    def print_pages(self) -> None:
        from ..ui.report_preview import ReportPreviewDialog

        self._apply_header()
        dialog = ReportPreviewDialog(self.project, self.spec, self)
        dialog.print_pages()

    def save(self) -> bool:
        self._apply_header()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Report non valido", "\n".join(errors))
            return False
        if not self.spec.name:
            self.spec.name = f"report_{slugify(self.spec.table)}"
        try:
            self.project.put_object(
                "reports", self.spec.to_dict(), previous_name=self.original_name
            )
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self.original_name = self.spec.name
        self._saved_state = copy.deepcopy(self.spec.to_dict())
        self._undo.clear()
        self._redo.clear()
        self._refresh_history()
        self.saved.emit(self.spec.name)
        self.status_message.emit(f"Report {self.spec.name} salvato")
        return True

    def is_dirty(self) -> bool:
        self._apply_header()
        return self.spec.to_dict() != self._saved_state


# Compatibilità con il nome storico usato da smoke, test e capture.
ReportBuilderDialog = ReportDesignerWidget
