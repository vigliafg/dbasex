from pathlib import Path

import pytest

from dbx.core import types as T
from dbx.core.metadata import Field, Table
from dbx.core.project import Project
from dbx.runtime.script_engine import (
    ACTIONS,
    NullUI,
    ScriptEngine,
    ScriptError,
    count_steps,
    from_text,
    new_step,
    to_text,
)


class RecordingUI(NullUI):
    def __init__(self):
        self.messages = []
        self.forms = []
        self.reports = []
        self.statuses = []
        self.answers = []
        self.confirmations = []

    def message(self, text):
        self.messages.append(text)

    def status(self, text):
        self.statuses.append(text)

    def ask(self, prompt, default=""):
        self.answers.append(prompt)
        return "valore"

    def confirm(self, text):
        self.confirmations.append(text)
        return True

    def open_form(self, name):
        self.forms.append(name)

    def print_report(self, name):
        self.reports.append(name)


@pytest.fixture()
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("DBX_CONFIG_DIR", str(tmp_path / "config"))
    proj = Project.create(tmp_path / "ScriptTest", "ScriptTest")
    proj.apply_table(
        Table(
            name="clienti",
            fields=[Field("nome", T.TEXT), Field("anni", T.INTEGER)],
        )
    )
    proj.db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Ada", 36))
    proj.db.execute('INSERT INTO "clienti" ("nome", "anni") VALUES (?, ?)', ("Bob", 15))
    proj.add_object("forms", {"name": "clienti_form", "controls": []})
    proj.add_object("reports", {"name": "per_cliente", "bands": {}})
    yield proj
    proj.close()


def test_message_set_and_if(project):
    ui = RecordingUI()
    steps = [
        new_step("set", variable="tot", expr="2 * 21"),
        new_step("message", text="Valore: :tot"),
    ]
    result = ScriptEngine(project, ui).run(steps)
    assert result.error is None
    assert result.variables["tot"] == 42
    assert ui.messages[0].startswith("Valore: ")


def test_if_else_and_nested_blocks(project):
    ui = RecordingUI()
    step = new_step("if", expr=":flag")
    step["then"].append(new_step("message", text="vero"))
    step["else"].append(new_step("message", text="falso"))
    engine = ScriptEngine(project, ui, variables={"flag": False})
    engine.run([step])
    assert ui.messages == ["falso"]
    engine.variables["flag"] = True
    engine.run([step])
    assert ui.messages == ["falso", "vero"]


def test_foreach_over_table(project):
    engine = ScriptEngine(project)
    step = new_step("foreach", table="clienti", filter="anni >= 18")
    step["steps"].append(new_step("message", text="[nome]"))
    result = engine.run([step])
    assert result.error is None
    assert engine.log[-1] == "Ada"


def test_open_form_print_report_and_errors(project):
    ui = RecordingUI()
    engine = ScriptEngine(project, ui)
    engine.run([new_step("open_form", form="clienti_form"), new_step("print_report", report="per_cliente")])
    assert ui.forms == ["clienti_form"] and ui.reports == ["per_cliente"]
    result = engine.run([new_step("open_form", form="inesistente")])
    assert result.error and "sconosciuto" in result.error


def test_ask_and_confirm(project):
    ui = RecordingUI()
    steps = [
        new_step("ask", prompt="Nome?", variable="nome"),
        new_step("message", text=":nome"),
    ]
    confirm = new_step("confirm", text="Procedo?")
    confirm["steps"].append(new_step("message", text="confermato"))
    ScriptEngine(project, ui).run(steps + [confirm])
    assert ui.answers == ["Nome?"]
    assert "valore" in ui.messages
    assert "confermato" in ui.messages


def test_export_csv(project, tmp_path):
    target = tmp_path / "clienti.csv"
    engine = ScriptEngine(project)
    result = engine.run([new_step("export_csv", table="clienti", filter="", path=str(target))])
    assert result.error is None
    content = target.read_text(encoding="utf-8-sig")
    assert "nome" in content and "Ada" in content


def test_forbidden_sql_is_refused(project):
    result = ScriptEngine(project).run([new_step("sql", statement="DROP TABLE clienti")])
    assert result.error and "struttura" in result.error
    assert project.table("clienti") is not None


def test_call_script(project):
    project.add_object(
        "scripts",
        {"name": "saluta", "steps": [new_step("message", text="ciao")]},
    )
    engine = ScriptEngine(project)
    result = engine.run([new_step("call", script="saluta")])
    assert result.error is None
    assert "ciao" in engine.log


def test_text_roundtrip():
    steps = [
        new_step("message", text='Ciao "mondo"'),
        new_step("set", variable="tot", expr="1 + 2"),
    ]
    if_step = new_step("if", expr="[anni] > 18")
    if_step["then"].append(new_step("message", text="adulto"))
    if_step["else"].append(new_step("message", text="minore"))
    steps.append(if_step)
    loop = new_step("foreach", table="clienti", filter="anni >= 18")
    loop["steps"].append(new_step("message", text="[nome]"))
    steps.append(loop)
    steps.append(new_step("open_form", form="clienti_form"))

    text = to_text(steps)
    parsed = from_text(text)
    assert count_steps(parsed) == count_steps(steps)
    assert parsed[0]["params"]["text"] == 'Ciao "mondo"'
    assert parsed[1]["params"]["variable"] == "tot"
    assert parsed[2]["action"] == "if"
    assert parsed[2]["then"][0]["params"]["text"] == "adulto"
    assert parsed[2]["else"][0]["params"]["text"] == "minore"
    assert parsed[3]["action"] == "foreach"
    assert parsed[3]["params"]["filter"] == "anni >= 18"
    assert to_text(parsed) == text


def test_text_parser_errors():
    with pytest.raises(ScriptError):
        from_text("IF [a] > 1\nMESSAGE \"x\"")
    with pytest.raises(ScriptError):
        from_text("COMANDO_INESISTENTE x")


def test_action_catalog_is_consistent():
    for action, spec in ACTIONS.items():
        step = new_step(action)
        assert step["action"] == action
        assert isinstance(spec["params"], list)
