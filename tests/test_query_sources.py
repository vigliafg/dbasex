"""Test di form e report alimentati da query."""

from __future__ import annotations

from PyQt6.QtWidgets import QPushButton

from dbx.core.form_model import FormPage, FormSpec
from dbx.core.query_engine import query_table
from dbx.designers.form_builder import FormDesignerWidget
from dbx.designers.form_expert import FormExpert
from dbx.designers.project_builder import validate_project
from dbx.designers.report_builder import NewReportDialog, ReportDesignerWidget
from dbx.runtime.form_runtime import FormRuntime
from dbx.runtime.report_engine import Control, ReportSpec
from dbx.ui.report_preview import build_pages


def _query_form(demo_project) -> FormSpec:
    artifact = demo_project.artifact("forms", "form_clienti_attivi")
    assert artifact is not None
    return FormSpec.from_dict(artifact)


def test_form_spec_query_validation() -> None:
    spec = FormSpec(
        name="form_query",
        source_type="query",
        query="clienti_attivi",
        table="",
        pages=[FormPage()],
    )
    assert spec.validate() == []
    spec.query = ""
    assert any("query" in error for error in spec.validate())
    spec.source_type = "table"
    assert any("tabella" in error for error in spec.validate())


def test_query_form_runtime_is_read_only(qapp, demo_project) -> None:
    runtime = FormRuntime(demo_project, _query_form(demo_project))
    try:
        assert runtime.read_only is True
        assert runtime.table.name == "clienti_attivi"
        assert runtime.rowset.count() == 2
        assert runtime.rowset.current["codice"] == "C001"
        assert "sola lettura" in runtime._status.text()
        runtime.perform("next")
        assert runtime.rowset.current["nome"] == "Beta Studio"
        values = runtime.collect()
        assert values["codice"] == "C002"
        assert "rowid" not in values
        assert runtime.save() is False
        runtime.delete_current()
        assert "sola lettura" in runtime._status.text()
        assert runtime.rowset.count() == 2
        buttons = {
            item.widget().text(): item.widget()
            for index in range(runtime._toolbar.count())
            for item in [runtime._toolbar.itemAt(index)]
            if isinstance(item.widget(), QPushButton)
        }
        for caption in ("Nuovo", "Salva", "Elimina"):
            assert buttons[caption].isEnabled() is False
    finally:
        runtime.close()


def test_query_form_opens_in_designer(qapp, demo_project) -> None:
    designer = FormDesignerWidget(demo_project, _query_form(demo_project))
    try:
        assert designer.table is not None
        assert designer.table.name == "clienti_attivi"
        assert designer.palette.fields.count() == 5
        assert designer.spec.source_type == "query"
        assert "Query · clienti_attivi" in designer.inspector.item("source").text(1)
    finally:
        designer.close()


def test_form_expert_generates_query_form(qapp, demo_project) -> None:
    wizard = FormExpert(demo_project, suggested_name="form_da_query")
    try:
        wizard.initializePage(1)
        wizard.source_combo.setCurrentIndex(wizard.source_combo.findData("query"))
        wizard.query_combo.setCurrentIndex(wizard.query_combo.findData("clienti_attivi"))
        wizard.initializePage(2)
        assert wizard.destination_list.count() == 5
        spec = wizard.build_spec()
        assert spec.source_type == "query"
        assert spec.query == "clienti_attivi"
        assert spec.table == ""
        assert spec.validate() == []
        actions = [control.action for control in spec.pages[0].controls if control.kind == "button"]
        assert "save" not in actions
        assert "delete" not in actions
        assert "new" not in actions
        assert any(control.field == "nome" for control in spec.pages[0].controls)
    finally:
        wizard.close()


def test_report_from_query_spec_and_pages(qapp, demo_project) -> None:
    artifact = demo_project.artifact("reports", "fatture_clienti_report")
    assert artifact is not None
    spec = ReportSpec.from_dict(artifact)
    assert spec.source_type == "query"
    assert spec.query == "fatture_clienti"
    assert spec.validate() == []
    clone = ReportSpec.from_dict(spec.to_dict())
    assert clone.source_type == "query"
    assert clone.query == "fatture_clienti"

    pages = build_pages(demo_project, spec)
    texts = [op.text for page in pages for op in page.ops]
    assert any("Alfa Srl" in text for text in texts)
    assert any("3.200" in text for text in texts)
    assert any("5.900" in text for text in texts)


def test_report_query_filter_and_order(demo_project) -> None:
    table = query_table(demo_project, "fatture_clienti")
    spec = ReportSpec.create_for_query(
        "solo_grandi", "fatture_clienti", [field.name for field in table.fields]
    )
    spec.filter = "[importo] > 1000"
    spec.order = "importo desc"
    spec.bands["detail"] = [
        Control(id="importo", kind="field", x=0, y=0, w=40, h=6, expr="importo")
    ]
    pages = build_pages(demo_project, spec)
    texts = [op.text for page in pages for op in page.ops]
    assert any("3.200" in text for text in texts)
    assert any("1.200" in text for text in texts)
    assert not any("450" in text for text in texts)


def test_report_designer_with_query_source(qapp, demo_project) -> None:
    artifact = demo_project.artifact("reports", "fatture_clienti_report")
    assert artifact is not None
    designer = ReportDesignerWidget(demo_project, ReportSpec.from_dict(artifact))
    try:
        assert designer.spec.source_type == "query"
        assert designer._field_table().name == "fatture_clienti"
        assert designer.table_combo.currentData() == ("query", "fatture_clienti")
        designer.save()
        assert demo_project.artifact("reports", "fatture_clienti_report") is not None
    finally:
        designer.close()


def test_new_report_dialog_can_choose_query(qapp, demo_project) -> None:
    dialog = NewReportDialog(demo_project, suggested_name="report_query")
    try:
        dialog.name_edit.setText("report_query")
        index = next(
            i
            for i in range(dialog.source_combo.count())
            if dialog.source_combo.itemData(i) == ("query", "fatture_clienti")
        )
        dialog.source_combo.setCurrentIndex(index)
        spec = dialog.spec()
        assert spec.source_type == "query"
        assert spec.query == "fatture_clienti"
        assert spec.validate() == []
        assert spec.bands["detail"][0].expr == "numero"
    finally:
        dialog.close()


def test_project_validation_checks_query_sources(qapp, demo_project) -> None:
    demo_project.add_object(
        "forms",
        FormSpec(
            name="form_query_rotta",
            source_type="query",
            query="inesistente",
            table="",
            pages=[FormPage()],
        ).to_dict(),
    )
    spec = ReportSpec.create_for_query("report_query_rotto", "inesistente", ["campo"])
    demo_project.add_object("reports", spec.to_dict())
    errors = validate_project(demo_project)
    assert any("Form form_query_rotta: query inesistente" in error for error in errors)
    assert any("Report report_query_rotto: query inesistente" in error for error in errors)
