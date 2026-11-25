"""Database Designer visuale: diagramma ER e modifica dello schema.

Il canvas mostra le tabelle reali del progetto e le relazioni derivate dalle
foreign key. Le modifiche a tabelle, campi e relazioni passano dalle primitive
del progetto (``apply_table``/``drop_table``), con backup e conferma.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtSvg import QSvgGenerator

from ..core.diagram_model import DiagramSpec
from ..core.metadata import ForeignKey, MetadataError, Table
from ..core.project import Project, ProjectError
from ..core.schema_graph import SchemaEdge, SchemaGraph
from ..ui import design, icons
from ..ui.widgets import PropertyInspector
from .table_builder import TableBuilderDialog

CARD_WIDTH = 252.0
HEADER_HEIGHT = 30.0
ROW_HEIGHT = 19.0
CARD_PADDING = 8.0
GRID_STEP = 20.0
SNAP = 10.0


def _theme() -> str:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    name = app.property("dbx_theme") if app is not None else None
    return name if isinstance(name, str) else design.DEFAULT_THEME


def _palette() -> dict[str, str]:
    return design.palette(_theme())


def _unique_fields(table: Table | None) -> list[str]:
    if table is None:
        return []
    result: list[str] = []
    for field in table.fields:
        if field.pk and field.name not in result:
            result.append(field.name)
    for index in table.indexes:
        if index.unique:
            for name in index.fields:
                if name not in result:
                    result.append(name)
    return result


class RelationshipDialog(QDialog):
    """Crea una foreign key scegliendo tabella/campo figlio e padre."""

    def __init__(self, graph: SchemaGraph, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph = graph
        self.setWindowTitle("Nuova relazione")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.child_table = QComboBox()
        self.parent_table = QComboBox()
        for name in graph.nodes:
            self.child_table.addItem(name, name)
            self.parent_table.addItem(name, name)
        self.child_field = QComboBox()
        self.parent_field = QComboBox()
        self.on_delete = QComboBox()
        for label, key in (
            ("NO ACTION", "NO ACTION"),
            ("CASCADE", "CASCADE"),
            ("SET NULL", "SET NULL"),
            ("RESTRICT", "RESTRICT"),
        ):
            self.on_delete.addItem(label, key)
        form.addRow("Tabella figlio", self.child_table)
        form.addRow("Campo figlio", self.child_field)
        form.addRow("Tabella padre", self.parent_table)
        form.addRow("Campo padre", self.parent_field)
        form.addRow("ON DELETE", self.on_delete)
        layout.addLayout(form)
        hint = QLabel(
            "Il campo padre deve essere una chiave primaria o un campo con indice unico. "
            "La relazione viene applicata allo schema con backup."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.child_table.currentIndexChanged.connect(self._refresh_child)
        self.parent_table.currentIndexChanged.connect(self._refresh_parent)
        self._refresh_child()
        self._refresh_parent()
        self.resize(480, 260)

    def _refresh_child(self) -> None:
        table = self.graph.table(str(self.child_table.currentData() or ""))
        self.child_field.clear()
        for field in (table.fields if table else []):
            self.child_field.addItem(field.display_name(), field.name)

    def _refresh_parent(self) -> None:
        table = self.graph.table(str(self.parent_table.currentData() or ""))
        self.parent_field.clear()
        names = _unique_fields(table)
        for name in names:
            field = table.field(name) if table else None
            if field is not None:
                self.parent_field.addItem(field.display_name(), field.name)

    def relationship(self) -> tuple[str, ForeignKey] | None:
        child_name = str(self.child_table.currentData() or "")
        parent_name = str(self.parent_table.currentData() or "")
        child_field = str(self.child_field.currentData() or "")
        parent_field = str(self.parent_field.currentData() or "")
        if not (child_name and parent_name and child_field and parent_field):
            return None
        fk = ForeignKey(
            columns=[child_field],
            ref_table=parent_name,
            ref_columns=[parent_field],
            on_delete=str(self.on_delete.currentData() or "NO ACTION"),
        )
        return child_name, fk


class DatabaseCanvas(QWidget):
    """Canvas del diagramma: card delle tabelle, archi e selezione."""

    selection_changed = pyqtSignal(object)
    changed = pyqtSignal()
    table_activated = pyqtSignal(str)
    relationship_activated = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graph: SchemaGraph | None = None
        self.diagram: DiagramSpec | None = None
        self.zoom = 1.0
        self.selected_table: str | None = None
        self.selected_edge: SchemaEdge | None = None
        self._mode: str | None = None
        self._drag_table: str | None = None
        self._drag_start = QPointF()
        self._drag_origin = QPointF()
        self._pan_start = QPoint()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAccessibleName("Diagramma ER del database")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    # ------------------------------------------------------------------ dati
    def load(self, graph: SchemaGraph, diagram: DiagramSpec) -> None:
        self.graph = graph
        self.diagram = diagram
        self.zoom = diagram.zoom
        self._resize()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        if self.diagram is None:
            return
        self.zoom = max(0.25, min(2.0, float(zoom)))
        self.diagram.zoom = self.zoom
        self._resize()
        self.update()

    def card_height(self, table: Table) -> float:
        return HEADER_HEIGHT + CARD_PADDING + max(1, len(table.fields)) * ROW_HEIGHT + CARD_PADDING

    def card_rect(self, table_name: str) -> QRectF:
        if self.graph is None or self.diagram is None:
            return QRectF()
        table = self.graph.table(table_name)
        node = self.diagram.node(table_name)
        if table is None or node is None:
            return QRectF()
        return QRectF(node.x, node.y, CARD_WIDTH, self.card_height(table))

    def content_rect(self) -> QRectF:
        if self.graph is None or self.diagram is None:
            return QRectF(0, 0, 900, 600)
        rect = QRectF()
        for name in self.graph.nodes:
            card = self.card_rect(name)
            rect = card if rect.isNull() else rect.united(card)
        if rect.isNull():
            return QRectF(0, 0, 900, 600)
        return rect.adjusted(-60, -60, 60, 60)

    def _resize(self) -> None:
        rect = self.content_rect()
        self.setFixedSize(
            max(320, int(rect.width() * self.zoom)),
            max(240, int(rect.height() * self.zoom)),
        )

    # ------------------------------------------------------------------ paint
    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        painter = QPainter(self)
        try:
            self.render_diagram(painter, self.content_rect(), grid=True)
        finally:
            painter.end()

    def render_diagram(self, painter: QPainter, bounds: QRectF, grid: bool = True) -> None:
        palette = _palette()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(palette["workspace"]))
        painter.save()
        painter.scale(self.zoom, self.zoom)
        if grid:
            painter.setPen(QPen(QColor(palette["grid_dot"]), 0.7))
            x = int(bounds.left() // GRID_STEP) * GRID_STEP
            while x <= bounds.right():
                y = int(bounds.top() // GRID_STEP) * GRID_STEP
                while y <= bounds.bottom():
                    painter.drawPoint(QPointF(x, y))
                    y += GRID_STEP
                x += GRID_STEP
        if self.graph is None or self.diagram is None:
            painter.restore()
            return
        for edge in self.graph.edges:
            self._paint_edge(painter, edge, palette)
        for name, table in self.graph.nodes.items():
            self._paint_card(painter, table, palette, name == self.selected_table)
        painter.restore()

    def _paint_card(self, painter: QPainter, table: Table, palette: dict[str, str], selected: bool) -> None:
        rect = self.card_rect(table.name)
        if rect.isNull():
            return
        painter.setPen(QPen(QColor(palette["focus"] if selected else palette["panel_shadow"]), 2.0 if selected else 1.2))
        painter.setBrush(QColor(palette["input_bg"]))
        painter.drawRoundedRect(rect, 8, 8)

        header = QRectF(rect.left(), rect.top(), rect.width(), HEADER_HEIGHT)
        gradient = QLinearGradient(header.topLeft(), header.topRight())
        gradient.setColorAt(0.0, QColor(palette["accent"]))
        gradient.setColorAt(1.0, QColor(palette["accent2"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(header, 8, 8)
        painter.drawRect(QRectF(header.left(), header.bottom() - 8, header.width(), 8))

        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(8.5)
        painter.setFont(title_font)
        painter.setPen(QColor(palette["header_text"]))
        painter.drawText(
            header.adjusted(10, 0, -10, 0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            table.display_name(),
        )

        fk_fields: set[str] = set()
        for fk in table.foreign_keys:
            fk_fields.update(name.lower() for name in fk.columns)
        body_font = QFont(self.font())
        body_font.setPointSizeF(7.6)
        painter.setFont(body_font)
        y = rect.top() + HEADER_HEIGHT + CARD_PADDING
        for index, field in enumerate(table.fields):
            row = QRectF(rect.left() + 4, y, rect.width() - 8, ROW_HEIGHT)
            if index % 2:
                painter.fillRect(row, QColor(palette["alternate_bg"]))
            painter.setPen(QColor(palette["text"]))
            marker = "PK" if field.pk else ("FK" if field.name.lower() in fk_fields else "  ")
            marker_color = palette["error"] if field.pk else palette["accent"]
            painter.setPen(QColor(marker_color))
            painter.drawText(
                row.adjusted(6, 0, 0, 0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                marker,
            )
            painter.setPen(QColor(palette["text"]))
            painter.drawText(
                row.adjusted(34, 0, -70, 0),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                field.display_name(),
            )
            type_text = field.type.upper()
            if field.size:
                type_text += f"({field.size})"
            painter.setPen(QColor(palette["disabled"]))
            painter.drawText(
                row.adjusted(0, 0, -8, 0),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                type_text,
            )
            y += ROW_HEIGHT

    def _paint_edge(self, painter: QPainter, edge: SchemaEdge, palette: dict[str, str]) -> None:
        points = self._edge_points(edge)
        if len(points) < 2:
            return
        selected = self.selected_edge is not None and self.selected_edge.name == edge.name
        color = QColor(palette["focus"] if selected else palette["panel_dark"])
        painter.setPen(QPen(color, 2.4 if selected else 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for first, second in zip(points, points[1:]):
            painter.drawLine(first, second)
        self._draw_crow(painter, points[0], points[1], color, edge.cardinality)
        self._draw_parent_mark(painter, points[-1], color, edge.cardinality)
        midpoint = points[len(points) // 2]
        label = f"{edge.cardinality} · {edge.on_delete}"
        label_font = QFont(self.font())
        label_font.setPointSizeF(6.8)
        metrics = QFontMetrics(label_font)
        width = metrics.horizontalAdvance(label) + 10
        pill = QRectF(midpoint.x() - width / 2, midpoint.y() - 8, width, 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette["menu_bg"]))
        painter.drawRoundedRect(pill, 5, 5)
        painter.setPen(QColor(palette["text"]))
        painter.setFont(label_font)
        painter.drawText(pill, int(Qt.AlignmentFlag.AlignCenter), label)

    def _edge_points(self, edge: SchemaEdge) -> list[QPointF]:
        child = self.card_rect(edge.child)
        parent = self.card_rect(edge.parent)
        if child.isNull() or parent.isNull():
            return []
        if edge.child.lower() == edge.parent.lower():
            start = QPointF(child.right(), child.center().y())
            end = QPointF(child.center().x(), child.top())
            return [
                start,
                QPointF(start.x() + 35, start.y()),
                QPointF(start.x() + 35, end.y() - 30),
                QPointF(end.x(), end.y() - 30),
                end,
            ]
        dx = parent.center().x() - child.center().x()
        dy = parent.center().y() - child.center().y()
        if abs(dx) >= abs(dy):
            if dx >= 0:
                start = QPointF(child.right(), child.center().y())
                end = QPointF(parent.left(), parent.center().y())
            else:
                start = QPointF(child.left(), child.center().y())
                end = QPointF(parent.right(), parent.center().y())
            middle = (start.x() + end.x()) / 2
            return [start, QPointF(middle, start.y()), QPointF(middle, end.y()), end]
        if dy >= 0:
            start = QPointF(child.center().x(), child.bottom())
            end = QPointF(parent.center().x(), parent.top())
        else:
            start = QPointF(child.center().x(), child.top())
            end = QPointF(parent.center().x(), parent.bottom())
        middle = (start.y() + end.y()) / 2
        return [start, QPointF(start.x(), middle), QPointF(end.x(), middle), end]

    @staticmethod
    def _draw_crow(painter: QPainter, point: QPointF, other: QPointF, color: QColor, cardinality: str) -> None:
        dx = other.x() - point.x()
        dy = other.y() - point.y()
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        painter.setPen(QPen(color, 1.4))
        for offset in (-5.0, 0.0, 5.0):
            q = QPointF(point.x() + ux * 11 + px * offset, point.y() + uy * 11 + py * offset)
            painter.drawLine(point, q)
        if cardinality == "1:1":
            painter.drawLine(
                QPointF(point.x() + ux * 4 - px * 5, point.y() + uy * 4 - py * 5),
                QPointF(point.x() + ux * 4 + px * 5, point.y() + uy * 4 + py * 5),
            )

    @staticmethod
    def _draw_parent_mark(painter: QPainter, point: QPointF, color: QColor, cardinality: str) -> None:
        painter.setPen(QPen(color, 1.6))
        painter.drawLine(QPointF(point.x() - 6, point.y() - 6), QPointF(point.x() + 6, point.y() + 6))
        if cardinality == "1:1":
            painter.drawLine(QPointF(point.x() - 6, point.y() + 6), QPointF(point.x() + 6, point.y() - 6))

    # ------------------------------------------------------------------ hit test
    def _hit_card(self, point: QPointF) -> str | None:
        if self.graph is None:
            return None
        for name in reversed(list(self.graph.nodes)):
            if self.card_rect(name).contains(point):
                return name
        return None

    def _hit_edge(self, point: QPointF) -> SchemaEdge | None:
        if self.graph is None:
            return None
        for edge in reversed(self.graph.edges):
            points = self._edge_points(edge)
            for first, second in zip(points, points[1:]):
                if self._distance_to_segment(point, first, second) <= 8.0:
                    return edge
        return None

    @staticmethod
    def _distance_to_segment(point: QPointF, first: QPointF, second: QPointF) -> float:
        dx, dy = second.x() - first.x(), second.y() - first.y()
        if dx == dy == 0:
            return ((point.x() - first.x()) ** 2 + (point.y() - first.y()) ** 2) ** 0.5
        t = ((point.x() - first.x()) * dx + (point.y() - first.y()) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        x, y = first.x() + t * dx, first.y() + t * dy
        return ((point.x() - x) ** 2 + (point.y() - y) ** 2) ** 0.5

    # ------------------------------------------------------------------ mouse
    def _logical(self, position: QPointF) -> QPointF:
        return QPointF(position.x() / self.zoom, position.y() / self.zoom)

    def mousePressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() == Qt.MouseButton.MiddleButton:
            self._mode = "pan"
            self._pan_start = event.globalPosition().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._logical(event.position())
        card = self._hit_card(point)
        if card is not None:
            self.selected_table = card
            self.selected_edge = None
            self._mode = "move"
            self._drag_table = card
            node = self.diagram.node(card) if self.diagram else None
            if node is not None:
                self._drag_origin = QPointF(node.x, node.y)
            self._drag_start = point
            self.selection_changed.emit(("table", card))
            self.setFocus()
            self.update()
            return
        edge = self._hit_edge(point)
        if edge is not None:
            self.selected_table = None
            self.selected_edge = edge
            self.selection_changed.emit(("edge", edge))
            self.setFocus()
            self.update()
            return
        self.selected_table = None
        self.selected_edge = None
        self.selection_changed.emit(None)
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self._mode == "pan":
            current = event.globalPosition().toPoint()
            delta = current - self._pan_start
            self._pan_start = current
            scroll = self.parentWidget().parentWidget() if self.parentWidget() else None
            if isinstance(scroll, QScrollArea):
                scroll.horizontalScrollBar().setValue(scroll.horizontalScrollBar().value() - delta.x())
                scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().value() - delta.y())
            return
        if self._mode != "move" or self.diagram is None or self._drag_table is None:
            return
        point = self._logical(event.position())
        dx = round((point.x() - self._drag_start.x()) / SNAP) * SNAP
        dy = round((point.y() - self._drag_start.y()) / SNAP) * SNAP
        self.diagram.place(
            self._drag_table,
            max(0.0, self._drag_origin.x() + dx),
            max(0.0, self._drag_origin.y() + dy),
        )
        self._resize()
        self.changed.emit()
        self.update()

    def mouseReleaseEvent(self, _event) -> None:  # noqa: D102 - API Qt
        self._mode = None
        self._drag_table = None
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self._logical(event.position())
        card = self._hit_card(point)
        if card is not None:
            self.table_activated.emit(card)
            return
        edge = self._hit_edge(point)
        if edge is not None:
            self.relationship_activated.emit(edge)

    def keyPressEvent(self, event) -> None:  # noqa: D102 - API Qt
        if self.diagram is None or self.selected_table is None:
            super().keyPressEvent(event)
            return
        deltas = {
            Qt.Key.Key_Left: (-SNAP, 0.0),
            Qt.Key.Key_Right: (SNAP, 0.0),
            Qt.Key.Key_Up: (0.0, -SNAP),
            Qt.Key.Key_Down: (0.0, SNAP),
        }
        if event.key() in deltas:
            node = self.diagram.node(self.selected_table)
            if node is not None:
                dx, dy = deltas[event.key()]
                node.x = max(0.0, node.x + dx)
                node.y = max(0.0, node.y + dy)
                self._resize()
                self.changed.emit()
                self.update()
            return
        super().keyPressEvent(event)


class DatabaseDesignerWidget(QWidget):
    """Database Designer: diagramma ER, schema e layout in una finestra MDI."""

    saved = pyqtSignal(str)
    status_message = pyqtSignal(str)
    tables_changed = pyqtSignal()
    open_table = pyqtSignal(str, str)

    def __init__(self, project: Project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("database_designer")
        self.project = project
        self.graph = SchemaGraph.from_project(project)
        self.diagram = DiagramSpec.from_project(project, self.graph)
        self.selected_table: str | None = None
        self.selected_edge: SchemaEdge | None = None
        self._saved_state = self.diagram.to_dict()
        self.setWindowTitle("Database — schema ER")
        self.resize(1180, 760)
        self._build_ui()
        self._load()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        toolbar = QVBoxLayout()
        toolbar.setSpacing(2)
        primary = QHBoxLayout()
        primary.setSpacing(2)
        self.new_table_button = icons.make_button("Nuova tabella", "nuovo", self.new_table, self, "Crea una tabella")
        self.edit_table_button = icons.make_button("Modifica", "modifica", self.edit_table, self, "Modifica la tabella selezionata")
        self.open_data_button = icons.make_button("Dati", "tabella", self.open_data_for_selected, self, "Mostra i dati della tabella selezionata nella scheda Dati")
        self.delete_table_button = icons.make_button("Elimina", "elimina", self.delete_table, self, "Elimina la tabella selezionata")
        self.relation_button = icons.make_button("Relazione", "tabella", self.new_relationship, self, "Crea una relazione")
        self.delete_relation_button = icons.make_button("Elimina relazione", "elimina", self.delete_relationship, self, "Elimina la relazione selezionata")
        for button in (
            self.new_table_button,
            self.edit_table_button,
            self.open_data_button,
            self.delete_table_button,
            self.relation_button,
            self.delete_relation_button,
        ):
            primary.addWidget(button)
        primary.addSpacing(8)
        self.layout_button = icons.make_button("Auto layout", "cascata", self.auto_layout, self, "Disponi automaticamente le tabelle")
        primary.addWidget(self.layout_button)
        primary.addStretch(1)
        toolbar.addLayout(primary)

        secondary = QHBoxLayout()
        secondary.setSpacing(2)
        self.export_png_button = icons.make_button("PNG", "esporta", self.export_png, self, "Esporta il diagramma in PNG")
        self.export_svg_button = icons.make_button("SVG", "esporta", self.export_svg, self, "Esporta il diagramma in SVG")
        secondary.addWidget(self.export_png_button)
        secondary.addWidget(self.export_svg_button)
        secondary.addStretch(1)
        secondary.addWidget(QLabel("Zoom:"))
        self.zoom_combo = QComboBox()
        for percent in (25, 50, 75, 100, 125, 150, 200):
            self.zoom_combo.addItem(f"{percent}%", percent)
        self.zoom_combo.setCurrentIndex(3)
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        secondary.addWidget(self.zoom_combo)
        self.save_button = icons.make_button("Salva layout", "salva", self.save, self, "Salva posizioni e zoom")
        secondary.addWidget(self.save_button)
        toolbar.addLayout(secondary)
        layout.addLayout(toolbar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("database_horizontal")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)
        tables_header = QLabel("Tabelle")
        tables_header.setObjectName("browse_header")
        left_layout.addWidget(tables_header)
        self.table_list = QListWidget()
        self.table_list.setObjectName("database_tables")
        self.table_list.setMinimumWidth(110)
        self.table_list.setMaximumWidth(220)
        self.table_list.currentItemChanged.connect(self._on_table_list_changed)
        self.table_list.itemDoubleClicked.connect(
            lambda item: self.open_table.emit(str(item.data(Qt.ItemDataRole.UserRole)), "edit")
        )
        left_layout.addWidget(self.table_list, 1)
        self.splitter.addWidget(left)

        self.canvas = DatabaseCanvas()
        self.canvas.selection_changed.connect(self._on_selection)
        self.canvas.changed.connect(self._on_changed)
        self.canvas.table_activated.connect(self.edit_table_by_name)
        self.canvas.relationship_activated.connect(self._on_relationship_activated)
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.splitter.addWidget(self.scroll)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        self.selection_label = QLabel("Nessun oggetto selezionato")
        self.selection_label.setObjectName("browse_header")
        self.selection_label.setWordWrap(True)
        right_layout.addWidget(self.selection_label)
        self.inspector = PropertyInspector()
        self.inspector.setMinimumWidth(240)
        self.inspector.property_changed.connect(self._on_property_changed)
        right_layout.addWidget(self.inspector, 1)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([120, 810, 250])
        layout.addWidget(self.splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("nav_hint")
        layout.addWidget(self.status_label)
        self._refresh_buttons()
        self._show_diagram_properties()

    def _load(self) -> None:
        self.canvas.load(self.graph, self.diagram)
        self._sync_table_list()
        self._sync_zoom_combo()
        self._refresh_status()

    def _sync_zoom_combo(self) -> None:
        percent = int(round(self.diagram.zoom * 100))
        index = self.zoom_combo.findData(percent)
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentIndex(index if index >= 0 else 3)
        self.zoom_combo.blockSignals(False)

    def _refresh_status(self) -> None:
        summary = self.graph.summary()
        selected = ""
        if self.selected_table:
            selected = f" · Tabella: {self.selected_table}"
        elif self.selected_edge:
            selected = f" · Relazione: {self.selected_edge.child} → {self.selected_edge.parent}"
        tables = summary["tables"]
        relations = summary["relationships"]
        self.status_label.setText(
            f"{tables} {'tabella' if tables == 1 else 'tabelle'} · "
            f"{relations} {'relazione' if relations == 1 else 'relazioni'} · "
            f"Zoom {int(round(self.diagram.zoom * 100))}%{selected}"
        )

    def _refresh_buttons(self) -> None:
        has_table = self.selected_table is not None
        has_edge = self.selected_edge is not None
        if hasattr(self, "edit_table_button"):
            self.edit_table_button.setEnabled(has_table)
            self.open_data_button.setEnabled(has_table)
            self.delete_table_button.setEnabled(has_table)
            self.delete_relation_button.setEnabled(has_edge)

    # ------------------------------------------------------------- selezione
    def _on_selection(self, selection: object) -> None:
        self.selected_table = None
        self.selected_edge = None
        if isinstance(selection, tuple) and len(selection) == 2:
            kind, value = selection
            if kind == "table":
                self.selected_table = str(value)
            elif kind == "edge":
                self.selected_edge = value
        if self.selected_table:
            table = self.graph.table(self.selected_table)
            if table is not None:
                self._show_table(table)
        elif self.selected_edge:
            self._show_edge(self.selected_edge)
        else:
            self._show_diagram_properties()
        self._sync_table_list()
        self._refresh_buttons()
        self._refresh_status()

    def _show_diagram_properties(self) -> None:
        self.selection_label.setText("Diagramma ER")
        self.inspector.set_properties(
            [
                (
                    "• Schema",
                    [
                        ("tables", "Tabelle", "ro", str(len(self.graph.nodes)), None),
                        ("edges", "Relazioni", "ro", str(len(self.graph.edges)), None),
                        ("zoom", "Zoom", "ro", f"{int(round(self.diagram.zoom * 100))}%", None),
                    ],
                ),
                (
                    "• Layout",
                    [
                        ("name", "Name", "ro", self.diagram.name, None),
                        ("caption", "Caption", "ro", self.diagram.caption, None),
                        ("notes", "Note", "text", self.diagram.notes, None),
                    ],
                ),
            ]
        )
        self.inspector.set_events([])
        self.inspector.set_methods([])

    def _show_table(self, table: Table) -> None:
        self.selection_label.setText(f"Tabella — {table.display_name()}")
        keys = [field.name for field in table.fields if field.pk]
        self.inspector.set_properties(
            [
                (
                    "• Table",
                    [
                        ("name", "Name", "ro", table.name, None),
                        ("caption", "Caption", "text", table.caption, None),
                        ("fields", "Campi", "ro", str(len(table.fields)), None),
                        ("keys", "Chiavi", "ro", ", ".join(keys) or "(nessuna)", None),
                        ("indexes", "Indici", "ro", str(len(table.indexes)), None),
                        ("relations", "Relazioni", "ro", str(len(table.foreign_keys)), None),
                    ],
                ),
                (
                    "• Campi",
                    [
                        (
                            f"field:{field.name}",
                            field.display_name(),
                            "ro",
                            f"{field.type.upper()}{f' ({field.size})' if field.size else ''}",
                            None,
                        )
                        for field in table.fields
                    ],
                ),
            ]
        )
        self.inspector.set_events([])
        self.inspector.set_methods([])

    def _show_edge(self, edge: SchemaEdge) -> None:
        self.selection_label.setText(f"Relazione — {edge.child} → {edge.parent}")
        self.inspector.set_properties(
            [
                (
                    "• Relationship",
                    [
                        ("name", "Name", "ro", edge.name, None),
                        ("child", "Figlio", "ro", edge.child, None),
                        ("columns", "Campi figlio", "ro", ", ".join(edge.columns), None),
                        ("parent", "Padre", "ro", edge.parent, None),
                        ("ref_columns", "Campi padre", "ro", ", ".join(edge.ref_columns), None),
                        ("on_delete", "ON DELETE", "ro", edge.on_delete, None),
                        ("cardinality", "Cardinalità", "ro", edge.cardinality, None),
                    ],
                )
            ]
        )
        self.inspector.set_events([])
        self.inspector.set_methods([])

    def _on_property_changed(self, key: str, value: Any) -> None:
        if key == "notes":
            self.diagram.notes = str(value)
            self._on_changed()
            return
        if key == "caption" and self.selected_table:
            table = self.graph.table(self.selected_table)
            if table is not None:
                table.caption = str(value)
                try:
                    self.project.put_object(
                        "tables", table.to_dict(), previous_name=table.name
                    )
                    self.project.save()
                except ProjectError as exc:
                    QMessageBox.warning(self, "Salvataggio non riuscito", str(exc))
                    return
                self._refresh_schema(keep_selection=True)
                self._on_changed()

    # --------------------------------------------------------------- comandi
    def _on_changed(self) -> None:
        self._refresh_status()
        self._refresh_buttons()

    def _on_zoom_changed(self, _index: int) -> None:
        percent = int(self.zoom_combo.currentData() or 100)
        self.canvas.set_zoom(percent / 100.0)
        self.diagram.zoom = self.canvas.zoom
        self._refresh_status()
        self._on_changed()

    def _refresh_schema(self, keep_selection: bool = False) -> None:
        selected_table = self.selected_table if keep_selection else None
        selected_edge_name = self.selected_edge.name if keep_selection and self.selected_edge else None
        self.graph = SchemaGraph.from_project(self.project)
        self.diagram = DiagramSpec.from_graph(
            self.graph,
            name=self.diagram.name,
            caption=self.diagram.caption,
            previous=self.diagram,
        )
        self.diagram.zoom = self.canvas.zoom
        self.canvas.load(self.graph, self.diagram)
        self.selected_table = selected_table if self.graph.table(selected_table or "") else None
        self.selected_edge = (
            next((edge for edge in self.graph.edges if edge.name == selected_edge_name), None)
            if selected_edge_name
            else None
        )
        self.canvas.selected_table = self.selected_table
        self.canvas.selected_edge = self.selected_edge
        self._sync_table_list()
        self._sync_zoom_combo()
        if self.selected_table:
            table = self.graph.table(self.selected_table)
            if table is not None:
                self._show_table(table)
        elif self.selected_edge:
            self._show_edge(self.selected_edge)
        else:
            self._show_diagram_properties()
        self._refresh_buttons()
        self._refresh_status()

    def _sync_table_list(self) -> None:
        if not hasattr(self, "table_list"):
            return
        self.table_list.blockSignals(True)
        self.table_list.clear()
        for name in self.project.names("tables"):
            item = QListWidgetItem(
                icons.icon("database", design.category_color("tables")), name
            )
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.table_list.addItem(item)
            if name == self.selected_table:
                self.table_list.setCurrentItem(item)
        if not self.selected_table:
            self.table_list.clearSelection()
            self.table_list.setCurrentRow(-1)
        self.table_list.blockSignals(False)

    def _on_table_list_changed(self, current, _previous) -> None:
        if current is not None:
            self.select_table(str(current.data(Qt.ItemDataRole.UserRole)))

    def open_data_for_selected(self) -> None:
        if self.selected_table:
            self.open_table.emit(self.selected_table, "browse")

    def new_table(self) -> None:
        dialog = TableBuilderDialog(self.project, None, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        table = dialog.current_table()
        self._refresh_schema()
        self._on_selection(("table", table.name))
        self._on_changed()
        self.tables_changed.emit()
        self.open_table.emit(table.name, "edit")
        self.status_message.emit(f"Tabella {table.name} creata")

    def select_table(self, name: str) -> None:
        """Seleziona una tabella senza aprire l'editor della struttura."""
        if name not in self.diagram.nodes and self.project.table(name) is None:
            return
        self.selected_table = name
        self.selected_edge = None
        self.canvas.selected_table = name
        self.canvas.selected_edge = None
        table = self.graph.table(name)
        if table is not None:
            self._show_table(table)
        self._sync_table_list()
        self._refresh_buttons()
        self._refresh_status()

    def edit_table(self) -> None:
        if self.selected_table:
            self.open_table.emit(self.selected_table, "edit")

    def edit_table_by_name(self, name: str) -> None:
        if self.project.table(name) is not None:
            self.open_table.emit(name, "edit")

    def delete_table(self) -> None:
        if not self.selected_table:
            return
        name = self.selected_table
        incoming = self.graph.incoming(name)
        if incoming:
            QMessageBox.information(
                self,
                "Relazioni presenti",
                "Rimuovi prima le relazioni che puntano a questa tabella.",
            )
            return
        answer = QMessageBox.question(
            self,
            "Elimina tabella",
            f"Eliminare la tabella «{name}» e tutti i suoi dati?\n"
            "Verrà creato un backup del database.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.project.drop_table(name)
        except (ProjectError, MetadataError) as exc:
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self.diagram.nodes.pop(name, None)
        self.selected_table = None
        self.canvas.selected_table = None
        self._refresh_schema()
        self._on_changed()
        self.tables_changed.emit()
        self.status_message.emit(f"Tabella {name} eliminata")

    def new_relationship(self) -> None:
        if len(self.graph.nodes) < 1:
            QMessageBox.information(self, "Relazione", "Crea prima una tabella.")
            return
        dialog = RelationshipDialog(self.graph, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        relationship = dialog.relationship()
        if relationship is None:
            QMessageBox.warning(
                self,
                "Relazione non valida",
                "Scegli tabella e campo figlio, tabella e campo padre. Il campo padre deve essere "
                "una chiave primaria o avere un indice unico.",
            )
            return
        child_name, fk = relationship
        self._apply_relationship(child_name, fk)
        self._refresh_schema()
        self.selected_edge = next(
            (edge for edge in self.graph.edges if edge.name == fk.resolved_name(child_name)), None
        )
        self.canvas.selected_edge = self.selected_edge
        if self.selected_edge:
            self._show_edge(self.selected_edge)
        self._on_changed()
        self.status_message.emit(f"Relazione {child_name} → {fk.ref_table} creata")

    def _apply_relationship(self, child_name: str, fk: ForeignKey) -> bool:
        table = self.project.table(child_name)
        if table is None:
            return False
        table.foreign_keys.append(fk)
        try:
            self.project.apply_table(table, backup=True)
        except ProjectError as exc:
            table.foreign_keys.remove(fk)
            QMessageBox.warning(self, "Relazione non applicata", str(exc))
            return False
        return True

    def delete_relationship(self) -> None:
        edge = self.selected_edge
        if edge is None:
            return
        answer = QMessageBox.question(
            self,
            "Elimina relazione",
            f"Eliminare la relazione {edge.child} → {edge.parent}?\n"
            "Verrà creato un backup del database.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        table = self.project.table(edge.child)
        if table is None:
            return
        target = next(
            (fk for fk in table.foreign_keys if fk.resolved_name(table.name) == edge.name),
            None,
        )
        if target is None:
            return
        table.foreign_keys.remove(target)
        try:
            self.project.apply_table(table, backup=True)
        except ProjectError as exc:
            table.foreign_keys.append(target)
            QMessageBox.warning(self, "Eliminazione non riuscita", str(exc))
            return
        self.selected_edge = None
        self.canvas.selected_edge = None
        self._refresh_schema()
        self._on_changed()
        self.status_message.emit("Relazione eliminata")

    def _on_relationship_activated(self, edge: object) -> None:
        if isinstance(edge, SchemaEdge):
            self.selected_edge = edge
            self.selected_table = None
            self.canvas.selected_edge = edge
            self.canvas.selected_table = None
            self._show_edge(edge)
            self._on_selection(("edge", edge))

    def auto_layout(self) -> None:
        self.diagram.auto_layout(self.graph)
        self.canvas.load(self.graph, self.diagram)
        self._on_changed()
        self.status_message.emit("Layout automatico applicato")

    # --------------------------------------------------------------- export
    def _export_bounds(self) -> QRectF:
        return self.canvas.content_rect()

    def export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Esporta diagramma PNG", "schema-er.png", "PNG (*.png)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".png"
        bounds = self._export_bounds()
        image = QImage(
            max(1, int(bounds.width())),
            max(1, int(bounds.height())),
            QImage.Format.Format_ARGB32_Premultiplied,
        )
        palette = _palette()
        image.fill(QColor(palette["workspace"]))
        painter = QPainter(image)
        try:
            painter.translate(-bounds.left(), -bounds.top())
            old_zoom = self.canvas.zoom
            self.canvas.zoom = 1.0
            self.canvas.render_diagram(painter, bounds, grid=False)
            self.canvas.zoom = old_zoom
        finally:
            painter.end()
        if not image.save(path, "PNG"):
            QMessageBox.warning(self, "Export non riuscito", f"Impossibile salvare {path}")
            return
        self.status_message.emit(f"Diagramma esportato in {path}")

    def export_svg(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Esporta diagramma SVG", "schema-er.svg", "SVG (*.svg)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".svg"
        bounds = self._export_bounds()
        generator = QSvgGenerator()
        generator.setFileName(path)
        generator.setSize(QSize(max(1, int(bounds.width())), max(1, int(bounds.height()))))
        generator.setViewBox(QRectF(0, 0, bounds.width(), bounds.height()))
        generator.setTitle("Schema ER — dBX")
        painter = QPainter(generator)
        try:
            painter.translate(-bounds.left(), -bounds.top())
            old_zoom = self.canvas.zoom
            self.canvas.zoom = 1.0
            self.canvas.render_diagram(painter, bounds, grid=False)
            self.canvas.zoom = old_zoom
        finally:
            painter.end()
        self.status_message.emit(f"Diagramma esportato in {path}")

    # --------------------------------------------------------------- salvataggio
    def is_dirty(self) -> bool:
        return self.diagram.to_dict() != self._saved_state

    def save(self) -> bool:
        try:
            self.project.put_object("diagrams", self.diagram.to_dict(), previous_name="schema")
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self._saved_state = self.diagram.to_dict()
        self.saved.emit(self.diagram.name)
        self.status_message.emit("Layout del diagramma salvato")
        return True
