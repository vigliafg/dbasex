"""Scenari C — Browse, editing, validazione, findByReplace, saved finds."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.search import (
    SearchCriterion,
    SearchRequest,
    count_matches,
    delete_find,
    replace_in_rowset,
    save_find,
    saved_finds,
)
from dbx.runtime.rowset import Rowset
from dbx.ui.data_view import DataView, EditingOptionsDialog, RecordDialog
from dbx.ui.find_dialog import FindDialog, ReplaceDialog

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _settled(ctx: E2EContext, name: str = "Browse"):
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


@scenario(
    "brw-01-crud-navigation",
    "C01 — CRUD e navigazione nella Browse",
    "browse",
    features=("DV-CRUD", "DV-NAV", "DV-EDIT-CELL", "DV-STATUS"),
    min_checks=10,
    budget_s=8.0,
    screenshots=("browse-crud",),
)
def brw_crud_navigation(ctx: E2EContext) -> None:
    project = _settled(ctx)
    view = ctx.data_view(project, "clienti")
    view.order_combo.setCurrentIndex(view.order_combo.findData("codice"))
    ctx.check_close(view.grid.rowCount(), 5, "cinque righe")
    ctx.check("Record 1 di 5" in view.status.text(), "stato iniziale")
    view.last_record()
    ctx.check_close(view.rowset.current["codice"], "C005", "ultimo record")
    view.first_record()
    ctx.check_close(view.rowset.current["codice"], "C001", "primo record")
    view.next_record()
    ctx.check_close(view.rowset.current["codice"], "C002", "record successivo")
    view.previous_record()
    ctx.check_close(view.rowset.current["codice"], "C001", "record precedente")
    name_column = [field.name for field in view.table.fields].index("nome")
    view.grid.item(0, name_column).setText("Alfa Nuova")
    ctx.check_close(Rowset(project.db, view.table).open().find("codice", "C001")["nome"], "Alfa Nuova", "modifica in cella")
    ctx.check("Record 1 di 5" in view.status.text(), "stato dopo modifica")
    view.last_record()
    view.delete_record()
    ctx.check_close(view.grid.rowCount(), 4, "record eliminato")
    ctx.check_close(Rowset(project.db, view.table).count(), 4, "conteggio database")
    ctx.capture(view, "browse-crud", (1000, 620))


@scenario(
    "brw-02-validation-cell",
    "C02 — Validazione per cella con rollback",
    "browse",
    features=("DV-VALIDATION", "DV-EDIT-CELL"),
    min_checks=5,
    budget_s=8.0,
)
def brw_validation_cell(ctx: E2EContext) -> None:
    project = ctx.new_project("ValidazioneCella")
    fixtures.settled_project(project)
    view = ctx.data_view(project, "clienti")
    view.order_combo.setCurrentIndex(view.order_combo.findData("codice"))
    code_column = [field.name for field in view.table.fields].index("codice")
    original = Rowset(project.db, view.table).open().find("codice", "C001")["codice"]
    view.grid.item(0, code_column).setText("")
    ctx.check("non valido" in view.status.text().lower() or "obbligatorio" in view.status.text().lower(), "errore mostrato")
    ctx.check_close(Rowset(project.db, view.table).open().find("codice", "C001")["codice"], original, "valore ripristinato")
    ctx.check_close(view.grid.item(0, code_column).text(), "C001", "cella ripristinata")
    number_column = [field.name for field in view.table.fields].index("saldo")
    view.grid.item(0, number_column).setText("non-numero")
    ctx.check("non valido" in view.status.text().lower(), "errore numerico")
    ctx.check_close(float(Rowset(project.db, view.table).open().find("codice", "C001")["saldo"]), 1200.5, "saldo invariato")


@scenario(
    "brw-03-editors",
    "C03 — Editor e formattazione per tipo",
    "browse",
    features=("DV-CHOICE", "DV-EDIT-CELL", "TB-TYPE-DATE", "TB-TYPE-BOOLEAN"),
    min_checks=8,
    budget_s=8.0,
)
def brw_editors(ctx: E2EContext) -> None:
    project = ctx.new_project("Editor")
    table = fixtures.tutti_tipi_table()
    fixtures.apply(project, table)
    rowset = Rowset(project.db, project.require_table("tutti_tipi"))
    rowset.insert(
        {
            "testo": "esempio",
            "intero": 7,
            "decimale": 3.5,
            "data": "2026-05-01",
            "booleano": True,
            "scelta": "C",
            "lungo": "nota",
        }
    )
    view = ctx.data_view(project, "tutti_tipi")
    headers = [view.grid.horizontalHeaderItem(index).text() for index in range(view.grid.columnCount())]
    ctx.check("Data" in headers and "Booleano" in headers, "intestazioni dei tipi")
    choice_column = headers.index("Scelta")
    ctx.check_close(view.grid.item(0, choice_column).text(), "Chiuso", "etichetta Scelta nella griglia")
    from dbx.ui.data_view import ChoiceCellDelegate

    ctx.check(isinstance(view.grid.itemDelegateForColumn(choice_column), ChoiceCellDelegate), "delegate Scelta")
    boolean_column = headers.index("Booleano")
    ctx.check(view.grid.item(0, boolean_column).text() in ("Sì", "Si", "1", "True"), "booleano formattato")
    date_column = headers.index("Data")
    ctx.check("2026" in view.grid.item(0, date_column).text(), "data formattata")
    decimal_column = headers.index("Decimale")
    ctx.check("3" in view.grid.item(0, decimal_column).text(), "decimale formattato")
    ctx.check(view.grid.item(0, headers.index("Testo")).text() == "esempio", "testo")
    ctx.check(view.grid.item(0, headers.index("Lungo")).text() == "nota", "memo")


@scenario(
    "brw-04-calculated-readonly",
    "C04 — Campi calcolati in sola lettura",
    "browse",
    features=("DV-CALCULATED", "TB-FIELD-CALCULATED"),
    min_checks=4,
    budget_s=6.0,
)
def brw_calculated_readonly(ctx: E2EContext) -> None:
    project = ctx.new_project("CalcolatiBrowse")
    fixtures.settled_project(project)
    view = ctx.data_view(project, "clienti")
    column = [field.name for field in view.table.fields].index("nome_maiuscolo")
    item = view.grid.item(0, column)
    ctx.check_close(item.text(), "ALFA SRL", "calcolato valorizzato")
    ctx.check(not bool(item.flags() & Qt.ItemFlag.ItemIsEditable), "cella non editabile")
    ctx.check("calcolato" in item.toolTip().lower(), "tooltip calcolato")
    before = Rowset(project.db, view.table).open().find("codice", "C001")["nome_maiuscolo"]
    view.grid.item(0, column).setText("MANOMESSO")
    ctx.check_close(Rowset(project.db, view.table).open().find("codice", "C001")["nome_maiuscolo"], before, "valore non alterabile")


@scenario(
    "brw-05-find-operators",
    "C05 — Find mode: tutti gli operatori",
    "browse",
    features=("DV-FIND", "DV-FIND-AND", "DV-FIND-OR", "DV-FIND-OMIT"),
    min_checks=12,
    budget_s=8.0,
)
def brw_find_operators(ctx: E2EContext) -> None:
    project = _settled(ctx, "TrovaOperatori")
    table = project.require_table("clienti")
    cases = [
        ("contains", "nome", "a", 4),
        ("eq", "citta", "Roma", 2),
        ("ne", "citta", "Roma", 3),
        ("starts", "nome", "Al", 1),
        ("ends", "nome", "Srl", 1),
        ("gt", "saldo", "100", 2),
        ("ge", "saldo", "500", 2),
        ("lt", "saldo", "0", 1),
        ("le", "saldo", "0", 2),
        ("blank", "note", "", 5),
        ("notblank", "note", "", 0),
    ]
    for op, field, value, expected in cases:
        request = SearchRequest([SearchCriterion(field, op, value)])
        ctx.check_close(count_matches(project.db, table, request), expected, f"operatore {op}")
    request_all = SearchRequest(
        [SearchCriterion("citta", "eq", "Roma"), SearchCriterion("attivo", "eq", "1")]
    )
    ctx.check_close(count_matches(project.db, table, request_all), 2, "AND")
    request_any = SearchRequest(
        [SearchCriterion("citta", "eq", "Milano"), SearchCriterion("citta", "eq", "Torino")],
        match="any",
    )
    ctx.check_close(count_matches(project.db, table, request_any), 2, "OR")
    request_omit = SearchRequest([SearchCriterion("attivo", "eq", "1", omit=True)])
    ctx.check_close(count_matches(project.db, table, request_omit), 2, "Ometti")
    ctx.check(not SearchRequest(), "richiesta vuota")


@scenario(
    "brw-06-find-dialog",
    "C06 — FindDialog applicato alla griglia",
    "browse",
    features=("DV-FIND", "DV-FIND-AND", "DV-STATUS"),
    min_checks=7,
    budget_s=8.0,
    screenshots=("browse-find",),
)
def brw_find_dialog(ctx: E2EContext) -> None:
    project = _settled(ctx, "TrovaDialogo")
    view = ctx.data_view(project, "clienti")
    dialog = ctx.track(FindDialog(project, view.table))
    initial_rows = dialog.grid.rowCount()
    dialog.add_criterion(SearchCriterion("citta", "eq", "Roma"))
    ctx.check_close(dialog.grid.rowCount(), initial_rows + 1, "criterio aggiunto")
    dialog.add_criterion(SearchCriterion("attivo", "eq", "1"))
    ctx.check_close(dialog.grid.rowCount(), initial_rows + 2, "secondo criterio")
    request = dialog.request()
    ctx.check_close(len(request.criteria), initial_rows + 2, "richiesta letta")
    view._search = request
    view.refresh()
    ctx.check_close(view.rowset.count(), 2, "griglia filtrata")
    ctx.check("ricerca:" in view.status.text() and "Record 1 di 2" in view.status.text(), "stato ricerca")
    view.clear_find()
    ctx.check_close(view.rowset.count(), 5, "ricerca azzerata")
    dialog.remove_criterion()
    ctx.check(dialog.grid.rowCount() >= 1, "criterio rimosso")
    ctx.capture(dialog, "browse-find", (760, 520))


@scenario(
    "brw-07-replace",
    "C07 — Sostituzione con ambito e maiuscole",
    "browse",
    features=("DV-REPLACE", "DV-REPLACE-CASE"),
    min_checks=5,
    budget_s=8.0,
)
def brw_replace(ctx: E2EContext) -> None:
    project = _settled(ctx, "Sostituisci")
    table = project.require_table("clienti")
    dialog = ctx.track(ReplaceDialog(table))
    dialog.find_edit.setText("Srl")
    dialog.replace_edit.setText("S.p.A.")
    ctx.check_close(dialog.values()["find"], "Srl", "valore da cercare")
    rowset = Rowset(project.db, table).open(order="codice")
    changed = replace_in_rowset(rowset, "Srl", "S.p.A.", field="nome")
    ctx.check_close(changed, 1, "una cella sostituita")
    ctx.check_close(Rowset(project.db, table).open().find("codice", "C001")["nome"], "Alfa S.p.A.", "sostituzione applicata")
    rowset = Rowset(project.db, table).open(order="codice")
    changed = replace_in_rowset(rowset, "s.p.a.", "X", field="nome", match_case=True)
    ctx.check_close(changed, 0, "maiuscole distinte")
    dialog.case_box.setChecked(True)
    dialog.field_combo.setCurrentIndex(dialog.field_combo.findData("nome"))
    values = dialog.values()
    ctx.check(values["match_case"] and values["field"] == "nome", "opzioni sostituzione")


@scenario(
    "brw-08-saved-finds",
    "C08 — Ricerche salvate",
    "browse",
    features=("DV-SAVED-FINDS", "DV-FIND"),
    min_checks=7,
    budget_s=8.0,
)
def brw_saved_finds(ctx: E2EContext) -> None:
    project = _settled(ctx, "RicercheSalvate")
    table = project.require_table("clienti")
    request = SearchRequest([SearchCriterion("citta", "eq", "Roma")])
    save_find(project, "clienti", "solo Roma", request)
    ctx.check("solo Roma" in saved_finds(project, "clienti"), "ricerca salvata")
    dialog = ctx.track(FindDialog(project, table))
    ctx.check(dialog.saved_combo.count() >= 1, "combo ricerche salvate")
    index = dialog.saved_combo.findText("solo Roma")
    ctx.check(index >= 0, "nome in combo")
    dialog.saved_combo.setCurrentIndex(max(0, index))
    dialog.load_saved()
    ctx.check_close(len(dialog.request().criteria), 1, "criteri caricati")
    project = ctx.reopen(project)
    ctx.check("solo Roma" in saved_finds(project, "clienti"), "ricerca persistita")
    ctx.check(delete_find(project, "clienti", "solo Roma"), "ricerca eliminata")
    ctx.check("solo Roma" not in saved_finds(project, "clienti"), "rimozione confermata")


@scenario(
    "brw-09-sort-filter-status",
    "C09 — Ordinamento, filtro rapido e stato",
    "browse",
    features=("DV-SORT", "DV-FILTER", "DV-STATUS"),
    min_checks=6,
    budget_s=8.0,
)
def brw_sort_filter_status(ctx: E2EContext) -> None:
    project = _settled(ctx, "OrdinaFiltra")
    view = ctx.data_view(project, "clienti")
    index = view.order_combo.findData("nome")
    view.order_combo.setCurrentIndex(index)
    codes = [view.grid.item(row, 0).text() for row in range(view.grid.rowCount())]
    names = [view.grid.item(row, [f.name for f in view.table.fields].index("nome")).text() for row in range(view.grid.rowCount())]
    ctx.check(names == sorted(names), "ordine alfabetico")
    ctx.check("ordine:" in view.status.text(), "stato mostra ordine")
    view.search_edit.setText("Roma")
    view.apply_filter()
    ctx.check_close(view.grid.rowCount(), 2, "filtro rapido")
    ctx.check("filtro: Roma" in view.status.text(), "stato mostra filtro")
    view.search_edit.setText("")
    view.apply_filter()
    ctx.check_close(view.grid.rowCount(), 5, "filtro rimosso")
    ctx.check(len(codes) == 5, "codici letti")


@scenario(
    "brw-10-columns-options",
    "C10 — Larghezza colonne ed Editing Options",
    "browse",
    features=("DV-COLUMNS", "DV-OPTIONS"),
    min_checks=6,
    budget_s=8.0,
)
def brw_columns_options(ctx: E2EContext) -> None:
    project = _settled(ctx, "Colonne")
    view = ctx.data_view(project, "clienti")
    view.grid.setColumnWidth(0, 175)
    view._persist_columns()
    second = ctx.data_view(project, "clienti")
    ctx.check_close(second.grid.columnWidth(0), 175, "larghezza ripristinata")
    dialog = ctx.track(EditingOptionsDialog(view.options))
    ctx.check(dialog.alternate.isChecked(), "righe alternate predefinite")
    dialog.alternate.setChecked(False)
    dialog.record_numbers.setChecked(False)
    dialog.confirm_delete.setChecked(False)
    options = dialog.options()
    ctx.check(not options["alternate"], "opzione righe alternate")
    ctx.check(not options["record_numbers"], "opzione colonna selettore")
    ctx.check(not options["confirm_delete"], "opzione conferma eliminazione")
    view.options.update(options)
    view._apply_options()
    ctx.check(not view.grid.alternatingRowColors(), "opzione applicata alla griglia")


@scenario(
    "brw-11-record-dialogs",
    "C11 — Dialogo nuovo record e validazione",
    "browse",
    features=("DV-NEW-DIALOG", "DV-DELETE", "DV-CRUD"),
    min_checks=5,
    budget_s=8.0,
)
def brw_record_dialogs(ctx: E2EContext) -> None:
    project = _settled(ctx, "NuovoRecord")
    table = project.require_table("clienti")
    rowset = Rowset(project.db, table)
    dialog = ctx.track(RecordDialog(table, validator=rowset.check_insert, db=project.db))
    dialog.editors["codice"].setText("C100")
    dialog.editors["nome"].setText("Nuovo Cliente")
    dialog.editors["citta"].setText("Bologna")
    dialog.accept()
    ctx.check_close(dialog.result(), int(QDialog.DialogCode.Accepted), "dialogo accettato")
    values = dialog.values()
    ctx.check_close(values["codice"], "C100", "valori letti")
    rowset.insert(values)
    ctx.check_close(rowset.count(), 6, "record inserito")
    empty = ctx.track(RecordDialog(table, validator=rowset.check_insert, db=project.db))
    empty.editors["nome"].setText("Senza codice")
    empty.accept()
    ctx.check(empty.result() != int(QDialog.DialogCode.Accepted), "record incompleto rifiutato")
    view = ctx.data_view(project, "clienti")
    view.last_record()
    view.delete_record()
    ctx.check_close(view.rowset.count(), 5, "record eliminato dalla griglia")


@scenario(
    "brw-12-empty-boundary-refresh",
    "C12 — Tabella vuota, confini e refresh",
    "browse",
    features=("DV-EMPTY", "DV-NAV", "DV-REFRESH"),
    min_checks=8,
    budget_s=8.0,
)
def brw_empty_boundary_refresh(ctx: E2EContext) -> None:
    project = ctx.new_project("VuotaBrowse")
    fixtures.apply(project, fixtures.clienti_table())
    view = ctx.data_view(project, "clienti")
    ctx.check_close(view.grid.rowCount(), 0, "griglia vuota")
    ctx.check(not view.first_button.isEnabled(), "primo disabilitato")
    ctx.check(not view.last_button.isEnabled(), "ultimo disabilitato")
    ctx.check("Record 0 di 0" in view.status.text(), "stato vuoto")
    Rowset(project.db, view.table).insert({"codice": "C001", "nome": "Uno"})
    view.refresh()
    ctx.check_close(view.grid.rowCount(), 1, "refresh dopo inserimento esterno")
    view.first_record()
    ctx.check(not view.next_button.isEnabled(), "successivo disabilitato su un record")
    Rowset(project.db, view.table).insert({"codice": "C002", "nome": "Due"})
    view.refresh()
    ctx.check_close(view.grid.rowCount(), 2, "secondo refresh")
    view.last_record()
    ctx.check_close(view.rowset.current["codice"], "C002", "ultimo dopo refresh")
