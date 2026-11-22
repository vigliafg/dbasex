"""Rendering delle pagine di report: anteprima, stampa e PDF (E7)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QPointF, QRectF, QSizeF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QImage,
    QPageSize,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtPrintSupport import QPrinter

from ..runtime.report_engine import LINE_FACTOR, MM_PER_PT, Page
from ..ui import design


class ExportError(RuntimeError):
    """Errore di stampa o di esportazione PDF."""


_ALIGN = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
}


def _color(value: str, fallback: str = "#000000") -> QColor:
    color = QColor(value or fallback)
    return color if color.isValid() else QColor(fallback)


def _series_color(index: int) -> QColor:
    colors = design.CHART_COLORS
    return QColor(colors[index % len(colors)])


def _draw_chart(painter: QPainter, op: "Op", rect: QRectF, scale: float, pen_width: float) -> None:
    """Disegna barre, linee o torta dentro il rettangolo del controllo."""
    if op.border:
        painter.setPen(QPen(_color(op.color, "#94a3b8"), pen_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
    title_height = 0.0
    if op.text:
        font = QFont()
        if op.font_name:
            font.setFamily(op.font_name)
        font.setPixelSize(max(6, int(round(op.font_size * MM_PER_PT * scale))))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(_color(op.color, "#334155")))
        title_height = op.font_size * MM_PER_PT * scale * 1.55
        painter.drawText(
            QRectF(rect.x(), rect.y(), rect.width(), title_height),
            int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
            op.text,
        )
    series = [(label, float(value)) for label, value in op.series]
    if not series:
        painter.setPen(QPen(QColor("#64748b")))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "(nessun dato)")
        return
    label_font = QFont()
    label_font.setPixelSize(max(5, int(round(2.5 * scale))))
    label_height = 3.2 * scale if len(series) <= 12 else 0.0
    plot = rect.adjusted(
        2.0 * scale,
        title_height + 1.0 * scale,
        -2.0 * scale,
        -label_height - 1.0 * scale,
    )
    if plot.width() <= 2 or plot.height() <= 2:
        return
    if op.chart_type == "pie":
        _draw_pie(painter, series, rect, plot, scale, pen_width, label_font)
        return
    maximum = max((value for _label, value in series), default=0.0)
    if maximum <= 0:
        painter.setPen(QPen(QColor("#64748b")))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "(nessun dato)")
        return
    baseline = plot.bottom()
    if op.chart_type == "line":
        points = []
        slot = plot.width() / max(1, len(series))
        for index, (_label, value) in enumerate(series):
            x = plot.left() + slot * (index + 0.5)
            y = baseline - (max(0.0, value) / maximum) * plot.height() * 0.92
            points.append(QPointF(x, y))
        pen = QPen(_color(op.color, design.CHART_COLORS[0]), max(1.0, pen_width * 1.6))
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if len(points) > 1:
            painter.drawPolyline(QPolygonF(points))
        for point in points:
            painter.setBrush(pen.color())
            painter.drawEllipse(point, max(1.2, 1.1 * scale * 0.5), max(1.2, 1.1 * scale * 0.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
    else:
        slot = plot.width() / max(1, len(series))
        bar_width = slot * 0.62
        for index, (_label, value) in enumerate(series):
            height = (max(0.0, value) / maximum) * plot.height() * 0.92
            x = plot.left() + slot * index + (slot - bar_width) / 2
            painter.fillRect(
                QRectF(x, baseline - height, bar_width, height),
                _series_color(index),
            )
    painter.setPen(QPen(QColor("#94a3b8"), max(0.6, pen_width * 0.8)))
    painter.drawLine(plot.bottomLeft(), plot.bottomRight())
    if label_height:
        painter.setFont(label_font)
        painter.setPen(QPen(QColor("#475569")))
        slot = plot.width() / max(1, len(series))
        for index, (label, _value) in enumerate(series):
            x = plot.left() + slot * index
            text = label if len(label) <= 12 else label[:11] + "…"
            painter.drawText(
                QRectF(x, plot.bottom() + 0.4 * scale, slot, label_height),
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                text,
            )


def _draw_pie(
    painter: QPainter,
    series: list[tuple[str, float]],
    rect: QRectF,
    plot: QRectF,
    scale: float,
    pen_width: float,
    label_font: QFont,
) -> None:
    total = sum(max(0.0, value) for _label, value in series)
    if total <= 0:
        painter.setPen(QPen(QColor("#64748b")))
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), "(nessun dato)")
        return
    side = min(plot.width() * 0.55, plot.height())
    pie = QRectF(plot.left(), plot.top() + (plot.height() - side) / 2, side, side)
    start = 90 * 16
    for index, (_label, value) in enumerate(series):
        span = int(-360 * 16 * max(0.0, value) / total)
        painter.setPen(QPen(QColor("#ffffff"), max(0.6, pen_width * 0.6)))
        painter.setBrush(_series_color(index))
        painter.drawPie(pie, start, span)
        start += span
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setFont(label_font)
    legend_x = pie.right() + 2.0 * scale
    legend_width = max(1.0, plot.right() - legend_x)
    line_height = label_font.pixelSize() * 1.5
    top = plot.top() + max(0.0, (plot.height() - line_height * min(8, len(series))) / 2)
    for index, (label, value) in enumerate(series[:8]):
        y = top + index * line_height
        painter.fillRect(
            QRectF(legend_x, y + line_height * 0.2, 2.2 * scale, 2.2 * scale),
            _series_color(index),
        )
        painter.setPen(QPen(QColor("#334155")))
        text = label if len(label) <= 16 else label[:15] + "…"
        painter.drawText(
            QRectF(legend_x + 3.0 * scale, y, max(1.0, legend_width - 3.0 * scale), line_height),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            text,
        )


def _paint_page(painter: QPainter, page: Page, scale: float) -> None:
    """Disegna la pagina convertendo le coordinate mm in pixel con ``scale``.

    Il ridimensionamento è fatto sui numeri, non con ``painter.scale``: così i
    caratteri hanno la dimensione reale (un punto tipografico ≈ 0,3528 mm) e non
    vengono ingranditi due volte dalla trasformazione del painter.
    """
    pen_width = max(0.6, scale * 0.12)
    for op in page.ops:
        rect = QRectF(op.x * scale, op.y * scale, op.w * scale, op.h * scale)
        if op.fill:
            painter.fillRect(rect, _color(op.fill, "#ffffff"))
        if op.kind == "line":
            painter.setPen(QPen(_color(op.color, "#333333"), pen_width))
            painter.drawLine(rect.topLeft(), rect.topRight())
            continue
        if op.kind == "rect":
            painter.setPen(QPen(_color(op.color, "#333333"), pen_width))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            continue
        if op.kind == "chart":
            _draw_chart(painter, op, rect, scale, pen_width)
            continue
        if op.kind == "image" and op.text:
            pixmap = QPixmap(op.text)
            if not pixmap.isNull():
                painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
            continue
        font = QFont()
        if op.font_name:
            font.setFamily(op.font_name)
        font.setPixelSize(max(4, int(round(op.font_size * MM_PER_PT * scale))))
        font.setBold(op.bold)
        font.setItalic(op.italic)
        font.setUnderline(op.underline)
        painter.setFont(font)
        painter.setPen(QPen(_color(op.color, "#111111")))
        if op.border:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        if not op.lines:
            continue
        line_height = op.font_size * MM_PER_PT * LINE_FACTOR * scale
        flags = _ALIGN.get(op.align, Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignTop
        for index, line in enumerate(op.lines):
            line_rect = QRectF(op.x * scale, op.y * scale + index * line_height, op.w * scale, line_height)
            painter.drawText(line_rect, int(flags), line)


def paint_pages(painter: QPainter, pages: Iterable[Page]) -> None:
    for page in pages:
        _paint_page(painter, page, 25.4)  # 1 px = 1 pollice


def _configure_printer(printer: QPrinter, page: Page) -> None:
    size = QSizeF(page.width, page.height)
    try:
        printer.setPageSize(QPageSize(size, QPageSize.Unit.Millimeter, "dBX"))
    except TypeError:  # pragma: no cover - API alternative
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    printer.setPageMargins(
        __import__("PyQt6.QtCore", fromlist=["QMarginsF"]).QMarginsF(0, 0, 0, 0)
    )


def render_to_printer(printer: QPrinter, pages: list[Page]) -> None:
    if not pages:
        raise ExportError("Nessuna pagina da stampare")
    _configure_printer(printer, pages[0])
    painter = QPainter(printer)
    if not painter.isActive():
        raise ExportError("Impossibile inizializzare la stampante")
    try:
        for index, page in enumerate(pages):
            if index:
                printer.newPage()
            _paint_page(painter, page, printer.logicalDpiX() / 25.4)
    finally:
        painter.end()


def export_pdf(pages: list[Page], path: str | Path, title: str = "") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(target))
    printer.setDocName(title or "report dBX")
    render_to_printer(printer, pages)
    if not target.exists():
        raise ExportError(f"PDF non creato: {target}")
    return target


def page_image(page: Page, px_per_mm: float = 2.2) -> QImage:
    width = max(1, int(page.width * px_per_mm))
    height = max(1, int(page.height * px_per_mm))
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    try:
        _paint_page(painter, page, px_per_mm)
    finally:
        painter.end()
    return image


def page_pixmap(page: Page, px_per_mm: float = 2.2) -> QPixmap:
    return QPixmap.fromImage(page_image(page, px_per_mm))
