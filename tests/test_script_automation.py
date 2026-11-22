"""Test di parametri, variabili globali e transazioni degli script (0.9 O10)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.designers.project_builder import validate_project
from dbx.runtime.script_engine import (
    ScriptEngine,
    ScriptError,
    count_steps,
    from_text,
    new_step,
    parameter_values,
    script_parameters,
    to_text,
)


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    proj = Project.create(tmp_path / "Automazione", "Automazione")
    proj.apply_table(
        Table(
            name="clienti",
            fields=[
                Field("nome", T.TEXT),
                Field("anni", T.INTEGER),
                Field("note", T.TEXT),
            ],
        )
    )
    proj.db.execute(
        'INSERT INTO "clienti" ("nome", "anni", "note") VALUES (?, ?, ?)',
        ("Ada", 36, ""),
    )
    proj.db.execute(
        'INSERT INTO "clienti" ("nome", "anni", "note") VALUES (?, ?, ?)',
        ("Bob", 15, ""),
    )
    try:
        yield proj
    finally:
        proj.close()


def _param_script(project, **artifact) -> dict:
    data = {
        "name": "saluta",
        "params": [{"name": "chi", "label": "Chi", "default": "mondo"}],
        "steps": [new_step("message", text="Ciao :chi")],
    }
    data.update(artifact)
    project.add_object("scripts", data)
    return data


def test_parameter_declarations_accept_strings_and_dicts():
    declared = script_parameters(
        {
            "params": [
                "soglia",
                {"name": "anno", "label": "Anno", "default": 2026},
                {"name": "nota"},
            ]
        }
    )
    assert declared == [
        {"name": "soglia", "label": "soglia", "default": ""},
        {"name": "anno", "label": "Anno", "default": "2026"},
        {"name": "nota", "label": "nota", "default": ""},
    ]
    assert script_parameters({}) == []
    assert script_parameters(None) == []


def test_parameter_declarations_reject_invalid_and_duplicate_names():
    with pytest.raises(ScriptError):
        script_parameters({"params": [{"name": "nome non valido"}]})
    with pytest.raises(ScriptError):
        script_parameters({"params": ["soglia", {"name": "SOGLIA"}]})


def test_parameter_values_use_defaults_and_overrides():
    artifact = {
        "params": [
            {"name": "soglia", "default": "100"},
            {"name": "anno", "default": "2026"},
        ]
    }
    assert parameter_values(artifact) == {"soglia": "100", "anno": "2026"}
    values = parameter_values(artifact, {"soglia": 500, "extra": "x"})
    assert values["soglia"] == 500
    assert values["extra"] == "x"
    assert values["anno"] == "2026"


def test_run_named_applies_parameters_to_messages(project):
    _param_script(project)
    engine = ScriptEngine(project)
    result = engine.run_named("saluta")
    assert result.error is None
    assert result.log == ["Ciao mondo"]

    result = engine.run_named("saluta", params={"chi": "Ada"})
    assert result.error is None
    assert result.log == ["Ciao Ada"]
    assert result.variables["chi"] == "Ada"


def test_parameters_are_interpolated_in_filters(project):
    _param_script(
        project,
        name="adulti",
        params=[{"name": "eta", "default": "18"}],
        steps=[
            new_step(
                "foreach",
                table="clienti",
                filter="anni >= :eta",
            )
        ],
    )
    artifact = project.artifact("scripts", "adulti")
    artifact["steps"][0]["steps"].append(new_step("message", text="[nome]"))
    result = ScriptEngine(project).run_named("adulti")
    assert result.error is None, result.error
    assert result.log == ["Ada"]

    result = ScriptEngine(project).run_named("adulti", params={"eta": "10"})
    assert result.log == ["Ada", "Bob"]


def test_parameter_filters_are_not_evaluated_as_expressions(project):
    step = new_step("foreach", table="clienti", filter="anni >= :eta")
    step["steps"].append(new_step("message", text="[nome]"))
    result = ScriptEngine(project).run(
        [
            new_step("select_table", table="clienti", order="nome"),
            step,
        ],
        params={"eta": "10"},
    )
    assert result.error is None, result.error
    assert result.log[-2:] == ["Ada", "Bob"]


def test_global_variables_are_shared_and_persisted(project):
    writer = ScriptEngine(project)
    result = writer.run(
        [new_step("set_global", variable="ultimo", expr='"Ada"')]
    )
    assert result.error is None, result.error
    assert project.globals == {"ultimo": "Ada"}

    reader = ScriptEngine(project)
    assert reader.globals["ultimo"] == "Ada"
    read = reader.run([new_step("message", text=":ultimo")])
    assert read.log == ["Ada"]

    project.save()
    reopened = Project.open(project.path, force=True)
    try:
        assert reopened.globals == {"ultimo": "Ada"}
        assert ScriptEngine(reopened).globals["ultimo"] == "Ada"
    finally:
        reopened.close()


def test_global_variables_can_be_unset(project):
    project.set_global("temporanea", "x")
    project.save()
    engine = ScriptEngine(project)
    assert engine.globals["temporanea"] == "x"
    result = engine.run(
        [new_step("unset_global", variable="temporanea")]
    )
    assert result.error is None
    assert "temporanea" not in project.globals
    assert "temporanea" not in ScriptEngine(project).globals


def test_local_variables_shadow_globals_but_set_global_wins(project):
    project.set_global("prezzo", 10)
    engine = ScriptEngine(project, variables={"prezzo": "99"})
    assert engine.run([new_step("message", text=":prezzo")]).log == ["99"]
    result = engine.run(
        [new_step("set_global", variable="prezzo", expr="VAL(:prezzo) + 1")]
    )
    assert result.error is None, result.error
    assert project.globals["prezzo"] == 100
    assert engine.variables.get("prezzo") is None
    assert engine.run([new_step("message", text=":prezzo")]).log == ["100.0"]


def test_dates_are_stored_as_text(project):
    result = ScriptEngine(project).run(
        [new_step("set_global", variable="oggi", expr="TODAY()")]
    )
    assert result.error is None
    value = project.globals["oggi"]
    assert isinstance(value, str)
    assert len(value) == 10


def test_transaction_commit_keeps_changes(project):
    result = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE clienti SET note = 'ok'"),
            new_step("commit_transaction"),
        ]
    )
    assert result.error is None, result.error
    note = project.db.query("SELECT note FROM clienti WHERE nome = 'Ada'")[0][0]
    assert note == "ok"


def test_transaction_rollback_discards_changes(project):
    result = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE clienti SET note = 'no'"),
            new_step("rollback_transaction"),
        ]
    )
    assert result.error is None, result.error
    note = project.db.query("SELECT note FROM clienti WHERE nome = 'Ada'")[0][0]
    assert note == ""


def test_open_transaction_is_rolled_back_after_error(project):
    result = ScriptEngine(project).run(
        [
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE clienti SET note = 'persa'"),
            new_step("halt", message="stop"),
        ]
    )
    assert result.error is None
    note = project.db.query("SELECT note FROM clienti WHERE nome = 'Ada'")[0][0]
    assert note == ""
    assert any("annullata automaticamente" in line for line in result.log)


def test_transaction_state_errors(project):
    engine = ScriptEngine(project)
    assert engine.run([new_step("commit_transaction")]).error
    result = engine.run(
        [new_step("begin_transaction"), new_step("begin_transaction")]
    )
    assert result.error and "già aperta" in result.error
    assert engine.run([new_step("rollback_transaction")]).error


def test_transaction_rollback_refreshes_cursor(project):
    engine = ScriptEngine(project)
    result = engine.run(
        [
            new_step("select_table", table="clienti", order="nome"),
            new_step("begin_transaction"),
            new_step("sql", statement="UPDATE clienti SET note = 'x'"),
            new_step("revert_record"),
            new_step("rollback_transaction"),
        ]
    )
    assert result.error is None, result.error
    assert engine._record["note"] == ""


def test_script_text_roundtrip_for_automation_actions():
    steps = [
        new_step("set_global", variable="ultimo", expr='"Ada"'),
        new_step("unset_global", variable="vecchia"),
        new_step("begin_transaction"),
        new_step("rollback_transaction"),
        new_step("commit_transaction"),
    ]
    text = to_text(steps)
    assert "SET GLOBAL :ultimo" in text
    assert "CLEAR GLOBAL :vecchia" in text
    parsed = from_text(text)
    assert count_steps(parsed) == count_steps(steps)
    assert [step["action"] for step in parsed] == [
        "set_global",
        "unset_global",
        "begin_transaction",
        "rollback_transaction",
        "commit_transaction",
    ]
    assert to_text(parsed) == text


def test_project_validation_checks_parameter_names(project):
    _param_script(project, name="rotto", params=["nome non valido"])
    errors = validate_project(project)
    assert any("Script rotto" in error and "parametro" in error.lower() for error in errors)
