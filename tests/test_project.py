from pathlib import Path

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.project import MANIFEST_NAME, Project, ProjectError


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    proj = Project.create(tmp_path / "Rubrica", "Rubrica", "Rubrica personale")
    yield proj
    proj.close()


def test_create_writes_layout_and_manifest(project):
    assert project.manifest_path.exists()
    assert (project.path / "objects" / "tables").is_dir()
    assert (project.path / "data").is_dir()
    assert project.db.con is not None
    assert (project.path / "data" / "Rubrica.sqlite").exists()
    text = project.manifest_path.read_text(encoding="utf-8")
    assert '"format_version"' in text
    assert "Rubrica" in text


def test_table_migration_and_reopen(tmp_path, project):
    table = Table(name="contatti", caption="Contatti", fields=[Field("nome", T.TEXT, required=True)])
    project.apply_table(table)
    project.db.execute('INSERT INTO "contatti" ("nome") VALUES (?)', ("Ada",))
    assert project.table("contatti") is not None
    path = project.path
    project.close()

    reopened = Project.open(path)
    try:
        assert reopened.table("contatti").field("nome").required is True
        assert reopened.db.scalar('SELECT nome FROM "contatti"') == "Ada"
        assert (path / "objects" / "tables" / "contatti.table.json").exists()
    finally:
        reopened.close()


def test_reopen_requires_absent_lock(tmp_path, project):
    path = project.path
    with pytest.raises(ProjectError):
        Project.open(path)


def test_force_open_and_save_objects(tmp_path, project):
    path = project.path
    project.add_object("scripts", {"name": "prova", "steps": []})
    project.save()
    forced = Project.open(path, force=True)
    try:
        assert forced.artifact("scripts", "prova") is not None
        assert forced.names("scripts") == ["prova"]
    finally:
        forced.close()


def test_apply_table_backs_up_before_rebuild(project):
    table = Table(name="clienti", fields=[Field("nome", T.TEXT)])
    project.apply_table(table)
    project.db.execute('INSERT INTO "clienti" ("nome") VALUES (?)', ("Ada",))
    changed = project.table("clienti")
    changed.fields[0].name = "ragione_sociale"
    plan = project.apply_table(changed)
    assert plan.kind == "rebuild"
    backups = list((project.path / "backups").glob("*.sqlite"))
    assert backups, "atteso un backup prima della ricostruzione"
    assert project.db.scalar('SELECT ragione_sociale FROM "clienti"') == "Ada"


def test_rename_object_and_remove(project):
    project.add_object("reports", {"name": "per_citta"})
    project.save()
    assert (project.path / "objects" / "reports" / "per_citta.report.json").exists()
    project.put_object("reports", {"name": "per_citta_nuovo"}, previous_name="per_citta")
    project.save()
    assert project.names("reports") == ["per_citta_nuovo"]
    # Il file del vecchio nome non deve sopravvivere: altrimenti ricomparirebbe alla riapertura.
    assert not (project.path / "objects" / "reports" / "per_citta.report.json").exists()
    assert project.remove_object("reports", "per_citta_nuovo") is True
    assert project.names("reports") == []


def test_create_refuses_non_empty_folder(tmp_path):
    folder = tmp_path / "occupata"
    folder.mkdir()
    (folder / "file.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ProjectError):
        Project.create(folder, "Occupata")


def test_open_rejects_future_format(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    folder = tmp_path / "futuro"
    folder.mkdir()
    (folder / MANIFEST_NAME).write_text('{"format_version": 99, "name": "x"}', encoding="utf-8")
    with pytest.raises(ProjectError) as exc:
        Project.open(folder)
    assert "formato" in str(exc.value)
