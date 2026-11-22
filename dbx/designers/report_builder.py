"""Report Builder: bande, controlli, raggruppamenti e anteprima (E2–E4, E9)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPoint, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core.metadata import new_id, slugify
from ..core.project import Project, ProjectError
from ..runtime.report_engine import BAND_NAMES, Control, ReportSpec
from ..ui import icons
from ..ui.report_preview import ReportPreviewDialog
from ..ui.widgets import PropertyEditor

BAND_LABELS = {
    "title": "Titolo (prima pagina)",
    "page_header": "Intestazione pagina",
    "group_header": "Intestazione gruppo",
    "detail": "Dettaglio",
    "group_footer": "Piè di gruppo",
    "page_footer": "Piè di pagina",
    "summary": "Riepilogo finale",
}
SCALE = 3.0  # px per mm


class ReportCanvas(QWidget):
    """Canvas a bande con selezione e trascinamento dei controlli."""

    control_selected = pyqtSignal(str)
    control_moved = pyqtSignal(str)
    drag_finished = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec: ReportSpec | None = None
        self.band = "detail"
        self.selected: str | None = None
        self._dragging = False
        self._offset = QPoint()
        self.setStyleSheet("background: #ffffff;")
        self.setMouseTracking(True)

    def load(self, spec: ReportSpec, band: str) -> None:
        self.spec = spec
        self.band = band
        width, height = spec.page_dimensions()
        self.setFixedSize(int(width * SCALE), int(height * SCALE))
        self.update()

    def _controls(self) -> list[Control]:
        if self.spec is None:
            return []
        return self.spec.band(self.band)

    def _hit(self, x_mm: float, y_mm: float) -> Control | None:
        for control in reversed(self._controls()):
            if control.x <= x_mm <= control.x + control.w and control.y <= y_mm <= control.y + control.h:
                return control
        return None

    def paintEvent(self, event) -> None:  # noqa: D102
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        if self.spec is None:
            return
        width_mm, height_mm = self.spec.page_dimensions()
        margins = self.spec.margins
        width, height = width_mm * SCALE, height_mm * SCALE
        left, top = margins["left"] * SCALE, margins["top"] * SCALE
        area_width = width - left - margins["right"] * SCALE
        area_height = height - top - margins["bottom"] * SCALE
        painter.setPen(QPen(QColor("#b9bfb3"), 1))
        painter.drawRect(QRectF(0, 0, width - 1, height - 1))
        painter.setPen(QPen(QColor("#d7dbd0"), 1))
        painter.drawRect(QRectF(left, top, area_width, area_height))
        controls = self._controls()
        band_height = max([c.y + c.h for c in controls], default=18.0) * SCALE
        painter.fillRect(QRectF(left, top, area_width, max(8.0, band_height)), QColor("#f0f4ec"))
        header_font = QFont()
        header_font.setPointSizeF(8)
        header_font.setBold(True)
        painter.setFont(header_font)
        painter.setPen(QPen(QColor("#3d4742")))
        painter.drawText(6, 14, f"Banda: {BAND_LABELS.get(self.band, self.band)}")
        footer_font = QFont()
        footer_font.setPointSizeF(7)
        painter.setFont(footer_font)
        painter.setPen(QPen(QColor("#7a8477")))
        painter.drawText(6, self.height() - 5, f"{width_mm:.0f} × {height_mm:.0f} mm · {SCALE:.0f} px/mm")
        for control in controls:
            rect = QRectF(
                left + control.x * SCALE,
                top + control.y * SCALE,
                max(4.0, control.w * SCALE),
                max(4.0, control.h * SCALE),
            )
            selected = control.id == self.selected
            painter.setPen(QPen(QColor("#2f6f4f" if selected else "#7a8477"), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            font = QFont()
            font.setPointSizeF(max(6.0, min(14.0, float(control.font_size) * 0.75)))
            font.setBold(control.bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#1f2a22")))
            text = str(control.text or control.expr or control.kind)
            painter.drawText(
                rect.adjusted(2, 0, -2, 0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                text,
            )

    def mousePressEvent(self, event) -> None:  # noqa: D102
        if self.spec is None:
            return
        x = event.position().x() / SCALE - self.spec.margins["left"]
        y = event.position().y() / SCALE - self.spec.margins["top"]
        control = self._hit(x, y)
        if control is not None:
            self.selected = control.id
            self._dragging = True
            self._offset = QPoint(int((x - control.x) * SCALE), int((y - control.y) * SCALE))
            self.control_selected.emit(control.id)
            self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: D102
        if not self._dragging or self.spec is None:
            return
        control = next((c for c in self._controls() if c.id == self.selected), None)
        if control is None:
            return
        x_mm = (event.position().x() - self._offset.x()) / SCALE - self.spec.margins["left"]
        y_mm = (event.position().y() - self._offset.y()) / SCALE - self.spec.margins["top"]
        control.x = max(0.0, round(x_mm, 1))
        control.y = max(0.0, round(y_mm, 1))
        self.control_moved.emit(control.id)
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: D102
        if self._dragging and self.selected:
            self.drag_finished.emit(self.selected)
        self._dragging = False


class ReportBuilderDialog(QDialog):
    """Designer di report con bande, controlli e anteprima."""

    def __init__(self, project: Project, spec: ReportSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.original_name = spec.name
        self.selected: Control | None = None
        self.setWindowTitle(f"Report Designer ({spec.name})")
        self.resize(1140, 780)
        self._build_ui()
        self._reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.name_edit = QLineEdit(self.spec.name)
        self.name_edit.setPlaceholderText("nome_report")
        self.title_edit = QLineEdit(self.spec.title)
        self.title_edit.setPlaceholderText("Titolo")
        self.table_combo = QComboBox()
        for name in self.project.names("tables"):
            self.table_combo.addItem(name, name)
        index = self.table_combo.findData(self.spec.table)
        self.table_combo.setCurrentIndex(max(0, index))
        header.addWidget(QLabel("Nome:"))
        header.addWidget(self.name_edit)
        header.addWidget(QLabel("Titolo:"))
        header.addWidget(self.title_edit)
        header.addWidget(QLabel("Tabella:"))
        header.addWidget(self.table_combo)
        layout.addLayout(header)

        second = QHBoxLayout()
        self.filter_edit = QLineEdit(self.spec.filter)
        self.filter_edit.setPlaceholderText("Filtro SQL, es. importo > 100")
        self.order_edit = QLineEdit(self.spec.order)
        self.order_edit.setPlaceholderText("Ordine, es. data")
        self.group_edit = QLineEdit(self.spec.group_by)
        self.group_edit.setPlaceholderText("Raggruppa per (campo o espressione)")
        self.page_combo = QComboBox()
        self.page_combo.addItem("A4", "A4")
        self.page_combo.addItem("Letter", "Letter")
        self.page_combo.setCurrentIndex(max(0, self.page_combo.findData(self.spec.page_size)))
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Verticale", "portrait")
        self.orientation_combo.addItem("Orizzontale", "landscape")
        self.orientation_combo.setCurrentIndex(max(0, self.orientation_combo.findData(self.spec.orientation)))
        for label, widget in (
            ("Filtro:", self.filter_edit),
            ("Ordine:", self.order_edit),
            ("Gruppo:", self.group_edit),
            ("Pagina:", self.page_combo),
            ("Orientamento:", self.orientation_combo),
        ):
            second.addWidget(QLabel(label))
            second.addWidget(widget, 1)
        layout.addLayout(second)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Banda:"))
        self.band_combo = QComboBox()
        for band in BAND_NAMES:
            self.band_combo.addItem(BAND_LABELS[band], band)
        self.band_combo.setCurrentIndex(BAND_NAMES.index("detail"))
        self.band_combo.currentIndexChanged.connect(self._on_band_changed)
        bar.addWidget(self.band_combo)
        bar.addSpacing(10)
        for caption, kind, glyph in (
            ("Testo", "text", "testo"),
            ("Campo", "field", "campo"),
            ("Espressione", "expr", "somma"),
            ("Totale", "total", "somma"),
            ("Linea", "line", "linea"),
            ("Riquadro", "rect", "riquadro"),
        ):
            bar.addWidget(icons.make_button(caption, glyph, lambda _checked=False, k=kind: self.add_control(k), self))
        bar.addWidget(icons.make_button("Elimina", "elimina", self.remove_control, self))
        bar.addStretch(1)
        bar.addWidget(icons.make_button("Anteprima", "anteprima", self.preview, self))
        layout.addLayout(bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.canvas = ReportCanvas()
        self.canvas.control_selected.connect(self._on_control_selected)
        self.canvas.drag_finished.connect(self._on_control_selected)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        splitter.addWidget(scroll)
        self.inspector = PropertyEditor()
        self.inspector.changed.connect(self._on_property_changed)
        splitter.addWidget(self.inspector)
        splitter.setSizes([820, 300])
        layout.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        buttons.addButton("Salva", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Annulla", QDialogButtonBox.ButtonRole.RejectRole)
        icons.style_button_box(buttons)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------- stato corrente
    def current_band(self) -> str:
        return self.band_combo.currentData() or "detail"

    def _apply_header(self) -> None:
        self.spec.name = self.name_edit.text().strip() or self.spec.name
        self.spec.title = self.title_edit.text()
        self.spec.table = self.table_combo.currentData() or self.spec.table
        self.spec.filter = self.filter_edit.text().strip()
        self.spec.order = self.order_edit.text().strip()
        self.spec.group_by = self.group_edit.text().strip()
        self.spec.page_size = self.page_combo.currentData() or "A4"
        self.spec.orientation = self.orientation_combo.currentData() or "portrait"

    def _reload(self) -> None:
        self._apply_header()
        self.canvas.load(self.spec, self.current_band())

    def _on_band_changed(self, _index: int) -> None:
        self.canvas.load(self.spec, self.current_band())
        self.selected = None
        self.inspector.clear()

    # ---------------------------------------------------------------- controlli
    def add_control(self, kind: str) -> None:
        band = self.current_band()
        table = self.project.table(self.spec.table)
        first_text = table.fields[0].name if table and table.fields else ""
        first_number = next(
            (f.name for f in (table.fields if table else []) if f.type in ("integer", "decimal")), first_text
        )
        control = Control(
            id=new_id(),
            kind=kind,
            x=4,
            y=max([c.y + c.h for c in self.spec.band(band)], default=0),
            w=60 if kind != "line" else 100,
            h=6,
            text="Nuovo testo" if kind == "text" else "",
            expr=first_text if kind == "field" else (f"[{first_number}]" if kind in ("expr", "total") else ""),
            label="Totale: " if kind == "total" else "",
            func="sum",
        )
        self.spec.bands.setdefault(band, []).append(control)
        self.canvas.load(self.spec, band)
        self.canvas.selected = control.id
        self._on_control_selected(control.id)

    def remove_control(self) -> None:
        if self.selected is None:
            return
        band = self.current_band()
        self.spec.bands[band] = [c for c in self.spec.band(band) if c.id != self.selected.id]
        self.selected = None
        self.inspector.clear()
        self.canvas.load(self.spec, band)

    def _on_control_selected(self, control_id: str) -> None:
        control = next((c for c in self.spec.band(self.current_band()) if c.id == control_id), None)
        if control is None:
            return
        self.selected = control
        self.inspector.set_properties(
            [
                ("kind", "Tipo", "choice", control.kind, [(k, k) for k in ("text", "field", "expr", "total", "line", "rect", "image")]),
                ("text", "Testo", "text", control.text, None),
                ("expr", "Espressione", "text", control.expr, None),
                ("x", "X (mm)", "float", control.x, None),
                ("y", "Y (mm)", "float", control.y, None),
                ("w", "Larghezza (mm)", "float", control.w, None),
                ("h", "Altezza (mm)", "float", control.h, None),
                ("font_size", "Corpo", "int", control.font_size, None),
                ("bold", "Grassetto", "bool", control.bold, None),
                ("italic", "Corsivo", "bool", control.italic, None),
                ("align", "Allineamento", "choice", control.align, [("left", "Sinistra"), ("center", "Centro"), ("right", "Destra")]),
                ("border", "Bordo", "bool", control.border, None),
                ("func", "Funzione totale", "choice", control.func, [("sum", "Somma"), ("count", "Conteggio"), ("avg", "Media"), ("min", "Minimo"), ("max", "Massimo")]),
                ("label", "Prefisso totale", "text", control.label, None),
            ]
        )

    def _on_property_changed(self, key: str, value: Any) -> None:
        if self.selected is None:
            return
        setattr(self.selected, key, value)
        self.canvas.update()

    def _sync_from_inspector(self) -> None:
        if self.selected is None:
            return
        for key, value in self.inspector.values().items():
            if key not in ("kind",):
                setattr(self.selected, key, value)

    # ------------------------------------------------------------------ azioni
    def preview(self) -> None:
        self._apply_header()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Report non valido", "\n".join(errors))
            return
        dialog = ReportPreviewDialog(self.project, self.spec, self)
        dialog.exec()

    def save(self) -> None:
        self._apply_header()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Report non valido", "\n".join(errors))
            return
        if not self.spec.name:
            self.spec.name = f"report_{slugify(self.spec.table)}"
        try:
            self.project.put_object("reports", self.spec.to_dict(), previous_name=self.original_name)
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return
        self.accept()
