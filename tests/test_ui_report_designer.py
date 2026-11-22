"""Test del Report Designer a bande impilate e delle sue finestre (O5)."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest

from dbx.designers.report_builder import (
    EditTextDialog,
    GroupDialog,
    InsertFieldDialog,
    ReportBuilderDialog,
    ReportDesignerWidget,
    SortOrderDialog,
    TotalDialog,
)
from dbx.runtime.report_engine import (
    BAND_NAMES,
    Control,
    ReportSpec,
    field_display_name,
    render_report,
)
from dbx.ui.main_window import MainWindow
from dbx.ui.report_preview import ReportPreviewDialog
import dbx.ui.report_preview as report_preview


def _spec(demo_project) -> ReportSpec:
    artifact = demo_project.artifact("reports", "fatture_per_cliente")
    assert artifact is not None
    return ReportSpec.from_dict(artifact)


def test_designer_shows_all_stacked_bands(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        tops = designer.canvas.band_tops()
        assert [name for name, _top, _height in tops] == list(BAND_NAMES)
        assert tops[0][1] < tops[1][1] < tops[-1][1]
        assert designer.status_label.text().startswith("L:")
        assert designer.inspector.item("page_size") is not None
        assert designer.save_button is not None
        assert designer.preview_button is not None
        assert designer.font_spin.value() >= 4
    finally:
        designer.close()


def test_band_visibility_toggle(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.set_band_visible("page_footer", False)
        names = [name for name, _top, _height in designer.canvas.band_tops()]
        assert "page_footer" not in names
        assert designer.spec.band_visible["page_footer"] is False
        designer.show_all_bands()
        assert "page_footer" in [name for name, _top, _height in designer.canvas.band_tops()]
    finally:
        designer.close()


def test_band_divider_drag_sets_height(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        title = designer.canvas.band_tops()[0]
        _name, top, _height = title
        start = QPoint(10, int(top + 2))
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(designer.canvas, QPoint(10, int(top + 62)))
        QTest.mouseRelease(
            designer.canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(10, int(top + 62)),
        )
        assert designer.spec.band_heights.get("title", 0) >= 10
        assert designer.is_dirty() is True
    finally:
        designer.close()


def test_control_drag_and_resize(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.show()
        qapp.processEvents()
        band = next(name for name in BAND_NAMES if designer.spec.band(name))
        control = designer.spec.band(band)[0]
        rect = designer.canvas.control_rect(band, control)
        start = QPoint(int(rect.left()) + 8, int(rect.top()) + 4)
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
        QTest.mouseMove(designer.canvas, start + QPoint(30, 18))
        QTest.mouseRelease(
            designer.canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            start + QPoint(30, 18),
        )
        assert control.x >= 8
        assert control.y > 0
        designer.canvas.selected = control.id
        designer.selected_id = control.id
        rect = designer.canvas.control_rect(band, control)
        handle = QPoint(int(rect.right()), int(rect.bottom()))
        before = (control.w, control.h)
        QTest.mousePress(designer.canvas, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, handle)
        QTest.mouseMove(designer.canvas, handle + QPoint(30, 15))
        QTest.mouseRelease(
            designer.canvas,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            handle + QPoint(30, 15),
        )
        assert (control.w, control.h) != before
        assert control.w > before[0] and control.h > before[1]
    finally:
        designer.close()


def test_zoom_range_and_status(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        base_width = designer.canvas.width()
        designer.zoom_combo.setCurrentIndex(4)  # 200%
        assert designer.canvas.zoom_factor == 2.0
        assert designer.canvas.width() > base_width
        designer.zoom_combo.setCurrentIndex(0)  # 50%
        assert designer.canvas.zoom_factor == 0.5
        assert "Zoom 50%" in designer.status_label.text()
    finally:
        designer.close()


def test_inspector_edits_control_geometry(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        band = next(name for name in BAND_NAMES if designer.spec.band(name))
        control = designer.spec.band(band)[0]
        designer.canvas.selected = control.id
        designer.canvas.selection_changed.emit(control.id)
        assert "L:" in designer.status_label.text()
        item = designer.inspector.item("x")
        assert item is not None
        item.setText(1, "25")
        assert abs(control.x - 25) < 0.01
        width = designer.inspector.item("w")
        assert width is not None
        width.setText(1, "70")
        assert abs(control.w - 70) < 0.01
    finally:
        designer.close()


def test_formatting_toolbar_applies_to_selection(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        band = next(name for name in BAND_NAMES if designer.spec.band(name))
        control = designer.spec.band(band)[0]
        control.bold = False
        control.italic = False
        control.underline = False
        control.border = False
        control.align = "left"
        designer.canvas.selected = control.id
        designer.canvas.selection_changed.emit(control.id)
        designer.bold_button.click()
        assert control.bold is True
        designer.italic_button.click()
        assert control.italic is True
        designer.underline_button.click()
        assert control.underline is True
        designer.align_buttons["right"].click()
        assert control.align == "right"
        designer.font_spin.setValue(14)
        assert control.font_size == 14
        designer.font_combo.setCurrentIndex(designer.font_combo.findData("Courier New"))
        assert control.font_name == "Courier New"
        designer.border_button.click()
        assert control.border is True
    finally:
        designer.close()


def test_align_control_in_band(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        band = next(name for name in BAND_NAMES if designer.spec.band(name))
        control = designer.spec.band(band)[0]
        designer.canvas.selected = control.id
        designer.canvas.selection_changed.emit(control.id)
        content_width = (
            designer.spec.page_dimensions()[0]
            - designer.spec.margins["left"]
            - designer.spec.margins["right"]
        )
        designer.align_control("right")
        assert abs(control.x - (content_width - control.w)) < 0.01
        designer.align_control("left")
        assert control.x == 0.0
        designer.align_control("center")
        assert abs(control.x - (content_width - control.w) / 2) < 0.01
    finally:
        designer.close()


def test_insert_group_adds_header_field(qapp, demo_project, monkeypatch) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        monkeypatch.setattr(GroupDialog, "exec", lambda self: GroupDialog.DialogCode.Accepted)
        monkeypatch.setattr(
            GroupDialog,
            "group",
            lambda self: {"field": "cliente", "label": "Cliente"},
        )
        designer.insert_group()
        assert designer.spec.groups[-1]["field"] == "cliente"
        assert any(control.expr == "cliente" for control in designer.spec.band("group_header"))
        assert designer.spec.is_visible("group_header") is True
    finally:
        designer.close()


def test_insert_field_dialog_and_insertion(qapp, demo_project, monkeypatch) -> None:
    dialog = InsertFieldDialog(demo_project, "fatture")
    try:
        texts = [dialog.list.item(i).text() for i in range(dialog.list.count())]
        assert field_display_name("fatture", "cliente") in texts
        dialog.list.setCurrentRow(1)
        assert dialog.selected_field()
    finally:
        dialog.close()

    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        monkeypatch.setattr(InsertFieldDialog, "exec", lambda self: InsertFieldDialog.DialogCode.Accepted)
        monkeypatch.setattr(InsertFieldDialog, "selected_field", lambda self: "cliente")
        before = len(designer.spec.band(designer.active_band))
        designer.insert_field()
        assert len(designer.spec.band(designer.active_band)) == before + 1
        control = designer.spec.band(designer.active_band)[-1]
        assert control.kind == "field"
        assert control.expr == "cliente"
        assert designer.canvas.selected == control.id
    finally:
        designer.close()


def test_sort_order_dialog_roundtrip(qapp, demo_project) -> None:
    dialog = SortOrderDialog(demo_project, "fatture", [])
    try:
        dialog.available.setCurrentRow(0)
        dialog.add_selected()
        assert len(dialog.sort_fields()) == 1
        dialog.direction.setCurrentIndex(dialog.direction.findData("desc"))
        dialog.sorted.setCurrentRow(0)
        dialog.direction.setCurrentIndex(dialog.direction.findData("desc"))
        entries = dialog.sort_fields()
        assert entries[0]["direction"] in ("asc", "desc")
        dialog.remove_selected()
        assert dialog.sort_fields() == []
    finally:
        dialog.close()

    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.spec.sort_fields = [{"field": "importo", "direction": "desc"}]
        designer._show_report_properties()
        item = designer.inspector.item("sort_fields")
        assert item is not None
        assert "importo desc" in item.text(1)
    finally:
        designer.close()


def test_sort_order_changes_preview_order(qapp, demo_project) -> None:
    spec = ReportSpec(name="ordine", table="fatture")
    spec.bands["detail"] = [Control("c", "field", x=0, y=0, w=60, h=6, expr="cliente")]
    spec.sort_fields = [{"field": "cliente", "direction": "desc"}]
    rows = [{"cliente": "Alfa"}, {"cliente": "Zeta"}]
    pages = render_report(spec, rows)
    assert [op.text for op in pages[0].ops if op.text in ("Alfa", "Zeta")] == ["Zeta", "Alfa"]


def test_total_and_group_dialogs(qapp, demo_project) -> None:
    total = TotalDialog(demo_project, "fatture")
    try:
        band, control = total.control()
        assert band == "summary"
        assert control.kind == "total"
        assert control.func == "sum"
    finally:
        total.close()

    group = GroupDialog(demo_project, "fatture")
    try:
        group.label_edit.setText("Cliente")
        data = group.group()
        assert data["field"]
        assert data["label"] == "Cliente"
    finally:
        group.close()


def test_edit_text_dialog_applies(qapp) -> None:
    control = Control("t", "text", text="Prima", font_size=9)
    dialog = EditTextDialog(control)
    try:
        dialog.text_edit.setPlainText("Dopo")
        dialog.size_spin.setValue(15)
        dialog.align_combo.setCurrentIndex(dialog.align_combo.findData("center"))
        dialog.apply_to(control)
        assert control.text == "Dopo"
        assert control.font_size == 15
        assert control.align == "center"
    finally:
        dialog.close()


def test_save_roundtrip_with_sort_and_bands(qapp, demo_project) -> None:
    designer = ReportDesignerWidget(demo_project, _spec(demo_project))
    try:
        designer.spec.sort_fields = [{"field": "importo", "direction": "desc"}]
        designer.spec.band_heights = {"detail": 8.5}
        designer.spec.band_visible = {"title": False}
        assert designer.is_dirty() is True
        assert designer.save() is True
        assert designer.is_dirty() is False
        artifact = demo_project.artifact("reports", designer.spec.name)
        assert artifact is not None
        assert artifact["sort_fields"] == [{"field": "importo", "direction": "desc"}]
        assert artifact["band_heights"]["detail"] == 8.5
        assert artifact["band_visible"]["title"] is False
        reopened = ReportDesignerWidget(demo_project, ReportSpec.from_dict(artifact))
        try:
            assert reopened.spec.sort_fields == designer.spec.sort_fields
            assert reopened.spec.band_heights["detail"] == 8.5
        finally:
            reopened.close()
    finally:
        designer.close()


def test_preview_toolbar_single_page_and_zoom(qapp, demo_project) -> None:
    report_preview._SESSION_ZOOM = None
    preview = ReportPreviewDialog(demo_project, _spec(demo_project))
    try:
        assert preview.total_label.text().startswith("Totale:")
        assert preview.first_button is not None
        assert preview.last_button is not None
        preview.single_button.click()
        assert preview.single_button.isChecked()
        visible = [label for label in preview.page_labels if label.isVisible()]
        assert len(visible) <= 1
        preview.set_zoom(2.0)
        assert f"{int(round(2.0 / preview.baseline * 100))}%" in preview.zoom_label.text()
        preview.accept()
    finally:
        preview.close()
    second = ReportPreviewDialog(demo_project, _spec(demo_project))
    try:
        assert second.zoom == 2.0
    finally:
        second.close()
        report_preview._SESSION_ZOOM = None


def test_main_window_opens_report_designer_and_preview_in_mdi(qapp, demo_project) -> None:
    report_preview._SESSION_ZOOM = None
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("reports", "fatture_per_cliente")
        qapp.processEvents()
        sub = window.editors.find("reports:fatture_per_cliente")
        assert sub is not None
        designer = sub.widget()
        assert isinstance(designer, ReportDesignerWidget)
        assert window.mode_label.text().endswith("Design")

        window.run_object("reports", "fatture_per_cliente")
        qapp.processEvents()
        assert window.editors.find("preview:reports:fatture_per_cliente") is not None

        designer.preview()
        qapp.processEvents()
        assert window.editors.find("preview:reports:fatture_per_cliente") is not None
        assert len(window.editors.windows()) == 2
        assert designer.save() is True
        qapp.processEvents()
    finally:
        window.close()
        report_preview._SESSION_ZOOM = None


def test_alias_keeps_legacy_name(qapp, demo_project) -> None:
    assert ReportBuilderDialog is ReportDesignerWidget
    legacy = ReportBuilderDialog(demo_project, _spec(demo_project))
    try:
        assert legacy.canvas.spec is not None
        assert legacy.spec.table == "fatture"
    finally:
        legacy.close()


def test_new_report_object_opens_designer(qapp, demo_project, monkeypatch) -> None:
    from PyQt6.QtWidgets import QInputDialog

    monkeypatch.setattr(
        QInputDialog,
        "getItem",
        staticmethod(lambda *args, **kwargs: ("fatture", True)),
    )
    window = MainWindow(demo_project)
    try:
        window.show()
        window.new_object("reports")
        qapp.processEvents()
        keys = [str(sub.property("dbx_key")) for sub in window.editors.windows()]
        assert any(key.startswith("reports:new:") for key in keys)
        designer = window.editors.current_editor()
        assert isinstance(designer, ReportDesignerWidget)
        assert designer.spec.table == "fatture"
        assert designer.save() is True
        qapp.processEvents()
        artifact = demo_project.artifact("reports", designer.spec.name)
        assert artifact is not None
    finally:
        window.close()
