import zipfile

import pytest

from dbx.designers.project_builder import BuildError, build_project, validate_project
from dbx.runtime.report_engine import ReportRenderer, ReportSpec
from dbx.runtime.rowset import Rowset
from dbx.runtime.script_engine import ScriptEngine
from dbx.samples import create_demo_project


@pytest.fixture()
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    project = create_demo_project(tmp_path / "Rubrica")
    yield project
    project.close()


def test_demo_is_valid_and_run_without_errors(demo):
    assert validate_project(demo) == []
    assert demo.names("forms") == ["form_clienti", "form_clienti_attivi", "form_fatture"]
    assert demo.names("reports") == ["fatture_clienti_report", "fatture_per_cliente"]
    assert demo.names("diagrams") == ["schema"]
    assert demo.names("queries") == ["clienti_attivi", "fatture_clienti"]
    assert demo.names("scripts") == ["fatture_sopra_soglia", "riepilogo_fatture"]
    assert demo.settings["main_form"] == "form_clienti"


def test_demo_data_and_relations(demo):
    clienti = Rowset(demo.db, demo.require_table("clienti")).open(order="codice").rows()
    assert [row["codice"] for row in clienti] == ["C001", "C002", "C003"]
    fatture = Rowset(demo.db, demo.require_table("fatture")).open().rows()
    assert len(fatture) == 5
    assert sum(row["importo"] for row in fatture) == pytest.approx(5900.5)
    # ON DELETE RESTRICT protegge i clienti con fatture.
    with pytest.raises(Exception):
        demo.db.execute('DELETE FROM "clienti" WHERE "codice" = ?', ("C001",))


def test_demo_report_layout(demo):
    spec = ReportSpec.from_dict(demo.artifact("reports", "fatture_per_cliente"))
    rows = Rowset(demo.db, demo.require_table("fatture")).open(order=spec.order).rows()
    pages = ReportRenderer(spec, rows).layout()
    assert len(pages) >= 1
    text = " ".join(op.text for page in pages for op in page.ops)
    assert "Fatture per cliente" in text
    assert "Totale generale: 5.900,50" in text
    # raggruppamento per cliente: 3 totali di gruppo
    assert text.count("Totale cliente:") == 3


def test_demo_script(demo):
    engine = ScriptEngine(demo)
    result = engine.run_named("riepilogo_fatture")
    assert result.error is None
    assert any("Fattura 2" in line for line in result.log)
    assert any("Fattura 3" in line for line in result.log)


def test_demo_parameterized_script_and_global(demo):
    result = ScriptEngine(demo).run_named("fatture_sopra_soglia")
    assert result.error is None
    assert result.variables["soglia"] == "1000"
    assert any("Fatture sopra 1000" in line for line in result.log)
    assert demo.globals.get("ultima_soglia") == "1000"


def test_build_creates_directory_and_zip(demo, tmp_path):
    archive = build_project(demo, tmp_path / "dist")
    assert archive.exists() and archive.suffix == ".zip"
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
    assert "project.dbx.json" in names
    assert "data/Rubrica.sqlite" in names
    assert any(name.endswith("clienti.table.json") for name in names)
    assert any(name.endswith("form_clienti.form.json") for name in names)
    assert any(name.endswith("schema.diagram.json") for name in names)


def test_build_refuses_invalid_project(demo, tmp_path):
    demo.remove_object("forms", "form_clienti")
    with pytest.raises(BuildError):
        build_project(demo, tmp_path / "dist")
