from dbx.core import types as T
from dbx.core.form_model import FormSpec, form_references
from dbx.core.metadata import Field, Table


def sample_table() -> Table:
    return Table(
        name="clienti",
        caption="Clienti",
        fields=[
            Field("nome", T.TEXT, caption="Nome"),
            Field("anni", T.INTEGER),
            Field("attivo", T.BOOLEAN),
            Field("note", T.MEMO),
        ],
    )


def test_create_form_from_table():
    spec = FormSpec.create(sample_table())
    assert spec.name == "form_clienti"
    assert spec.table == "clienti"
    assert spec.validate() == []
    kinds = [c.kind for c in spec.all_controls()]
    assert "label" in kinds and "number" in kinds and "checkbox" in kinds and "memo" in kinds
    assert {c.action for c in spec.all_controls() if c.kind == "button"} >= {"save", "new", "delete"}


def test_roundtrip_form():
    spec = FormSpec.create(sample_table())
    clone = FormSpec.from_dict(spec.to_dict())
    assert clone.to_dict() == spec.to_dict()
    assert len(clone.all_controls()) == len(spec.all_controls())


def test_master_detail_adds_grid_and_reference():
    spec = FormSpec.create_master_detail(
        Table(name="clienti", fields=[Field("nome")]),
        Table(name="fatture", fields=[Field("cliente"), Field("totale", T.DECIMAL)]),
        "id",
        "cliente",
    )
    grid = [c for c in spec.all_controls() if c.kind == "grid"]
    assert len(grid) == 1
    assert grid[0].table == "fatture"
    assert form_references(spec) == {"clienti", "fatture"}


def test_validation_reports_missing_table_and_field():
    spec = FormSpec(name="x", table="")
    spec.pages[0].controls.append(
        __import__("dbx.core.form_model", fromlist=["FormControl"]).FormControl(id="c", kind="field", field="")
    )
    errors = spec.validate()
    assert any("tabella" in e.lower() for e in errors)
    assert any("campo" in e.lower() for e in errors)
