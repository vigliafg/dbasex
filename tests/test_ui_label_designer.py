"""Test UI di Label Designer, anteprima e integrazione desktop (0.8 O7)."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.core.label_model import LabelSpec


def _spec(project, name: str = "et_clienti") -> LabelSpec:
    table = project.require_table("clienti")
    spec = LabelSpec.create(name, table.name, [field.name for field in table.fields])
    spec.template = "[nome]\n[citta]"
    return spec


def test_designer_loads_source_and_inserts_fields(qapp, demo_project):
    from dbx.designers.label_builder import LabelDesignerWidget

    designer = LabelDesignerWidget(demo_project, _spec(demo_project))
    try:
        assert designer.fields_list.count() == len(
            demo_project.require_table("clienti").fields
        )
        assert designer.preset_combo.currentData() == "a4_70x37"
        designer.template_edit.setPlainText("")
        index = next(
            row
            for row in range(designer.fields_list.count())
            if designer.fields_list.item(row).data(Qt.ItemDataRole.UserRole) == "nome"
        )
        designer.fields_list.setCurrentRow(index)
        designer.insert_field()
        assert designer.template_edit.toPlainText() == "[nome]"
        assert designer.is_dirty() is True
    finally:
        designer.close()


def test_designer_applies_preset_and_counts_mail_merge(qapp, demo_project):
    from dbx.designers.label_builder import LabelDesignerWidget

    designer = LabelDesignerWidget(demo_project, _spec(demo_project))
    try:
        index = designer.preset_combo.findData("avery5160")
        designer.preset_combo.setCurrentIndex(index)
        designer._on_preset_chosen(index)
        assert designer.spec.page_size == "Letter"
        assert designer.spec.columns == 3
        assert designer.spec.rows == 10
        designer.width_spin.setValue(66.7)
        designer.filter_edit.setText("attivo = 1")
        designer.order_edit.setText("nome")
        designer._collect()
        assert "2 record" in designer.status_label.text()
        assert "etichette per foglio" in designer.status_label.text()
    finally:
        designer.close()


def test_designer_saves_label_and_preview_builds_pages(qapp, demo_project):
    from dbx.designers.label_builder import LabelDesignerWidget
    from dbx.ui.label_preview import LabelPreviewDialog

    designer = LabelDesignerWidget(demo_project, _spec(demo_project))
    try:
        assert designer.save() is True
        assert demo_project.names("labels") == ["et_clienti"]
        artifact = demo_project.artifact("labels", "et_clienti")
        assert artifact["template"] == "[nome]\n[citta]"
        assert designer.is_dirty() is False

        designer.template_edit.setPlainText("[nome]")
        assert designer.is_dirty() is True

        preview = LabelPreviewDialog(demo_project, "et_clienti")
        try:
            assert len(preview.pages) == 1
            text = " ".join(
                op.text for page in preview.pages for op in page.ops
            )
            assert "Alfa Srl" in text
            assert preview.windowTitle().startswith("Preview etichette")
            assert preview.info.text().endswith("1 pagina")
        finally:
            preview.close()
    finally:
        designer.close()


def test_new_label_dialog_for_table_and_query(qapp, demo_project):
    from dbx.designers.label_builder import NewLabelDialog

    dialog = NewLabelDialog(demo_project, suggested_name="et_dialog")
    try:
        dialog.title_edit.setText("Etichette dialog")
        spec = dialog.spec()
        assert spec.name == "et_dialog"
        assert spec.source_type == "table"
        assert spec.table == "clienti"
        assert spec.validate() == []
        query_index = next(
            (
                index
                for index in range(dialog.source_combo.count())
                if dialog.source_combo.itemData(index) == ("query", "clienti_attivi")
            ),
            -1,
        )
        assert query_index >= 0
        dialog.source_combo.setCurrentIndex(query_index)
        query_spec = dialog.spec()
        assert query_spec.source_type == "query"
        assert query_spec.query == "clienti_attivi"
        assert query_spec.validate() == []
    finally:
        dialog.close()


def test_main_window_opens_label_designer_and_preview(qapp, demo_project):
    from dbx.designers.label_builder import LabelDesignerWidget
    from dbx.ui.main_window import MainWindow

    demo_project.put_object("labels", _spec(demo_project).to_dict())
    demo_project.save()
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("labels", "et_clienti")
        qapp.processEvents()
        sub = window.editors.find("labels:et_clienti")
        assert sub is not None
        assert isinstance(sub.widget(), LabelDesignerWidget)
        assert window.mode_label.text().endswith("Etichette")

        window.run_object("labels", "et_clienti")
        qapp.processEvents()
        assert window.editors.find("preview:labels:et_clienti") is not None
    finally:
        window.close()


def test_label_folder_and_project_validation(qapp, demo_project):
    from dbx.designers.project_builder import validate_project

    spec = _spec(demo_project)
    demo_project.put_object("labels", spec.to_dict())
    demo_project.save()
    assert (
        demo_project.path / "objects" / "labels" / "et_clienti.label.json"
    ).exists()
    assert demo_project.names("labels") == ["et_clienti"]
    assert validate_project(demo_project) == []
    spec.table = "tabella_inesistente"
    demo_project.put_object("labels", spec.to_dict(), previous_name="et_clienti")
    errors = validate_project(demo_project)
    assert any("Etichetta" in error and "tabella inesistente" in error for error in errors)
