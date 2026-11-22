"""Test del dispatcher eventi del runtime form."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication

from dbx.core.form_model import FormControl, FormPage, FormSpec
from dbx.runtime.form_runtime import FormRuntime


def _spec(**overrides) -> FormSpec:
    data = {
        "name": "eventi_runtime",
        "caption": "Eventi runtime",
        "table": "clienti",
        "width": 400,
        "height": 260,
    }
    data.update(overrides)
    return FormSpec(
        **data,
        pages=[
            FormPage(
                controls=[
                    FormControl(
                        id="f1",
                        kind="field",
                        field="codice",
                        x=8,
                        y=8,
                        w=120,
                        h=20,
                        events={"onEnter": "next"},
                    ),
                    FormControl(
                        id="b1", kind="button", text="Ultimo", action="last", x=8, y=40, w=80, h=22
                    ),
                    FormControl(
                        id="b2",
                        kind="button",
                        text="Primo",
                        action="last",
                        x=96,
                        y=40,
                        w=80,
                        h=22,
                        events={"onClick": "first"},
                    ),
                    FormControl(
                        id="b3",
                        kind="button",
                        text="Errore",
                        action="none",
                        x=184,
                        y=40,
                        w=80,
                        h=22,
                        events={"onClick": "azione_inesistente"},
                    ),
                ]
            )
        ],
    )


def test_on_enter_event_moves_record(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _spec())
    try:
        assert runtime.rowset.index == 0
        widget = runtime.binders[0].widget
        QApplication.sendEvent(widget, QEvent(QEvent.Type.Enter))
        assert runtime.rowset.index == 1
        assert runtime.buttons[1][0].text() == "Primo"
    finally:
        runtime.deleteLater()


def test_button_click_uses_action_when_event_is_empty(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _spec())
    try:
        runtime.buttons[0][0].click()
        assert runtime.rowset.index == runtime.rowset.count() - 1
        assert runtime.rowset.index == 2
    finally:
        runtime.deleteLater()


def test_on_click_event_overrides_button_action(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _spec())
    try:
        runtime.buttons[0][0].click()
        assert runtime.rowset.index == 2
        runtime.buttons[1][0].click()
        assert runtime.rowset.index == 0
    finally:
        runtime.deleteLater()


def test_unknown_action_is_logged_without_crash(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _spec())
    try:
        runtime.buttons[2][0].click()
        assert runtime.rowset.index == 0
        assert "azione sconosciuta: azione_inesistente" in runtime.event_log
        assert "sconosciuta" in runtime._status.text()
    finally:
        runtime.deleteLater()


def test_form_on_open_and_on_close_events(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _spec(events={"onOpen": "last", "onClose": "first"}))
    try:
        assert runtime.rowset.index == 2
        runtime._close()
        assert runtime.rowset.index == 0
    finally:
        runtime.deleteLater()


def test_runtime_without_events_behaves_as_before(qapp, demo_project) -> None:
    spec = FormSpec(
        name="silenzioso",
        table="clienti",
        pages=[FormPage(controls=[FormControl(id="f", kind="field", field="nome")])],
    )
    runtime = FormRuntime(demo_project, spec)
    try:
        assert runtime.event_log == []
        runtime.perform("last")
        assert runtime.rowset.index == 2
        assert "Record 3 di 3" in runtime._status.text()
    finally:
        runtime.deleteLater()
