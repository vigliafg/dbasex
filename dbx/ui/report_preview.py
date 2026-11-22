"""Anteprima report in stile dBASE: pagina, navigazione, zoom, stampa e PDF (E7)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

from ..io.pdf_export import ExportError, export_pdf, page_pixmap, render_to_printer
from ..runtime.report_engine import ReportRenderer, ReportSpec
from ..runtime.rowset import Rowset, RowsetError
from . import icons


def build_pages(project, spec: ReportSpec):
    table = project.table(spec.table)
    if table is None:
        raise ValueError(f"Tabella del report inesistente: {spec.table}")
    try:
        rows = Rowset(project.db, table).open(where=spec.filter or "", order=spec.order or "").rows()
    except RowsetError as exc:
        raise ValueError(f"Filtro del report non valido: {exc}") from exc
    return ReportRenderer(spec, rows).layout()


class ReportPreviewDialog(QDialog):
    """Finestra Preview: pagina bianca, barra inferiore con navigazione e zoom."""

    def __init__(self, project, report, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        if isinstance(report, ReportSpec):
            self.spec = report
        else:
            artifact = project.artifact("reports", str(report))
            if artifact is None:
                raise ValueError(f"Report sconosciuto: {report}")
            self.spec = ReportSpec.from_dict(artifact)
        self.setWindowTitle(f"Preview — {self.spec.title or self.spec.name}")
        self.resize(940, 800)
        self.pages = []
        self.page_labels: list[QLabel] = []
        self.index = 0
        self.baseline = 3.6
        self.zoom = self.baseline
        self._fitted = False
        self._build_ui()
        self.reload()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        header = QHBoxLayout()
        self.info = QLabel("")
        header.addWidget(self.info, 1)
        layout.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.pages_layout = QVBoxLayout(self.container)
        self.pages_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        bar = QHBoxLayout()
        self.first_button = icons.make_button("", "primo", lambda: self.goto(0), self, "Prima pagina")
        self.prev_button = icons.make_button("", "precedente", lambda: self.goto(self.index - 1), self, "Pagina precedente")
        self.next_button = icons.make_button("", "successivo", lambda: self.goto(self.index + 1), self, "Pagina successiva")
        self.last_button = icons.make_button("", "ultimo", lambda: self.goto(len(self.pages) - 1), self, "Ultima pagina")
        for button in (self.first_button, self.prev_button, self.next_button, self.last_button):
            button.setToolTip(button.toolTip())
            bar.addWidget(button)
        self.page_label = QLabel("0 di 0")
        bar.addWidget(self.page_label)
        bar.addSpacing(12)
        bar.addWidget(icons.make_button("Riduci", "zoom_out", lambda: self.set_zoom(self.zoom / 1.25), self, "Riduci zoom"))
        self.zoom_label = QLabel("")
        bar.addWidget(self.zoom_label)
        bar.addWidget(icons.make_button("Aumenta", "zoom_in", lambda: self.set_zoom(self.zoom * 1.25), self, "Aumenta zoom"))
        bar.addStretch(1)
        bar.addWidget(icons.make_button("Stampa…", "stampa", self.print_pages, self))
        bar.addWidget(icons.make_button("Esporta PDF…", "esporta", self.save_pdf, self))
        bar.addWidget(icons.make_button("Chiudi", "chiudi", self.accept, self))
        layout.addLayout(bar)

    def showEvent(self, event) -> None:  # noqa: D102
        super().showEvent(event)
        if not self._fitted:
            self._fitted = True
            self._fit_width()

    def _fit_width(self) -> None:
        width_mm, _height_mm = self.spec.page_dimensions()
        available = max(200, self.scroll.viewport().width() - 40)
        self.zoom = max(0.8, min(6.0, available / max(1.0, width_mm)))
        self._render_pages()

    # ----------------------------------------------------------------- pagine
    def reload(self) -> None:
        while self.pages_layout.count():
            item = self.pages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.page_labels = []
        try:
            self.pages = build_pages(self.project, self.spec)
        except ValueError as exc:
            QMessageBox.warning(self, "Report non disponibile", str(exc))
            self.info.setText(str(exc))
            return
        for _page in self.pages:
            label = QLabel()
            label.setStyleSheet("background: #ffffff; border: 1px solid #b9bfb3; margin: 8px;")
            self.page_labels.append(label)
            self.pages_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.index = min(self.index, max(0, len(self.pages) - 1))
        self._render_pages()
        self.info.setText(f"{self.spec.title or self.spec.name} — {len(self.pages)} pagina" + ("e" if len(self.pages) != 1 else ""))

    def _render_pages(self) -> None:
        for label, page in zip(self.page_labels, self.pages):
            label.setPixmap(page_pixmap(page, self.zoom))
        self.zoom_label.setText(f"{int(round(self.zoom / self.baseline * 100))}%")
        self.page_label.setText(f"{self.index + 1 if self.pages else 0} di {len(self.pages)}")
        self.first_button.setEnabled(self.index > 0)
        self.prev_button.setEnabled(self.index > 0)
        self.next_button.setEnabled(self.index < len(self.pages) - 1)
        self.last_button.setEnabled(self.index < len(self.pages) - 1)

    def goto(self, index: int) -> None:
        if not self.pages:
            return
        self.index = max(0, min(index, len(self.pages) - 1))
        self._render_pages()
        self.scroll.ensureWidgetVisible(self.page_labels[self.index])

    def set_zoom(self, zoom: float) -> None:
        self.zoom = max(0.4, min(4.0, zoom))
        self._render_pages()

    # ------------------------------------------------------------------ azioni
    def print_pages(self) -> None:
        if not self.pages:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            render_to_printer(printer, self.pages)
        except ExportError as exc:
            QMessageBox.warning(self, "Stampa non riuscita", str(exc))

    def save_pdf(self) -> None:
        if not self.pages:
            return
        default = f"{self.spec.name or 'report'}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Esporta PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            export_pdf(self.pages, path, self.spec.title or self.spec.name)
        except ExportError as exc:
            QMessageBox.warning(self, "PDF non creato", str(exc))
            return
        self.info.setText(f"PDF salvato: {path}")
