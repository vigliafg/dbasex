"""Scenari B — Table Structure, metadati, validazione e Table Expert."""

from __future__ import annotations

from unittest import mock

from dbx.core import types as T
from dbx.core.ddl import quote
from dbx.core.input_rules import InputRules
from dbx.core.metadata import Field, ForeignKey, Index, Table
from dbx.designers.table_builder import COL_INDEX, COL_NAME, COL_TYPE, TableBuilderDialog
from dbx.designers.table_expert import TEMPLATES, TableExpert
from dbx.runtime.rowset import Rowset
from dbx.runtime.validation import ValidationError, resolve_choices
from dbx.ui.data_view import DataView, choice_label

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _builder_apply(ctx: E2EContext, project, table: Table) -> TableBuilderDialog:
    builder = ctx.table_builder(project, table)
    builder._apply()
    return builder


@scenario(
    "tbl-01-new-minimal",
    "B01 — Nuova tabella minima dal Table Builder",
    "tables",
    features=("TB-NEW", "TB-CAPTION", "TB-DDL", "TB-REMOVE"),
    min_checks=7,
    budget_s=8.0,
    screenshots=("table-new-minimal",),
)
def tbl_new_minimal(ctx: E2EContext) -> None:
    project = ctx.new_project("Tabelle")
    builder = ctx.table_builder(project)
    ctx.check_close(builder.name_edit.text(), "", "nome iniziale vuoto")
    builder.name_edit.setText("contatti")
    builder.caption_edit.setText("Rubrica contatti")
    builder.fields_grid.item(0, COL_NAME).setText("codice")
    builder._add_field_row(Field("email", T.TEXT, size=80))
    builder._add_field_row(Field("temporaneo", T.TEXT))
    builder.fields_grid.setCurrentCell(builder.fields_grid.rowCount() - 1, COL_NAME)
    builder._remove_field_row()
    ctx.check_close(builder.fields_grid.rowCount(), 2, "campo temporaneo rimosso")
    ctx.check("CREATE TABLE" in builder.ddl_view.toPlainText().upper(), "DDL di creazione mostrato")
    builder._apply()
    project = ctx.reopen(project)
    table = project.require_table("contatti")
    ctx.check_close(table.caption, "Rubrica contatti", "didascalia persistita")
    ctx.check_close([field.name for field in table.fields], ["codice", "email"], "campi persistiti")
    ctx.check_close(table.field("email").size, 80, "larghezza campo")
    ctx.check((project.objects_path / "tables" / "contatti.table.json").exists(), "JSON su disco")
    ctx.capture(builder, "table-new-minimal", (1040, 720))


@scenario(
    "tbl-02-all-types",
    "B02 — Tutti i tipi campo",
    "tables",
    features=(
        "TB-NEW",
        *(f"TB-TYPE-{item.upper()}" for item in T.ALL_TYPES),
    ),
    min_checks=8,
    budget_s=8.0,
    screenshots=("table-all-types",),
)
def tbl_all_types(ctx: E2EContext) -> None:
    project = ctx.new_project("Tipi")
    table = fixtures.tutti_tipi_table()
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    saved = project.require_table("tutti_tipi")
    ctx.check_close(
        [field.type for field in saved.fields],
        [field.type for field in table.fields],
        "tipi persistiti",
    )
    ctx.check_close(len(saved.fields), 9, "nove campi")
    rowset = Rowset(project.db, saved)
    record_id = rowset.insert(
        {
            "testo": "ciao",
            "intero": 42,
            "decimale": 12.5,
            "data": "2026-01-10",
            "dataora": "2026-01-10 08:30:00",
            "booleano": True,
            "lungo": "testo lungo",
            "scelta": "A",
            "allegato": b"\x00\x01",
        }
    )
    row = rowset.load(record_id)
    ctx.check_close(row["intero"], 42, "intero memorizzato")
    ctx.check_close(str(row["data"]), "2026-01-10", "data memorizzata")
    ctx.check(row["allegato"] == b"\x00\x01", "BLOB memorizzato")
    ctx.check_close(row["scelta"], "A", "scelta memorizzata")
    ctx.check(T.format_value(row["decimale"], T.DECIMAL, saved.field("decimale").fmt) != "", "formato decimale")
    view = ctx.data_view(project, "tutti_tipi")
    ctx.check_close(view.grid.rowCount(), 1, "DataView mostra il record")
    ctx.capture(view, "table-all-types", (1000, 620))


@scenario(
    "tbl-03-field-attributes",
    "B03 — Attributi campo e formati",
    "tables",
    features=(
        "TB-FIELD-REQUIRED",
        "TB-FIELD-DEFAULT",
        "TB-FIELD-CAPTION",
        "TB-FIELD-FORMAT",
        "TB-CAPTION",
    ),
    min_checks=9,
    budget_s=8.0,
)
def tbl_field_attributes(ctx: E2EContext) -> None:
    project = ctx.new_project("Attributi")
    table = Table(
        name="articoli",
        caption="Articoli",
        fields=[
            Field("codice", T.TEXT, size=10, required=True, pk=True, caption="Codice articolo"),
            Field("prezzo", T.DECIMAL, size=12, fmt="###,##0.00", default="0"),
            Field("giacenza", T.INTEGER, default="0"),
            Field("attivo", T.BOOLEAN, default="1"),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    saved = project.require_table("articoli")
    ctx.check(saved.field("codice").required, "obbligatorietà persistita")
    ctx.check_close(saved.field("codice").caption, "Codice articolo", "didascalia campo")
    ctx.check_close(saved.field("prezzo").fmt, "###,##0.00", "formato decimale")
    ctx.check_close(saved.field("attivo").default, "1", "default booleano")
    rowset = Rowset(project.db, saved)
    record_id = rowset.insert({"codice": "A1", "prezzo": 1234.5})
    row = rowset.load(record_id)
    ctx.check_close(float(row["prezzo"]), 1234.5, "prezzo memorizzato")
    ctx.check(bool(row["attivo"]) is True, "default booleano applicato")
    view = ctx.data_view(project, "articoli")
    ctx.check_close(view.grid.horizontalHeaderItem(0).text(), "Codice articolo", "intestazione con didascalia")
    ctx.check("1.234,50" in view.grid.item(0, 1).text() or "1234" in view.grid.item(0, 1).text(), "formato visibile")
    with ctx.expect_error(ValidationError, "Obbligatorio"):
        rowset.insert({"prezzo": 1})


@scenario(
    "tbl-04-required-conditional",
    "B04 — Obbligatorietà semplice e condizionale",
    "tables",
    features=("TB-FIELD-REQUIRED", "TB-FIELD-REQUIRED-IF", "TB-FIELD-SKIP-IF"),
    min_checks=5,
    budget_s=8.0,
)
def tbl_required_conditional(ctx: E2EContext) -> None:
    project = ctx.new_project("Obblighi")
    table = Table(
        name="iscritti",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("attivo", T.BOOLEAN, default="1"),
            Field("email", T.TEXT, size=60, required_expr="[attivo] = .T."),
            Field("motivo", T.TEXT, size=60, skip_expr="[attivo] = .T."),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    rowset = Rowset(project.db, project.require_table("iscritti"))
    with ctx.expect_error(ValidationError, "Obbligatorio"):
        rowset.insert({"codice": "I1", "attivo": True})
    record_id = rowset.insert({"codice": "I1", "attivo": False})
    ctx.check(record_id > 0, "record non attivo senza email accettato")
    rowset.insert({"codice": "I2", "attivo": True, "email": "a@b.it"})
    ctx.check_close(rowset.count(), 2, "due record")
    ctx.check("attivo" in str(project.require_table("iscritti").field("email").required_expr), "condizione persistita")
    ctx.check("attivo" in str(project.require_table("iscritti").field("motivo").skip_expr), "salto persistito")


@scenario(
    "tbl-05-rule",
    "B05 — Regola di validazione con messaggio",
    "tables",
    features=("TB-FIELD-RULE", "TB-FIELD-RULE-MSG"),
    min_checks=4,
    budget_s=6.0,
)
def tbl_rule(ctx: E2EContext) -> None:
    project = ctx.new_project("Regole")
    table = Table(
        name="soci",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("eta", T.INTEGER, rule="[eta] >= 18", rule_message="Serve almeno 18 anni"),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    rowset = Rowset(project.db, project.require_table("soci"))
    with ctx.expect_error(ValidationError, "Serve almeno 18 anni"):
        rowset.insert({"codice": "S1", "eta": 17})
    rowset.insert({"codice": "S2", "eta": 18})
    ctx.check_close(rowset.count(), 1, "solo il maggiorenne inserito")
    ctx.check_close(project.require_table("soci").field("eta").rule, "[eta] >= 18", "regola persistita")
    ctx.check_close(
        project.require_table("soci").field("eta").rule_message,
        "Serve almeno 18 anni",
        "messaggio persistito",
    )


@scenario(
    "tbl-06-calculated",
    "B06 — Campo calcolato e ricalcolo",
    "tables",
    features=("TB-FIELD-CALCULATED", "DV-CALCULATED"),
    min_checks=5,
    budget_s=8.0,
)
def tbl_calculated(ctx: E2EContext) -> None:
    project = ctx.new_project("Calcolati")
    table = Table(
        name="righe",
        fields=[
            Field("codice", T.TEXT, size=8, pk=True, required=True),
            Field("prezzo", T.DECIMAL, size=12, default="0"),
            Field("quantita", T.INTEGER, default="1"),
            Field("totale", T.DECIMAL, calculated="[prezzo] * [quantita]"),
            Field("etichetta", T.TEXT, calculated='UPPER([codice]) + " - " + [codice]'),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    rowset = Rowset(project.db, project.require_table("righe"))
    record_id = rowset.insert({"codice": "r1", "prezzo": 10, "quantita": 3})
    row = rowset.load(record_id)
    ctx.check_close(float(row["totale"]), 30.0, "totale calcolato")
    ctx.check_close(row["etichetta"], "R1 - r1", "espressione con stringhe")
    rowset.update(record_id, {"prezzo": 12.5})
    ctx.check_close(float(rowset.load(record_id)["totale"]), 37.5, "ricalcolo dopo modifica")
    view = ctx.data_view(project, "righe")
    totale_column = [field.name for field in project.require_table("righe").fields].index("totale")
    item = view.grid.item(0, totale_column)
    from PyQt6.QtCore import Qt

    ctx.check(not bool(item.flags() & Qt.ItemFlag.ItemIsEditable), "calcolato in sola lettura")
    ctx.check("calcolato" in item.toolTip().lower(), "tooltip calcolato")


@scenario(
    "tbl-07-auto-enter",
    "B07 — Auto-enter, serie e date automatiche",
    "tables",
    features=(
        "TB-FIELD-AUTOENTER",
        "TB-FIELD-INCREMENT",
        "TB-FIELD-AUTODATE",
    ),
    min_checks=8,
    budget_s=8.0,
)
def tbl_auto_enter(ctx: E2EContext) -> None:
    project = ctx.new_project("Automatici")
    table = Table(
        name="pratiche",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("progressivo", T.INTEGER, increment="records"),
            Field("revisione", T.INTEGER, increment="updates"),
            Field("creato", T.DATE, auto_date="insert"),
            Field("modificato", T.DATE, auto_date="update"),
            Field("stato", T.TEXT, size=20, auto_enter='"nuovo"'),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    rowset = Rowset(project.db, project.require_table("pratiche"))
    first = rowset.insert({"codice": "P1"})
    second = rowset.insert({"codice": "P2"})
    row1 = rowset.load(first)
    ctx.check_close(row1["progressivo"], 1, "prima serie")
    ctx.check_close(rowset.load(second)["progressivo"], 2, "seconda serie")
    ctx.check_close(row1["revisione"], 1, "revisione iniziale")
    ctx.check(row1["creato"] is not None, "data di creazione")
    ctx.check_close(row1["stato"], "nuovo", "auto-enter applicato")
    rowset.update(first, {"stato": "chiuso"})
    updated = rowset.load(first)
    ctx.check_close(updated["revisione"], 2, "revisione incrementata")
    ctx.check(updated["modificato"] is not None, "data di modifica")
    ctx.check_close(updated["progressivo"], 1, "serie invariata in modifica")


@scenario(
    "tbl-08-choice-static",
    "B08 — Scelta statica, etichette e testo libero",
    "tables",
    features=(
        "TB-FIELD-CHOICE-STATIC",
        "TB-FIELD-CHOICE-LABELS",
        "TB-FIELD-CHOICE-CASE",
        "TB-FIELD-CHOICE-BLANK",
        "TB-FIELD-CHOICE-OTHER",
    ),
    min_checks=8,
    budget_s=8.0,
)
def tbl_choice_static(ctx: E2EContext) -> None:
    project = ctx.new_project("Scelte")
    table = Table(
        name="ticket",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field(
                "stato",
                T.CHOICE,
                choices=[{"value": "A", "label": "Aperto"}, {"value": "C", "label": "Chiuso"}],
                choice_allow_blank=True,
                choice_allow_other=False,
            ),
            Field(
                "reparto",
                T.CHOICE,
                choices=[{"value": "IT", "label": "Informatica"}, {"value": "AM", "label": "Amministrazione"}],
                choice_case_sensitive=False,
                choice_allow_other=True,
            ),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    saved = project.require_table("ticket")
    field = saved.field("stato")
    options = resolve_choices(field, project.db)
    ctx.check_close([option.value for option in options], ["A", "C"], "valori statici")
    ctx.check_close(choice_label(field, "A", project.db), "Aperto", "etichetta Scelta")
    rowset = Rowset(project.db, saved)
    row_id = rowset.insert({"codice": "T1", "stato": "A", "reparto": "it"})
    row = rowset.load(row_id)
    ctx.check_close(row["stato"], "A", "valore valido")
    ctx.check_close(row["reparto"], "IT", "normalizzazione maiuscole Scelta")
    ctx.check(rowset.insert({"codice": "T2", "stato": ""}) > 0, "vuoto ammesso")
    with ctx.expect_error(ValidationError, "non ammesso"):
        rowset.insert({"codice": "T3", "stato": "X"})
    ctx.check(rowset.insert({"codice": "T4", "reparto": "ALTRO"}) > 0, "testo libero con avviso")
    ctx.check(any("fuori elenco" in issue.message for issue in rowset.validate_report({"codice": "T5", "reparto": "ALTRO"}).issues), "avviso testo libero")


@scenario(
    "tbl-09-choice-dynamic",
    "B09 — Scelta dinamica da tabella",
    "tables",
    features=("TB-FIELD-CHOICE-DYNAMIC", "TB-FIELD-CHOICE-COMBINE", "TB-FIELD-CHOICE-LABELS"),
    min_checks=6,
    budget_s=8.0,
)
def tbl_choice_dynamic(ctx: E2EContext) -> None:
    project = ctx.new_project("SceltaDinamica")
    stati = Table(
        name="stati",
        fields=[
            Field("codice", T.TEXT, size=4, required=True, pk=True),
            Field("descrizione", T.TEXT, size=30),
        ],
    )
    ordini = Table(
        name="ordini",
        fields=[
            Field("numero", T.INTEGER, required=True, pk=True),
            Field(
                "stato",
                T.CHOICE,
                choice_source="table",
                choice_table="stati",
                choice_value="codice",
                choice_label="descrizione",
                choice_combine="replace",
            ),
            Field(
                "priorita",
                T.CHOICE,
                choices=[{"value": "N", "label": "Normale"}],
                choice_source="table",
                choice_table="stati",
                choice_value="codice",
                choice_label="descrizione",
                choice_combine="append",
            ),
        ],
    )
    fixtures.apply(project, stati, ordini)
    for code, label in (("AP", "Aperto"), ("CH", "Chiuso")):
        Rowset(project.db, stati).insert({"codice": code, "descrizione": label})
    project = ctx.reopen(project)
    saved = project.require_table("ordini")
    field = saved.field("stato")
    options = resolve_choices(field, project.db)
    ctx.check_close([option.label for option in options], ["Aperto", "Chiuso"], "etichette dinamiche")
    rowset = Rowset(project.db, saved)
    row_id = rowset.insert({"numero": 1, "stato": "AP", "priorita": "CH"})
    ctx.check_close(rowset.load(row_id)["stato"], "AP", "valore dinamico")
    ctx.check_close(choice_label(field, "CH", project.db), "Chiuso", "etichetta risolta")
    priorita = saved.field("priorita")
    ctx.check_close(
        [option.value for option in resolve_choices(priorita, project.db)],
        ["N", "AP", "CH"],
        "combinazione append",
    )
    with ctx.expect_error(ValidationError, "non ammesso"):
        rowset.insert({"numero": 2, "stato": "ZZ"})
    ctx.check(project.require_table("ordini").field("stato").choice_combine == "replace", "replace persistito")


@scenario(
    "tbl-10-domain-mask-case",
    "B10 — Dominio, maschere e maiuscole",
    "tables",
    features=(
        "TB-FIELD-DOMAIN",
        "TB-FIELD-DOMAIN-RANGES",
        "TB-FIELD-MASK",
        "TB-FIELD-CASE",
    ),
    min_checks=9,
    budget_s=8.0,
)
def tbl_domain_mask_case(ctx: E2EContext) -> None:
    project = ctx.new_project("Domini")
    table = Table(
        name="misure",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True),
            Field("voto", T.INTEGER, domain_min="1", domain_max="10"),
            Field("fascia", T.DECIMAL, domain_ranges=[["0", "5"], ["10", "20"]]),
            Field("targa", T.TEXT, size=7, mask="AA 999"),
            Field("sigla", T.TEXT, size=10, case_mode="upper"),
        ],
    )
    _builder_apply(ctx, project, table)
    project = ctx.reopen(project)
    saved = project.require_table("misure")
    ctx.check_close(saved.field("voto").domain_min, "1", "minimo persistito")
    ctx.check_close(saved.field("voto").domain_max, "10", "massimo persistito")
    ctx.check_close(len(saved.field("fascia").domain_ranges), 2, "due intervalli")
    rowset = Rowset(project.db, saved)
    with ctx.expect_error(ValidationError, "compreso"):
        rowset.insert({"codice": "M1", "voto": 11})
    with ctx.expect_error(ValidationError, "intervallo"):
        rowset.insert({"codice": "M2", "fascia": 7})
    row_id = rowset.insert({"codice": "M3", "voto": 8, "fascia": 12, "sigla": "abc"})
    ctx.check(row_id > 0, "valori nel dominio accettati")
    targa = saved.field("targa")
    ctx.check_close(InputRules.shape(targa, "ab 123"), "AB 123", "maschera applicata")
    ctx.check(not InputRules.fits("AA 999", "ab12"), "maschera incompleta rifiutata")
    ctx.check_close(InputRules.apply_case("ciao mondo", "upper"), "CIAO MONDO", "maiuscole")
    ctx.check_close(InputRules.apply_case("ciao mondo", "title"), "Ciao Mondo", "iniziali maiuscole")


@scenario(
    "tbl-11-indexes-relations",
    "B11 — Indici e relazioni con azioni ON DELETE",
    "tables",
    features=(
        "TB-INDEX",
        "TB-INDEX-UNIQUE",
        "TB-INDEX-COMPOSITE",
        "TB-FK",
        *(f"TB-ONDELETE-{item.replace(' ', '-')}" for item in ("NO ACTION", "CASCADE", "SET NULL", "RESTRICT")),
    ),
    min_checks=10,
    budget_s=10.0,
)
def tbl_indexes_relations(ctx: E2EContext) -> None:
    project = ctx.new_project("Relazioni")
    parent = fixtures.clienti_table()
    parent.indexes.append(Index(fields=["citta", "nome"]))
    fixtures.apply(project, parent)
    fixtures.seed_clienti(project)
    actions = ("NO ACTION", "CASCADE", "SET NULL", "RESTRICT")
    for position, action in enumerate(actions, start=1):
        child = Table(
            name=f"figli_{position}",
            fields=[
                Field("id", T.INTEGER, required=True, pk=True),
                Field("cliente", T.TEXT, size=8),
            ],
            foreign_keys=[
                ForeignKey(
                    columns=["cliente"],
                    ref_table="clienti",
                    ref_columns=["codice"],
                    on_delete=action,
                )
            ],
        )
        project.apply_table(child, backup=False)
    project = ctx.reopen(project)
    saved = project.require_table("clienti")
    names = [index.resolved_name(saved.name) for index in saved.indexes]
    ctx.check(any("citta" in name for name in names), "indice composto presente")
    ctx.check(any(index.unique for index in saved.indexes), "indice univoco presente")
    for position, action in enumerate(actions, start=1):
        rows = project.db.query(f'PRAGMA foreign_key_list("figli_{position}")')
        ctx.check_close(str(rows[0]["on_delete"]).upper(), action, f"ON DELETE {action} nel database")
    ctx.check(any(fk.ref_table == "clienti" for fk in project.require_table("figli_1").foreign_keys), "FK nel metadato")
    rowset = Rowset(project.db, project.require_table("figli_1"))
    with ctx.expect_error(Exception, "FOREIGN KEY"):
        rowset.insert({"id": 1, "cliente": "ASSENTE"})
    ctx.check(rowset.insert({"id": 1, "cliente": "C001"}) > 0, "FK valida accettata")
    ctx.check(project.db.query(f'PRAGMA index_list("clienti")'), "indici creati in SQLite")


@scenario(
    "tbl-12-migration-saveas",
    "B12 — Migrazione, backup, Save As e stampa struttura",
    "tables",
    features=(
        "TB-MIGRATE",
        "TB-BACKUP",
        "TB-SAVE-AS",
        "TB-PRINT",
        "TB-REORDER",
        "TB-ADD-RECORDS",
        "TB-STATS",
    ),
    min_checks=9,
    budget_s=12.0,
)
def tbl_migration_saveas(ctx: E2EContext) -> None:
    project = ctx.new_project("Migrazione")
    fixtures.apply(project, fixtures.clienti_table())
    fixtures.seed_clienti(project)
    builder = ctx.table_builder(project, project.require_table("clienti"))
    note_row = [index for index, field in enumerate(builder.current_table().fields) if field.name == "note"][0]
    builder.fields_grid.setCurrentCell(note_row, COL_NAME)
    builder._remove_field_row()
    builder._add_field_row(Field("telefono", T.TEXT, size=30))
    builder.fields_grid.setCurrentCell(builder.fields_grid.rowCount() - 1, COL_NAME)
    builder._move_field_to(builder.fields_grid.rowCount() - 1, 1)
    builder._apply()
    ctx.check((project.backups_path / "x").parent.exists(), "cartella backup presente")
    ctx.check(any(project.backups_path.iterdir()), "backup creato dalla migrazione")
    project = ctx.reopen(project)
    migrated = project.require_table("clienti")
    ctx.check(migrated.field("telefono") is not None, "campo aggiunto")
    ctx.check(migrated.field("note") is None, "campo rimosso")
    ctx.check_close(migrated.fields[1].name, "telefono", "campo riordinato")
    ctx.check_close(Rowset(project.db, migrated).open().count(), 5, "dati preservati")
    builder = ctx.table_builder(project, migrated)
    added = builder.add_records(2)
    ctx.check_close(added, 2, "Add Records")
    ctx.check("Records: 7" in builder.records_label.text(), "statistiche aggiornate")
    copy = builder.save_as("clienti_copia")
    ctx.check(copy is not None, "Save As eseguito")
    ctx.check("clienti_copia" in project.names("tables"), "tabella copiata")
    with mock.patch("PyQt6.QtPrintSupport.QPrintDialog.exec", return_value=1), mock.patch(
        "PyQt6.QtGui.QTextDocument.print", return_value=None
    ):
        builder.print_structure()
    ctx.check("MODIFICHE PIANIFICATE" in builder.ddl_view.toPlainText().upper() or "CREATE TABLE" in builder.ddl_view.toPlainText().upper(), "DDL disponibile per la stampa")
    ctx.check(len(project.names("tables")) == 2, "due tabelle dopo Save As")


@scenario(
    "tbl-13-expert",
    "B13 — Table Expert",
    "tables",
    features=("TB-EXPERT", "TB-EXPERT-TEMPLATE", "TB-EXPERT-FIELDS", "TB-EXPERT-INDEXES"),
    min_checks=9,
    budget_s=10.0,
    screenshots=("table-expert",),
)
def tbl_expert(ctx: E2EContext) -> None:
    project = ctx.new_project("EspertoTabella")
    expert = ctx.track(TableExpert(project, suggested_name="rubrica"))
    ctx.check_close(expert.template_combo.count(), len(TEMPLATES), "tutti i template elencati")
    seen: list[str] = []
    for index in range(expert.template_combo.count()):
        expert.template_combo.setCurrentIndex(index)
        key = str(expert.template_combo.currentData())
        if key == "vuota":
            seen.append(key)
            ctx.check(expert.template_description.text() != "", "template vuoto descritto")
            continue
        table = expert.build_table()
        seen.append(key)
        ctx.check(table.fields, f"template {key} costruisce campi")
    expert.template_combo.setCurrentIndex(expert.template_combo.findData("contatti"))
    expert.name_edit.setText("rubrica")
    expert.caption_edit.setText("Rubrica contatti")
    table = expert.build_table()
    ctx.check_close([field.name for field in table.fields][:2], ["nome", "cognome"], "campi del template")
    ctx.check(table.indexes, "indici suggeriti")
    expert.initializePage(3)
    ctx.check("CREATE TABLE" in expert.summary_view.toPlainText().upper(), "DDL nel riepilogo")
    project.apply_table(table, backup=False)
    ctx.check("rubrica" in project.names("tables"), "tabella esperta applicata")
    ctx.check_close(len(seen), len(TEMPLATES), "template attraversati")
    ctx.capture(expert, "table-expert", (760, 560))
