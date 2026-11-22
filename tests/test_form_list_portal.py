"""Test della vista Lista del form e del portale ordinato/filtrato (0.8 O9)."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.core.form_model import FormControl, FormSpec


def _clienti_spec(project) -> FormSpec:
    spec = FormSpec.from_dict(project.artifact("forms", "form_clienti"))
    spec.view_mode = "list"
    spec.list_fields = "codice,nome,citta"
    return spec


def _fatture_spec(project) -> FormSpec:
    return FormSpec.from_dict(project.artifact("forms", "form_fatture"))


def _grid(spec: FormSpec) -> FormControl:
    return next(control for control in spec.all_controls() if control.kind == "grid")


def test_form_spec_round_trip_list_and_portal():
    spec = FormSpec(name="f", table="clienti", view_mode="list")
    spec.list_fields = "codice, nome"
    grid = FormControl(
        id="g",
        kind="grid",
        table="fatture",
        link_parent="codice",
        link_child="cliente",
        order="importo desc",
        filter="[importo] >= 500",
    )
    spec.pages[0].controls.append(grid)
    clone = FormSpec.from_dict(spec.to_dict())
    assert clone.view_mode == "list"
    assert clone.list_fields == "codice, nome"
    clone_grid = clone.pages[0].controls[0]
    assert clone_grid.order == "importo desc"
    assert clone_grid.filter == "[importo] >= 500"
    assert clone.to_dict() == spec.to_dict()


def test_form_validation_rejects_unknown_view():
    spec = FormSpec(name="f", table="clienti", view_mode="gallery")
    assert any("Vista del form" in error for error in spec.validate())
    spec.view_mode = "form"
    assert spec.validate() == []


def test_runtime_starts_in_list_and_navigates(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    runtime = FormRuntime(demo_project, _clienti_spec(demo_project))
    try:
        assert runtime.is_list_view() is True
        assert runtime._list.rowCount() == 3
        assert runtime._list.columnCount() == 3
        headers = [
            runtime._list.horizontalHeaderItem(column).text()
            for column in range(3)
        ]
        assert headers == ["Codice", "Nome", "Città"]
        assert runtime._list.currentRow() == 0
        runtime._list.selectRow(2)
        assert runtime.rowset.index == 2
        assert runtime.rowset.current["codice"] == "C003"
        assert "Record 3 di 3" in runtime._status.text()

        runtime.toggle_view()
        assert runtime.is_list_view() is False
        runtime.toggle_view()
        assert runtime.is_list_view() is True
    finally:
        runtime.deleteLater()


def test_list_uses_default_fields_when_not_configured(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    spec = FormSpec.from_dict(demo_project.artifact("forms", "form_clienti"))
    spec.view_mode = "list"
    runtime = FormRuntime(demo_project, spec)
    try:
        assert runtime._list.columnCount() == len(runtime.table.fields)
        assert runtime._list.columnCount() > 3
    finally:
        runtime.deleteLater()


def test_list_refreshes_after_save_and_delete(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    spec = _clienti_spec(demo_project)
    runtime = FormRuntime(demo_project, spec)
    try:
        assert runtime._list.rowCount() == 3
        assert runtime.perform("new") is None
        assert runtime.is_list_view() is False
        binding = next(b for b in runtime.binders if b.control.field == "codice")
        binding.widget.setText("C004")
        name = next(b for b in runtime.binders if b.control.field == "nome")
        name.widget.setText("Delta Srl")
        assert runtime.save() is True
        assert runtime._list.rowCount() == 4
        assert runtime.rowset.current["codice"] == "C004"
        assert runtime.is_list_view() is False

        runtime._set_view("list")
        runtime.rowset.goto(3)
        runtime.load_current()
        assert runtime._list.currentRow() == 3
    finally:
        runtime.deleteLater()


def test_query_form_list_is_read_only(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    spec = FormSpec.from_dict(demo_project.artifact("forms", "form_clienti_attivi"))
    spec.view_mode = "list"
    runtime = FormRuntime(demo_project, spec)
    try:
        assert runtime.read_only is True
        assert runtime.is_list_view() is True
        assert runtime._list.rowCount() == 2
        runtime.perform("new")
        assert "sola lettura" in runtime._status.text()
    finally:
        runtime.deleteLater()


def test_portal_applies_order_and_filter(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    spec = _fatture_spec(demo_project)
    grid = _grid(spec)
    grid.order = "importo desc"
    grid.filter = "[importo] >= 200"
    runtime = FormRuntime(demo_project, spec)
    try:
        runtime.rowset.goto(1)
        runtime.load_current()
        table = runtime.grids[0][0]
        assert runtime.rowset.current["codice"] == "C002"
        assert table.rowCount() == 2
        assert table.item(0, 4).text() == "3200"
        assert table.item(1, 4).text() == "250.5"
    finally:
        runtime.deleteLater()


def test_portal_invalid_filter_is_reported(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    spec = _fatture_spec(demo_project)
    grid = _grid(spec)
    grid.filter = "[importo] >"
    runtime = FormRuntime(demo_project, spec)
    try:
        assert runtime.grids[0][0].rowCount() == 0
        assert "non valido" in runtime._status.text()
        assert any("filtro portale" in line for line in runtime.event_log)
    finally:
        runtime.deleteLater()


def test_portal_without_filter_lists_all_related_rows(qapp, demo_project):
    from dbx.runtime.form_runtime import FormRuntime

    runtime = FormRuntime(demo_project, _fatture_spec(demo_project))
    try:
        assert runtime.rowset.current["codice"] == "C001"
        assert runtime.grids[0][0].rowCount() == 2
        assert not (
            runtime.grids[0][0].item(0, 0).flags()
            & Qt.ItemFlag.ItemIsEditable
        )
    finally:
        runtime.deleteLater()
