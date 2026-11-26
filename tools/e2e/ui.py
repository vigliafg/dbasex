"""Helper Qt per simulare l'interazione dell'utente."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QComboBox, QLineEdit, QTableWidget, QWidget


def click(button: QWidget) -> None:
    button.click()


def type_text(line: QLineEdit, text: str) -> None:
    line.setText(text)


def select_data(combo: QComboBox, data: Any) -> bool:
    index = combo.findData(data)
    if index < 0:
        return False
    combo.setCurrentIndex(index)
    return True


def select_text(combo: QComboBox, text: str) -> bool:
    index = combo.findText(text)
    if index < 0:
        return False
    combo.setCurrentIndex(index)
    return True


def set_cell(grid: QTableWidget, row: int, column: int, text: str) -> None:
    item = grid.item(row, column)
    if item is None:
        from PyQt6.QtWidgets import QTableWidgetItem

        item = QTableWidgetItem("")
        grid.setItem(row, column, item)
    item.setText(str(text))


def press(widget: QWidget, key: Qt.Key, modifier: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> None:
    QTest.keyClick(widget, key, modifier)


def drag(widget: QWidget, start: QPoint, end: QPoint, steps: int = 4) -> None:
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, pos=start)
    for index in range(1, steps + 1):
        point = QPoint(
            start.x() + (end.x() - start.x()) * index // steps,
            start.y() + (end.y() - start.y()) * index // steps,
        )
        QTest.mouseMove(widget, point)
    QTest.mouseRelease(widget, Qt.MouseButton.LeftButton, pos=end)


def find_action(window: Any, text: str):
    from PyQt6.QtGui import QAction

    for action in window.findChildren(QAction):
        if action.text().replace("&", "").startswith(text):
            return action
    return None
