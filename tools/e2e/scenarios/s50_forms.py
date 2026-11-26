"""Scenari F — Form Expert, Designer, Inspector e Runtime."""

from __future__ import annotations

from unittest import mock

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QInputDialog, QPushButton

from dbx.core.form_model import BUTTON_ACTIONS, CONTROL_KINDS, FormControl, FormPage, FormSpec
from dbx.core.query_model import QueryAggregate, QueryField, QuerySpec, QuerySort
from dbx.designers.form_builder import SNAP, FormDesignerWidget
from dbx.designers.form_expert import FormExpert, LAYOUTS
from dbx.designers.project_builder import validate_project
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.rowset import Rowset

from .. import fixtures
from ..context import E2EContext
from ..registry import scenario


def _settled(ctx: E2EContext, name: str = "Form") -> object:
    project = ctx.new_project(name)
    fixtures.settled_project(project)
    return project


def _designer(ctx: E2EContext, project, spec: FormSpec) -> FormDesignerWidget:
    designer = FormDesignerWidget(project, spec)
    return ctx.track(designer)


def _runtime(ctx: E2EContext, project, spec: FormSpec) -> FormRuntime:
    runtime = FormRuntime(project, spec)
    return ctx.track(runtime)


def _control(spec: FormSpec, kind: str = "", field: str = "", action: str = "") -> FormControl:
    for control in spec.all_controls():
        if kind and control.kind != kind:
            continue
        if field and control.field != field:
            continue
        if action and control.action != action:
            continue
        return control
    raise AssertionError(f"controllo non trovato: {kind} {field} {action}")


@scenario(
    "frm-01-expert-steps",
    "F01 — Form Expert: cinque passi e scelta dei campi",
    "forms",
    features=("FRM-EXPERT-5STEPS", "FRM-EXPERT-FIELDS"),
    min_checks=10,
    budget_s=10.0,
)
def frm_expert_steps(ctx: E2EContext) -> None:
    project = _settled(ctx, "EspertoForm")
    expert = FormExpert(project, suggested_name="form_clienti_e2e")
    ctx.track(expert)
    expert.initializePage(1)
    expert.name_edit.setText("clienti_expert")
    expert.caption_edit.setText("Clienti da esperto")
    expert.table_combo.setCurrentIndex(expert.table_combo.findData("clienti"))
    ctx.check_close(expert.source_list.count() + expert.destination_list.count(), 8, "tutti i campi")

    for row in range(expert.destination_list.count()):
        item = expert.destination_list.item(row)
        if item.data(Qt.ItemDataRole.UserRole) == "note":
            expert.destination_list.setCurrentItem(item)
    expert.remove_selected()
    ctx.check_close(expert.source_list.count(), 1, "campo rimosso dalla destinazione")

    spec = expert.build_spec()
    ctx.check_close(spec.name, "clienti_expert", "nome del form")
    ctx.check_close(spec.table, "clienti", "tabella del form")
    ctx.check_close(spec.source_type, "table", "sorgente tabella")
    ctx.check(spec.validate() == [], "form esperto valido")
    fields = [control.field for control in spec.all_controls() if control.field]
    ctx.check("codice" in fields and "note" not in fields, "campi scelti")
    ctx.check_close(len([c for c in spec.all_controls() if c.kind == "button"]), 8, "otto pulsanti")
    label = next(control for control in spec.all_controls() if control.kind == "label")
    ctx.check_close(label.text, "Clienti", "intestazione del form")

    project.put_object("forms", spec.to_dict())
    project.save()
    reopened = ctx.reopen(project)
    artifact = reopened.artifact("forms", "clienti_expert")
    ctx.check(artifact is not None, "form persistito")
    restored = FormSpec.from_dict(artifact)
    ctx.check_close(len([c for c in restored.all_controls() if c.field]), len(fields), "campi persistiti")
    ctx.check(validate_project(reopened) == [], "progetto valido")


@scenario(
    "frm-02-expert-variants",
    "F02 — Form Expert: vuoto, layout, font e colori",
    "forms",
    features=(
        "FRM-EXPERT-BLANK",
        "FRM-EXPERT-LAYOUTS",
        "FRM-EXPERT-STYLE",
        "FRM-EXPERT-COLORS",
    ),
    min_checks=13,
    budget_s=12.0,
)
def frm_expert_variants(ctx: E2EContext) -> None:
    project = _settled(ctx, "VariantiForm")
    expert = FormExpert(project, suggested_name="varianti")
    ctx.track(expert)
    expert.initializePage(1)
    expert.table_combo.setCurrentIndex(expert.table_combo.findData("clienti"))

    expert.blank_radio.setChecked(True)
    blank = expert.build_spec()
    ctx.check_close(len(blank.all_controls()), 0, "form vuoto senza controlli")
    ctx.check_close(len(blank.pages), 1, "form vuoto con una pagina")

    expert.expert_radio.setChecked(True)
    positions: dict[str, tuple[int, int]] = {}
    for key, _label in LAYOUTS:
        expert.layout_radios[key].setChecked(True)
        spec = expert.build_spec()
        field = next(control for control in spec.all_controls() if control.field == "codice")
        positions[key] = (field.x, field.y)
        ctx.check(spec.validate() == [], f"layout {key} valido")
    ctx.check(positions["labels_left"][0] > positions["labels_above"][0], "etichette a sinistra")
    ctx.check(positions["labels_above"][1] > positions["labels_left"][1], "etichetta sopra")
    two = [control.x for control in expert.build_spec().all_controls() if control.field]
    ctx.check(positions["two_columns"][0] == 128, "prima colonna")
    ctx.check(any(x >= 400 for x in two), "seconda colonna")

    expert.layout_radios["labels_left"].setChecked(True)
    expert.font_combo.setCurrentIndex(expert.font_combo.findData("Courier New"))
    expert.size_spin.setValue(14)
    expert.bold_check.setChecked(True)
    expert.style_combo.setCurrentIndex(expert.style_combo.findData("compact"))
    styled = expert.build_spec()
    field = next(control for control in styled.all_controls() if control.field == "codice")
    ctx.check_close(field.font_name, "Courier New", "font scelto")
    ctx.check_close(field.font_size, 14, "dimensione font")
    ctx.check(field.bold, "grassetto")
    ctx.check_close(field.h, 20, "altezza compatta")

    expert.background_combo.setCurrentIndex(expert.background_combo.findData("#eef3fb"))
    expert.foreground_combo.setCurrentIndex(expert.foreground_combo.findData("#000080"))
    colored = expert.build_spec()
    ctx.check_close(colored.backcolor, "#eef3fb", "sfondo del form")
    ctx.check_close(colored.forecolor, "#000080", "colore del testo")
    field = next(control for control in colored.all_controls() if control.field == "codice")
    ctx.check_close(field.forecolor, "#000080", "colore del controllo")


@scenario(
    "frm-03-palette-controls",
    "F03 — Form Designer: palette con i dodici controlli",
    "forms",
    features=("FRM-DESIGNER-PALETTE", "FRM-CONTROL-LABEL", "FRM-CONTROL-FIELD", "FRM-CONTROL-MEMO", "FRM-CONTROL-CHECKBOX", "FRM-CONTROL-COMBO", "FRM-CONTROL-NUMBER", "FRM-CONTROL-DATE", "FRM-CONTROL-BUTTON", "FRM-CONTROL-GRID", "FRM-CONTROL-LINE", "FRM-CONTROL-RECT", "FRM-CONTROL-IMAGE"),
    min_checks=16,
    budget_s=10.0,
    screenshots=("form-designer",),
)
def frm_palette_controls(ctx: E2EContext) -> None:
    project = _settled(ctx, "PaletteForm")
    spec = FormSpec(name="palette", caption="Palette", table="clienti")
    designer = _designer(ctx, project, spec)
    ctx.check_close(len(designer.palette.tool_buttons), 27, "pointer, controlli e pulsanti dBASE")
    for kind in CONTROL_KINDS:
        ctx.check(kind in designer.palette.tool_buttons, f"pulsante {kind}")
    added: list[FormControl] = []
    for index, kind in enumerate(CONTROL_KINDS):
        control = designer.add_control(kind, x=20 + index * 8, y=20 + index * 8)
        ctx.check(control is not None, f"aggiunto {kind}")
        added.append(control)
    ctx.check_close({control.kind for control in added}, set(CONTROL_KINDS), "dodici tipi presenti")
    ctx.check_close(len(designer.current_page().controls), 12, "dodici controlli sulla pagina")
    ctx.check(designer.save(), "form salvato")
    reopened = ctx.reopen(project)
    artifact = reopened.artifact("forms", "palette")
    ctx.check_close(len(artifact["pages"][0]["controls"]), 12, "controlli persistiti")
    ctx.capture(designer, "form-designer", (1160, 760))


@scenario(
    "frm-04-field-palette",
    "F04 — Palette Field, etichetta automatica e binding",
    "forms",
    features=("FRM-PALETTE-FIELD", "FRM-AUTOLABEL", "FRM-FIELD-KINDS"),
    min_checks=10,
    budget_s=8.0,
)
def frm_field_palette(ctx: E2EContext) -> None:
    project = _settled(ctx, "PaletteField")
    spec = FormSpec(name="campi", caption="Campi", table="clienti")
    designer = _designer(ctx, project, spec)
    ctx.check_close(designer.palette.fields.count(), 8, "campi disponibili")
    ctx.check(designer.palette.fields.dragEnabled(), "trascinamento abilitato")
    expected = {
        "codice": "field",
        "note": "memo",
        "saldo": "number",
        "data_nascita": "date",
        "attivo": "checkbox",
    }
    for index, (field_name, kind) in enumerate(expected.items()):
        before = len(designer.current_page().controls)
        designer.palette.field_activated.emit(field_name)
        controls = designer.current_page().controls
        ctx.check_close(len(controls), before + 2, f"{field_name}: etichetta e controllo")
        label, control = controls[-2], controls[-1]
        ctx.check_close(control.field, field_name, f"{field_name}: binding")
        ctx.check_close(control.kind, kind, f"{field_name}: tipo controllo")
        ctx.check_close(label.kind, "label", f"{field_name}: etichetta")
        ctx.check_close(label.x, control.x - 150, f"{field_name}: etichetta a sinistra")
        ctx.check_close(label.text, project.require_table("clienti").field(field_name).display_name(), f"{field_name}: testo etichetta")
    ctx.check_close(len(designer.current_page().controls), 10, "cinque campi completi")


@scenario(
    "frm-05-geometry",
    "F05 — Geometria: righelli, griglia, maniglie e tastiera",
    "forms",
    features=("FRM-GRID-SNAP", "FRM-HANDLES", "FRM-KEYBOARD"),
    min_checks=10,
    budget_s=8.0,
)
def frm_geometry(ctx: E2EContext) -> None:
    project = _settled(ctx, "Geometria")
    spec = FormSpec(name="geometria", caption="Geometria", table="clienti")
    designer = _designer(ctx, project, spec)
    ctx.check_close(SNAP, 8, "passo della griglia")
    ctx.check(designer.h_ruler.horizontal, "righello orizzontale")
    ctx.check(not designer.v_ruler.horizontal, "righello verticale")
    control = designer.add_control("label", 13, 13)
    ctx.check_close((control.x, control.y), (8, 8), "snap all'aggiunta")
    points = designer.canvas.handle_points(control)
    ctx.check_close(len(points), 8, "otto maniglie")
    ctx.check_close({name for name, _x, _y in points}, {"nw", "n", "ne", "e", "se", "s", "sw", "w"}, "nomi maniglie")
    designer.canvas.set_selection([control.id])
    designer.canvas.setFocus()
    QTest.keyClick(designer.canvas, Qt.Key.Key_Right)
    ctx.check_close(control.x, 16, "freccia a passo griglia")
    QTest.keyClick(designer.canvas, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    ctx.check_close(control.x, 17, "shift a passo fine")
    ctx.check_close(designer.status_labels["Left"].text(), "Left: 2.12", "stato geometria")
    designer.toggle_grid(False)
    ctx.check(not designer.canvas.show_grid, "griglia nascosta")
    designer.toggle_grid(True)
    ctx.check(designer.canvas.show_grid, "griglia mostrata")


@scenario(
    "frm-06-clipboard",
    "F06 — Selezione multipla, clipboard e undo/redo",
    "forms",
    features=("FRM-MULTISELECT", "FRM-CLIPBOARD", "FRM-UNDO-REDO"),
    min_checks=10,
    budget_s=8.0,
)
def frm_clipboard(ctx: E2EContext) -> None:
    project = _settled(ctx, "Clipboard")
    spec = FormSpec(name="clipboard", caption="Clipboard", table="clienti")
    designer = _designer(ctx, project, spec)
    controls = [designer.add_control("label", 20 + index * 40, 20) for index in range(3)]
    ids = [control.id for control in controls]
    designer._select(ids[:2])
    ctx.check_close(len(designer.selected_controls()), 2, "selezione multipla")
    designer.copy_selection()
    ctx.check_close(len(designer.clipboard), 2, "due oggetti copiati")
    designer.paste_clipboard()
    ctx.check_close(len(designer.current_page().controls), 5, "incolla due oggetti")
    ctx.check_close(len(designer.selected_controls()), 2, "incollati selezionati")
    designer.duplicate_selection()
    ctx.check_close(len(designer.current_page().controls), 7, "duplica selezione")
    designer.remove_selected()
    ctx.check_close(len(designer.current_page().controls), 5, "elimina selezione")
    ctx.check(designer.undo_button.isEnabled(), "annulla disponibile")
    designer.undo()
    ctx.check_close(len(designer.current_page().controls), 7, "annulla ripristina")
    ctx.check(designer.redo_button.isEnabled(), "ripeti disponibile")
    designer.redo()
    ctx.check_close(len(designer.current_page().controls), 5, "ripeti elimina")
    designer._select(ids[:2])
    designer.cut_selection()
    ctx.check_close(len(designer.current_page().controls), 3, "taglia selezione")
    ctx.check_close(len(designer.clipboard), 2, "clipboard conservata")


@scenario(
    "frm-07-align-distribute",
    "F07 — Allinea, distribuisci e ordine Z",
    "forms",
    features=("FRM-ALIGN", "FRM-DISTRIBUTE", "FRM-ZORDER"),
    min_checks=9,
    budget_s=8.0,
)
def frm_align_distribute(ctx: E2EContext) -> None:
    project = _settled(ctx, "Allineamento")
    spec = FormSpec(name="allinea", caption="Allinea", table="clienti")
    designer = _designer(ctx, project, spec)
    controls = [
        designer.add_control("label", 10, 10),
        designer.add_control("label", 100, 40),
        designer.add_control("label", 220, 70),
    ]
    ids = [control.id for control in controls]
    designer._select(ids)

    def reset() -> None:
        for control, (x, y) in zip(controls, ((10, 10), (100, 40), (220, 70))):
            control.x, control.y = x, y

    reset()
    designer.align_selection("left")
    ctx.check_close([control.x for control in controls], [10, 10, 10], "allinea a sinistra")
    reset()
    designer.align_selection("right")
    ctx.check_close([control.x + control.w for control in controls], [400, 400, 400], "allinea a destra")
    reset()
    designer.align_selection("top")
    ctx.check_close([control.y for control in controls], [10, 10, 10], "allinea in alto")
    reset()
    designer.align_selection("bottom")
    ctx.check_close([control.y + control.h for control in controls], [94, 94, 94], "allinea in basso")
    reset()
    designer.align_selection("middle")
    centers = [control.y + control.h // 2 for control in controls]
    ctx.check_close(len(set(centers)), 1, "centro verticale")

    reset()
    designer.distribute_selection("horizontal")
    ctx.check_close([control.x for control in controls], [10, 115, 220], "distribuisci orizzontalmente")
    reset()
    designer.distribute_selection("vertical")
    ctx.check_close([control.y for control in controls], [10, 40, 70], "distribuisci verticalmente")

    designer._select([controls[0].id])
    designer.bring_to_front()
    ctx.check_close(designer.current_page().controls[-1].id, controls[0].id, "porta in primo piano")
    designer.send_to_back()
    ctx.check_close(designer.current_page().controls[0].id, controls[0].id, "porta sullo sfondo")


@scenario(
    "frm-08-pages",
    "F08 — Pagine: aggiunta, rinomina, rimozione e persistenza",
    "forms",
    features=("FRM-PAGES",),
    min_checks=9,
    budget_s=8.0,
)
def frm_pages(ctx: E2EContext) -> None:
    project = _settled(ctx, "Pagine")
    spec = FormSpec(name="pagine", caption="Pagine", table="clienti")
    designer = _designer(ctx, project, spec)
    designer.add_control("label", 20, 20)
    with mock.patch.object(QInputDialog, "getText", return_value=("Dettagli", True)):
        designer.add_page()
    ctx.check_close(len(designer.spec.pages), 2, "seconda pagina")
    ctx.check_close(designer.page_bar.count(), 2, "schede allineate")
    designer.add_control("field", 40, 40, field_name="nome")
    ctx.check_close(len(designer.spec.pages[1].controls), 1, "controllo sulla seconda pagina")
    with mock.patch.object(QInputDialog, "getText", return_value=("Extra", True)):
        designer.rename_page()
    ctx.check_close(designer.spec.pages[1].caption, "Extra", "pagina rinominata")
    designer.page_bar.setCurrentIndex(0)
    ctx.check_close(designer.page_index, 0, "cambio pagina")
    ctx.check_close(len(designer.current_page().controls), 1, "controlli della prima pagina")
    ctx.check(designer.save(), "form con pagine salvato")
    reopened = ctx.reopen(project)
    stored = FormSpec.from_dict(reopened.artifact("forms", "pagine"))
    ctx.check_close([page.caption for page in stored.pages], ["Dati", "Extra"], "pagine persistite")

    second = _designer(ctx, reopened, stored)
    second.page_bar.setCurrentIndex(1)
    second.remove_page()
    ctx.check_close(len(second.spec.pages), 1, "pagina rimossa")
    ctx.check(second.save(), "form con una pagina salvato")
    again = ctx.reopen(reopened)
    final = FormSpec.from_dict(again.artifact("forms", "pagine"))
    ctx.check_close(len(final.pages), 1, "rimozione persistita")


@scenario(
    "frm-09-inspector",
    "F09 — Object Inspector: gruppi e modifica immediata",
    "forms",
    features=("FRM-INSPECTOR", "FRM-INSPECTOR-FORM", "FRM-INSPECTOR-DATA"),
    min_checks=13,
    budget_s=10.0,
)
def frm_inspector(ctx: E2EContext) -> None:
    project = _settled(ctx, "Inspector")
    spec = FormSpec.create(project.require_table("clienti"), name="ispettore")
    designer = _designer(ctx, project, spec)
    control = _control(spec, field="nome")
    designer._select([control.id])
    groups = [designer.inspector.tree.topLevelItem(i).text(0) for i in range(designer.inspector.tree.topLevelItemCount())]
    ctx.check_close(groups, ["• Font Properties", "• Geometry", "• Data", "• Behavior", "• Layout"], "gruppi del controllo")
    ctx.check_close(designer.inspector.tabs.count(), 3, "tre schede inspector")

    designer._on_property_changed("font_size", 15)
    designer._on_property_changed("bold", True)
    designer._on_property_changed("x", 40)
    designer._on_property_changed("kind", "memo")
    designer._on_property_changed("field", "citta")
    designer._on_property_changed("align", "center")
    designer._on_property_changed("backcolor", "#eeeeee")
    ctx.check_close(control.font_size, 15, "dimensione font")
    ctx.check(control.bold, "grassetto")
    ctx.check_close(control.x, 40, "posizione")
    ctx.check_close(control.kind, "memo", "classe del controllo")
    ctx.check_close(control.field, "citta", "campo collegato")
    ctx.check_close(control.align, "center", "allineamento")
    ctx.check_close(control.backcolor, "#eeeeee", "sfondo del controllo")

    designer._select([])
    form_groups = [designer.inspector.tree.topLevelItem(i).text(0) for i in range(designer.inspector.tree.topLevelItemCount())]
    ctx.check_close(form_groups, ["• Form", "• Data"], "gruppi del form")
    designer._on_property_changed("width", 800)
    designer._on_property_changed("caption", "Form largo")
    designer._on_property_changed("view_mode", "list")
    designer._on_property_changed("list_fields", "codice,nome")
    designer._on_property_changed("backcolor", "#ffffff")
    designer._on_property_changed("forecolor", "#000000")
    designer._on_property_changed("order", "nome")
    ctx.check_close(designer.spec.width, 800, "larghezza form")
    ctx.check_close(designer.canvas.width(), 800, "canvas aggiornato")
    ctx.check_close(designer.spec.caption, "Form largo", "didascalia form")
    ctx.check_close(designer.spec.view_mode, "list", "vista lista")
    ctx.check_close(designer.spec.list_fields, "codice,nome", "campi lista")
    ctx.check_close(designer.spec.order, "nome", "ordine del form")
    ctx.check_close(designer.spec.backcolor, "#ffffff", "sfondo del form")


@scenario(
    "frm-10-control-events",
    "F10 — Eventi controllo onClick/onEnter/onExit",
    "forms",
    features=("FRM-EVENT-ONCLICK", "FRM-EVENT-ONENTER", "FRM-EVENT-ONEXIT"),
    min_checks=7,
    budget_s=8.0,
)
def frm_control_events(ctx: E2EContext) -> None:
    project = _settled(ctx, "EventiControllo")
    spec = FormSpec.create(project.require_table("clienti"), name="eventi_controllo")
    designer = _designer(ctx, project, spec)
    field = _control(spec, field="nome")
    button = _control(spec, kind="button", action="save")
    designer._select([field.id])
    designer._on_event_changed("onEnter", "message:Entrato")
    designer._on_event_changed("onExit", "message:Uscito")
    designer._select([button.id])
    designer._on_event_changed("onClick", "message:Click")
    ctx.check_close(field.events["onEnter"], "message:Entrato", "evento onEnter")
    ctx.check_close(field.events["onExit"], "message:Uscito", "evento onExit")
    ctx.check_close(button.events["onClick"], "message:Click", "evento onClick")

    runtime = _runtime(ctx, project, designer.spec)
    binder = next(item for item in runtime.binders if item.control.field == "nome")
    ctx.qapp.sendEvent(binder.widget, QEvent(QEvent.Type.Enter))
    ctx.check("Entrato" in runtime._status.text(), "onEnter eseguito")
    ctx.qapp.sendEvent(binder.widget, QEvent(QEvent.Type.Leave))
    ctx.check("Uscito" in runtime._status.text(), "onExit eseguito")
    widget = next(button_widget for button_widget, control_id in runtime.buttons if control_id == button.id)
    widget.click()
    ctx.check("Click" in runtime._status.text(), "onClick eseguito")
    ctx.check(any("Click" in entry[2] for entry in ctx.dialogs), "messaggio onClick")


@scenario(
    "frm-11-form-events-methods",
    "F11 — Eventi form onOpen/onClose e metodi save/close",
    "forms",
    features=("FRM-EVENT-ONOPEN", "FRM-EVENT-ONCLOSE", "FRM-METHOD-SAVE", "FRM-METHOD-CLOSE", "FRM-METHODS"),
    min_checks=10,
    budget_s=8.0,
)
def frm_form_events_methods(ctx: E2EContext) -> None:
    project = _settled(ctx, "EventiForm")
    spec = FormSpec.create(project.require_table("clienti"), name="eventi_form")
    designer = _designer(ctx, project, spec)
    designer._select([])
    designer._on_event_changed("onOpen", "last")
    designer._on_event_changed("onClose", "first")
    designer._on_method_changed("save", "salva il record corrente")
    designer._on_method_changed("close", "chiude la finestra")
    ctx.check_close(designer.spec.events["onOpen"], "last", "evento onOpen")
    ctx.check_close(designer.spec.events["onClose"], "first", "evento onClose")
    ctx.check_close(designer.spec.methods["save"], "salva il record corrente", "metodo save")
    ctx.check_close(designer.spec.methods["close"], "chiude la finestra", "metodo close")
    ctx.check_close(designer.inspector.methods.rowCount(), 2, "metodi nell'ispettore")
    ctx.check("non esegue" in designer.inspector.methods_hint.text(), "metodi descrittivi")

    ctx.check(designer.save(), "form salvato")
    reopened = ctx.reopen(project)
    stored = FormSpec.from_dict(reopened.artifact("forms", "eventi_form"))
    ctx.check_close(stored.events["onOpen"], "last", "evento persistito")
    ctx.check_close(stored.methods["save"], "salva il record corrente", "metodo persistito")

    runtime = _runtime(ctx, reopened, stored)
    ctx.check_close(runtime.rowset.index, runtime.rowset.count() - 1, "onOpen eseguito")
    runtime._close()
    ctx.check_close(runtime.rowset.index, 0, "onClose eseguito")


@scenario(
    "frm-12-runtime",
    "F12 — Runtime: CRUD, navigazione, stato e validazione",
    "forms",
    features=(
        "FRM-RUNTIME-CRUD",
        "FRM-RUNTIME-NAV",
        "FRM-RUNTIME-STATUS",
        "FRM-RUNTIME-VALIDATION",
        "FRM-RUNTIME-MESSAGES",
    ),
    min_checks=16,
    budget_s=10.0,
    screenshots=("form-runtime",),
)
def frm_runtime(ctx: E2EContext) -> None:
    project = _settled(ctx, "RuntimeForm")
    spec = FormSpec.create(project.require_table("clienti"), name="runtime_clienti")
    runtime = _runtime(ctx, project, spec)
    ctx.check_close(runtime.rowset.index, 0, "primo record")
    ctx.check("Record 1 di 5" in runtime._status.text(), "stato iniziale")
    runtime.perform("next")
    ctx.check_close(runtime.rowset.index, 1, "successivo")
    ctx.check("Record 2 di 5" in runtime._status.text(), "stato dopo next")
    runtime.perform("last")
    ctx.check_close(runtime.rowset.index, 4, "ultimo")
    runtime.perform("first")
    ctx.check_close(runtime.rowset.index, 0, "primo")
    runtime.perform("previous")
    ctx.check_close(runtime.rowset.index, 0, "precedente ai limiti")

    binders = {binder.control.field: binder for binder in runtime.binders}
    binders["nome"].set_value("Alfa Modificata")
    ctx.check(runtime.save(), "modifica salvata")
    ctx.check_close(runtime.rowset.current["nome"], "Alfa Modificata", "modifica persistita")
    ctx.check("Record salvato" in runtime._status.text(), "messaggio di salvataggio")

    runtime.perform("new")
    ctx.check("Nuovo record" in runtime._status.text(), "stato nuovo record")
    binders["codice"].set_value("C900")
    binders["nome"].set_value("Nuovo record")
    ctx.check(runtime.save(), "nuovo record salvato")
    ctx.check_close(runtime.rowset.count(), 6, "conteggio dopo creazione")
    ctx.check_close(runtime.rowset.current["codice"], "C900", "record corrente creato")

    runtime.perform("new")
    ctx.check(not runtime.save(), "validazione blocca il salvataggio")
    ctx.check("Salvataggio non riuscito" in runtime._status.text(), "messaggio di validazione")
    ctx.check(any(binder.widget.property("state") == "error" for binder in runtime.binders), "campo evidenziato")
    ctx.check(any(binder.widget.toolTip() for binder in runtime.binders), "motivo nel tooltip")

    runtime.perform("delete")
    ctx.check_close(runtime.rowset.count(), 5, "eliminazione record nuovo")
    ctx.check("Record eliminato" in runtime._status.text(), "messaggio di eliminazione")
    runtime.perform("message:Evento di prova")
    ctx.check("Evento di prova" in runtime._status.text(), "messaggio runtime")
    ctx.capture(runtime, "form-runtime", (980, 700))


@scenario(
    "frm-13-buttons",
    "F13 — Runtime: tutti gli otto pulsanti azione",
    "forms",
    features=tuple(f"FRM-BUTTON-{action.upper()}" for action in BUTTON_ACTIONS),
    min_checks=9,
    budget_s=10.0,
)
def frm_buttons(ctx: E2EContext) -> None:
    project = _settled(ctx, "PulsantiForm")
    spec = FormSpec.create(project.require_table("clienti"), name="pulsanti")
    runtime = _runtime(ctx, project, spec)
    with ctx.quiet_qt():
        runtime.show()
        ctx.qapp.processEvents()
    controls = {control.id: control for control in spec.all_controls()}
    buttons = {
        controls[control_id].action: button
        for button, control_id in runtime.buttons
        if control_id in controls
    }
    ctx.check_close(set(buttons), set(BUTTON_ACTIONS), "otto azioni presenti")
    buttons["last"].click()
    ctx.check_close(runtime.rowset.index, 4, "pulsante Ultimo")
    buttons["first"].click()
    ctx.check_close(runtime.rowset.index, 0, "pulsante Primo")
    buttons["next"].click()
    ctx.check_close(runtime.rowset.index, 1, "pulsante Successivo")
    buttons["previous"].click()
    ctx.check_close(runtime.rowset.index, 0, "pulsante Precedente")
    buttons["new"].click()
    ctx.check("Nuovo record" in runtime._status.text(), "pulsante Nuovo")
    binders = {binder.control.field: binder for binder in runtime.binders}
    binders["codice"].set_value("C777")
    binders["nome"].set_value("Da pulsante")
    buttons["save"].click()
    ctx.check_close(runtime.rowset.count(), 6, "pulsante Salva")
    buttons["delete"].click()
    ctx.check_close(runtime.rowset.count(), 5, "pulsante Elimina")
    buttons["close"].click()
    ctx.qapp.processEvents()
    ctx.check(not runtime.isVisible(), "pulsante Chiudi")


@scenario(
    "frm-14-list-view",
    "F14 — Vista Lista: campi, ordinamento e apertura record",
    "forms",
    features=("FRM-LIST-VIEW", "FRM-LIST-FIELDS", "FRM-LIST-SELECT"),
    min_checks=9,
    budget_s=8.0,
    screenshots=("form-list",),
)
def frm_list_view(ctx: E2EContext) -> None:
    project = _settled(ctx, "ListaForm")
    spec = FormSpec.create(project.require_table("clienti"), name="lista_clienti")
    spec.view_mode = "list"
    spec.list_fields = "codice,nome,citta"
    spec.order = "nome desc"
    runtime = _runtime(ctx, project, spec)
    ctx.check(runtime.is_list_view(), "vista Lista iniziale")
    ctx.check_close(runtime._list.columnCount(), 3, "tre colonne")
    headers = [runtime._list.horizontalHeaderItem(i).text() for i in range(3)]
    ctx.check_close(headers, ["Codice", "Nome", "Citta"], "campi della lista")
    names = [runtime._list.item(row, 1).text() for row in range(runtime._list.rowCount())]
    ctx.check_close(names, ["Gamma snc", "Epsilon", "Delta Spa", "Beta Studio", "Alfa Srl"], "ordine discendente")
    runtime._list.selectRow(2)
    ctx.qapp.processEvents()
    ctx.check_close(runtime.rowset.current["codice"], "C004", "selezione dalla lista")
    runtime._on_list_clicked(4, 0)
    ctx.check_close(runtime.rowset.current["codice"], "C001", "clic sulla lista")
    runtime.toggle_view()
    ctx.check(not runtime.is_list_view(), "ritorno alla scheda")
    ctx.check("lista" not in runtime._status.text(), "stato scheda")
    runtime.toggle_view()
    ctx.check("lista" in runtime._status.text(), "stato lista")
    ctx.capture(runtime, "form-list", (900, 620))


@scenario(
    "frm-15-portal",
    "F15 — Portale uno-a-molti: collegamento, ordine e filtro",
    "forms",
    features=("FRM-PORTAL-LINK", "FRM-PORTAL-ORDER", "FRM-PORTAL-FILTER"),
    min_checks=9,
    budget_s=10.0,
)
def frm_portal(ctx: E2EContext) -> None:
    project = _settled(ctx, "PortaleForm")
    invoices = Rowset(project.db, project.require_table("fatture"))
    invoices.insert({"numero": 5, "cliente": "C001", "data": "2026-05-10", "importo": 250.0, "pagata": False})
    spec = FormSpec.create_master_detail(
        project.require_table("clienti"),
        project.require_table("fatture"),
        "codice",
        "cliente",
        name="clienti_portale",
    )
    grid = next(control for control in spec.all_controls() if control.kind == "grid")
    grid.order = "importo desc"
    grid.filter = "[importo] >= 200"
    ctx.check_close(grid.link_parent, "codice", "campo padre")
    ctx.check_close(grid.link_child, "cliente", "campo figlio")
    runtime = _runtime(ctx, project, spec)
    runtime.rowset.first()
    runtime.load_current()
    table = runtime.grids[0][0]
    ctx.check_close(table.rowCount(), 2, "due fatture filtrate")
    ctx.check_close(table.item(0, 3).text(), "250", "ordine discendente")
    ctx.check_close(table.item(1, 3).text(), "200", "seconda fattura")
    runtime.rowset.goto(1)
    runtime.load_current()
    ctx.check_close(table.rowCount(), 1, "filtro per il secondo cliente")
    ctx.check_close(table.item(0, 0).text(), "3", "fattura del cliente")
    project.put_object("forms", spec.to_dict())
    project.save()
    reopened = ctx.reopen(project)
    stored = FormSpec.from_dict(reopened.artifact("forms", "clienti_portale"))
    restored = next(control for control in stored.all_controls() if control.kind == "grid")
    ctx.check_close(restored.filter, "[importo] >= 200", "filtro persistito")
    ctx.check_close(restored.order, "importo desc", "ordine persistito")


@scenario(
    "frm-16-form-query",
    "F16 — Form su query: aggregati, sola lettura e navigazione",
    "forms",
    features=("FRM-QUERY-READONLY", "FRM-QUERY-CALC", "FRM-QUERY-NAV"),
    min_checks=11,
    budget_s=10.0,
)
def frm_form_query(ctx: E2EContext) -> None:
    project = _settled(ctx, "FormQuery")
    query = QuerySpec(
        name="fatture_totali",
        caption="Totale per cliente",
        base="fatture",
        fields=[QueryField("fatture", "cliente")],
        group_by=["fatture.cliente"],
        aggregates=[QueryAggregate("sum", "fatture", "importo", "totale")],
        sorts=[QuerySort("totale", "desc")],
    )
    project.put_object("queries", query.to_dict())
    project.save()
    from dbx.core.query_engine import query_table

    columns = query_table(project, "fatture_totali")
    ctx.check(columns.field("totale") is not None, "colonna aggregata")
    spec = FormSpec.create_from_query(columns, "fatture_totali", name="form_fatture_totali")
    runtime = _runtime(ctx, project, spec)
    ctx.check(runtime.read_only, "form in sola lettura")
    ctx.check_close(runtime.rowset.count(), 3, "tre gruppi")
    totale = next(binder for binder in runtime.binders if binder.control.field == "totale")
    ctx.check_close(round(totale.widget.value(), 1), 300.0, "valore aggregato mostrato")
    ctx.check("sola lettura" in runtime._status.text(), "stato sola lettura")
    runtime.perform("next")
    ctx.check_close(runtime.rowset.current["cliente"], "C002", "navigazione sul gruppo")
    ctx.check_close(round(totale.widget.value(), 1), 300.0, "aggregato aggiornato")
    ctx.check(not runtime.save(), "salvataggio bloccato")
    ctx.check("sola lettura" in runtime._status.text(), "messaggio di blocco")
    runtime.perform("new")
    ctx.check("sola lettura" in runtime._status.text(), "nuovo record bloccato")
    toolbar = {button.text(): button for button in runtime.findChildren(QPushButton)}
    ctx.check(not toolbar["Nuovo"].isEnabled(), "pulsante Nuovo disabilitato")
    ctx.check(not toolbar["Salva"].isEnabled(), "pulsante Salva disabilitato")
    ctx.check(not toolbar["Elimina"].isEnabled(), "pulsante Elimina disabilitato")
    del spec


@scenario(
    "frm-17-round-trip",
    "F17 — Round-trip del form e compatibilità JSON legacy",
    "forms",
    features=("FRM-ROUNDTRIP", "FRM-LEGACY-JSON"),
    min_checks=10,
    budget_s=8.0,
)
def frm_round_trip(ctx: E2EContext) -> None:
    project = _settled(ctx, "RoundTripForm")
    spec = FormSpec.create(project.require_table("clienti"), name="round_trip")
    spec.events["onOpen"] = "first"
    spec.methods["save"] = "salva"
    spec.pages[0].caption = "Anagrafica"
    designer = _designer(ctx, project, spec)
    ctx.check(designer.save(), "form salvato")
    reopened = ctx.reopen(project)
    stored = FormSpec.from_dict(reopened.artifact("forms", "round_trip"))
    ctx.check_close(stored.to_dict(), spec.to_dict(), "JSON identico")
    second = _designer(ctx, reopened, stored)
    ctx.check_close(second.page_bar.count(), 1, "designer riaperto")
    ctx.check_close(
        len(second.current_page().controls),
        len(spec.pages[0].controls),
        "controlli riaperti",
    )
    ctx.check_close(second.spec.events["onOpen"], "first", "eventi riaperti")
    ctx.check_close(second.spec.methods["save"], "salva", "metodi riaperti")

    legacy = {
        "name": "legacy_form",
        "table": "clienti",
        "pages": [
            {
                "caption": "Dati",
                "controls": [
                    {"id": "legacy1", "kind": "field", "field": "nome", "x": 8, "y": 8, "w": 180, "h": 24}
                ],
            }
        ],
    }
    old = FormSpec.from_dict(legacy)
    ctx.check_close(old.source_type, "table", "sorgente legacy")
    ctx.check_close(old.view_mode, "form", "vista legacy")
    ctx.check_close(old.width, 620, "larghezza predefinita")
    ctx.check_close(old.events, {}, "eventi predefiniti")
    ctx.check_close(old.methods, {}, "metodi predefiniti")
    control = old.pages[0].controls[0]
    ctx.check_close(control.action, "save", "azione predefinita")
    ctx.check_close(control.lookup, "", "lookup predefinito")
    ctx.check(old.validate() == [], "form legacy valido")
    reopened.put_object("forms", old.to_dict(), previous_name="legacy_form")
    reopened.save()
    again = ctx.reopen(reopened)
    restored = FormSpec.from_dict(again.artifact("forms", "legacy_form"))
    ctx.check_close(restored.pages[0].controls[0].field, "nome", "campo legacy persistito")
    ctx.check(validate_project(again) == [], "progetto legacy valido")
