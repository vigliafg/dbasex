"""Scenari E — Query Designer, QBE, risultati, Crosstab e Query Expert."""

from __future__ import annotations

from unittest import mock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog

from dbx.core.crosstab import CrosstabError, build_crosstab
from dbx.core.query_engine import run_query
from dbx.core.query_model import (
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySpec,
    QuerySort,
)
from dbx.designers.qbe_panel import QbePanel
from dbx.designers.query_builder import JoinDialog, NewQueryDialog, QueryDesignerWidget
from dbx.designers.query_expert import QueryExpert
from dbx.runtime.rowset import Rowset
from dbx.ui.crosstab_dialog import CrosstabDialog
from dbx.ui.query_results import QueryResultsWidget

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _settled(ctx: E2EContext, name: str = "Query") -> object:
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


def _designer(ctx: E2EContext, project, spec: QuerySpec) -> QueryDesignerWidget:
    designer = QueryDesignerWidget(project, spec)
    return ctx.track(designer)


def _join_spec(project) -> QuerySpec:
    return QuerySpec(
        name="fatture_clienti",
        caption="Fatture per cliente",
        base="fatture",
        fields=[
            QueryField("fatture", "numero"),
            QueryField("clienti", "nome"),
            QueryField("fatture", "importo"),
            QueryField("fatture", "pagata"),
        ],
        joins=[QueryJoin("inner", "clienti", "fatture.cliente", "clienti.codice")],
    )


def _rows(result) -> int:
    return len(result.rows)


@scenario(
    "qry-01-new-guided",
    "E01 — Nuova query guidata: tabelle, campi, alias",
    "queries",
    features=("QRY-NEW", "QRY-FIELD-INCLUDE", "QRY-FIELD-ALIAS"),
    min_checks=8,
    budget_s=8.0,
)
def qry_new_guided(ctx: E2EContext) -> None:
    project = _settled(ctx, "NuovaQuery")
    dialog = NewQueryDialog(project, suggested_name="clienti_query")
    ctx.track(dialog)
    dialog.name_edit.setText("clienti_query")
    dialog.caption_edit.setText("Clienti per città")
    dialog.table_combo.setCurrentIndex(dialog.table_combo.findData("clienti"))
    spec = dialog.spec()
    ctx.check_close(spec.name, "clienti_query", "nome query")
    ctx.check_close(spec.caption, "Clienti per città", "didascalia query")
    ctx.check_close(spec.base, "clienti", "tabella base")
    ctx.check_close(
        [field.name for field in project.require_table("clienti").stored_fields],
        [field.field for field in spec.fields],
        "campi proposti",
    )

    designer = _designer(ctx, project, spec)
    ctx.check_close(designer.fields_table.rowCount(), len(spec.fields), "griglia campi")
    designer.fields_table.item(0, 1).setText("codice_cliente")
    ctx.check_close(designer.spec.fields[0].alias, "codice_cliente", "alias modificato")
    ctx.check("campi ·" in designer.status_label.text(), "stato campi")
    designer.remove_field("clienti", "note")
    ctx.check_close(designer.fields_table.rowCount(), 6, "campo rimosso")
    designer.add_field("clienti", "note")
    ctx.check_close(designer.fields_table.rowCount(), len(spec.fields), "campo reincluso")
    ctx.check(designer.save(), "query salvata")
    reopened = ctx.reopen(project)
    saved = QuerySpec.from_project(reopened, "clienti_query")
    ctx.check(saved is not None, "query riaperta")
    ctx.check_close(saved.fields[0].alias, "codice_cliente", "alias persistito")
    ctx.check_close(len(saved.fields), len(spec.fields), "campi persistiti")
    ctx.capture(designer, "query-designer", (1100, 700))


@scenario(
    "qry-02-joins",
    "E02 — Join INNER/LEFT suggeriti dalle foreign key",
    "queries",
    features=("QRY-JOIN-INNER", "QRY-JOIN-LEFT", "QRY-JOIN-SUGGEST"),
    min_checks=7,
    budget_s=8.0,
)
def qry_joins(ctx: E2EContext) -> None:
    project = _settled(ctx, "Join")
    spec = QuerySpec.create(project.require_table("clienti"), name="clienti_fatture")
    dialog = JoinDialog(project, spec)
    ctx.track(dialog)
    dialog.table_combo.setCurrentIndex(dialog.table_combo.findData("fatture"))
    ctx.check_close(dialog.table_combo.currentData(), "fatture", "tabella da aggiungere")
    ctx.check_close(dialog.left_combo.currentData(), "clienti.codice", "campo sinistro suggerito")
    ctx.check_close(dialog.right_combo.currentData(), "cliente", "campo destro suggerito")
    ctx.check_close(dialog.kind_combo.count(), 2, "due tipi di join")

    dialog.kind_combo.setCurrentIndex(dialog.kind_combo.findData("inner"))
    inner = dialog.join()
    ctx.check(inner is not None, "join costruito")
    spec.joins = [inner]
    ctx.check_close(run_query(project, spec).rows.__len__(), 4, "INNER JOIN")

    dialog.kind_combo.setCurrentIndex(dialog.kind_combo.findData("left"))
    left = dialog.join()
    spec.joins = [left]
    ctx.check_close(left.kind, "left", "tipo LEFT JOIN")
    ctx.check_close(run_query(project, spec).rows.__len__(), 6, "LEFT JOIN conserva i clienti")

    designer = _designer(ctx, project, spec)
    ctx.check_close(designer.tree.topLevelItemCount(), 2, "due tabelle nell'albero")
    target = None
    for index in range(designer.tree.topLevelItemCount()):
        node = designer.tree.topLevelItem(index)
        data = node.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and data == ("table", "fatture"):
            target = node
    ctx.check(target is not None, "nodo tabella aggiunta")
    designer.tree.setCurrentItem(target)
    designer.remove_selected_table()
    ctx.check_close(len(designer.spec.joins), 0, "tabella rimossa dalla query")


@scenario(
    "qry-03-all-operators",
    "E03 — Tutti i 14 operatori di filtro",
    "queries",
    features=tuple(f"QRY-OP-{name.upper()}" for name in (
        "eq", "ne", "gt", "ge", "lt", "le", "contains", "starts", "ends",
        "like", "between", "ref", "null", "notnull",
    )),
    min_checks=20,
    budget_s=12.0,
)
def qry_all_operators(ctx: E2EContext) -> None:
    project = _settled(ctx, "Operatori")
    table = project.require_table("clienti")
    rowset = Rowset(project.db, table).open()
    record = rowset.find("codice", "C001")
    rowset.update(record["_id"], {"note": "nota"})
    spec = QuerySpec(
        name="operatori",
        base="clienti",
        fields=[QueryField("clienti", "codice"), QueryField("clienti", "nome"), QueryField("clienti", "saldo")],
    )
    designer = _designer(ctx, project, spec)

    cases = [
        ("clienti.citta", "eq", "Roma", 2),
        ("clienti.attivo", "ne", "1", 2),
        ("clienti.saldo", "gt", "100", 2),
        ("clienti.saldo", "ge", "500", 2),
        ("clienti.saldo", "lt", "0", 1),
        ("clienti.saldo", "le", "0", 2),
        ("clienti.nome", "contains", "a", 4),
        ("clienti.nome", "starts", "A", 1),
        ("clienti.nome", "ends", "a", 1),
        ("clienti.nome", "like", "*a*", 4),
        ("clienti.note", "null", "", 4),
        ("clienti.note", "notnull", "", 1),
    ]
    for field, op, value, expected in cases:
        designer.add_filter(field, op, value)
        if op not in ("null", "notnull"):
            item = designer.filters_table.item(0, 2)
            item.setText(value)
        result = designer.run_preview()
        ctx.check(result is not None, f"{op}: anteprima")
        ctx.check_close(_rows(result), expected, f"{op}: righe")
        designer.filters_table.selectRow(0)
        designer.remove_selected_filter()

    designer.add_filter("clienti.codice", "ref", "clienti.codice")
    ctx.check_close(_rows(designer.run_preview()), 5, "ref: confronto tra campi")
    designer.filters_table.selectRow(0)
    designer.remove_selected_filter()

    designer.set_mode("qbe")
    designer.qbe_page.set_cell("clienti", "saldo", 0, "0..600")
    designer.qbe_page.apply_and_notify()
    ctx.check_close(designer.spec.filters[0].op, "between", "between da QBE")
    ctx.check_close(_rows(designer.run_preview()), 3, "between: righe")
    ctx.check_close(designer.filters_table.cellWidget(0, 1).count(), 14, "quattordici operatori")
    ctx.check("?" in designer.sql_edit.toPlainText(), "SQL parametrizzato")


@scenario(
    "qry-04-and-or",
    "E04 — Filtri AND/OR con gruppi",
    "queries",
    features=("QRY-FILTER-AND", "QRY-FILTER-OR"),
    min_checks=7,
    budget_s=8.0,
)
def qry_and_or(ctx: E2EContext) -> None:
    project = _settled(ctx, "EOu")
    spec = QuerySpec(
        name="and_or",
        base="clienti",
        fields=[QueryField("clienti", "codice"), QueryField("clienti", "citta")],
    )
    designer = _designer(ctx, project, spec)
    designer.add_filter("clienti.citta", "eq", "Roma", group=0)
    designer.add_filter("clienti.attivo", "eq", "1", group=0)
    designer.add_filter("clienti.citta", "eq", "Milano", group=1)
    result = designer.run_preview()
    ctx.check(" OR " in designer.sql_edit.toPlainText(), "SQL con OR fra gruppi")
    ctx.check(" AND " in designer.sql_edit.toPlainText(), "SQL con AND nello stesso gruppo")
    ctx.check_close(_rows(result), 3, "OR: Roma attivi più Milano")
    groups = [
        designer.filters_table.item(row, 3).text()
        for row in range(designer.filters_table.rowCount())
    ]
    ctx.check_close(groups, ["0", "0", "1"], "gruppi visibili nella scheda Filtri")
    ctx.check_close([item.group for item in designer.spec.filters], [0, 0, 1], "gruppi nel modello")
    designer.filters_table.selectRow(2)
    designer.remove_selected_filter()
    ctx.check_close(_rows(designer.run_preview()), 2, "AND senza gruppo OR")
    ctx.check_close(designer.filters_table.rowCount(), 2, "filtri rimasti")


@scenario(
    "qry-05-sorts",
    "E05 — Ordinamento multiplo crescente e decrescente",
    "queries",
    features=("QRY-SORT-ASC", "QRY-SORT-DESC", "QRY-SORT-MULTI"),
    min_checks=8,
    budget_s=8.0,
)
def qry_sorts(ctx: E2EContext) -> None:
    project = _settled(ctx, "Ordinamento")
    spec = QuerySpec(
        name="ordinata",
        base="clienti",
        fields=[QueryField("clienti", "codice"), QueryField("clienti", "citta"), QueryField("clienti", "saldo")],
    )
    designer = _designer(ctx, project, spec)
    designer.add_sort("clienti.citta", "asc")
    designer.add_sort("clienti.saldo", "desc")
    result = designer.run_preview()
    ctx.check_close(
        [(row["citta"], row["codice"]) for row in result.rows],
        [("Milano", "C002"), ("Napoli", "C005"), ("Roma", "C001"), ("Roma", "C004"), ("Torino", "C003")],
        "ordine città e saldo",
    )
    ctx.check("ORDER BY" in designer.sql_edit.toPlainText(), "SQL con ORDER BY")
    ctx.check_close(designer.sorts_table.rowCount(), 2, "due criteri in griglia")
    ctx.check_close(designer.sorts_table.cellWidget(0, 1).count(), 2, "due direzioni")
    designer.sorts_table.selectRow(1)
    designer.move_sort(-1)
    ctx.check_close(designer.spec.sorts[0].field, "clienti.saldo", "criterio spostato in alto")
    ctx.check_close(_rows(designer.run_preview()), 5, "anteprima dopo riordino")
    designer.sorts_table.selectRow(0)
    designer.move_sort(1)
    ctx.check_close(designer.spec.sorts[0].field, "clienti.citta", "criterio ripristinato")
    ctx.check_close([item.field for item in designer.spec.sorts], ["clienti.citta", "clienti.saldo"], "criteri nel modello")


@scenario(
    "qry-06-group-aggregates",
    "E06 — GROUP BY e cinque aggregati",
    "queries",
    features=(
        "QRY-GROUP-BY",
        "QRY-AGG-COUNT",
        "QRY-AGG-SUM",
        "QRY-AGG-AVG",
        "QRY-AGG-MIN",
        "QRY-AGG-MAX",
    ),
    min_checks=12,
    budget_s=10.0,
)
def qry_group_aggregates(ctx: E2EContext) -> None:
    project = _settled(ctx, "Aggregati")
    spec = _join_spec(project)
    spec.fields = [QueryField("clienti", "citta")]
    spec.group_by = ["clienti.citta"]
    designer = _designer(ctx, project, spec)
    ctx.check_close(designer.group_table.rowCount(), 1, "raggruppamento presente")
    ctx.check_close(designer.group_table.cellWidget(0, 0).currentData(), "clienti.citta", "campo gruppo")

    config = [
        ("count", "", "quanti"),
        ("sum", "fatture.importo", "totale"),
        ("avg", "fatture.importo", "media"),
        ("min", "fatture.importo", "minimo"),
        ("max", "fatture.importo", "massimo"),
    ]
    for function, field, alias in config:
        designer.add_aggregate()
        row = designer.aggregates_table.rowCount() - 1
        combo = designer.aggregates_table.cellWidget(row, 0)
        combo.setCurrentIndex(combo.findData(function))
        field_combo = designer.aggregates_table.cellWidget(row, 1)
        if field:
            field_combo.setCurrentIndex(field_combo.findData(field))
        alias_edit = designer.aggregates_table.cellWidget(row, 2)
        alias_edit.setText(alias)
    ctx.check_close(designer.aggregates_table.rowCount(), 5, "cinque aggregati")
    ctx.check("1 raggruppamenti · 5 aggregati" in designer.status_label.text(), "stato raggruppamento")
    result = designer.run_preview()
    ctx.check_close(_rows(result), 2, "due gruppi di fatture")
    rows = {row["citta"]: row for row in result.rows}
    ctx.check_close(rows["Roma"]["quanti"], 3, "COUNT Roma")
    ctx.check_close(rows["Roma"]["totale"], 450.5, "SUM Roma")
    ctx.check_close(round(rows["Roma"]["media"], 3), 150.167, "AVG Roma")
    ctx.check_close(rows["Roma"]["minimo"], 100.0, "MIN Roma")
    ctx.check_close(rows["Roma"]["massimo"], 200.0, "MAX Roma")
    ctx.check_close(rows["Milano"]["totale"], 300.0, "SUM Milano")
    ctx.check_close(len(designer.spec.group_by), 1, "un campo GROUP BY")


@scenario(
    "qry-07-sql-validation",
    "E07 — Anteprima SQL parametrizzata e validazione",
    "queries",
    features=("QRY-SQL-PREVIEW", "QRY-SQL-PARAMS", "QRY-VALIDATE"),
    min_checks=8,
    budget_s=8.0,
)
def qry_sql_validation(ctx: E2EContext) -> None:
    project = _settled(ctx, "SQL")
    spec = QuerySpec(
        name="sql_query",
        base="clienti",
        fields=[QueryField("clienti", "codice")],
        filters=[QueryFilter("clienti.nome", "contains", "a")],
    )
    designer = _designer(ctx, project, spec)
    sql = designer.sql_edit.toPlainText()
    ctx.check("SELECT" in sql, "anteprima SELECT")
    ctx.check("?" in sql, "parametro segnaposto")
    ctx.check("-- parametri" in sql, "valori dei parametri mostrati")
    ctx.check("%a%" in sql, "pattern del filtro")
    ctx.check("1 campi · 0 join · 1 filtri" in designer.status_label.text(), "stato filtri")

    designer.spec.fields.append(QueryField("clienti", "inesistente"))
    ctx.check(designer.spec.validate(project.tables()) != [], "validazione segnala il campo")
    ctx.check(designer.run_preview() is None, "anteprima rifiutata")
    ctx.check("Query non valida" in designer.result_label.text(), "errore nell'anteprima")
    ctx.check(not designer.save(), "salvataggio rifiutato")
    ctx.check(any("Query non valida" in entry[1] for entry in ctx.dialogs), "avviso di validazione")

    designer.spec.fields.pop()
    designer.spec.base = "tabella_inesistente"
    errors = designer.spec.validate(project.tables())
    ctx.check(any("Tabella base inesistente" in error for error in errors), "base inesistente")
    designer.spec.base = "clienti"
    ctx.check(designer.spec.validate(project.tables()) == [], "query tornata valida")


@scenario(
    "qry-08-save-reopen",
    "E08 — Salvataggio, rinomina e rifiuto di query invalida",
    "queries",
    features=("QRY-SAVE-REOPEN", "QRY-SAVE-REJECT", "QRY-VALIDATE"),
    min_checks=9,
    budget_s=8.0,
)
def qry_save_reopen(ctx: E2EContext) -> None:
    project = _settled(ctx, "Salvataggio")
    spec = QuerySpec(
        name="clienti_attivi",
        caption="Clienti attivi",
        base="clienti",
        fields=[QueryField("clienti", "codice", "cod"), QueryField("clienti", "nome")],
        filters=[QueryFilter("clienti.attivo", "eq", "1")],
        sorts=[QuerySort("clienti.nome", "asc")],
    )
    designer = _designer(ctx, project, spec)
    ctx.check(designer.save(), "query salvata")
    ctx.check_close(reopened_name(project, "clienti_attivi"), "clienti_attivi", "oggetto nel progetto")

    designer.name_edit.setText("clienti_attivi_2026")
    designer._on_name_changed()
    ctx.check(designer.save(), "query rinominata")
    ctx.check(project.artifact("queries", "clienti_attivi") is None, "vecchio nome rimosso")
    reopened = ctx.reopen(project)
    saved = QuerySpec.from_project(reopened, "clienti_attivi_2026")
    ctx.check(saved is not None, "query riaperta dopo rinomina")
    ctx.check_close(saved.fields[0].alias, "cod", "alias persistito")
    ctx.check_close(saved.filters[0].value, "1", "filtro persistito")
    ctx.check_close(saved.sorts[0].direction, "asc", "ordinamento persistito")

    invalid = QuerySpec(name="rotta", base="tabella_mancante", fields=[QueryField("x", "y")])
    broken = _designer(ctx, project, invalid)
    ctx.check(not broken.save(), "query invalida rifiutata")
    ctx.check(any("Query non valida" in entry[1] for entry in ctx.dialogs), "messaggio di rifiuto")
    ctx.check(reopened.artifact("queries", "rotta") is None, "query invalida non salvata")


def reopened_name(project, name: str) -> str:
    artifact = project.artifact("queries", name)
    return str(artifact.get("name", "")) if artifact else ""


@scenario(
    "qry-09-qbe-image",
    "E09 — QBE: query image, includi e tre righe di criteri",
    "queries",
    features=("QRY-QBE-IMAGE", "QRY-QBE-INCLUDE", "QRY-QBE-ROWS"),
    min_checks=10,
    budget_s=10.0,
    screenshots=("query-qbe",),
)
def qry_qbe_image(ctx: E2EContext) -> None:
    project = _settled(ctx, "QBEImmagine")
    spec = _join_spec(project)
    designer = _designer(ctx, project, spec)
    designer.set_mode("qbe")
    panel = designer.qbe_page
    ctx.check_close(len(panel.images()), 2, "due query image")
    title = panel.image("fatture").title_text
    ctx.check("BASE" in title, "ruolo tabella base")
    ctx.check("INNER JOIN" in panel.image("clienti").title_text, "ruolo tabella collegata")
    image = panel.image("fatture")
    ctx.check(image.is_included("numero"), "campo incluso")
    image.set_included("numero", False)
    panel.image("clienti").set_included("citta", True)
    ctx.check_close(image.cell_text(2, "importo"), "", "terza riga disponibile")
    image.set_cell(0, "importo", "100..300")
    panel.apply_and_notify()
    ctx.check_close(len(designer.spec.fields), 4, "campi dopo includi")
    ctx.check_close(len(designer.spec.filters), 1, "criterio applicato")
    result = designer.run_preview()
    ctx.check(result is not None and _rows(result) == 4, "anteprima QBE")
    designer.set_mode("qbe")
    ctx.check(designer.qbe_mode_button.isChecked(), "modalità QBE attiva")
    designer.set_mode("guided")
    ctx.check(not designer.qbe_mode_button.isChecked(), "ritorno alla vista guidata")
    ctx.check_close(designer.fields_table.rowCount(), 4, "campi allineati al guidato")
    ctx.capture(designer, "query-qbe", (1100, 720))


@scenario(
    "qry-10-qbe-example",
    "E10 — QBE: example elements e avvisi",
    "queries",
    features=("QRY-QBE-EXAMPLE", "QRY-QBE-EXAMPLE-WARN"),
    min_checks=7,
    budget_s=8.0,
)
def qry_qbe_example(ctx: E2EContext) -> None:
    project = _settled(ctx, "QBEExample")
    spec = _join_spec(project)
    designer = _designer(ctx, project, spec)
    designer.set_mode("qbe")
    panel: QbePanel = designer.qbe_page
    panel.set_cell("fatture", "cliente", 0, "_cliente")
    panel.set_cell("clienti", "codice", 0, "_cliente")
    panel.apply_and_notify()
    refs = [item for item in designer.spec.filters if item.op == "ref"]
    ctx.check_close(len(refs), 1, "filtro ref creato")
    ctx.check_close(refs[0].field, "fatture.cliente", "campo di partenza")
    ctx.check_close(refs[0].value, "clienti.codice", "campo di arrivo")
    result = designer.run_preview()
    ctx.check(result is not None and _rows(result) == 4, "example element eseguito")

    panel.set_cell("clienti", "nome", 1, "_solo")
    warnings = panel.apply_and_notify()
    ctx.check(any("usato una sola volta" in warning for warning in warnings), "avviso uso singolo")
    panel.set_cell("fatture", "importo", 0, "_mix")
    panel.set_cell("clienti", "nome", 2, "_mix")
    warnings = panel.apply_and_notify()
    ctx.check(any("tipi incompatibili" in warning for warning in warnings), "avviso tipi incompatibili")
    ctx.check(len(designer.spec.filters) >= 1, "filtri conservati")


@scenario(
    "qry-11-qbe-syntax",
    "E11 — QBE: between, like e campi vuoti",
    "queries",
    features=("QRY-QBE-BETWEEN", "QRY-QBE-LIKE", "QRY-QBE-NULL"),
    min_checks=9,
    budget_s=8.0,
)
def qry_qbe_syntax(ctx: E2EContext) -> None:
    project = _settled(ctx, "QBESintassi")
    spec = _join_spec(project)
    designer = _designer(ctx, project, spec)
    designer.set_mode("qbe")
    panel = designer.qbe_page
    panel.set_cell("fatture", "importo", 0, "100..300")
    panel.set_cell("clienti", "nome", 0, "*a*")
    panel.set_cell("clienti", "note", 0, "not blank")
    panel.set_cell("clienti", "citta", 1, "blank")
    panel.apply_and_notify()
    ops = {item.op for item in designer.spec.filters}
    ctx.check("between" in ops, "intervallo")
    ctx.check("like" in ops, "jolly")
    ctx.check("notnull" in ops, "non vuoto")
    ctx.check("null" in ops, "vuoto")
    between = next(item for item in designer.spec.filters if item.op == "between")
    ctx.check_close((between.value, between.value2), ("100", "300"), "estremi intervallo")
    ctx.check(designer.run_preview() is not None, "anteprima con intervallo")

    panel.set_cell("clienti", "citta", 1, "")
    panel.set_cell("clienti", "note", 0, "")
    panel.set_cell("clienti", "nome", 0, "")
    panel.set_cell("clienti", "codice", 0, "C00?")
    panel.apply_and_notify()
    like = next(item for item in designer.spec.filters if item.op == "like")
    ctx.check_close(like.value, "C00?", "jolly a carattere singolo")
    ctx.check_close(_rows(designer.run_preview()), 4, "C00? più intervallo")
    panel.set_cell("fatture", "importo", 0, "abc..300")
    warnings = panel.apply_and_notify()
    ctx.check(any("fatture.importo" in warning for warning in warnings), "cella non valida segnalata")


@scenario(
    "qry-12-qbe-or",
    "E12 — QBE: righe OR e gruppo nella scheda Filtri",
    "queries",
    features=("QRY-QBE-OR", "QRY-FILTER-GROUPS"),
    min_checks=8,
    budget_s=8.0,
)
def qry_qbe_or(ctx: E2EContext) -> None:
    project = _settled(ctx, "QBEOr")
    spec = QuerySpec(
        name="or_rows",
        base="clienti",
        fields=[QueryField("clienti", "codice"), QueryField("clienti", "citta")],
    )
    designer = _designer(ctx, project, spec)
    designer.set_mode("qbe")
    panel = designer.qbe_page
    panel.set_cell("clienti", "citta", 0, "Roma")
    panel.set_cell("clienti", "attivo", 1, "0")
    panel.apply_and_notify()
    groups = {item.group for item in designer.spec.filters}
    ctx.check_close(groups, {0, 1}, "due gruppi OR")
    result = designer.run_preview()
    ctx.check_close(_rows(result), 4, "OR fra le due righe")
    designer.set_mode("guided")
    ctx.check(not designer.qbe_mode_button.isChecked(), "vista guidata attiva")
    ctx.check_close(designer.filters_table.rowCount(), 2, "filtri nella scheda guidata")
    texts = [designer.filters_table.item(row, 3).text() for row in range(2)]
    ctx.check_close(texts, ["0", "1"], "gruppi preservati")
    ctx.check_close(designer.filters_table.item(0, 2).text(), "Roma", "valore del criterio")
    ctx.check_close(designer.qbe_page.cell_text("clienti", "citta", 0), "Roma", "cella QBE conservata")
    ctx.check(" OR " in designer.sql_edit.toPlainText(), "SQL con OR")


@scenario(
    "qry-13-results",
    "E13 — Query Results: griglia, formati, refresh ed export",
    "queries",
    features=(
        "QRY-RESULTS-GRID",
        "QRY-RESULTS-FORMAT",
        "QRY-RESULTS-REFRESH",
        "QRY-RESULTS-EXPORT",
    ),
    min_checks=10,
    budget_s=8.0,
    screenshots=("query-results",),
)
def qry_results(ctx: E2EContext) -> None:
    project = ctx.new_project("Risultati")
    table = fixtures.tutti_tipi_table()
    fixtures.apply(project, table)
    rowset = Rowset(project.db, project.require_table("tutti_tipi"))
    rowset.insert(
        {
            "testo": "Alfa",
            "intero": 7,
            "decimale": 1234.5,
            "data": "2026-01-10",
            "booleano": True,
            "scelta": "A",
        }
    )
    spec = QuerySpec.create(project.require_table("tutti_tipi"), name="tutti_tipi_query")
    widget = QueryResultsWidget(project, spec)
    ctx.track(widget)
    ctx.check_close(widget.table.rowCount(), 1, "una riga")
    headers = [widget.table.horizontalHeaderItem(i).text() for i in range(widget.table.columnCount())]
    ctx.check("decimale" in headers and "data" in headers, "intestazioni dei tipi")
    decimal_column = headers.index("decimale")
    date_column = headers.index("data")
    bool_column = headers.index("booleano")
    ctx.check_close(widget.table.item(0, date_column).text(), "10/01/2026", "data formattata")
    ctx.check_close(widget.table.item(0, bool_column).text(), "Sì", "booleano formattato")
    ctx.check_close(widget.table.item(0, decimal_column).text(), "1234.5", "decimale formattato")
    ctx.check("1 righe" in widget.info_label.text() and "sola lettura" in widget.info_label.text(), "stato risultati")

    rowset.insert({"testo": "Beta", "intero": 8, "decimale": 10.0, "data": "2026-02-10", "booleano": False})
    ctx.check(widget.refresh(), "refresh eseguito")
    ctx.check_close(widget.table.rowCount(), 2, "righe aggiornate")
    ctx.check("2 righe" in widget.info_label.text(), "conteggio aggiornato")

    export_path = ctx.work / "query_results.csv"
    with mock.patch.object(QFileDialog, "getSaveFileName", lambda *a, **k: (str(export_path), "")):
        ctx.check(widget.export_csv() == export_path, "export CSV")
    content = export_path.read_text(encoding="utf-8-sig")
    ctx.check("testo" in content and "Alfa" in content, "contenuto CSV")
    ctx.check_close(widget.row_values(0)["testo"], "Alfa", "valori riga")
    ctx.capture(widget, "query-results", (1000, 620))


@scenario(
    "qry-14-crosstab",
    "E14 — Crosstab: righe, colonne, totali e casi limite",
    "queries",
    features=(
        "QRY-CROSSTAB",
        "QRY-CROSSTAB-TOTALS",
        "QRY-CROSSTAB-EMPTY",
        "QRY-CROSSTAB-ERROR",
        "QRY-CROSSTAB-CSV",
    ),
    min_checks=11,
    budget_s=8.0,
    screenshots=("crosstab",),
)
def qry_crosstab(ctx: E2EContext) -> None:
    project = _settled(ctx, "Crosstab")
    spec = _join_spec(project)
    result = run_query(project, spec)
    dialog = CrosstabDialog(result, "Fatture per cliente")
    ctx.track(dialog)
    dialog.row_combo.setCurrentIndex(dialog.row_combo.findData("nome"))
    dialog.column_combo.setCurrentIndex(dialog.column_combo.findData("pagata"))
    dialog.value_combo.setCurrentIndex(dialog.value_combo.findData("importo"))
    ctx.check(dialog.rebuild(), "matrice costruita")
    ctx.check_close(dialog.crosstab.row_values, ["Alfa Srl", "Beta Studio", "Delta Spa"], "righe")
    ctx.check_close(dialog.crosstab.column_values, [False, True], "colonne")
    ctx.check_close(dialog.crosstab.grand_total, 750.5, "totale generale")
    ctx.check_close(dialog.table.rowCount(), 4, "tre righe più totale")
    ctx.check_close(dialog.table.columnCount(), 4, "etichetta, due colonne e totale")
    ctx.check("3 righe · 2 colonne · 4 record" in dialog.summary.text(), "riepilogo matrice")

    export_path = ctx.work / "crosstab.csv"
    with mock.patch.object(QFileDialog, "getSaveFileName", lambda *a, **k: (str(export_path), "")):
        ctx.check(dialog.export_csv() == export_path, "export CSV crosstab")
    ctx.check("Totale" in export_path.read_text(encoding="utf-8-sig"), "totale nel CSV")
    ctx.capture(dialog, "crosstab", (940, 620))

    empty_spec = _join_spec(project)
    empty_spec.filters = [QueryFilter("fatture.importo", "gt", "9999")]
    empty = run_query(project, empty_spec)
    empty_dialog = CrosstabDialog(empty, "Vuota")
    ctx.track(empty_dialog)
    ctx.check_close(empty_dialog.table.rowCount(), 1, "solo riga totale")
    ctx.check_close(empty_dialog.crosstab.grand_total, 0.0, "totale zero")
    try:
        build_crosstab(result, "nome", "pagata", "nome")
    except CrosstabError as exc:
        ctx.check("non è numerica" in str(exc), "colonna valore non numerica")
    else:
        ctx.check(False, "colonna valore non numerica")


@scenario(
    "qry-15-expert",
    "E15 — Query Expert: relazioni, campi, criteri e ordinamento",
    "queries",
    features=("QRY-EXPERT", "QRY-EXPERT-RELATIONS", "QRY-EXPERT-CRITERIA", "QRY-EXPERT-SORT"),
    min_checks=10,
    budget_s=10.0,
)
def qry_expert(ctx: E2EContext) -> None:
    project = _settled(ctx, "QueryExpert")
    expert = QueryExpert(project, suggested_name="fatture_expert")
    ctx.track(expert)
    expert.initializePage(1)
    expert.base_combo.setCurrentIndex(expert.base_combo.findData("fatture"))
    expert.name_edit.setText("fatture_expert")
    expert.caption_edit.setText("Fatture con cliente")
    ctx.check_close(expert.relations_table.rowCount(), 1, "relazione suggerita")
    check = expert.relations_table.item(0, 0)
    ctx.check_close(expert.relations_table.item(0, 1).text(), "clienti", "tabella collegata")
    check.setCheckState(Qt.CheckState.Checked)
    kind = expert.relations_table.cellWidget(0, 3)
    kind.setCurrentIndex(kind.findData("inner"))
    expert.add_criterion()
    field = expert.criteria_table.cellWidget(0, 0)
    field.setCurrentIndex(field.findData("clienti.nome"))
    operator = expert.criteria_table.cellWidget(0, 1)
    operator.setCurrentIndex(operator.findData("contains"))
    expert.criteria_table.cellWidget(0, 2).setText("a")
    expert.add_sort()
    sort_field = expert.sort_table.cellWidget(0, 0)
    sort_field.setCurrentIndex(sort_field.findData("fatture.importo"))
    expert.sort_table.cellWidget(0, 1).setCurrentIndex(1)

    spec = expert.build_spec()
    ctx.check_close(spec.joins[0].table, "clienti", "join esperto")
    ctx.check_close(spec.filters[0].op, "contains", "criterio esperto")
    ctx.check_close(spec.sorts[0].direction, "desc", "ordinamento esperto")
    ctx.check(spec.validate(project.tables()) == [], "query esperto valida")
    result = run_query(project, spec)
    ctx.check_close(_rows(result), 4, "risultato esperto")
    ctx.check_close([row["importo"] for row in result.rows], [300.0, 200.0, 150.5, 100.0], "ordine esperto")
    ctx.check_close(len(expert.relations()), 1, "relazioni esportate dall'esperto")
    project.put_object("queries", spec.to_dict())
    project.save()
    reopened = ctx.reopen(project)
    ctx.check(QuerySpec.from_project(reopened, "fatture_expert") is not None, "query esperto persistita")
