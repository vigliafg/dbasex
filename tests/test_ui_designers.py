"""Test headless dei designer e delle viste principali."""

from __future__ import annotations

from dbx.core.form_model import FormSpec
from dbx.designers.form_builder import FormBuilderDialog
from dbx.designers.report_builder import ReportBuilderDialog
from dbx.designers.table_builder import TableBuilderDialog
from dbx.runtime.report_engine import BAND_NAMES, ReportSpec
from dbx.ui.command_window import CommandWindow
from dbx.ui.data_view import DataView
from dbx.ui.report_preview import ReportPreviewDialog
from dbx.ui.theme import apply_theme


def test_apply_theme(qapp) -> None:
    try:
        assert apply_theme(qapp, "dark") == "dark"
        assert apply_theme(qapp, "silver") == "silver"
    finally:
        apply_theme(qapp, "silver")


def test_table_builder(qapp, demo_project) -> None:
    table = demo_project.require_table("clienti")
    dialog = TableBuilderDialog(demo_project, table)
    try:
        assert dialog.fields_grid.rowCount() == len(table.fields)
        assert dialog.index_grid.rowCount() == len(table.indexes)
        assert dialog.relation_grid.rowCount() == len(table.foreign_keys)
        assert dialog.current_table().name == table.name
        assert dialog.ddl_view.toPlainText()
    finally:
        dialog.close()


def test_form_builder(qapp, demo_project) -> None:
    artifact = demo_project.artifact("forms", "form_clienti")
    assert artifact is not None
    dialog = FormBuilderDialog(demo_project, FormSpec.from_dict(artifact))
    try:
        assert dialog.canvas.page is not None
        assert dialog.canvas.page.controls
        assert dialog.object_combo.count() >= 2
        assert dialog.status_labels["Page"].text().endswith("1")
        assert dialog.inspector.tree.topLevelItemCount() >= 2
        combo_item = dialog.inspector.item("caption")
        assert combo_item is not None
    finally:
        dialog.close()


def test_report_builder(qapp, demo_project) -> None:
    artifact = demo_project.artifact("reports", "fatture_per_cliente")
    assert artifact is not None
    spec = ReportSpec.from_dict(artifact)
    dialog = ReportBuilderDialog(demo_project, spec)
    try:
        assert dialog.canvas.spec is spec
        bands = [name for name, _top, _height in dialog.canvas.band_tops()]
        assert bands == [name for name in spec.effective_band_order() if spec.is_visible(name)]
        assert set(bands) == set(BAND_NAMES)
        assert dialog.spec.table == "fatture"
        assert dialog.zoom_combo.count() == 5
        assert dialog.status_label.text().startswith("L:")
    finally:
        dialog.close()


def test_data_view(qapp, demo_project) -> None:
    view = DataView(demo_project, "clienti")
    try:
        assert view.rowset.count() == 3
        assert view.grid.rowCount() == 3
        assert view.grid.columnCount() == len(view.table.fields)
        assert view.status.text().startswith("Record 1 di 3")
        assert not view.grid.verticalHeader().isHidden()
    finally:
        view.deleteLater()


def test_command_window(qapp, demo_project) -> None:
    window = CommandWindow(demo_project)
    try:
        assert window.output.isReadOnly()
        window.input.setText("2 + 2")
        window.execute()
        assert "4" in window.output.toPlainText()
    finally:
        window.deleteLater()


def test_report_preview(qapp, demo_project) -> None:
    preview = ReportPreviewDialog(demo_project, "fatture_per_cliente")
    try:
        assert preview.pages
        assert "di" in preview.page_label.text()
        assert preview.info.text()
    finally:
        preview.close()
