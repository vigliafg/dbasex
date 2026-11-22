"""Test del modello form esteso: eventi, metodi, colori e compatibilità."""

from __future__ import annotations

from dbx.core.form_model import (
    CONTROL_EVENTS,
    FORM_EVENTS,
    FormControl,
    FormPage,
    FormSpec,
    object_name,
)


def test_control_events_methods_roundtrip() -> None:
    control = FormControl(
        id="c1",
        kind="field",
        field="nome",
        events={"onClick": "save", "onEnter": "next"},
        methods={"validate": "controlla il campo"},
        backcolor="#ffffff",
        forecolor="#000080",
        font_name="Segoe UI",
    )
    payload = control.to_dict()
    assert payload["events"] == {"onClick": "save", "onEnter": "next"}
    assert payload["methods"] == {"validate": "controlla il campo"}
    restored = FormControl.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.backcolor == "#ffffff"
    assert restored.forecolor == "#000080"
    assert restored.font_name == "Segoe UI"


def test_legacy_form_without_events_loads_with_defaults() -> None:
    legacy = {
        "name": "legacy",
        "caption": "Legacy",
        "table": "clienti",
        "width": 620,
        "height": 440,
        "order": "",
        "pages": [
            {
                "caption": "Dati",
                "controls": [
                    {"id": "x", "kind": "field", "field": "nome", "x": 8, "y": 8, "w": 100, "h": 20}
                ],
            }
        ],
    }
    spec = FormSpec.from_dict(legacy)
    control = spec.pages[0].controls[0]
    assert control.events == {}
    assert control.methods == {}
    assert spec.events == {}
    assert spec.methods == {}
    assert spec.backcolor == ""
    assert spec.validate() == []


def test_form_events_roundtrip() -> None:
    spec = FormSpec(
        name="eventi",
        table="clienti",
        pages=[FormPage(controls=[FormControl(id="a")])],
        events={"onOpen": "first", "onClose": "save"},
        methods={"save": "salva"},
        backcolor="#c0c0c0",
    )
    payload = spec.to_dict()
    restored = FormSpec.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.events["onOpen"] == "first"
    assert set(FORM_EVENTS) == {"onOpen", "onClose"}
    assert set(CONTROL_EVENTS) == {"onClick", "onEnter", "onExit"}


def test_object_names_follow_dbase_style() -> None:
    controls = [
        FormControl(id="a", kind="label"),
        FormControl(id="b", kind="field", field="nome"),
        FormControl(id="c", kind="button"),
        FormControl(id="d", kind="field", field="citta"),
        FormControl(id="e", kind="button"),
    ]
    names = [object_name(control, controls) for control in controls]
    assert names == [
        "form.text1",
        "form.entryfield1",
        "form.commandbutton1",
        "form.entryfield2",
        "form.commandbutton2",
    ]
    spec = FormSpec(name="nomi", table="clienti", pages=[FormPage(controls=controls)])
    assert spec.control_object_name(controls[3]) == "form.entryfield2"
