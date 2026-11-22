"""Test UI della ricerca guidata e del dialogo di sostituzione (0.6)."""

from __future__ import annotations

from dbx.core.search import SearchCriterion, SearchRequest


def test_find_dialog_round_trip(qapp, demo_project):
    from dbx.ui.find_dialog import FindDialog

    table = demo_project.require_table("clienti")
    request = SearchRequest(
        [
            SearchCriterion("citta", "contains", "Roma"),
            SearchCriterion("attivo", "eq", "1", omit=True),
        ],
        match="any",
    )
    dialog = FindDialog(demo_project, table, request)
    assert dialog.grid.rowCount() == 2
    restored = dialog.request()
    assert restored.match == "any"
    assert restored.criteria[0].field == "citta"
    assert restored.criteria[0].value == "Roma"
    assert restored.criteria[1].omit is True
    dialog.close()


def test_find_dialog_add_and_remove(qapp, demo_project):
    from dbx.ui.find_dialog import FindDialog

    table = demo_project.require_table("clienti")
    dialog = FindDialog(demo_project, table)
    assert dialog.grid.rowCount() == 1
    dialog.add_criterion()
    assert dialog.grid.rowCount() == 2
    dialog.grid.setCurrentCell(0, 0)
    dialog.remove_criterion()
    assert dialog.grid.rowCount() == 1
    dialog.close()


def test_data_view_applies_search(qapp, demo_project):
    from dbx.ui.data_view import DataView

    view = DataView(demo_project, "clienti")
    total = len(view.rowset)
    view._search = SearchRequest([SearchCriterion("citta", "contains", "Roma")])
    view.refresh()
    assert len(view.rowset) <= total
    assert all("roma" in str(row.get("citta", "")).lower() for row in view.rowset.rows())
    assert "ricerca:" in view.status.text()
    view.clear_find()
    assert len(view.rowset) == total
    view.deleteLater()


def test_replace_dialog_values(qapp, demo_project):
    from dbx.ui.find_dialog import ReplaceDialog

    table = demo_project.require_table("clienti")
    dialog = ReplaceDialog(table)
    dialog.find_edit.setText("Roma")
    dialog.replace_edit.setText("Milano")
    dialog.case_box.setChecked(True)
    values = dialog.values()
    assert values["find"] == "Roma"
    assert values["replace"] == "Milano"
    assert values["match_case"] is True
    assert values["field"] == ""
    dialog.close()
