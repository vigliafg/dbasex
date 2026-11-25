from dbx.core import types as T
from dbx.core.metadata import Field, ForeignKey, Index, MetadataError, Table, validate_project_tables


def make_table(name="clienti", fields=None):
    return Table(
        name=name,
        caption="Clienti",
        fields=fields
        or [
            Field("nome", T.TEXT, required=True),
            Field("anni", T.INTEGER),
        ],
    )


def test_roundtrip_serialization():
    table = make_table()
    table.indexes.append(Index(fields=["nome"], unique=True))
    table.foreign_keys.append(
        ForeignKey(columns=["nome"], ref_table="citta", ref_columns=["nome"], on_delete="CASCADE")
    )
    clone = Table.from_dict(table.to_dict())
    assert clone.to_dict() == table.to_dict()
    assert clone.field("NOME").name == "nome"


def test_validation_rejects_bad_names_and_duplicates():
    bad = Table(name="1tabella", fields=[Field("x")])
    try:
        bad.validate()
    except MetadataError as exc:
        assert "nome tabella" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("atteso errore sul nome tabella")

    dup = Table(name="t", fields=[Field("a"), Field("A")])
    try:
        dup.validate()
    except MetadataError as exc:
        assert "duplicato" in str(exc).lower()
    else:  # pragma: no cover
        raise AssertionError("atteso errore sul campo duplicato")


def test_index_name_and_lookup_validation():
    table = make_table()
    index = Index(fields=["nome"])
    assert index.resolved_name(table.name) == "idx_clienti_nome"
    field = Field("x", lookup="senza_punto")
    try:
        field.validate()
    except MetadataError:
        pass
    else:  # pragma: no cover
        raise AssertionError("lookup non valido accettato")


def test_cross_table_validation_reports_missing_reference():
    parent = Table(name="clienti", fields=[Field("codice")])
    child = Table(name="fatture", fields=[Field("cliente")])
    child.foreign_keys.append(ForeignKey(columns=["cliente"], ref_table="clienti", ref_columns=["codice"]))
    assert validate_project_tables([parent, child]) == []
    child.foreign_keys[0].ref_columns = ["inesistente"]
    errors = validate_project_tables([parent, child])
    assert errors and "inesistente" in errors[0]


def test_new_record_defaults():
    table = Table(
        name="t",
        fields=[
            Field("a", T.INTEGER),
            Field("b", T.TEXT, default="x"),
            Field("c", T.BOOLEAN),
        ],
    )
    record = table.new_record()
    assert record == {"a": 0, "b": "x", "c": 0}


def test_table_names_allow_internal_spaces():
    table = make_table(name="tabella 2")
    table.validate()
    clone = Table.from_dict(table.to_dict())
    clone.validate()
    assert clone.name == "tabella 2"

    for bad in (" tabella 2", "tabella  2", "tabella 2 ", "1tabella 2"):
        try:
            make_table(name=bad).validate()
        except MetadataError:
            continue
        raise AssertionError(f"nome tabella accettato: {bad!r}")


def test_references_accept_table_names_with_spaces():
    child = Table(name="figli", fields=[Field("codice")])
    child.foreign_keys.append(
        ForeignKey(
            columns=["codice"],
            ref_table="tabella 2",
            ref_columns=["codice"],
        )
    )
    child.validate()
    choice = Field(
        "stato",
        T.CHOICE,
        choice_source="table",
        choice_table="tabella 2",
        choice_value="codice",
    )
    choice.validate()
