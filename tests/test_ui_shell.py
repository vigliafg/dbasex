"""Test della shell: token di design, tema, MDI, menu, SpeedBar e status bar."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QToolBar, QWidgetAction

from dbx import __version__
from dbx.ui import design, icons
from dbx.ui.main_window import MainWindow
from dbx.ui.menu import MenuEntry


def test_design_tokens_aurora_and_silver() -> None:
    aurora = design.palette("aurora")
    silver = design.palette("silver")
    assert design.DEFAULT_THEME == "aurora"
    assert aurora["window_bg"] == "#f5f7ff"
    assert aurora["menu_bar_bg"] == "#312e81"
    assert aurora["accent"] == "#7c3aed"
    assert silver["window_bg"] == "#c0c0c0"
    assert silver["selection_bg"] == "#000080"
    assert design.METRICS.grid_step == 8
    assert design.METRICS.ruler_size == 18
    assert design.UI_FONT.family == "MS Sans Serif"


def test_theme_aliases_and_qss() -> None:
    assert design.normalize_theme("light") == "light"
    assert design.palette("light") is design.AURORA
    assert design.palette("bright") is design.AURORA
    assert design.palette("dark") is design.SILVER_DARK
    assert design.normalize_theme("inesistente") == design.DEFAULT_THEME
    for theme in ("aurora", "silver", "dark"):
        sheet = design.qss(theme)
        assert "$" not in sheet
        assert "font-size" in sheet
        assert "qlineargradient" in sheet


def test_main_window_fits_short_screen_with_dialog(qapp, demo_project) -> None:
    """La shell non cresce oltre lo schermo e i dialoghi lunghi scorrono."""
    window = MainWindow(demo_project)
    try:
        window.resize(1024, 600)
        window.show()
        qapp.processEvents()
        assert window.height() == 600
        assert window.centralWidget().geometry().bottom() < window.statusBar().geometry().top()
        from dbx.designers.table_builder import TableBuilderDialog

        dialog = TableBuilderDialog(demo_project, demo_project.require_table("clienti"))
        window.editors.open_dialog("test:structure", dialog)
        qapp.processEvents()
        qapp.processEvents()
        assert window.height() == 600
        assert window.centralWidget().geometry().bottom() < window.statusBar().geometry().top()
        editor = window.editors.find("test:structure").widget()
        # La scheda Proprietà ha uno scorrimento interno: il dialogo può
        # adattarsi allo schermo e il contenuto lungo resta raggiungibile.
        properties = dialog.tabs.widget(2)
        assert (
            editor.scroll.verticalScrollBar().maximum() > 0
            or properties.verticalScrollBar().maximum() > 0
        )
    finally:
        window.close()


def test_main_window_basics(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert window.project is demo_project
        assert window.navigator is not None
        assert window.editors.windows() == []
        assert window.project_label.text().startswith(demo_project.name)
        titles = [action.text() for action in window.menuBar().actions()]
        assert titles == [
            "&Progetto",
            "&Modifica",
            "&Visualizza",
            "&Oggetto",
            "&Procedure",
            "&Proprietà",
            "&Finestra",
            "&?",
        ]
        toolbar = window.findChild(QToolBar, "main_toolbar")
        assert toolbar is not None
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert toolbar.iconSize().width() == design.METRICS.icon_size
        assert window.pos_label.text().startswith("Pos:")
        assert window.object_label.text().startswith("Oggetto:")
        assert window.record_label.text().startswith("Record:")
        assert window.mode_label.text().startswith("Modalità:")
        assert not window.act_undo.isEnabled()
        assert not window.act_zoom_in.isEnabled()
    finally:
        window.close()


def test_tabs_open_two_documents_and_dedupe(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("tables", "clienti")
        window.open_object("forms", "form_clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 2
        keys = {tab.property("dbx_key") for tab in window.editors.windows()}
        assert keys == {"tables:clienti", "forms:form_clienti"}
        assert window.object_label.text().startswith("Oggetto: Form Designer")
        assert window.mode_label.text().endswith("Design")

        window.open_object("tables", "clienti")
        qapp.processEvents()
        assert len(window.editors.windows()) == 2

        window.act_close_window.trigger()
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
        window.act_close_all.trigger()
        qapp.processEvents()
        assert window.editors.windows() == []
        assert window.object_label.text() == "Oggetto: —"
    finally:
        window.close()


def test_window_menu_lists_documents(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_object("tables", "clienti")
        qapp.processEvents()
        labels = [action.text() for action in window._window_menu.actions()]
        assert "Chiudi scheda" in labels
        assert "Chiudi tutte le schede" in labels
        assert any(label.startswith("Browse") for label in labels)
    finally:
        window.close()


def test_workspace_uses_navigator_and_tabs(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert not hasattr(window, "mdi")
        assert window.centralWidget() is window.workspace_splitter
        assert window.workspace_splitter.widget(0) is window.navigator
        assert window.workspace_splitter.widget(1) is window.editors
        assert window.workspace_splitter.count() == 2
    finally:
        window.close()


def test_command_window_opens_in_one_tab(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        window.show()
        window.open_command_window()
        qapp.processEvents()
        assert window.editors.find("command") is not None
        window.open_command_window()
        qapp.processEvents()
        assert len(window.editors.windows()) == 1
        assert "Command Window" in window.object_label.text()
    finally:
        window.close()


def test_release_version_and_pinned_pyqt() -> None:
    from dbx.config import DEFAULT_CONFIG

    assert __version__ == "0.9.0"
    assert DEFAULT_CONFIG["theme"] == "aurora"


def test_high_dpi_policy_and_icon_sizes(qapp) -> None:
    assert (
        QGuiApplication.highDpiScaleFactorRoundingPolicy()
        == Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    sizes = {size.width() for size in icons.icon("nuovo").availableSizes()}
    assert max(sizes) >= 32
    assert {16, 20, 24, 32, 48}.issubset(sizes)


def test_focus_is_visible_in_qss() -> None:
    for theme in ("silver", "dark"):
        sheet = design.qss(theme)
        assert "QPushButton:focus" in sheet
        assert "QToolButton:focus" in sheet


def test_accessible_names_on_shell_and_navigator(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert window.navigator.list.accessibleName() == "Oggetti del progetto"
        assert window.navigator.filter_combo.accessibleName() == "Filtro dei file"
        assert window.navigator._buttons["diagrams"].accessibleName() == "Database"
        assert window.navigator._buttons["tables"].accessibleName() == "Tabelle"
        window.open_command_window()
        qapp.processEvents()
        command = window.editors.current_editor()
        assert command.input.accessibleName() == "Comando"
        assert command.output.accessibleName() == "Risultati dei comandi"
    finally:
        window.close()


def test_main_menu_entries_have_icons_and_descriptions(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        menu = window.menuBar().actions()[0].menu()
        entries = [
            action.defaultWidget()
            for action in menu.actions()
            if isinstance(action, QWidgetAction)
        ]
        assert len(entries) >= 6
        assert all(isinstance(entry, MenuEntry) for entry in entries)
        assert all(entry.description for entry in entries)
        assert all(not entry.action.icon().isNull() for entry in entries)
        assert menu.actions()[0].text() == "Nuovo progetto…"

        edit_entries = [
            action.defaultWidget()
            for action in window.menuBar().actions()[1].menu().actions()
            if isinstance(action, QWidgetAction)
        ]
        assert edit_entries and all(entry.description for entry in edit_entries)
    finally:
        window.close()


def test_menu_entry_click_triggers_action(qapp) -> None:
    from PyQt6.QtGui import QAction

    triggered: list[str] = []
    action = QAction("Voce di prova", None)
    action.triggered.connect(lambda: triggered.append("ok"))
    entry = MenuEntry(action, "Descrizione della voce")
    entry.show()
    try:
        qapp.processEvents()
        QTest.mouseClick(entry, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert triggered == ["ok"]
    finally:
        entry.close()


def test_main_menu_entry_click_triggers_action_and_closes(qapp, demo_project) -> None:
    from PyQt6.QtCore import QPoint

    window = MainWindow(demo_project)
    try:
        window.show()
        qapp.processEvents()
        triggered: list[str] = []
        window.act_save.triggered.connect(lambda: triggered.append("save"))
        menu = window.menuBar().actions()[0].menu()
        menu.popup(window.mapToGlobal(QPoint(40, 40)))
        qapp.processEvents()
        qapp.processEvents()
        entry = next(
            action.defaultWidget()
            for action in menu.actions()
            if isinstance(action, QWidgetAction) and action.text() == "Salva progetto"
        )
        QTest.mouseClick(entry, Qt.MouseButton.LeftButton)
        qapp.processEvents()
        assert triggered == ["save"]
        assert not menu.isVisible()
    finally:
        window.close()


def test_menu_hover_moves_focus_to_single_entry(qapp, demo_project) -> None:
    from PyQt6.QtCore import QPoint

    window = MainWindow(demo_project)
    try:
        window.show()
        qapp.processEvents()
        menu = window.menuBar().actions()[0].menu()
        menu.popup(window.mapToGlobal(QPoint(40, 40)))
        qapp.processEvents()
        qapp.processEvents()
        entries = [
            action.defaultWidget()
            for action in menu.actions()
            if isinstance(action, QWidgetAction)
        ]
        QTest.mouseMove(entries[1], entries[1].rect().center())
        qapp.processEvents()
        assert [entry.hasFocus() for entry in entries] == [
            index == 1 for index in range(len(entries))
        ]
    finally:
        window.close()


def test_maintenance_menu_exposes_reevaluate_action(qapp, demo_project) -> None:
    window = MainWindow(demo_project)
    try:
        assert "Riapplica regole" in window.act_reevaluate.text()
    finally:
        window.close()
