"""Test headless della vista QBE del Query Designer (0.4/O4)."""

from __future__ import annotations

from dbx.core.query_model import QueryFilter, QuerySpec
from dbx.designers.qbe_panel import QbePanel
from dbx.designers.query_builder import QueryDesignerWidget


def _designer(project, name: str = "fatture_clienti") -> QueryDesignerWidget:
    spec = QuerySpec.from_project(project, name)
    assert spec is not None
    return QueryDesignerWidget(project, spec)


def _panel(designer: QueryDesignerWidget) -> QbePanel:
    return designer.qbe_page


def test_qbe_is_a_view_of_the_same_spec(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        assert panel.spec is designer.spec
        assert {image.table.name for image in panel.images()} == {"fatture", "clienti"}
        fatture = panel.image("fatture")
        clienti = panel.image("clienti")
        assert fatture is not None and clienti is not None
        assert fatture.is_included("numero")
        assert not fatture.is_included("descrizione")
        assert clienti.is_included("nome")
        assert fatture.cell_text(0, "importo") == ""
        assert fatture._sorts[fatture.column("numero")].currentData() == "asc"
    finally:
        designer.close()


def test_qbe_mode_toggle(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        assert designer.tabs.currentWidget() is designer.fields_page
        assert designer.guided_mode_button.isChecked()
        designer.set_mode("qbe")
        assert designer.tabs.currentWidget() is designer.qbe_page
        assert designer.qbe_mode_button.isChecked()
        assert not designer.guided_mode_button.isChecked()
        designer.set_mode("guided")
        assert designer.tabs.currentWidget() is designer.fields_page
        assert designer.guided_mode_button.isChecked()
    finally:
        designer.close()


def test_qbe_or_rows_and_preview(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("clienti", "citta", 0, "Milano")
        panel.set_cell("clienti", "citta", 1, "Torino")
        warnings = panel.apply_and_notify()
        assert warnings == []
        groups = [(item.field, item.value, item.group) for item in designer.spec.filters]
        assert ("clienti.citta", "Milano", 0) in groups
        assert ("clienti.citta", "Torino", 1) in groups
        assert " OR " in designer.sql_edit.toPlainText()
        result = designer.run_preview()
        assert result is not None
        assert [row["numero"] for row in result.rows] == [1, 2, 3, 5]
        assert designer.is_dirty()
    finally:
        designer.close()


def test_qbe_between_and_like(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("fatture", "importo", 0, "500..1300")
        panel.apply_and_notify()
        between = next(item for item in designer.spec.filters if item.op == "between")
        assert (between.value, between.value2) == ("500", "1300")
        assert "BETWEEN ? AND ?" in designer.sql_edit.toPlainText()
        result = designer.run_preview()
        assert result is not None
        assert [row["numero"] for row in result.rows] == [1, 4]
    finally:
        designer.close()

    designer = _designer(demo_project, "clienti_attivi")
    try:
        panel = _panel(designer)
        panel.set_cell("clienti", "nome", 0, "Al*")
        panel.apply_and_notify()
        like = next(item for item in designer.spec.filters if item.op == "like")
        assert like.value == "Al*"
        assert designer.run_preview() is not None
    finally:
        designer.close()


def test_qbe_example_element_creates_ref(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("fatture", "cliente", 0, "_cli")
        panel.set_cell("clienti", "codice", 0, "_cli")
        panel.apply_and_notify()
        refs = [item for item in designer.spec.filters if item.op == "ref"]
        assert len(refs) == 1
        assert refs[0].field == "fatture.cliente"
        assert refs[0].value == "clienti.codice"
        result = designer.run_preview()
        assert result is not None
        assert len(result.rows) == 5

        designer._refresh_qbe()
        panel = _panel(designer)
        assert panel.cell_text("fatture", "cliente", 0) == "_rif1"
        assert panel.cell_text("clienti", "codice", 0) == "_rif1"
    finally:
        designer.close()


def test_qbe_invalid_cell_is_not_applied(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("fatture", "importo", 0, ">")
        warnings = panel.apply_and_notify()
        assert warnings and "valore mancante" in warnings[0]
        assert all(item.field != "fatture.importo" for item in designer.spec.filters)
        edit = panel.image("fatture")._edits[(0, panel.image("fatture").column("importo"))]
        assert edit.property("state") == "error"

        panel.set_cell("fatture", "importo", 0, ">1000")
        assert panel.apply_and_notify() == []
        assert any(
            item.field == "fatture.importo" and item.op == "gt"
            for item in designer.spec.filters
        )
    finally:
        designer.close()


def test_qbe_warns_about_or_on_left_join(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        designer.spec.joins[0].kind = "left"
        designer._refresh_qbe()
        panel = _panel(designer)
        panel.set_cell("clienti", "citta", 1, "Roma")
        warnings = panel.apply_and_notify()
        assert any("LEFT JOIN" in warning for warning in warnings)
        assert any(item.group == 1 for item in designer.spec.filters)
    finally:
        designer.close()


def test_qbe_include_and_sort(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        fatture = panel.image("fatture")
        assert fatture is not None
        fatture.set_included("pagata", False)
        fatture.set_sort("importo", "desc")
        panel.apply_and_notify()
        assert all(item.field != "pagata" for item in designer.spec.fields)
        assert designer.fields_table.rowCount() == 4
        assert any(
            item.field == "fatture.importo" and item.direction == "desc"
            for item in designer.spec.sorts
        )
        assert fatture._sorts[fatture.column("importo")].currentText().endswith("(2°)")
    finally:
        designer.close()


def test_guided_filters_show_group_and_sync_qbe(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        designer.add_filter("clienti.citta", "eq", "Roma", group=1)
        assert designer.filters_table.columnCount() == 4
        assert designer.filters_table.item(0, 3).text() == "1"
        assert _panel(designer).cell_text("clienti", "citta", 1) == "Roma"
    finally:
        designer.close()


def test_qbe_save_persists_groups_and_ranges(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("fatture", "importo", 0, "500..1300")
        panel.set_cell("clienti", "citta", 1, "Roma")
        panel.apply_and_notify()
        assert designer.save() is True
        artifact = demo_project.artifact("queries", "fatture_clienti")
        assert artifact is not None
        filters = artifact["filters"]
        assert any(
            item["op"] == "between" and item["value2"] == "1300" for item in filters
        )
        assert any(item["group"] == 1 for item in filters)
        loaded = QuerySpec.from_dict(artifact)
        assert loaded.validate(demo_project.tables()) == []
    finally:
        designer.close()


def test_qbe_single_example_element_is_ignored(qapp, demo_project) -> None:
    designer = _designer(demo_project)
    try:
        panel = _panel(designer)
        panel.set_cell("fatture", "cliente", 0, "_solo")
        warnings = panel.apply_and_notify()
        assert any("una sola volta" in warning for warning in warnings)
        assert all(item.op != "ref" for item in designer.spec.filters)
    finally:
        designer.close()
