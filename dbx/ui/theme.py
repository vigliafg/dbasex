"""Temi QSS di dBX (A2, H5)."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from . import icons

LIGHT = """
* { font-size: 13px; }
QMainWindow, QDialog { background: #f4f5f2; }
QWidget { color: #1e2320; }
QMenuBar { background: #eceee9; border-bottom: 1px solid #d3d7cf; }
QMenuBar::item:selected { background: #d9e3d4; }
QMenu { background: #fbfbf9; border: 1px solid #cbd1c6; }
QMenu::item:selected { background: #dcebdd; }
QToolBar { background: #eceee9; border: 0; spacing: 2px; padding: 4px; }
QToolButton { padding: 3px 7px; border-radius: 4px; }
QToolButton:hover { background: #dce3d7; }
QTabWidget::pane { border: 1px solid #cfd4ca; background: #fbfbf9; }
QTabBar::tab { padding: 6px 12px; background: #e6e9e2; border: 1px solid #cfd4ca; border-bottom: 0; }
QTabBar::tab:selected { background: #fbfbf9; }
QDockWidget { titlebar-close-icon: none; }
QDockWidget::title { background: #e6e9e2; padding: 6px; }
QTreeView, QTableView, QTableWidget, QListView, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #cfd4ca; border-radius: 4px; selection-background-color: #bcd8c0;
    selection-color: #10231a;
}
QHeaderView::section { background: #e9ece5; border: 0; border-right: 1px solid #d5d9cf; padding: 4px; }
QPushButton { background: #e8ebe3; border: 1px solid #c6ccbf; border-radius: 5px; padding: 5px 12px; }
QPushButton:hover { background: #dde3d6; }
QPushButton:default { background: #2f6f4f; color: #ffffff; border-color: #255a40; }
QPushButton:default:hover { background: #3a8260; }
QStatusBar { background: #eceee9; border-top: 1px solid #d3d7cf; }
QGroupBox { border: 1px solid #d3d7cf; border-radius: 6px; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QSplitter::handle { background: #dfe3da; }
QPushButton[palette="true"] { text-align: left; padding: 6px 10px; }
QGroupBox QPushButton[palette="true"] { border: 1px solid #d5dbd2; background: #f3f5f0; }
QPushButton[palette="true"]:hover { background: #e3ece1; }
"""

DARK = """
* { font-size: 13px; }
QMainWindow, QDialog { background: #22261f; }
QWidget { color: #e6e9e1; }
QMenuBar { background: #2a2f26; border-bottom: 1px solid #3a4033; }
QMenuBar::item:selected { background: #3c4a38; }
QMenu { background: #2a2f26; border: 1px solid #3a4033; }
QMenu::item:selected { background: #3c4a38; }
QToolBar { background: #2a2f26; border: 0; padding: 4px; }
QToolButton { padding: 3px 7px; border-radius: 4px; }
QToolButton:hover { background: #3a4033; }
QTabWidget::pane { border: 1px solid #3a4033; background: #272b23; }
QTabBar::tab { padding: 6px 12px; background: #2f342a; border: 1px solid #3a4033; border-bottom: 0; }
QTabBar::tab:selected { background: #272b23; }
QDockWidget::title { background: #2f342a; padding: 6px; }
QTreeView, QTableView, QTableWidget, QListView, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #1c201a; border: 1px solid #3a4033; border-radius: 4px; selection-background-color: #3f6b4d;
    selection-color: #ffffff;
}
QHeaderView::section { background: #2f342a; border: 0; border-right: 1px solid #3a4033; padding: 4px; }
QPushButton { background: #30362b; border: 1px solid #444b3c; border-radius: 5px; padding: 5px 12px; }
QPushButton:hover { background: #3a4133; }
QPushButton:default { background: #3f8a60; color: #ffffff; border-color: #356f4e; }
QStatusBar { background: #2a2f26; border-top: 1px solid #3a4033; }
QGroupBox { border: 1px solid #3a4033; border-radius: 6px; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QPushButton[palette="true"] { text-align: left; padding: 6px 10px; }
QGroupBox QPushButton[palette="true"] { border: 1px solid #444b3c; background: #2c3227; }
QPushButton[palette="true"]:hover { background: #3a4133; }
"""


def apply_theme(app: QApplication, name: str = "light") -> None:
    dark = name == "dark"
    app.setStyleSheet(DARK if dark else LIGHT)
    icons.set_dark(dark)
    icons.refresh_all(app)
