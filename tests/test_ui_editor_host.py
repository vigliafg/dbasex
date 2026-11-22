"""Test dell'host MDI e dell'adapter per i QDialog legacy."""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QLabel, QMdiArea, QVBoxLayout, QWidget

from dbx.ui.editor_host import DialogEditor, EditorHost, editor_dirty


class _Editor(QWidget):
    def __init__(self, title: str = "Editor") -> None:
        super().__init__()
        self.setWindowTitle(title)


class _DirtyEditor(_Editor):
    def is_dirty(self) -> bool:
        return True


def test_editor_dirty_detection(qapp) -> None:
    assert editor_dirty(_Editor()) is False
    assert editor_dirty(_DirtyEditor()) is True
    assert editor_dirty(None) is False


def test_editor_host_open_find_and_close(qapp) -> None:
    area = QMdiArea()
    area.show()
    host = EditorHost(area)
    first = _Editor("Primo")
    second = _Editor("Secondo")
    try:
        sub = host.open("a", "Primo", first)
        qapp.processEvents()
        assert host.find("a") is sub
        assert host.current() is sub
        assert sub.windowTitle() == "Primo"
        assert sub.widget() is first
        assert host.open("a", "Primo", second) is sub
        assert host.windows() == [sub]
        host.close(sub)
        qapp.processEvents()
        assert host.find("a") is None
        assert host.windows() == []
    finally:
        area.close()
        area.deleteLater()


def test_dialog_editor_embeds_and_closes(qapp) -> None:
    area = QMdiArea()
    area.show()
    host = EditorHost(area)
    dialog = QDialog()
    dialog.setWindowTitle("Legacy")
    QVBoxLayout(dialog).addWidget(QLabel("contenuto"))
    try:
        sub = host.open_dialog("legacy", dialog)
        qapp.processEvents()
        page = sub.widget()
        assert isinstance(page, DialogEditor)
        assert page.dialog is dialog
        assert page.windowTitle() == "Legacy"
        assert dialog.isVisible()
        dialog.accept()
        qapp.processEvents()
        assert host.find("legacy") is None
    finally:
        area.close()
        area.deleteLater()
