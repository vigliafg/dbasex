"""Scenari G/H — Report Designer, anteprima, Report Expert, etichette."""

from __future__ import annotations

from math import ceil
from unittest import mock

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent, QTextCursor
from PyQt6.QtWidgets import QDialog, QFileDialog
from PyQt6.QtPrintSupport import QPrintDialog

from dbx.core.label_model import LABEL_PRESETS, LabelSpec, default_template
from dbx.core.query_model import QueryAggregate, QueryField, QuerySpec
from dbx.designers.label_builder import LabelDesignerWidget, NewLabelDialog
from dbx.designers.report_builder import (
    ChartDialog,
    EditTextDialog,
    FieldDataDialog,
    GroupDialog,
    InsertFieldDialog,
    NewReportDialog,
    ReportDesignerWidget,
    SortOrderDialog,
    TotalDialog,
)
from dbx.designers.report_expert import ReportExpert
from dbx.runtime.label_engine import label_text, load_label_rows, render_labels_for_project
from dbx.runtime.report_engine import (
    BAND_NAMES,
    CHART_TYPES,
    CONTROL_KINDS,
    Control,
    ReportSpec,
    format_number,
)
from dbx.ui.label_preview import LabelPreviewDialog
from dbx.ui.report_preview import ReportPreviewDialog, build_pages

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _settled(ctx: E2EContext, name: str = "Report") -> object:
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


def _combo_index(combo, data) -> int:
    for index in range(combo.count()):
        if combo.itemData(index) == data:
            return index
    return -1


def _designer(ctx: E2EContext, project, spec: ReportSpec) -> ReportDesignerWidget:
    widget = ReportDesignerWidget(project, spec)
    return ctx.track(widget)


def _pages(project, spec: ReportSpec):
    return build_pages(project, spec)


def _text(pages) -> str:
    return "\n".join(op.text for page in pages for op in page.ops)


def _base_report(project, name: str = "report_clienti") -> ReportSpec:
    spec = ReportSpec.create(name, "clienti", "Clienti")
    spec.bands["detail"] = [
        Control(id="nome", kind="field", x=0, y=0, w=45, h=6, expr="nome"),
        Control(id="citta", kind="field", x=45, y=0, w=45, h=6, expr="citta"),
        Control(id="saldo", kind="field", x=90, y=0, w=45, h=6, expr="saldo", align="right"),
    ]
    return spec


@scenario(
    "rep-01-new",
    "G01 — Nuovo report da tabella o query con filtro",
    "reports",
    features=("REP-NEW", "REP-SOURCE-TABLE", "REP-SOURCE-QUERY", "REP-FILTER"),
    min_checks=11,
    budget_s=10.0,
)
def rep_new(ctx: E2EContext) -> None:
    project = _settled(ctx, "NuovoReport")
    dialog = NewReportDialog(project, suggested_name="report_clienti")
    ctx.track(dialog)
    ctx.check_close(dialog.source_combo.count(), 2, "due tabelle disponibili")
    dialog.name_edit.setText("report_clienti")
    dialog.title_edit.setText("Elenco clienti")
    dialog.source_combo.setCurrentIndex(_combo_index(dialog.source_combo, ("table", "clienti")))
    spec = dialog.spec()
    ctx.check_close(spec.source_type, "table", "sorgente tabella")
    ctx.check_close(spec.table, "clienti", "tabella scelta")
    ctx.check_close(spec.title, "Elenco clienti", "titolo")
    ctx.check(spec.validate() == [], "report valido")
    ctx.check_close(spec.bands["detail"][0].expr, "codice", "primo campo di dettaglio")

    query = QuerySpec(name="clienti_roma", base="clienti", fields=[QueryField("clienti", "codice"), QueryField("clienti", "nome")], filters=[])
    project.put_object("queries", query.to_dict())
    project.save()
    query_report = NewReportDialog(project, suggested_name="report_query")
    ctx.track(query_report)
    ctx.check_close(query_report.source_combo.count(), 3, "query nella sorgente")
    query_report.source_combo.setCurrentIndex(_combo_index(query_report.source_combo, ("query", "clienti_roma")))
    query_spec = query_report.spec()
    ctx.check_close(query_spec.source_type, "query", "sorgente query")
    ctx.check_close(query_spec.query, "clienti_roma", "query scelta")
    ctx.check_close(query_spec.bands["detail"][0].expr, "codice", "colonna della query")

    designer = _designer(ctx, project, spec)
    designer.filter_edit.setText('"citta" = \'Roma\'')
    designer.order_edit.setText("nome DESC")
    designer._apply_header()
    ctx.check_close(designer.spec.filter, '"citta" = \'Roma\'', "filtro impostato")
    ctx.check_close(designer.spec.order, "nome DESC", "ordine impostato")
    ctx.check(designer.save(), "report salvato")
    reopened = ctx.reopen(project)
    stored = ReportSpec.from_dict(reopened.artifact("reports", "report_clienti"))
    ctx.check_close(stored.filter, '"citta" = \'Roma\'', "filtro persistito")
    ctx.check_close(stored.order, "nome DESC", "ordine persistito")


@scenario(
    "rep-02-bands",
    "G02 — Sette bande: visibilità, ordine, altezze e delimitatori",
    "reports",
    features=(
        "REP-BANDS-VISIBLE",
        "REP-BANDS-ORDER",
        "REP-BANDS-HEIGHT",
        "REP-BANDS-DRAG",
        "REP-BAND-TITLE",
        "REP-BAND-PAGE_HEADER",
        "REP-BAND-GROUP_HEADER",
        "REP-BAND-DETAIL",
        "REP-BAND-GROUP_FOOTER",
        "REP-BAND-PAGE_FOOTER",
        "REP-BAND-SUMMARY",
    ),
    min_checks=12,
    budget_s=10.0,
)
def rep_bands(ctx: E2EContext) -> None:
    project = _settled(ctx, "BandeReport")
    spec = _base_report(project)
    ctx.check_close(spec.effective_band_order(), list(BAND_NAMES), "sette bande")
    designer = _designer(ctx, project, spec)
    ctx.check_close(len(designer.canvas.band_tops()), 7, "sette delimitatori")
    designer.set_band_visible("summary", False)
    ctx.check(not designer.spec.is_visible("summary"), "summary nascosta")
    ctx.check(not designer.canvas.band_height("summary") > 0 or not designer.spec.is_visible("summary"), "banda nascosta")
    designer.show_all_bands()
    ctx.check(designer.spec.is_visible("summary"), "tutte le bande visibili")

    designer.spec.band_heights.update({"title": 20.0, "page_header": 10.0, "detail": 12.0, "page_footer": 8.0})
    designer.canvas.load(designer.spec)
    ctx.check_close(designer.canvas.band_height("title"), 20.0, "altezza titolo")
    ctx.check_close(designer.canvas.band_height("detail"), 12.0, "altezza dettaglio")
    tops = [name for name, _top, _height in designer.canvas.band_tops()]
    ctx.check_close(tops, list(designer.spec.effective_band_order()), "ordine sul foglio")

    designer.spec.band_order = ["summary", "title", "page_header", "group_header", "detail", "group_footer", "page_footer"]
    designer.canvas.load(designer.spec)
    ctx.check_close(designer.spec.effective_band_order()[0], "summary", "ordine personalizzato")
    ctx.check_close(designer.canvas.band_at(designer.canvas.band_tops()[0][1] + 1), "summary", "banda in cima")

    top = dict((name, top) for name, top, _height in designer.canvas.band_tops())["detail"]
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(4, top),
        QPointF(4, top),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(4, top + 40),
        QPointF(4, top + 40),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    before = designer.canvas.band_height("detail")
    designer.canvas.mousePressEvent(press)
    designer.canvas.mouseMoveEvent(move)
    designer.canvas.mouseReleaseEvent(move)
    ctx.check(designer.canvas.band_height("detail") > before, "delimitatore trascinato")
    ctx.check(designer.bands_menu.actions(), "menu delle bande")


@scenario(
    "rep-03-insert-field",
    "G03 — Insert Database Field e anteprima dati",
    "reports",
    features=("REP-INSERT-FIELD", "REP-FIELD-PREVIEW", "REP-CONTROL-FIELD", "REP-CONTROL-TEXT", "REP-CONTROL-LINE", "REP-CONTROL-RECT", "REP-CONTROL-IMAGE"),
    min_checks=9,
    budget_s=8.0,
)
def rep_insert_field(ctx: E2EContext) -> None:
    project = _settled(ctx, "CampoReport")
    dialog = InsertFieldDialog(project, "clienti")
    ctx.track(dialog)
    ctx.check_close(dialog.list.count(), 8, "campi disponibili")
    ctx.check(dialog.list.item(0).text().startswith("clienti->"), "formato TABELLA->CAMPO")
    dialog.list.setCurrentRow(1)
    ctx.check_close(dialog.selected_field(), "nome", "campo selezionato")
    data = FieldDataDialog(project, "clienti", "nome")
    ctx.track(data)
    ctx.check(data.list.count() >= 2, "valori distinti")
    ctx.check("Alfa Srl" in [data.list.item(i).text() for i in range(data.list.count())], "valore di anteprima")

    designer = _designer(ctx, project, _base_report(project))
    designer._insert("detail", Control(id="nome2", kind="field", x=0, y=10, w=60, h=6, expr="nome"))
    ctx.check_close(designer.spec.bands["detail"][-1].expr, "nome", "campo inserito")
    designer._insert("page_footer", Control(id="linea", kind="line", x=0, y=0, w=170, h=1))
    designer._insert("page_footer", Control(id="riquadro", kind="rect", x=0, y=2, w=40, h=8))
    designer._insert("page_header", Control(id="immagine", kind="image", x=140, y=0, w=20, h=10, text=""))
    kinds = {control.kind for controls in designer.spec.bands.values() for control in controls}
    ctx.check("field" in kinds and "line" in kinds and "rect" in kinds and "image" in kinds, "controlli statici")
    pages = _pages(project, designer.spec)
    ctx.check("Alfa Srl" in _text(pages), "anteprima dati nel report")
    ctx.check_close(designer.spec.bands["detail"][0].kind, "field", "dettaglio dalla tabella")


@scenario(
    "rep-04-edit-text",
    "G04 — Edit Text, stile ed espressioni",
    "reports",
    features=("REP-EDIT-TEXT", "REP-EXPRESSION", "REP-CONTROL-EXPR", "REP-FORMAT-BORDER", "REP-FORMAT-ALIGN", "REP-FORMAT-FONT"),
    min_checks=6,
    budget_s=8.0,
)
def rep_edit_text(ctx: E2EContext) -> None:
    project = _settled(ctx, "TestoReport")
    spec = _base_report(project)
    designer = _designer(ctx, project, spec)
    title = spec.bands["title"][0]
    dialog = EditTextDialog(title)
    ctx.track(dialog)
    dialog.text_edit.setPlainText("Clienti 2026")
    dialog.size_spin.setValue(18)
    dialog.border_check.setChecked(True)
    dialog.align_combo.setCurrentIndex(dialog.align_combo.findData("center"))
    dialog.apply_to(title)
    ctx.check_close(title.text, "Clienti 2026", "testo modificato")
    ctx.check_close(title.font_size, 18, "corpo del testo")
    ctx.check(title.border and title.align == "center", "bordo e allineamento")
    ctx.check_close(title.kind, "text", "tipo testo")

    expr = Control(id="upper", kind="expr", x=0, y=20, w=80, h=6, expr="UPPER([nome])")
    spec.bands["detail"].append(expr)
    pages = _pages(project, spec)
    ctx.check("ALFA SRL" in _text(pages), "espressione calcolata")
    ctx.check(any(op.kind == "expr" and "ALFA" in op.text for page in pages for op in page.ops), "controllo espressione")


@scenario(
    "rep-05-sort",
    "G05 — Record Sort Order",
    "reports",
    features=("REP-SORT",),
    min_checks=8,
    budget_s=8.0,
)
def rep_sort(ctx: E2EContext) -> None:
    project = _settled(ctx, "OrdineReport")
    dialog = SortOrderDialog(project, "clienti", [])
    ctx.track(dialog)
    ctx.check(dialog.available.count() >= 6, "campi disponibili")
    dialog.direction.setCurrentIndex(dialog.direction.findData("desc"))
    for row in range(dialog.available.count()):
        if dialog.available.item(row).data(Qt.ItemDataRole.UserRole) == "citta":
            dialog.available.setCurrentRow(row)
    dialog.add_selected()
    ctx.check_close(len(dialog.sort_fields()), 1, "primo criterio")
    for row in range(dialog.available.count()):
        if dialog.available.item(row).data(Qt.ItemDataRole.UserRole) == "nome":
            dialog.available.setCurrentRow(row)
    dialog.add_selected()
    ctx.check_close(len(dialog.sort_fields()), 2, "secondo criterio")
    dialog.sorted.setCurrentRow(1)
    dialog.direction.setCurrentIndex(dialog.direction.findData("asc"))
    dialog.move_entry(-1)
    ctx.check_close(dialog.sort_fields()[0]["field"], "nome", "criterio spostato")
    fields = dialog.sort_fields()
    ctx.check_close(fields[0]["direction"], "asc", "direzione ascendente")
    ctx.check_close(fields[1]["direction"], "desc", "direzione discendente")

    spec = _base_report(project, "ordinato")
    spec.sort_fields = fields
    pages = _pages(project, spec)
    names = [
        op.text
        for page in pages
        for op in page.ops
        if op.kind == "field" and op.text and abs(op.x - (15.0 + 0.0)) < 0.1
    ]
    ctx.check_close(names[:3], ["Alfa Srl", "Beta Studio", "Delta Spa"], "ordine nel report")
    dialog.sorted.setCurrentRow(0)
    dialog.remove_selected()
    ctx.check_close(len(dialog.sort_fields()), 1, "criterio rimosso")


@scenario(
    "rep-06-groups-totals",
    "G06 — Gruppi header/footer e cinque funzioni totale",
    "reports",
    features=(
        "REP-GROUP",
        "REP-TOTAL-SUM",
        "REP-TOTAL-COUNT",
        "REP-TOTAL-AVG",
        "REP-TOTAL-MIN",
        "REP-TOTAL-MAX",
        "REP-CONTROL-TOTAL",
    ),
    min_checks=12,
    budget_s=10.0,
)
def rep_groups_totals(ctx: E2EContext) -> None:
    project = _settled(ctx, "GruppiReport")
    spec = _base_report(project, "gruppi")
    group_dialog = GroupDialog(project, "clienti")
    ctx.track(group_dialog)
    group_dialog.field_combo.setCurrentIndex(group_dialog.field_combo.findData("citta"))
    group_dialog.label_edit.setText("Città")
    group = group_dialog.group()
    ctx.check_close(group["field"], "citta", "campo gruppo")
    spec.groups = [group]
    spec.group_by = "citta"
    spec.group_label = "Città"
    spec.band_visible["group_header"] = True
    spec.band_visible["group_footer"] = True
    spec.bands["group_header"] = [
        Control(id="testata_gruppo", kind="text", x=0, y=0, w=80, h=6, text="Città: [citta]", bold=True)
    ]
    spec.sort_fields = [{"field": "citta", "direction": "asc"}]
    expected = {"sum": "1.700,50", "count": "2", "avg": "850,25", "min": "500", "max": "1.200,50"}
    for function in ("sum", "count", "avg", "min", "max"):
        dialog = TotalDialog(project, "clienti")
        ctx.track(dialog)
        dialog.field_combo.setCurrentIndex(dialog.field_combo.findData("saldo"))
        dialog.func_combo.setCurrentIndex(dialog.func_combo.findData(function))
        dialog.band_combo.setCurrentIndex(dialog.band_combo.findData("group_footer"))
        dialog.label_edit.setText(f"{function}: ")
        band, control = dialog.control()
        ctx.check_close(band, "group_footer", f"{function}: banda")
        ctx.check_close(control.func, function, f"{function}: funzione")
        spec.bands["group_footer"].append(control)
    pages = _pages(project, spec)
    text = _text(pages)
    ctx.check("Città: Roma" in text, "intestazione gruppo")
    for function, value in expected.items():
        ctx.check(f"{function}: {value}" in text, f"totale {function}")
    ctx.check(text.count("Città: Roma") == 1, "gruppo Roma una volta")
    ctx.check("Città: Milano" in text, "secondo gruppo")


@scenario(
    "rep-07-charts",
    "G07 — Grafici barre, linee e torta",
    "reports",
    features=(
        "REP-CHART-BAR",
        "REP-CHART-LINE",
        "REP-CHART-PIE",
        "REP-CHART-CATEGORY",
        "REP-CHART-VALUE",
        "REP-CHART-BAND",
        "REP-CONTROL-CHART",
    ),
    min_checks=11,
    budget_s=10.0,
)
def rep_charts(ctx: E2EContext) -> None:
    project = _settled(ctx, "GraficiReport")
    spec = _base_report(project, "grafici")
    spec.groups = [{"field": "citta", "label": "Città"}]
    spec.group_by = "citta"
    spec.band_visible["summary"] = True
    for chart_type in CHART_TYPES:
        dialog = ChartDialog(project, "clienti", spec.effective_groups())
        ctx.track(dialog)
        dialog.type_combo.setCurrentIndex(dialog.type_combo.findData(chart_type))
        dialog.title_edit.setText(f"Saldo per città ({chart_type})")
        dialog.category_combo.setCurrentIndex(dialog.category_combo.findData("citta"))
        dialog.value_combo.setCurrentIndex(dialog.value_combo.findData("saldo"))
        dialog.func_combo.setCurrentIndex(dialog.func_combo.findData("sum"))
        dialog.band_combo.setCurrentIndex(dialog.band_combo.findData("summary"))
        band, control = dialog.control()
        ctx.check_close(control.chart_type, chart_type, f"{chart_type}: tipo")
        ctx.check_close(control.category, "[citta]", f"{chart_type}: categoria")
        ctx.check_close(control.expr, "[saldo]", f"{chart_type}: valore")
        ctx.check_close(band, "summary", f"{chart_type}: banda")
        spec.bands["summary"].append(control)
    pages = _pages(project, spec)
    charts = [op for page in pages for op in page.ops if op.kind == "chart"]
    ctx.check_close(len(charts), 3, "tre grafici")
    series = charts[0].series
    values = dict(series)
    ctx.check_close(values["Roma"], 1700.5, "somma Roma")
    ctx.check_close(values["Milano"], 0.0, "somma Milano")
    ctx.check_close(charts[2].chart_type, "pie", "torta")


@scenario(
    "rep-08-format",
    "G08 — Toolbar di formattazione e zoom",
    "reports",
    features=(
        "REP-FORMAT-FONT",
        "REP-FORMAT-STYLE",
        "REP-FORMAT-ALIGN",
        "REP-FORMAT-BORDER",
        "REP-FORMAT-COLOR",
        "REP-ALIGN-CONTROL",
        "REP-ZOOM",
    ),
    min_checks=12,
    budget_s=8.0,
    screenshots=("report-designer",),
)
def rep_format(ctx: E2EContext) -> None:
    project = _settled(ctx, "FormatoReport")
    spec = _base_report(project, "formato")
    designer = _designer(ctx, project, spec)
    control = spec.bands["detail"][0]
    designer.selected_id = control.id
    designer.canvas.selected = control.id
    designer.apply_format("font_name", "Courier New")
    designer.apply_format("font_size", 12)
    designer.toggle_format("bold")
    designer.toggle_format("italic")
    designer.toggle_format("underline")
    designer.apply_format("align", "center")
    designer.toggle_format("border")
    designer.apply_format("color", "#ff0000")
    ctx.check_close(control.font_name, "Courier New", "font")
    ctx.check_close(control.font_size, 12, "corpo")
    ctx.check(control.bold and control.italic and control.underline, "stili")
    ctx.check_close(control.align, "center", "allineamento")
    ctx.check(control.border, "bordo")
    ctx.check_close(control.color, "#ff0000", "colore")
    designer.toggle_format("bold")
    ctx.check(not control.bold, "grassetto tolto")

    designer.align_control("left")
    ctx.check_close(control.x, 0.0, "allinea a sinistra")
    designer.align_control("center")
    ctx.check_close(control.x, (180.0 - control.w) / 2, "centra nella banda")
    designer.align_control("right")
    ctx.check_close(control.x + control.w, 180.0, "allinea a destra")
    designer.align_control("top")
    ctx.check_close(control.y, 0.0, "allinea in alto")

    designer.zoom_combo.setCurrentIndex(designer.zoom_combo.findData(150))
    ctx.check_close(designer.canvas.zoom_factor, 1.5, "zoom 150%")
    ctx.check("Zoom 150%" in designer.status_label.text(), "stato zoom")
    designer.zoom_combo.setCurrentIndex(designer.zoom_combo.findData(50))
    ctx.check_close(designer.canvas.zoom_factor, 0.5, "zoom 50%")
    ctx.capture(designer, "report-designer", (1180, 800))


@scenario(
    "rep-09-preview",
    "G09 — Anteprima: pagine, una pagina, fit e zoom",
    "reports",
    features=("REP-PREVIEW-PAGES", "REP-PREVIEW-SINGLE", "REP-PREVIEW-FIT", "REP-PREVIEW-ZOOM"),
    min_checks=9,
    budget_s=10.0,
    screenshots=("report-preview",),
)
def rep_preview(ctx: E2EContext) -> None:
    project = _settled(ctx, "AnteprimaReport")
    spec = _base_report(project, "anteprima")
    spec.band_heights["detail"] = 240.0
    pages = _pages(project, spec)
    ctx.check(len(pages) > 1, "report multi-pagina")
    dialog = ReportPreviewDialog(project, spec)
    ctx.track(dialog)
    with ctx.quiet_qt():
        dialog.show()
        ctx.qapp.processEvents()
    ctx.check_close(len(dialog.pages), len(pages), "pagine in anteprima")
    ctx.check_close(dialog.page_label.text(), f"1 di {len(pages)}", "pagina iniziale")
    dialog.goto(len(pages) - 1)
    ctx.check_close(dialog.index, len(pages) - 1, "ultima pagina")
    dialog.goto(0)
    dialog.single_button.setChecked(True)
    dialog.toggle_single_page()
    ctx.check(dialog.single_button.isChecked(), "una pagina per volta")
    ctx.check(dialog.page_labels[1].isVisible() is False, "pagine successive nascoste")
    dialog.set_zoom(2.0)
    ctx.check_close(dialog.zoom, 2.0, "zoom impostato")
    dialog._fit_width()
    ctx.check(0.8 <= dialog.zoom <= 6.0, "fit width")
    second = ReportPreviewDialog(project, spec)
    ctx.track(second)
    ctx.check_close(second.zoom, dialog.zoom, "zoom persistente")
    ctx.capture(dialog, "report-preview", (940, 800))


@scenario(
    "rep-10-print-pdf",
    "G10 — Stampa mock e PDF multi-pagina",
    "reports",
    features=("REP-PRINT", "REP-PDF"),
    min_checks=5,
    budget_s=10.0,
)
def rep_print_pdf(ctx: E2EContext) -> None:
    project = _settled(ctx, "StampaReport")
    spec = _base_report(project, "stampa")
    spec.band_heights["detail"] = 200.0
    dialog = ReportPreviewDialog(project, spec)
    ctx.track(dialog)
    ctx.check(len(dialog.pages) > 1, "più pagine da stampare")
    pdf_path = ctx.work / "report.pdf"
    with mock.patch.object(QFileDialog, "getSaveFileName", lambda *a, **k: (str(pdf_path), "")):
        dialog.save_pdf()
    ctx.check(pdf_path.exists() and pdf_path.stat().st_size > 1000, "PDF creato")
    ctx.check("PDF salvato" in dialog.info.text(), "esito PDF")
    with mock.patch.object(QPrintDialog, "exec", return_value=QDialog.DialogCode.Accepted), mock.patch(
        "dbx.ui.report_preview.render_to_printer"
    ) as render:
        dialog.print_pages()
    ctx.check(render.called, "stampa invocata")
    ctx.check(render.call_args[0][1] == dialog.pages, "pagine stampate")


@scenario(
    "rep-11-query",
    "G11 — Report su query: colonne, gruppi, totali e filtro",
    "reports",
    features=("REP-QUERY", "REP-SOURCE-QUERY", "REP-GROUP", "REP-TOTAL-SUM"),
    min_checks=7,
    budget_s=10.0,
)
def rep_query(ctx: E2EContext) -> None:
    project = _settled(ctx, "ReportQuery")
    query = QuerySpec(
        name="fatture_clienti",
        base="fatture",
        fields=[QueryField("fatture", "cliente"), QueryField("clienti", "nome"), QueryField("fatture", "importo")],
        joins=[],
        filters=[],
    )
    from dbx.core.query_model import QueryJoin

    query.joins = [QueryJoin("inner", "clienti", "fatture.cliente", "clienti.codice")]
    project.put_object("queries", query.to_dict())
    project.save()
    spec = ReportSpec.create_for_query("report_query", "fatture_clienti", ["nome", "importo"], "Fatture per cliente")
    spec.bands["detail"] = [
        Control(id="cliente", kind="field", x=0, y=0, w=80, h=6, expr="nome"),
        Control(id="importo", kind="field", x=120, y=0, w=50, h=6, expr="importo", align="right"),
    ]
    spec.groups = [{"field": "nome", "label": "Cliente"}]
    spec.band_visible["group_header"] = True
    spec.band_visible["group_footer"] = True
    spec.bands["group_header"] = [Control(id="testata", kind="text", x=0, y=0, w=80, h=6, text="Cliente: [nome]", bold=True)]
    spec.bands["group_footer"] = [
        Control(id="totale", kind="total", x=120, y=0, w=50, h=6, expr="[importo]", func="sum", label="Totale: ", align="right")
    ]
    spec.filter = "[importo] >= 200"
    spec.order = "importo desc"
    ctx.check(spec.validate() == [], "report su query valido")
    pages = _pages(project, spec)
    text = _text(pages)
    ctx.check("Cliente: Alfa Srl" in text, "gruppo dalla query")
    ctx.check("Totale: 200" in text, "totale dal filtro")
    ctx.check("300" in text, "importo del secondo cliente")
    ctx.check("100" not in text, "filtro applicato ai record")
    ctx.check_close(spec.source_type, "query", "sorgente query")
    ctx.check_close(spec.query, "fatture_clienti", "query collegata")


@scenario(
    "rep-12-round-trip",
    "G12 — Round-trip report e JSON legacy",
    "reports",
    features=("REP-ROUNDTRIP", "REP-LEGACY"),
    min_checks=9,
    budget_s=8.0,
)
def rep_round_trip(ctx: E2EContext) -> None:
    project = _settled(ctx, "RoundTripReport")
    spec = _base_report(project, "round_report")
    spec.groups = [{"field": "citta", "label": "Città"}]
    spec.band_visible["group_header"] = True
    spec.bands["group_header"] = [Control(id="g", kind="text", x=0, y=0, w=80, h=6, text="[citta]")]
    designer = _designer(ctx, project, spec)
    ctx.check(designer.save(), "report salvato")
    reopened = ctx.reopen(project)
    stored = ReportSpec.from_dict(reopened.artifact("reports", "round_report"))
    ctx.check_close(stored.to_dict(), spec.to_dict(), "JSON identico")
    second = _designer(ctx, reopened, stored)
    ctx.check_close(second.spec.groups[0]["field"], "citta", "gruppo riaperto")
    ctx.check_close(len(second.spec.bands["detail"]), 3, "dettaglio riaperto")

    legacy = {
        "name": "legacy_report",
        "title": "Legacy",
        "table": "clienti",
        "bands": {"detail": [{"id": "d", "kind": "field", "expr": "nome"}]},
    }
    old = ReportSpec.from_dict(legacy)
    ctx.check_close(old.source_type, "table", "sorgente legacy")
    ctx.check_close(old.page_size, "A4", "formato predefinito")
    ctx.check_close(old.band_order, [], "ordine predefinito")
    ctx.check_close(old.effective_band_order(), list(BAND_NAMES), "bande completate")
    ctx.check(old.validate() == [], "report legacy valido")
    reopened.put_object("reports", old.to_dict())
    reopened.save()
    again = ctx.reopen(reopened)
    restored = ReportSpec.from_dict(again.artifact("reports", "legacy_report"))
    ctx.check_close(restored.bands["detail"][0].expr, "nome", "campo legacy persistito")


@scenario(
    "rep-13-expert",
    "G13 — Report Expert: layout, gruppi e risultato",
    "reports",
    features=("REP-EXPERT", "REP-EXPERT-LAYOUTS", "REP-EXPERT-GROUP", "REP-EXPERT-SORT"),
    min_checks=13,
    budget_s=10.0,
)
def rep_expert(ctx: E2EContext) -> None:
    project = _settled(ctx, "ReportExpert")
    expert = ReportExpert(project, suggested_name="clienti_expert")
    ctx.track(expert)
    expert.name_edit.setText("clienti_expert")
    expert.title_edit.setText("Clienti per città")
    expert.source_combo.setCurrentIndex(_combo_index(expert.source_combo, ("table", "clienti")))
    expert.orientation_combo.setCurrentIndex(expert.orientation_combo.findData("landscape"))
    expert.font_spin.setValue(11)
    tabular = expert.build_spec()
    ctx.check_close(tabular.orientation, "landscape", "orientamento")
    ctx.check(tabular.validate() == [], "layout tabellare valido")
    ctx.check(len(tabular.bands["detail"]) >= 2, "dettaglio tabellare")

    expert.layout_radios["columnar"].setChecked(True)
    columnar = expert.build_spec()
    ctx.check(any(control.kind == "text" and control.text for control in columnar.bands["detail"]), "etichette colonnari")
    ctx.check_close(len(columnar.bands["detail"]), 2 * len(expert.field_transfer.selected_keys()), "due controlli per campo")

    expert.group_combo.setCurrentIndex(expert.group_combo.findData("citta"))
    expert.group_label_edit.setText("Città")
    expert.add_sort()
    sort_field = expert.sort_table.cellWidget(0, 0)
    sort_field.setCurrentIndex(sort_field.findData("nome"))
    expert.sort_table.cellWidget(0, 1).setCurrentIndex(1)
    expert.layout_radios["summary"].setChecked(True)
    summary = expert.build_spec()
    ctx.check_close(summary.groups[0]["field"], "citta", "gruppo esperto")
    ctx.check_close(summary.group_label, "Città", "etichetta gruppo")
    ctx.check(summary.bands["group_header"], "intestazione gruppo")
    ctx.check(any(c.kind == "total" for c in summary.bands["group_footer"]), "totale gruppo")
    ctx.check(summary.is_visible("page_footer"), "numero di pagina")
    ctx.check_close(summary.sort_fields[-1]["direction"], "desc", "ordinamento esperto")
    pages = build_pages(project, summary)
    text = _text(pages)
    ctx.check("Clienti per città" in text or "Città: Roma" in text, "report esperto renderizzato")
    project.put_object("reports", summary.to_dict())
    project.save()
    reopened = ctx.reopen(project)
    ctx.check(ReportSpec.from_dict(reopened.artifact("reports", "clienti_expert")).groups, "report esperto persistito")


# --------------------------------------------------------------------------- #
# Etichette
# --------------------------------------------------------------------------- #
def _label_spec(project, name: str = "etichette_clienti") -> LabelSpec:
    table = project.require_table("clienti")
    spec = LabelSpec.create(name, "clienti", [field.name for field in table.fields], title="Etichette clienti")
    spec.template = "[codice] [nome]\n[citta]"
    return spec


@scenario(
    "lbl-01-presets",
    "H01 — Quattro preset, formato personalizzato, griglia e margini",
    "labels",
    features=(
        "LBL-NEW",
        "LBL-PRESET",
        "LBL-CUSTOM",
        "LBL-GRID",
        "LBL-MARGINS",
        "LBL-PRESET-A4_70X37",
        "LBL-PRESET-AVERY5160",
        "LBL-PRESET-AVERY5163",
        "LBL-PRESET-A4_52X30",
    ),
    min_checks=12,
    budget_s=10.0,
    screenshots=("label-designer",),
)
def lbl_presets(ctx: E2EContext) -> None:
    project = _settled(ctx, "PresetEtichette")
    dialog = NewLabelDialog(project, suggested_name="etichette_clienti")
    ctx.track(dialog)
    ctx.check_close(dialog.preset_combo.count(), 4, "quattro preset")
    dialog.name_edit.setText("etichette_clienti")
    for key, data in LABEL_PRESETS.items():
        dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData(key))
        spec = dialog.spec()
        ctx.check_close(spec.label_width, data["label_width"], f"{key}: larghezza")
        ctx.check_close(spec.columns, data["columns"], f"{key}: colonne")
        ctx.check(spec.validate() == [], f"{key}: valido")
        ctx.check_close(spec.preset_key(), key, f"{key}: riconosciuto")
    dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData("a4_52x30"))
    spec = dialog.spec()
    designer = ctx.track(LabelDesignerWidget(project, spec))
    ctx.check_close(designer.columns_spin.value(), 4, "griglia del preset")
    designer.columns_spin.setValue(3)
    designer.rows_spin.setValue(6)
    designer.width_spin.setValue(60.0)
    designer.height_spin.setValue(35.0)
    designer.margin_left_spin.setValue(5.0)
    designer.margin_top_spin.setValue(6.0)
    designer.gutter_x_spin.setValue(2.0)
    designer.gutter_y_spin.setValue(1.5)
    designer._collect()
    ctx.check_close(designer.spec.columns, 3, "colonne personalizzate")
    ctx.check_close(designer.spec.rows, 6, "righe personalizzate")
    ctx.check_close(designer.spec.margin("left"), 5.0, "margine sinistro")
    ctx.check_close(designer.spec.gutter_y, 1.5, "distanza verticale")
    ctx.check_close(designer.spec.preset_key(), "", "formato personalizzato")
    ctx.check(designer.spec.validate() == [], "formato personalizzato valido")
    ctx.check("5 record" in designer.status_label.text(), "conteggio record")
    ctx.capture(designer, "label-designer", (1060, 680))


@scenario(
    "lbl-02-template",
    "H02 — Modello [campo], {{espressione}}, stile e inserimento",
    "labels",
    features=(
        "LBL-TEMPLATE-FIELD",
        "LBL-TEMPLATE-EXPR",
        "LBL-FIELD-INSERT",
        "LBL-STYLE",
        "LBL-ALIGN-LEFT",
        "LBL-ALIGN-CENTER",
        "LBL-ALIGN-RIGHT",
    ),
    min_checks=10,
    budget_s=8.0,
)
def lbl_template(ctx: E2EContext) -> None:
    project = _settled(ctx, "ModelloEtichette")
    spec = _label_spec(project)
    record = next(row for row in load_label_rows(project, spec) if row["codice"] == "C001")
    spec.template = "[nome]\n{{[saldo] * 2}}"
    ctx.check_close(label_text(spec, record), "Alfa Srl\n2.401", "campo ed espressione")
    ctx.check_close(default_template(["nome", "citta"]), "[nome]\n[citta]", "modello predefinito")

    designer = ctx.track(LabelDesignerWidget(project, spec))
    ctx.check(designer.fields_list.count() >= 6, "campi disponibili")
    for row in range(designer.fields_list.count()):
        if designer.fields_list.item(row).data(Qt.ItemDataRole.UserRole) == "codice":
            designer.fields_list.setCurrentRow(row)
    designer.template_edit.moveCursor(QTextCursor.MoveOperation.End)
    designer.insert_field()
    ctx.check("[codice]" in designer.template_edit.toPlainText(), "campo inserito nel modello")
    designer.align_combo.setCurrentIndex(designer.align_combo.findData("center"))
    designer.font_spin.setValue(12)
    designer.bold_check.setChecked(True)
    designer.border_check.setChecked(True)
    designer._collect()
    ctx.check_close(designer.spec.align, "center", "allineamento")
    ctx.check(designer.spec.bold and designer.spec.border, "stile")
    pages = render_labels_for_project(project, designer.spec)
    op = next(op for page in pages for op in page.ops if op.kind == "text")
    ctx.check_close(op.align, "center", "allineamento reso")
    ctx.check(op.bold, "grassetto reso")
    ctx.check(any(op.kind == "rect" for page in pages for op in page.ops), "bordo reso")
    for align in ("left", "center", "right"):
        designer.align_combo.setCurrentIndex(designer.align_combo.findData(align))
        designer._collect()
        ctx.check_close(designer.spec.align, align, f"allineamento {align}")


@scenario(
    "lbl-03-filter-order",
    "H03 — Filtro, ordinamento e selezione dei record",
    "labels",
    features=("LBL-FILTER", "LBL-ORDER", "LBL-SELECTION"),
    min_checks=6,
    budget_s=8.0,
)
def lbl_filter_order(ctx: E2EContext) -> None:
    project = _settled(ctx, "FiltroEtichette")
    spec = _label_spec(project)
    spec.template = "[codice] [nome]"
    spec.filter = '"citta" = \'Roma\''
    spec.order = "nome desc"
    rows = load_label_rows(project, spec)
    ctx.check_close(len(rows), 2, "due clienti di Roma")
    texts = [label_text(spec, row) for row in rows]
    ctx.check_close(texts, ["C004 Delta Spa", "C001 Alfa Srl"], "ordine discendente")
    designer = ctx.track(LabelDesignerWidget(project, spec))
    designer._collect()
    ctx.check("2 record" in designer.status_label.text(), "conteggio filtrato")
    designer.filter_edit.setText('"citta" = \'Milano\'')
    designer.order_edit.setText("nome")
    designer._collect()
    ctx.check_close(designer.spec.filter, '"citta" = \'Milano\'', "filtro aggiornato")
    rows = load_label_rows(project, designer.spec)
    ctx.check_close(len(rows), 1, "un cliente di Milano")
    ctx.check_close(label_text(designer.spec, rows[0]), "C002 Beta Studio", "record selezionato")


@scenario(
    "lbl-04-offset-pages",
    "H04 — Salto etichette, pagine e anteprima",
    "labels",
    features=("LBL-OFFSET", "LBL-PAGES", "LBL-PREVIEW"),
    min_checks=8,
    budget_s=8.0,
    screenshots=("label-preview",),
)
def lbl_offset_pages(ctx: E2EContext) -> None:
    project = _settled(ctx, "PagineEtichette")
    spec = _label_spec(project)
    spec.start_offset = 20
    pages = render_labels_for_project(project, spec)
    ctx.check_close(len(pages), 2, "due fogli con salto")
    ctx.check_close(len(pages[0].ops), 4, "quattro etichette sul primo foglio")
    ctx.check_close(len(pages[1].ops), 1, "una etichetta sul secondo")
    first = pages[0].ops[0]
    ctx.check_close(first.x, spec.margin("left") + 2 * (spec.label_width + spec.gutter_x) + spec.padding, "colonna del salto")
    expected_pages = ceil((spec.start_offset + 5) / spec.labels_per_page)
    ctx.check_close(expected_pages, 2, "pagine calcolate")
    dialog = LabelPreviewDialog(project, spec)
    ctx.track(dialog)
    ctx.check_close(len(dialog.pages), 2, "anteprima multi-foglio")
    ctx.check("2 pagine" in dialog.info.text(), "riepilogo etichette")
    dialog.goto(1)
    ctx.check_close(dialog.index, 1, "navigazione foglio")
    dialog.set_zoom(1.5)
    ctx.check_close(dialog.zoom, 1.5, "zoom etichette")
    ctx.capture(dialog, "label-preview", (940, 800))


@scenario(
    "lbl-05-pdf-save",
    "H05 — PDF delle etichette, salvataggio e riapertura",
    "labels",
    features=("LBL-PDF", "LBL-SAVE-REOPEN"),
    min_checks=6,
    budget_s=8.0,
)
def lbl_pdf_save(ctx: E2EContext) -> None:
    project = _settled(ctx, "PdfEtichette")
    spec = _label_spec(project)
    spec.start_offset = 1
    designer = ctx.track(LabelDesignerWidget(project, spec))
    ctx.check(designer.save(), "etichetta salvata")
    reopened = ctx.reopen(project)
    stored = LabelSpec.from_project(reopened, "etichette_clienti")
    ctx.check(stored is not None, "etichetta riaperta")
    ctx.check_close(stored.to_dict(), spec.to_dict(), "JSON identico")
    dialog = LabelPreviewDialog(reopened, stored)
    ctx.track(dialog)
    pdf_path = ctx.work / "labels.pdf"
    with mock.patch.object(QFileDialog, "getSaveFileName", lambda *a, **k: (str(pdf_path), "")):
        dialog.save_pdf()
    ctx.check(pdf_path.exists() and pdf_path.stat().st_size > 1000, "PDF etichette")
    ctx.check("PDF salvato" in dialog.info.text(), "esito PDF etichette")
    with mock.patch.object(QPrintDialog, "exec", return_value=QDialog.DialogCode.Accepted), mock.patch(
        "dbx.ui.report_preview.render_to_printer"
    ) as render:
        dialog.print_pages()
    ctx.check(render.called, "stampa etichette")
