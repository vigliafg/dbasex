"""Test headless del Report Expert (0.4/O2)."""

from __future__ import annotations

from dbx.designers.report_expert import ReportExpert
from dbx.ui.report_preview import build_pages


def _select_source(wizard: ReportExpert, kind: str, name: str) -> None:
    for index in range(wizard.source_combo.count()):
        if wizard.source_combo.itemData(index) == (kind, name):
            wizard.source_combo.setCurrentIndex(index)
            return
    raise AssertionError(f"sorgente {kind}/{name} non trovata")


def test_report_expert_tabular(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="report_clienti")
    try:
        spec = wizard.build_spec()
        assert spec.name == "report_clienti"
        assert spec.source_type == "table"
        assert spec.table == "clienti"
        assert spec.bands["detail"]
        assert spec.bands["page_header"]
        assert spec.validate() == []
        pages = build_pages(demo_project, spec)
        assert pages
    finally:
        wizard.close()


def test_report_expert_summary_without_group_stays_tabular(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="riepilogo")
    try:
        wizard.layout_radios["summary"].setChecked(True)
        spec = wizard.build_spec()
        assert spec.groups == []
        assert spec.is_visible("group_header") is False
        assert spec.validate() == []
    finally:
        wizard.close()


def test_report_expert_summary_with_group(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="riepilogo")
    try:
        wizard.layout_radios["summary"].setChecked(True)
        wizard.group_combo.setCurrentIndex(1)
        spec = wizard.build_spec()
        assert spec.groups
        assert spec.sort_fields[0]["field"] == spec.groups[0]["field"]
        assert spec.bands["group_header"]
        assert spec.bands["group_footer"]
        assert spec.validate() == []
        pages = build_pages(demo_project, spec)
        assert pages
    finally:
        wizard.close()


def test_report_expert_columnar(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="colonne")
    try:
        wizard.layout_radios["columnar"].setChecked(True)
        spec = wizard.build_spec()
        controls = spec.bands["detail"]
        assert len(controls) >= 4
        assert controls[0].y == 0
        assert controls[2].y > controls[0].y
        assert spec.band_heights["detail"] > 8
    finally:
        wizard.close()


def test_report_expert_query_source(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="report_query")
    try:
        _select_source(wizard, "query", "clienti_attivi")
        spec = wizard.build_spec()
        assert spec.source_type == "query"
        assert spec.query == "clienti_attivi"
        assert spec.table == ""
        assert spec.validate() == []
    finally:
        wizard.close()


def test_report_expert_landscape(qapp, demo_project) -> None:
    wizard = ReportExpert(demo_project, suggested_name="orizzontale")
    try:
        wizard.orientation_combo.setCurrentIndex(
            wizard.orientation_combo.findData("landscape")
        )
        spec = wizard.build_spec()
        assert spec.orientation == "landscape"
        assert spec.bands["title"][0].w > 200
    finally:
        wizard.close()
