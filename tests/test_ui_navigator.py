"""Test del Navigator."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from dbx.ui.navigator import Navigator


def test_navigator_categories_and_list(qapp, demo_project) -> None:
    navigator = Navigator()
    navigator.set_project(demo_project)
    try:
        assert set(navigator._buttons) == {"all", "tables", "forms", "reports", "scripts", "menus"}
        assert navigator.filter_combo.count() == 5
        assert navigator.directory_edit.text() == str(demo_project.path)
        assert navigator.list.count() > 0
        data = [
            navigator.list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(navigator.list.count())
        ]
        assert any(isinstance(value, str) and value.startswith("new:") for value in data)
        assert any(isinstance(value, str) and value.startswith("tables:") for value in data)
    finally:
        navigator.deleteLater()


def test_navigator_filter(qapp, demo_project) -> None:
    navigator = Navigator()
    navigator.set_project(demo_project)
    try:
        navigator.set_category("tables")
        assert navigator.category == "tables"
        rows = [
            navigator.list.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(navigator.list.count())
        ]
        assert all(not str(value).startswith(("forms:", "reports:", "scripts:", "menus:")) for value in rows)
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
