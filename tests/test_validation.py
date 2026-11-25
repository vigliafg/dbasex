"""Test della validazione strutturata dei campi (piano validazione)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.db import Database
from dbx.core.ddl import apply_migration
from dbx.core.metadata import Field, MetadataError, Table
from dbx.runtime.rowset import Rowset, RowsetError, re_evaluate
from dbx.runtime.validation import (
    ValidationError,
    ValidationIssue,
    ValidationReport,
)


def make_rowset(configure=None) -> Rowset:
    db = Database(":memory:")
    table = Table(
        name="contatti",
        fields=[
            Field("nome", T.TEXT, required=True),
            Field("tipo", T.TEXT),
            Field("email", T.TEXT),
            Field("note", T.TEXT, required=True),
            Field("codice", T.TEXT, rule="LEN([codice]) >= 3"),
            Field("anni", T.INTEGER),
        ],
    )
    if configure is not None:
        configure(table)
    apply_migration(db.con, table, None)
    return Rowset(db, table)


def test_validation_error_is_a_rowset_error_and_exposes_issues():
    issue = ValidationIssue(field="nome", message="Nome obbligatorio", code="required")
    error = ValidationError([issue])
    assert isinstance(error, RowsetError)
    assert error.issues == [issue]
    assert "Nome obbligatorio" in str(error)


def test_validation_report_separates_errors_and_warnings():
    report = ValidationReport()
    report.add("a", "errore", "rule")
    report.add("b", "avviso", "choice_other", severity="warning")
    assert len(report.errors) == 1
    assert len(report.warnings) == 1
    assert not report.ok
    assert report.messages() == ["errore", "avviso"]


def test_required_reports_structured_issue():
    rowset = make_rowset()
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": " ", "note": "x", "codice": "ABC"})
    assert [issue.code for issue in exc.value.issues] == ["required"]
    assert exc.value.issues[0].field == "nome"


def test_required_expr_wins_over_boolean_required():
    def setup(table):
        table.field("email").required_expr = "[tipo] = 'cliente'"

    rowset = make_rowset(setup)
    rowset.insert({"nome": "Ada", "note": "x", "codice": "ABC", "tipo": "fornitore"})
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": "Bob", "note": "x", "codice": "DEF", "tipo": "cliente"})
    assert any(issue.code == "required" and issue.field == "email" for issue in exc.value.issues)


def test_skip_expr_excludes_required():
    def setup(table):
        table.field("note").skip_expr = "[tipo] = 'senza-note'"

    rowset = make_rowset(setup)
    rowset.insert({"nome": "Ada", "tipo": "senza-note", "codice": "ABC"})
    with pytest.raises(ValidationError):
        rowset.insert({"nome": "Bob", "tipo": "con-note", "codice": "DEF"})


def test_rule_message_replaces_default_message():
    rowset = make_rowset()
    field = rowset.table.field("codice")
    field.rule_message = "Il codice è troppo corto"
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": "Ada", "note": "x", "codice": "AB"})
    assert exc.value.issues[0].message == "Il codice è troppo corto"


def test_only_validates_a_single_field():
    rowset = make_rowset()
    record_id = rowset.insert({"nome": "Ada", "note": "x", "codice": "ABC"})
    rowset.update(record_id, {"anni": 36}, only={"anni"})
    assert rowset.load(record_id)["anni"] == 36


def test_only_allows_valid_cell_with_other_required_field_empty():
    rowset = make_rowset()
    record_id = rowset.insert({"nome": "Ada", "note": "x", "codice": "ABC"})
    rowset.update(record_id, {"note": ""}, validate=False)
    # La cella valida si salva anche con un altro campo obbligatorio vuoto.
    prepared = rowset.validate_field(record_id, "anni", 40)
    assert prepared["anni"] == 40
    with pytest.raises(ValidationError):
        rowset.validate(rowset.load(record_id))


def test_validate_field_does_not_write():
    rowset = make_rowset()
    record_id = rowset.insert({"nome": "Ada", "note": "x", "codice": "ABC"})
    rowset.validate_field(record_id, "anni", 40)
    assert rowset.load(record_id)["anni"] is None
    with pytest.raises(ValidationError):
        rowset.validate_field(record_id, "codice", "AB")


def test_insert_without_validation_skips_rules():
    rowset = make_rowset()
    record_id = rowset.insert(
        {"nome": "Ada", "note": "x", "codice": "AB"},
        validate=False,
    )
    assert rowset.load(record_id)["codice"] == "AB"


def test_metadata_roundtrip_of_new_validation_fields():
    field = Field(
        "stato",
        T.TEXT,
        rule_message="Valore non ammesso",
        required_expr="[attivo] = .T.",
        skip_expr="[tipo] = 'x'",
    )
    clone = Field.from_dict(field.to_dict())
    assert clone == field


def test_metadata_rejects_invalid_validation_expressions():
    with pytest.raises(MetadataError):
        Field("x", T.TEXT, required_expr="LEN(").validate()
    with pytest.raises(MetadataError):
        Field("x", T.TEXT, skip_expr="LEN(").validate()


def test_check_insert_dry_run_does_not_write():
    rowset = make_rowset()
    rowset.check_insert({"nome": "Ada", "note": "x", "codice": "ABC"})
    assert rowset.count() == 0


# ------------------------------------------------------------------ Scelta
from dbx.runtime.validation import (  # noqa: E402
    ChoiceOption,
    ChoiceSourceError,
    match_choice,
    resolve_choices,
    touch_choices,
)


def choice_rowset(**field_kwargs) -> Rowset:
    db = Database(":memory:")
    table = Table(
        name="clienti",
        fields=[
            Field("nome", T.TEXT),
            Field("stato", T.CHOICE, **field_kwargs),
        ],
    )
    apply_migration(db.con, table, None)
    return Rowset(db, table)


def test_choice_is_a_text_type():
    assert T.CHOICE in T.ALL_TYPES
    assert T.is_text_like(T.CHOICE)
    assert T.sql_type(T.CHOICE) == "TEXT"
    assert T.label(T.CHOICE) == "Scelta"
    assert T.to_storage("A", T.CHOICE) == "A"
    assert T.from_storage("A", T.CHOICE) == "A"


def test_static_choice_accepts_listed_value_and_canonicalizes_case():
    rowset = choice_rowset(
        choices=[{"value": "A", "label": "Attivo"}, {"value": "S", "label": "Sospeso"}],
        choice_case_sensitive=False,
    )
    record_id = rowset.insert({"nome": "Ada", "stato": "a"})
    assert rowset.load(record_id)["stato"] == "A"


def test_static_choice_rejects_value_outside_list():
    rowset = choice_rowset(choices=[{"value": "A", "label": "Attivo"}])
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": "Ada", "stato": "X"})
    assert exc.value.issues[0].code == "choice"


def test_choice_allow_other_is_a_warning():
    rowset = choice_rowset(
        choices=[{"value": "A", "label": "Attivo"}],
        choice_allow_other=True,
    )
    record_id = rowset.insert({"nome": "Ada", "stato": "X"})
    assert rowset.load(record_id)["stato"] == "X"
    assert rowset.last_warnings and rowset.last_warnings[0].code == "choice_other"


def test_choice_blank_option_is_enforced():
    rowset = choice_rowset(
        choices=[{"value": "A", "label": "Attivo"}],
        choice_allow_blank=False,
    )
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": "Ada", "stato": ""})
    assert exc.value.issues[0].code == "choice"


def test_resolve_static_and_dynamic_append_and_replace():
    db = Database(":memory:")
    db.execute("CREATE TABLE stati (codice TEXT, descrizione TEXT)")
    db.execute("INSERT INTO stati VALUES ('A', 'Attivo'), ('S', 'Sospeso')")
    field = Field(
        "stato",
        T.CHOICE,
        choices=[{"value": "A", "label": "Attivo fisso"}, {"value": "X", "label": "Extra"}],
        choice_source="table",
        choice_table="stati",
        choice_value="codice",
        choice_label="descrizione",
        choice_combine="append",
    )
    field.validate()
    options = resolve_choices(field, db)
    assert [option.value for option in options] == ["A", "X", "S"]
    assert options[0].label == "Attivo fisso"
    field.choice_combine = "replace"
    options = resolve_choices(field, db)
    assert [option.value for option in options] == ["A", "S"]
    assert match_choice(field, "S", options) == ChoiceOption("S", "Sospeso")


def test_resolve_choice_source_is_cached_and_invalidated():
    db = Database(":memory:")
    db.execute("CREATE TABLE stati (codice TEXT)")
    db.execute("INSERT INTO stati VALUES ('A')")
    field = Field(
        "stato",
        T.CHOICE,
        choice_source="table",
        choice_table="stati",
        choice_value="codice",
    )
    assert [option.value for option in resolve_choices(field, db)] == ["A"]
    db.execute("INSERT INTO stati VALUES ('B')")
    assert [option.value for option in resolve_choices(field, db)] == ["A"]
    touch_choices("stati")
    assert [option.value for option in resolve_choices(field, db)] == ["A", "B"]


def test_missing_choice_source_blocks_with_clear_code():
    rowset = choice_rowset(
        choice_source="table",
        choice_table="inesistente",
        choice_value="codice",
    )
    with pytest.raises(ValidationError) as exc:
        rowset.insert({"nome": "Ada", "stato": "A"})
    assert exc.value.issues[0].code == "choice_source"


def test_choice_limit_is_enforced():
    db = Database(":memory:")
    db.execute("CREATE TABLE stati (codice TEXT)")
    for index in range(1001):
        db.execute("INSERT INTO stati VALUES (?)", (f"S{index}",))
    field = Field(
        "stato",
        T.CHOICE,
        choice_source="table",
        choice_table="stati",
        choice_value="codice",
    )
    with pytest.raises(ChoiceSourceError) as exc:
        resolve_choices(field, db)
    assert "1000" in str(exc.value)


def test_old_lookup_is_read_as_choice():
    field = Field.from_dict(
        {"name": "stato", "type": T.TEXT, "lookup": "stati.codice", "size": 4}
    )
    assert field.type == T.CHOICE
    assert field.choice_source == "table"
    assert field.choice_table == "stati"
    assert field.choice_value == "codice"
    assert field.choice_combine == "replace"
    assert field.choice_allow_other is True
    assert field.lookup == ""
    assert field.to_dict()["type"] == T.CHOICE
    assert "lookup" not in field.to_dict() or field.to_dict()["lookup"] == ""


def test_choice_roundtrip_serialization():
    field = Field(
        "stato",
        T.CHOICE,
        choices=[{"value": "A", "label": "Attivo"}],
        choice_source="table",
        choice_table="stati",
        choice_value="codice",
        choice_label="descrizione",
        choice_combine="append",
        choice_case_sensitive=False,
        choice_allow_blank=False,
        choice_allow_other=True,
    )
    assert Field.from_dict(field.to_dict()) == field


def test_choice_schema_rejects_bad_configuration():
    with pytest.raises(MetadataError):
        Field("x", T.TEXT, choices=[{"value": "A"}]).validate()
    with pytest.raises(MetadataError):
        Field("x", T.CHOICE, choice_source="query").validate()
    with pytest.raises(MetadataError):
        Field("x", T.CHOICE, choice_source="table", choice_table="t").validate()
    with pytest.raises(MetadataError):
        Field("x", T.CHOICE, choices=[{"value": "A"}, {"value": "A"}]).validate()
    with pytest.raises(MetadataError):
        Field("x", T.CHOICE, calculated="[a]").validate()


# ------------------------------------------------------------------ Dominio
from dbx.runtime.validation import domain_error, domain_intervals  # noqa: E402


def numeric_rowset(**field_kwargs) -> Rowset:
    db = Database(":memory:")
    table = Table(
        name="misure",
        fields=[
            Field("nome", T.TEXT),
            Field("valore", T.DECIMAL, **field_kwargs),
        ],
    )
    apply_migration(db.con, table, None)
    return Rowset(db, table)


def test_domain_min_max_is_inclusive():
    rowset = numeric_rowset(domain_min="0", domain_max="50")
    for value in ("0", "50", "12.5"):
        record_id = rowset.insert({"nome": "x", "valore": value})
        assert rowset.load(record_id)["valore"] in (0.0, 50.0, 12.5)
    for value in ("-0.01", "50.01"):
        with pytest.raises(ValidationError) as exc:
            rowset.insert({"nome": "x", "valore": value})
        assert [issue.code for issue in exc.value.issues] == ["domain"]


def test_domain_empty_value_passes():
    rowset = numeric_rowset(domain_min="1", domain_max="2")
    record_id = rowset.insert({"nome": "x", "valore": ""})
    assert rowset.load(record_id)["valore"] is None
    field = rowset.table.field("valore")
    assert domain_error(field, None) is None
    assert domain_error(field, "") is None


def test_domain_open_endpoints():
    field = Field("valore", T.DECIMAL, domain_min="10")
    assert domain_error(field, 9.99) is not None
    assert domain_error(field, 10) is None
    assert domain_error(field, 1_000_000) is None
    field = Field("valore", T.DECIMAL, domain_max="10")
    assert domain_error(field, 10.01) is not None
    assert domain_error(field, -1_000) is None


def test_domain_ranges_are_a_union():
    rowset = numeric_rowset(domain_ranges=[["1", "10"], ["20", "30"]])
    for value in ("1", "10", "20", "30"):
        assert rowset.insert({"nome": "x", "valore": value})
    for value in ("0", "11", "19", "31"):
        with pytest.raises(ValidationError) as exc:
            rowset.insert({"nome": "x", "valore": value})
        assert exc.value.issues[0].code == "domain"
    field = rowset.table.field("valore")
    assert domain_intervals(field) == [
        (__import__("decimal").Decimal("1"), __import__("decimal").Decimal("10")),
        (__import__("decimal").Decimal("20"), __import__("decimal").Decimal("30")),
    ]


def test_domain_decimal_comparison_has_no_binary_artifacts():
    field = Field("valore", T.DECIMAL, domain_min="0", domain_max="0.3")
    assert domain_error(field, 0.3) is None
    assert domain_error(field, 0.30000000000000004) is not None


def test_domain_custom_message_is_used_verbatim():
    field = Field(
        "valore",
        T.DECIMAL,
        domain_min="0",
        domain_max="50",
        domain_message="Lo sconto deve essere tra 0 e 50",
    )
    issue = domain_error(field, 51)
    assert issue is not None and issue.message == "Lo sconto deve essere tra 0 e 50"
    default = domain_error(Field("valore", T.DECIMAL, domain_min="0", domain_max="50"), 51)
    assert default is not None and "compreso tra 0 e 50" in default.message


def test_domain_schema_rules():
    with pytest.raises(MetadataError):
        Field("x", T.TEXT, domain_min="0").validate()
    with pytest.raises(MetadataError):
        Field("x", T.CHOICE, domain_min="0").validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, domain_min="10", domain_max="1").validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, domain_min="abc").validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, domain_ranges=[["1", "10"], ["20"]]).validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, domain_ranges=[["10", "1"]]).validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, domain_min="0", calculated="[y]").validate()


def test_domain_roundtrip_serialization():
    field = Field(
        "valore",
        T.DECIMAL,
        domain_min="0",
        domain_max="50",
        domain_message="Fuori dominio",
    )
    assert Field.from_dict(field.to_dict()) == field
    ranged = Field("valore", T.INTEGER, domain_ranges=[["1", "10"], ["20", "30"]])
    assert Field.from_dict(ranged.to_dict()) == ranged
    legacy = Field.from_dict({"name": "valore", "type": T.INTEGER})
    assert legacy.domain_min == "" and legacy.domain_ranges == []


# --------------------------------------------------------------- incremento
def increment_rowset(mode: str = "records") -> Rowset:
    db = Database(":memory:")
    table = Table(
        name="progressivi",
        fields=[
            Field("nome", T.TEXT),
            Field("numero", T.INTEGER, increment=mode),
        ],
    )
    apply_migration(db.con, table, None)
    return Rowset(db, table)


def test_increment_records_assigns_on_insert_and_preserves_on_update():
    rowset = increment_rowset("records")
    first = rowset.insert({"nome": "a"})
    second = rowset.insert({"nome": "b"})
    assert rowset.load(first)["numero"] == 1
    assert rowset.load(second)["numero"] == 2
    rowset.update(second, {"nome": "b2"})
    assert rowset.load(second)["numero"] == 2


def test_increment_updates_advances_the_single_record():
    rowset = increment_rowset("updates")
    first = rowset.insert({"nome": "a"})
    second = rowset.insert({"nome": "b"})
    # Il contatore di revisione è per record: entrambi partono da 1.
    assert rowset.load(first)["numero"] == 1
    assert rowset.load(second)["numero"] == 1
    rowset.update(first, {"nome": "a2"})
    assert rowset.load(first)["numero"] == 2
    rowset.update(first, {"nome": "a3"})
    assert rowset.load(first)["numero"] == 3
    rowset.update(second, {"nome": "b2"})
    assert rowset.load(second)["numero"] == 2


def test_increment_preserves_manual_value_on_insert():
    rowset = increment_rowset("records")
    record = rowset.insert({"nome": "a", "numero": 42})
    assert rowset.load(record)["numero"] == 42


def test_increment_legacy_auto_serial_is_written_as_increment():
    legacy = Field.from_dict(
        {"name": "numero", "type": T.INTEGER, "auto_serial": True}
    )
    assert legacy.increment == "records"
    data = legacy.to_dict()
    assert data["increment"] == "records"
    assert "auto_serial" not in data
    assert Field.from_dict(data).increment == "records"


def test_increment_schema_rules():
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, increment="sempre").validate()
    with pytest.raises(MetadataError):
        Field("x", T.TEXT, increment="records").validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, increment="records", calculated="1").validate()
    with pytest.raises(MetadataError):
        Field("x", T.INTEGER, increment="records", auto_date="insert").validate()


# --------------------------------------------------------------- re-evaluate
def reevaluate_rowset(**field_kwargs) -> tuple[Database, Table, Rowset]:
    db = Database(":memory:")
    table = Table(
        name="dati",
        fields=[
            Field("nome", T.TEXT, case_mode="upper"),
            Field(
                "stato",
                T.CHOICE,
                choices=[
                    {"value": "A", "label": "Attivo"},
                    {"value": "S", "label": "Sospeso"},
                ],
                **field_kwargs,
            ),
            Field("quantita", T.INTEGER, domain_min="1", domain_max="10"),
            Field("revisione", T.INTEGER, increment="updates"),
        ],
    )
    apply_migration(db.con, table, None)
    return db, table, Rowset(db, table)


def test_re_evaluate_applies_case_mode_without_touching_increment():
    db, table, rowset = reevaluate_rowset()
    record = rowset.insert({"nome": "ada", "stato": "A", "quantita": 5})
    assert rowset.load(record)["revisione"] == 1
    updated, issues = re_evaluate(table, db)
    assert updated == 1
    assert issues == []
    loaded = rowset.load(record)
    assert loaded["nome"] == "ADA"
    assert loaded["revisione"] == 1


def test_re_evaluate_reports_stale_choice_and_domain_as_warnings():
    db, table, rowset = reevaluate_rowset()
    record = rowset.insert(
        {"nome": "ada", "stato": "X", "quantita": 50}, validate=False
    )
    updated, issues = re_evaluate(table, db)
    assert updated == 1
    assert {issue.code for issue in issues} == {"choice_stale", "domain_stale"}
    assert all(issue.severity == "warning" for issue in issues)
    loaded = rowset.load(record)
    assert loaded["nome"] == "ADA"
    # I valori storici fuori elenco/dominio non vengono riscritti.
    assert loaded["stato"] == "X"
    assert loaded["quantita"] == 50


def test_re_evaluate_skips_records_with_blocking_errors():
    db = Database(":memory:")
    table = Table(
        name="regole",
        fields=[
            Field("nome", T.TEXT, required=True, case_mode="upper"),
            Field("codice", T.TEXT, rule="LEN([codice]) >= 3", case_mode="upper"),
        ],
    )
    apply_migration(db.con, table, None)
    rowset = Rowset(db, table)
    good = rowset.insert({"nome": "ada", "codice": "abc"})
    bad = rowset.insert({"nome": "bob", "codice": "x"}, validate=False)
    updated, issues = re_evaluate(table, db)
    assert updated == 1
    assert rowset.load(good)["nome"] == "ADA"
    assert rowset.load(bad)["nome"] == "bob"
    assert any(issue.code == "rule" and issue.is_error for issue in issues)


def test_re_evaluate_does_not_canonicalize_historical_choice_case():
    db, table, rowset = reevaluate_rowset(choice_case_sensitive=False)
    record = rowset.insert(
        {"nome": "ada", "stato": "a", "quantita": 5}, validate=False
    )
    _updated, issues = re_evaluate(table, db)
    assert issues == []
    # "a" corrisponde a "A" senza distinzione di maiuscole: si accetta, ma il
    # valore storico non viene sostituito con quello canonico.
    assert rowset.load(record)["stato"] == "a"
