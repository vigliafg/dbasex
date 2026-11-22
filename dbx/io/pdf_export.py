"""Rendering delle pagine di report: anteprima, stampa e PDF (E7)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QFont, QImage, QPageSize, QPainter, QPen, QPixmap
from PyQt6.QtPrintSupport import QPrinter

from ..runtime.report_engine import LINE_FACTOR, MM_PER_PT, Page


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
        if op.kind == "image" and op.text:
            pixmap = QPixmap(op.text)
            if not pixmap.isNull():
                painter.drawPixmap(rect, pixmap, QRectF(pixmap.rect()))
            continue
        font = QFont()
        font.setPixelSize(max(4, int(round(op.font_size * MM_PER_PT * scale))))
        font.setBold(op.bold)
        font.setItalic(op.italic)
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
