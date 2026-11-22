"""Test del Form Designer a tre zone, dell'Inspector e del Form Expert."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QInputDialog

from dbx.core.form_model import FormSpec, object_name
from dbx.designers.form_builder import FormBuilderDialog, FormDesignerWidget
from dbx.designers.form_expert import FormExpert
from dbx.runtime.form_runtime import FormRuntime
from dbx.ui.main_window import MainWindow


def _spec(demo_project) -> FormSpec:
    artifact = demo_project.artifact("forms", "form_clienti")
    assert artifact is not None
    return FormSpec.from_dict(artifact)


def test_designer_basics_and_status(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        assert designer.canvas.page.controls
        assert designer.page_bar.count() == 1
        assert designer.object_combo.count() == len(designer.canvas.page.controls) + 1
        assert designer.status_labels["Object"].text().startswith("Object: form")
        assert designer.status_labels["Page"].text() == "Page: 1"
        assert designer.is_dirty() is False
        assert designer.inspector.tree.topLevelItemCount() >= 2
    finally:
        designer.close()


def test_drag_snaps_to_eight_pixels(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        control = designer.canvas.page.controls[0]
        designer.canvas.set_selection([control.id])
        start = QPoint(control.x + control.w // 2, control.y + control.h // 2)
        end = start + QPoint(41, 25)
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(designer.canvas, end)
        QTest.mouseRelease(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, end)
        assert control.x == (start.x() + 41 - control.w // 2) // 8 * 8
        assert control.x % 8 == 0 and control.y % 8 == 0
        assert control.x > 0
    finally:
        designer.close()


def test_resize_handles_change_geometry(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        control = designer.canvas.page.controls[0]
        designer.canvas.set_selection([control.id])
        before = (control.w, control.h)
        handle = QPoint(control.x + control.w, control.y + control.h)
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, handle)
        QTest.mouseMove(designer.canvas, handle + QPoint(32, 16))
        QTest.mouseRelease(
            designer.canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            handle + QPoint(32, 16),
        )
        assert (control.w, control.h) == (before[0] + 32, before[1] + 16)
    finally:
        designer.close()


def test_keyboard_moves_by_grid_and_shift_for_fine_step(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        control = designer.canvas.page.controls[0]
        designer.canvas.set_selection([control.id])
        designer.canvas.setFocus()
        start = (control.x, control.y)
        QTest.keyClick(designer.canvas, Qt.Key.Key_Right)
        assert (control.x, control.y) == (start[0] + 8, start[1])
        QTest.keyClick(designer.canvas, Qt.Key.Key_Down, Qt.KeyboardModifier.ShiftModifier)
        assert (control.x, control.y) == (start[0] + 8, start[1] + 1)
    finally:
        designer.close()


def test_align_and_distribute_selection(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        first = designer.add_control("label", 8, 200)
        second = designer.add_control("label", 120, 240)
        third = designer.add_control("label", 300, 280)
        assert first is not None and second is not None and third is not None
        designer._select([first.id, second.id, third.id])
        designer.align_selection("left")
        assert {control.x for control in (first, second, third)} == {8}
        second.x = 100
        third.x = 400
        designer.distribute_selection("horizontal")
        assert first.x == 8
        assert second.x == (8 + first.w + 400 - third.w) // 2 or first.x < second.x < third.x
        designer.align_selection("top")
        assert {control.y for control in (first, second, third)} == {200}
    finally:
        designer.close()


def test_clipboard_duplicate_and_undo(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        page = designer.current_page()
        initial = len(page.controls)
        control = designer.add_control("label", 8, 200)
        assert control is not None
        assert len(designer.current_page().controls) == initial + 1
        designer.undo()
        assert len(designer.current_page().controls) == initial
        designer.redo()
        assert len(designer.current_page().controls) == initial + 1
        designer._select([control.id])
        designer.copy_selection()
        assert len(designer.clipboard) == 1
        before_paste = len(designer.current_page().controls)
        designer.paste_clipboard()
        assert len(designer.current_page().controls) == before_paste + 1
        pasted = designer.selected_controls()[0]
        assert pasted.id != control.id
        designer.duplicate_selection()
        assert len(designer.current_page().controls) == before_paste + 2
    finally:
        designer.close()


def test_z_order_and_remove(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        control = designer.add_control("label", 8, 200)
        assert control is not None
        designer._select([control.id])
        assert designer.current_page().controls[-1] is control
        designer.send_to_back()
        assert designer.current_page().controls[0] is control
        designer.bring_to_front()
        assert designer.current_page().controls[-1] is control
        count = len(designer.current_page().controls)
        designer.remove_selected()
        assert len(designer.current_page().controls) == count - 1
        assert designer.canvas.selection == []
    finally:
        designer.close()


def test_pages_add_rename_remove(qapp, demo_project, monkeypatch) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Extra", True)))
        designer.add_page()
        assert designer.page_bar.count() == 2
        assert designer.current_page().caption == "Extra"
        monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Dettagli", True)))
        designer.rename_page()
        assert designer.current_page().caption == "Dettagli"
        designer.remove_page()
        assert designer.page_bar.count() == 1
    finally:
        designer.close()


def test_palette_places_dbase_button(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        assert "OKBUTTON" in designer.palette.tool_buttons
        assert "CLOSEBUTTON" in designer.palette.tool_buttons
        initial = len(designer.current_page().controls)
        designer.palette.tool_buttons["OKBUTTON"].click()
        QTest.mouseClick(designer.canvas, Qt.MouseButton.LeftButton, pos=QPoint(64, 64))
        assert len(designer.current_page().controls) == initial + 1
        button = designer.current_page().controls[-1]
        assert button.kind == "button"
        assert button.text == "OK"
        assert button.action == "save"
    finally:
        designer.close()


def test_field_palette_adds_label_and_control(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        initial = len(designer.current_page().controls)
        designer.add_field_control("nome", x=200, y=200)
        assert len(designer.current_page().controls) == initial + 2
        label, control = designer.current_page().controls[-2:]
        assert label.kind == "label" and label.text == "Nome"
        assert control.field == "nome"
        assert control.x == 200
        assert designer.selected_controls() == [control]
    finally:
        designer.close()


def test_inspector_edits_and_quick_filter(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        caption = designer.inspector.item("caption")
        assert caption is not None
        caption.setText(1, "Clienti 2026")
        assert designer.spec.caption == "Clienti 2026"
        assert designer.is_dirty() is True
        assert designer.windowTitle() == "Form Designer (Clienti 2026)"

        designer._select([designer.current_page().controls[0].id])
        font_size = designer.inspector.item("font_size")
        assert font_size is not None
        font_size.setText(1, "12")
        assert designer.selected_controls()[0].font_size == 12

        wide = designer.inspector.item("Width")
        assert wide is not None
        wide.setText(1, "250")
        assert designer.selected_controls()[0].w == 250

        designer._select([])
        designer.inspector.filter_edit.setText("Caption")
        qapp.processEvents()
        assert not designer.inspector.item("caption").isHidden()
        assert designer.inspector.item("order").isHidden()
    finally:
        designer.close()


def test_inspector_edit_geometry_syncs_canvas(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        control = designer.current_page().controls[0]
        designer._select([control.id])
        item = designer.inspector.item("Left")
        assert item is not None
        item.setText(1, "48")
        assert control.x == 48
        widget = designer.canvas.widgets[control.id]
        assert widget.x() == 48
    finally:
        designer.close()


def test_events_and_methods_are_persisted(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        control = designer.current_page().controls[0]
        designer._select([control.id])
        designer.inspector.tabs.setCurrentIndex(1)
        designer.inspector.events.item(0, 1).setText("message:ciao")
        assert control.events["onClick"] == "message:ciao"
        designer.inspector.tabs.setCurrentIndex(2)
        designer.inspector.methods.item(0, 1).setText("corpo del metodo")
        assert control.methods["first"] == "corpo del metodo"
        designer._select([])
        designer.inspector.tabs.setCurrentIndex(1)
        designer.inspector.events.item(0, 1).setText("first")
        assert designer.spec.events["onOpen"] == "first"
        assert designer.save() is True
        artifact = demo_project.artifact("forms", designer.spec.name)
        assert artifact is not None
        reopened = FormDesignerWidget(demo_project, FormSpec.from_dict(artifact))
        try:
            restored = reopened.current_page().controls[0]
            assert restored.events["onClick"] == "message:ciao"
            assert restored.methods["first"] == "corpo del metodo"
            assert reopened.spec.events["onOpen"] == "first"
        finally:
            reopened.close()
    finally:
        designer.close()


def test_save_clears_dirty_and_updates_project(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.spec.caption = "Nuova didascalia"
        assert designer.is_dirty() is True
        assert designer.save() is True
        assert designer.is_dirty() is False
        artifact = demo_project.artifact("forms", designer.spec.name)
        assert artifact is not None
        assert artifact["caption"] == "Nuova didascalia"
    finally:
        designer.close()


def test_alias_keeps_legacy_name(qapp, demo_project) -> None:
    assert FormBuilderDialog is FormDesignerWidget
    legacy = FormBuilderDialog(demo_project, _spec(demo_project))
    try:
        assert legacy.canvas.page.controls
    finally:
        legacy.close()


def test_form_expert_generates_valid_spec(qapp, demo_project) -> None:
    wizard = FormExpert(demo_project, suggested_name="form_expert_test")
    try:
        wizard.initializePage(1)
        wizard.initializePage(2)
        assert wizard.destination_list.count() == len(demo_project.require_table("clienti").fields)
        wizard.layout_radios["two_columns"].setChecked(True)
        spec = wizard.build_spec()
        assert spec.validate() == []
        assert spec.name == "form_expert_test"
        assert spec.table == "clienti"
        controls = spec.pages[0].controls
        assert any(control.kind == "button" and control.action == "close" for control in controls)
        assert any(control.kind == "field" and control.field == "nome" for control in controls)
        labels = [control for control in controls if control.kind == "label"]
        assert {label.x for label in labels if label.text != "Clienti"} == {12, 318}
    finally:
        wizard.close()


def test_form_expert_blank_form(qapp, demo_project) -> None:
    wizard = FormExpert(demo_project, suggested_name="form_vuoto")
    try:
        wizard.initializePage(1)
        wizard.blank_radio.setChecked(True)
        spec = wizard.build_spec()
        assert spec.pages[0].controls == []
        assert spec.table == "clienti"
        assert spec.validate() == []
    finally:
        wizard.close()


def test_form_expert_fields_selection(qapp, demo_project) -> None:
    wizard = FormExpert(demo_project, suggested_name="form_parziale")
    try:
        wizard.initializePage(1)
        while wizard.destination_list.count() > 1:
            item = wizard.destination_list.item(wizard.destination_list.count() - 1)
            wizard.destination_list.takeItem(wizard.destination_list.row(item))
        spec = wizard.build_spec()
        fields = {control.field for control in spec.pages[0].controls if control.field}
        assert fields == {"codice"}
    finally:
        wizard.close()


def test_main_window_opens_designer_and_runtime_in_mdi(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("forms", "form_clienti")
        qapp.processEvents()
        sub = window.editors.find("forms:form_clienti")
        assert sub is not None
        designer = sub.widget()
        assert isinstance(designer, FormDesignerWidget)
        assert window.mode_label.text().endswith("Design")

        window.run_object("forms", "form_clienti")
        qapp.processEvents()
        runtime_sub = window.editors.find("preview:forms:form_clienti")
        assert runtime_sub is not None
        assert isinstance(runtime_sub.widget(), FormRuntime)
        assert window.mode_label.text().endswith("Esecuzione")

        designer.spec.caption = "Anteprima"
        designer.preview()
        qapp.processEvents()
        assert window.editors.find("preview:forms:form_clienti") is not None
        assert len(window.editors.windows()) == 2

        assert designer.save() is True
        qapp.processEvents()
    finally:
        window.close()


def test_object_name_used_by_inspector_combo(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _spec(demo_project))
    try:
        controls = designer.current_page().controls
        labels = [designer.object_combo.itemText(index) for index in range(designer.object_combo.count())]
        assert labels[0].startswith("form — ")
        assert object_name(controls[0], controls) in labels
    finally:
        designer.close()
