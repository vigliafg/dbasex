"""Progetto dimostrativo "Rubrica + Fatture" (G8)."""

from __future__ import annotations

from pathlib import Path

from .core import types as T
from .core.form_model import FormControl, FormSpec
from .core.metadata import Field, ForeignKey, Index, Table, new_id
from .core.project import Project
from .runtime.report_engine import Control, ReportSpec
from .runtime.rowset import Rowset
from .runtime.script_engine import new_step


def _clienti() -> Table:
    return Table(
        name="clienti",
        caption="Clienti",
        fields=[
            Field("codice", T.TEXT, size=8, required=True, pk=True, caption="Codice"),
            Field("nome", T.TEXT, size=60, required=True, caption="Nome"),
            Field("citta", T.TEXT, size=40, caption="Città"),
            Field("email", T.TEXT, size=80, caption="Email"),
            Field("telefono", T.TEXT, size=24, caption="Telefono"),
            Field("attivo", T.BOOLEAN, default="1", caption="Attivo"),
            Field("note", T.MEMO, caption="Note"),
        ],
        indexes=[Index(fields=["nome"])],
    )


def _fatture() -> Table:
    return Table(
        name="fatture",
        caption="Fatture",
        fields=[
            Field("numero", T.INTEGER, required=True, pk=True, caption="Numero"),
            Field("cliente", T.TEXT, size=8, required=True, caption="Cliente"),
            Field("data", T.DATE, caption="Data"),
            Field("descrizione", T.TEXT, size=120, caption="Descrizione"),
            Field("importo", T.DECIMAL, default="0", caption="Importo"),
            Field("pagata", T.BOOLEAN, caption="Pagata"),
        ],
        indexes=[Index(fields=["cliente"]), Index(fields=["data"])],
        foreign_keys=[
            ForeignKey(columns=["cliente"], ref_table="clienti", ref_columns=["codice"], on_delete="RESTRICT")
        ],
    )


def _report() -> ReportSpec:
    spec = ReportSpec(
        name="fatture_per_cliente",
        title="Fatture per cliente",
        table="fatture",
        order="cliente, data",
        group_by="cliente",
        group_label="Cliente",
    )
    spec.bands["title"] = [
        Control(id=new_id(), kind="text", x=0, y=0, w=170, h=12, text="Fatture per cliente", font_size=16, bold=True),
        Control(id=new_id(), kind="text", x=0, y=14, w=170, h=6, text="Report dimostrativo dBX", font_size=9, color="#666666"),
    ]
    spec.bands["page_header"] = [
        Control(id=new_id(), kind="text", x=0, y=0, w=170, h=6, text="dBX — Rubrica e Fatture", font_size=8, color="#666666"),
    ]
    spec.bands["group_header"] = [
        Control(id=new_id(), kind="text", x=0, y=0, w=170, h=8, text="Cliente: [cliente]", font_size=12, bold=True, border=False),
    ]
    spec.bands["detail"] = [
        Control(id=new_id(), kind="field", x=0, y=0, w=20, h=6, expr="numero", font_size=10),
        Control(id=new_id(), kind="field", x=22, y=0, w=28, h=6, expr="data", font_size=10, fmt="DD/MM/YYYY"),
        Control(id=new_id(), kind="field", x=52, y=0, w=78, h=6, expr="descrizione", font_size=10),
        Control(id=new_id(), kind="expr", x=132, y=0, w=20, h=6, expr="[importo]", font_size=10, align="right"),
        Control(id=new_id(), kind="text", x=154, y=0, w=16, h=6, text="€", font_size=10, align="right"),
    ]
    spec.bands["group_footer"] = [
        Control(id=new_id(), kind="line", x=0, y=0, w=170, h=2),
        Control(id=new_id(), kind="total", x=120, y=2, w=50, h=7, expr="[importo]", func="sum", label="Totale cliente: ", font_size=10, bold=True, align="right"),
    ]
    spec.bands["page_footer"] = [
        Control(id=new_id(), kind="text", x=0, y=0, w=170, h=6, text="Pagina {PAGINA} di {PAGINE}", font_size=8, align="right"),
    ]
    spec.bands["summary"] = [
        Control(id=new_id(), kind="line", x=0, y=0, w=170, h=2),
        Control(id=new_id(), kind="total", x=110, y=2, w=60, h=9, expr="[importo]", func="sum", label="Totale generale: ", font_size=12, bold=True, align="right"),
        Control(id=new_id(), kind="total", x=0, y=2, w=60, h=8, expr="[numero]", func="count", label="Fatture: ", font_size=10),
    ]
    return spec


def _script() -> dict:
    steps = [
        new_step("status", text="Riepilogo fatture in corso…"),
        new_step("message", text="Riepilogo fatture non pagate"),
    ]
    if_step = new_step("if", expr=".T.")
    if_step["then"].append(new_step("message", text="Verranno elencate le fatture non pagate."))
    steps.append(if_step)
    loop = new_step("foreach", table="fatture", filter="pagata = 0")
    loop["steps"].append(new_step("message", text="Fattura [numero] del [data] — importo [importo]"))
    steps.append(loop)
    steps.append(new_step("set", variable="ultimo_riepilogo", expr="TODAY()"))
    steps.append(new_step("status", text="Riepilogo completato"))
    return {"name": "riepilogo_fatture", "steps": steps}


def create_demo_project(path: str | Path, name: str = "Rubrica") -> Project:
    """Crea un progetto pronto all'uso con tabelle, dati, form, report e script."""
    project = Project.create(path, name, "Rubrica e fatture (demo dBX)")
    clienti, fatture = _clienti(), _fatture()
    project.apply_table(clienti)
    project.apply_table(fatture)

    form_clienti = FormSpec.create(clienti, name="form_clienti")
    form_clienti.caption = "Clienti"
    project.add_object("forms", form_clienti.to_dict())
    form_fatture = FormSpec.create_master_detail(
        clienti, fatture, "codice", "cliente", name="form_fatture"
    )
    form_fatture.caption = "Clienti e fatture"
    project.add_object("forms", form_fatture.to_dict())
    project.add_object("reports", _report().to_dict())
    project.add_object("scripts", _script())
    project.add_object(
        "menus",
        {
            "name": "principale",
            "items": [
                {"label": "Clienti", "action": "open_form", "target": "form_clienti"},
                {"label": "Clienti e fatture", "action": "open_form", "target": "form_fatture"},
                {"label": "Fatture per cliente", "action": "open_report", "target": "fatture_per_cliente"},
                {"label": "Riepilogo fatture", "action": "run_script", "target": "riepilogo_fatture"},
            ],
        },
    )
    project.settings["main_form"] = "form_clienti"
    project.settings["title"] = "Rubrica e fatture"

    rows_clienti = [
        {"codice": "C001", "nome": "Alfa Srl", "citta": "Milano", "email": "info@alfa.it", "telefono": "02 1234567", "attivo": True, "note": "Cliente storico"},
        {"codice": "C002", "nome": "Beta Studio", "citta": "Torino", "email": "beta@studio.it", "telefono": "011 7654321", "attivo": True, "note": ""},
        {"codice": "C003", "nome": "Gamma snc", "citta": "Roma", "email": "gamma@snc.it", "telefono": "06 1122334", "attivo": False, "note": "Sospeso"},
    ]
    rows_fatture = [
        {"numero": 1, "cliente": "C001", "data": "2026-01-15", "descrizione": "Consulenza", "importo": 1200.0, "pagata": True},
        {"numero": 2, "cliente": "C001", "data": "2026-02-10", "descrizione": "Assistenza", "importo": 450.0, "pagata": False},
        {"numero": 3, "cliente": "C002", "data": "2026-02-28", "descrizione": "Progetto web", "importo": 3200.0, "pagata": False},
        {"numero": 4, "cliente": "C003", "data": "2026-03-05", "descrizione": "Formazione", "importo": 800.0, "pagata": True},
        {"numero": 5, "cliente": "C002", "data": "2026-03-21", "descrizione": "Manutenzione", "importo": 250.5, "pagata": False},
    ]
    for table, rows in ((clienti, rows_clienti), (fatture, rows_fatture)):
        rowset = Rowset(project.db, table)
        for row in rows:
            rowset.insert(row)
    project.save()
    return project
