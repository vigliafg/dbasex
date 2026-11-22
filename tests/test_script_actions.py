"""Test dei passi core e del runtime script (0.5/O6)."""

from __future__ import annotations

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.designers.project_builder import validate_project
from dbx.runtime.rowset import Rowset
from dbx.runtime.script_engine import (
    ACTIONS,
    NullUI,
    ScriptEngine,
    new_step,
    from_text,
    to_text,
)


class RecordingUI(NullUI):
    def __init__(self, answer: str | None = "valore", confirm: bool = True):
        self.messages: list[str] = []
        self.statuses: list[str] = []
        self.forms: list[str] = []
        self.queries: list[str] = []
        self.reports: list[str] = []
        self.beeps = 0
        self.confirmations: list[str] = []
        self.answer = answer
        self.confirm_answer = confirm

    def message(self, text: str) -> None:
        self.messages.append(text)

    def status(self, text: str) -> None:
        self.statuses.append(text)

    def ask(self, prompt: str, default: str = "") -> str | None:
        return self.answer

    def confirm(self, text: str) -> bool:
        self.confirmations.append(text)
        return self.confirm_answer

    def open_form(self, name: str) -> None:
        self.forms.append(name)

    def open_query(self, name: str) -> None:
        self.queries.append(name)

    def open_report(self, name: str) -> None:
        self.reports.append(name)

    def custom_dialog(self, title: str, message: str, default: str = "") -> str | None:
        return self.answer

    def beep(self) -> None:
        self.beeps += 1


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    proj = Project.create(tmp_path / "ScriptActions", "ScriptActions")
    proj.apply_table(
        Table(
            name="clienti",
            fields=[Field("nome", T.TEXT), Field("anni", T.INTEGER), Field("note", T.TEXT)],
        )
    )
    proj.db.execute('INSERT INTO "clienti" ("nome", "anni", "note") VALUES (?, ?, ?)', ("Ada", 36, ""))
    proj.db.execute('INSERT INTO "clienti" ("nome", "anni", "note") VALUES (?, ?, ?)', ("Bob", 15, ""))
    proj.add_object("forms", {"name": "clienti_form", "controls": []})
    proj.add_object("reports", {"name": "per_cliente", "bands": {}})
    proj.add_object("queries", {"name": "clienti_attivi", "base": "clienti", "fields": []})
    try:
        yield proj
    finally:
        proj.close()


def _attivita(project) -> None:
    project.apply_table(
        Table(
            name="attivita",
            fields=[
                Field("titolo", T.TEXT, size=40),
                Field("stato", T.TEXT, size=12, default="nuovo"),
                Field("quantita", T.INTEGER, default="0"),
            ],
        )
    )


def _rows(project, table_name: str) -> list[dict]:
    table = project.require_table(table_name)
    return Rowset(project.db, table).open(order="rowid").rows()


def test_catalog_includes_core_actions() -> None:
    for action in (
        "comment",
        "loop",
        "exit_loop_if",
        "exit_script",
        "halt",
        "select_table",
        "go_record",
        "set_field",
        "new_record",
        "duplicate_record",
        "delete_record",
        "commit_record",
        "revert_record",
        "open_query",
        "open_report",
        "custom_dialog",
        "beep",
    ):
        assert action in ACTIONS
        assert ACTIONS[action]["description"]


def test_select_go_and_set_field(project) -> None:
    ui = RecordingUI()
    steps = [
        new_step("select_table", table="clienti", order="nome"),
        new_step("go_record", mode="last"),
        new_step("set_field", field="anni", expr="40"),
        new_step("commit_record"),
    ]
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    rows = _rows(project, "clienti")
    assert [row["anni"] for row in rows] == [36, 40]
    assert any("clienti.anni = 40" in line for line in result.log)


def test_new_duplicate_and_delete_record(project) -> None:
    _attivita(project)
    ui = RecordingUI()
    steps = [
        new_step("select_table", table="attivita"),
        new_step("new_record"),
        new_step("set_field", field="titolo", expr='"uno"'),
        new_step("duplicate_record"),
        new_step("set_field", field="titolo", expr='"due"'),
        new_step("commit_record"),
        new_step("delete_record", confirm="no"),
    ]
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    rows = _rows(project, "attivita")
    assert len(rows) == 1
    assert rows[0]["titolo"] == "uno"
    assert rows[0]["stato"] == "nuovo"


def test_revert_record_reloads(project) -> None:
    ui = RecordingUI()
    steps = [
        new_step("select_table", table="clienti", order="nome"),
        new_step("set_field", field="anni", expr="50"),
        new_step("revert_record"),
    ]
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert _rows(project, "clienti")[0]["anni"] == 50
    assert any("ripristinato" in line for line in result.log)


def test_loop_and_exit_loop_if(project) -> None:
    steps = from_text(
        """
        SET :i = 0
        SELECT TABLE clienti ORDER BY nome
        LOOP
          SET :i = :i + 1
          EXIT LOOP IF :i >= 2
          GO RECORD next
        ENDLOOP
        """
    )
    result = ScriptEngine(project, RecordingUI()).run(steps)
    assert result.error is None
    assert result.variables["i"] == 2


def test_exit_script_and_halt(project) -> None:
    ui = RecordingUI()
    steps = from_text(
        """
        MESSAGE "prima"
        EXIT SCRIPT
        MESSAGE "dopo"
        """
    )
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert ui.messages == ["prima"]

    ui = RecordingUI()
    steps = from_text('HALT "stop"\nMESSAGE "dopo"')
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert ui.messages == ["stop"]
    assert "dopo" not in " ".join(result.log)


def test_custom_dialog_beep_and_navigation(project) -> None:
    ui = RecordingUI(answer="ok")
    steps = from_text(
        """
        CUSTOM DIALOG "Titolo" "Domanda" INTO :risposta
        BEEP
        OPEN QUERY clienti_attivi
        OPEN REPORT per_cliente
        OPEN FORM clienti_form
        """
    )
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert result.variables["risposta"] == "ok"
    assert ui.beeps == 1
    assert ui.queries == ["clienti_attivi"]
    assert ui.reports == ["per_cliente"]
    assert ui.forms == ["clienti_form"]


def test_comment_is_not_executed(project) -> None:
    steps = from_text('COMMENT "nota"\nMESSAGE "eseguito"')
    result = ScriptEngine(project, RecordingUI()).run(steps)
    assert result.error is None
    assert result.log == ["eseguito"]


def test_delete_record_confirmation(project) -> None:
    ui = RecordingUI(confirm=False)
    steps = [
        new_step("select_table", table="clienti", order="nome"),
        new_step("delete_record"),
    ]
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert len(_rows(project, "clienti")) == 2
    assert ui.confirmations


def test_errors_without_cursor(project) -> None:
    result = ScriptEngine(project, RecordingUI()).run([new_step("go_record", mode="first")])
    assert result.error and "Nessuna tabella" in result.error
    result = ScriptEngine(project, RecordingUI()).run([new_step("set_field", field="anni", expr="1")])
    assert result.error


def test_text_roundtrip_for_core_steps(project) -> None:
    steps = [
        new_step("comment", text="nota"),
        new_step("loop"),
        new_step("exit_loop_if", expr="i > 2"),
        new_step("exit_script"),
        new_step("halt", message="stop"),
        new_step("select_table", table="clienti", filter="anni > 10", order="nome"),
        new_step("go_record", mode="number", number="2"),
        new_step("set_field", field="anni", expr="anni + 1"),
        new_step("new_record", table="attivita"),
        new_step("duplicate_record"),
        new_step("delete_record", confirm="no"),
        new_step("commit_record"),
        new_step("revert_record"),
        new_step("open_query", query="clienti_attivi"),
        new_step("open_report", report="per_cliente"),
        new_step("custom_dialog", title="Titolo", message="Messaggio", variable="risposta"),
        new_step("beep"),
    ]
    text = to_text(steps)
    assert from_text(text) == steps


def test_else_if_is_nested_sugar(project) -> None:
    steps = from_text(
        """
        SET :a = 0
        SET :b = 1
        IF :a
          MESSAGE "ramo a"
        ELSE IF :b
          MESSAGE "ramo b"
        ENDIF
        """
    )
    assert steps[2]["action"] == "if"
    assert steps[2]["else"][0]["action"] == "if"
    ui = RecordingUI()
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert ui.messages == ["ramo b"]
    assert from_text(to_text(steps)) == steps


def test_validation_of_core_steps(demo_project) -> None:
    valid = [
        new_step("select_table", table="clienti", order="codice"),
        new_step("set_field", field="note", expr='"x"'),
        new_step("go_record", mode="first"),
        new_step("open_query", query="clienti_attivi"),
        new_step("open_report", report="fatture_clienti_report"),
    ]
    demo_project.put_object("scripts", {"name": "valido", "steps": valid})
    assert validate_project(demo_project) == []

    invalid = [
        new_step("select_table", table="sconosciuta"),
        new_step("select_table", table="clienti"),
        new_step("set_field", field="inesistente", expr='"x"'),
        new_step("go_record", mode="boh"),
        new_step("open_query", query="manca"),
        new_step("open_report", report="manca"),
    ]
    demo_project.put_object("scripts", {"name": "invalido", "steps": invalid})
    errors = "\n".join(validate_project(demo_project))
    assert "tabella inesistente sconosciuta" in errors
    assert "campo inesistente inesistente" in errors
    assert "modalità GO RECORD non valida boh" in errors
    assert "query inesistente manca" in errors
    assert "report inesistente manca" in errors


def test_form_runtime_script_adapter(qapp, demo_project) -> None:
    from dbx.core.form_model import FormSpec
    from dbx.runtime.form_runtime import FormRuntime

    script = {
        "name": "aggiorna_nota",
        "steps": [
            new_step("select_table", table="clienti", order="codice"),
            new_step("set_field", field="note", expr='"da script"'),
            new_step("commit_record"),
        ],
    }
    demo_project.put_object("scripts", script)
    demo_project.save()
    spec = FormSpec.create(demo_project.require_table("clienti"), name="clienti_form_test")
    runtime = FormRuntime(demo_project, spec)
    try:
        runtime._run_script("aggiorna_nota")
        assert runtime.rowset.current is not None
        assert runtime.rowset.current["note"] == "da script"
        assert _rows(demo_project, "clienti")[0]["note"] == "da script"
    finally:
        runtime.deleteLater()
