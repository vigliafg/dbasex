"""Test del Navigator."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.ui.navigator import NAV_CATEGORIES, Navigator


def _rows(navigator: Navigator) -> list[str]:
    return [
        str(navigator.list.item(row).data(Qt.ItemDataRole.UserRole))
        for row in range(navigator.list.count())
    ]


def test_navigator_categories_and_list(qapp, demo_project) -> None:
    navigator = Navigator()
    navigator.set_project(demo_project)
    try:
        assert set(navigator._buttons) == {key for key, *_ in NAV_CATEGORIES}
        assert navigator.filter_combo.count() == 9
        assert navigator.directory_edit.text() == str(demo_project.path)
        assert navigator.list.count() > 0
        rows = _rows(navigator)
        assert any(value.startswith("new:") for value in rows)
        assert any(value.startswith("tables:") for value in rows)
        assert any(value.startswith("queries:") for value in rows)
        assert navigator.list_header.text().startswith("Oggetti del progetto")
        assert "[Untitled]" in [
            navigator.list.item(row).text() for row in range(navigator.list.count())
        ]
    finally:
        navigator.deleteLater()


def test_navigator_unavailable_categories_are_visible_but_disabled(qapp) -> None:
    navigator = Navigator()
    try:
        for key in ("images", "sounds", "catalogs", "custom"):
            assert key in navigator._buttons
            assert not navigator._buttons[key].isEnabled()
            assert "non disponibile" in navigator._buttons[key].toolTip()
        for key in ("all", "tables", "diagrams", "queries", "forms", "reports", "labels", "scripts", "menus"):
            assert navigator._buttons[key].isEnabled()
    finally:
        navigator.deleteLater()


def test_navigator_filter(qapp, demo_project) -> None:
    navigator = Navigator()
    navigator.set_project(demo_project)
    try:
        navigator.set_category("tables")
        assert navigator.category == "tables"
        rows = _rows(navigator)
        assert all(
            not value.startswith(("diagrams:", "queries:", "forms:", "reports:", "scripts:", "menus:"))
            for value in rows
        )
        assert any(value.startswith("tables:") for value in rows)
        assert navigator.list_header.text().startswith("Tabelle (")
    finally:
        navigator.deleteLater()


def test_navigator_rejects_unavailable_category(qapp, demo_project) -> None:
    navigator = Navigator()
    navigator.set_project(demo_project)
    try:
        navigator.set_category("images")
        assert navigator.category == "all"
    finally:
        navigator.deleteLater()


def test_navigator_without_project(qapp) -> None:
    navigator = Navigator()
    try:
        navigator.set_project(None)
        assert navigator.list.count() == 0
        assert "Nessun progetto" in navigator.hint.text()
    finally:
        navigator.deleteLater()
