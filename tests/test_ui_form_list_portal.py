"""Test UI delle proprietà Lista e portale nel Form Designer (0.8 O9)."""

from __future__ import annotations

from dbx.core.form_model import FormSpec


def _spec(project, name: str) -> FormSpec:
    return FormSpec.from_dict(project.artifact("forms", name))


def test_form_designer_edits_list_view_properties(qapp, demo_project) -> None:
    from dbx.designers.form_builder import FormDesignerWidget

    designer = FormDesignerWidget(demo_project, _spec(demo_project, "form_clienti"))
    try:
        designer._select([])
        assert designer.inspector.item("view_mode") is not None
        assert designer.inspector.item("list_fields") is not None
        designer._on_property_changed("view_mode", "list")
        designer._on_property_changed("list_fields", "codice,nome,citta")
        assert designer.spec.view_mode == "list"
        assert designer.spec.list_fields == "codice,nome,citta"
        assert designer.is_dirty() is True
    finally:
        designer.close()


def test_form_designer_edits_portal_order_and_filter(qapp, demo_project) -> None:
    from dbx.designers.form_builder import FormDesignerWidget

    spec = _spec(demo_project, "form_fatture")
    grid = next(control for control in spec.all_controls() if control.kind == "grid")
    designer = FormDesignerWidget(demo_project, spec)
    try:
        designer._select([grid.id])
        assert designer.inspector.item("order") is not None
        assert designer.inspector.item("filter") is not None
        designer._on_property_changed("order", "importo desc")
        designer._on_property_changed("filter", "[importo] >= 500")
        assert grid.order == "importo desc"
        assert grid.filter == "[importo] >= 500"
    finally:
        designer.close()


def test_list_and_portal_properties_survive_save(qapp, demo_project) -> None:
    from dbx.designers.form_builder import FormDesignerWidget

    spec = _spec(demo_project, "form_fatture")
    grid = next(control for control in spec.all_controls() if control.kind == "grid")
    grid.order = "importo desc"
    grid.filter = "[importo] >= 500"
    spec.view_mode = "list"
    spec.list_fields = "codice,nome"
    designer = FormDesignerWidget(demo_project, spec)
    try:
        assert designer.save() is True
        artifact = demo_project.artifact("forms", "form_fatture")
        assert artifact["view_mode"] == "list"
        assert artifact["list_fields"] == "codice,nome"
        saved_grid = next(
            control
            for control in FormSpec.from_dict(artifact).all_controls()
            if control.kind == "grid"
        )
        assert saved_grid.order == "importo desc"
        assert saved_grid.filter == "[importo] >= 500"
    finally:
        designer.close()
