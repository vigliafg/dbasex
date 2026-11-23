"""Token di design di dBX.

Unica fonte di verità per colori, metriche e tipografia. Il tema predefinito è
``aurora``: superfici chiare, zone colorate con gradienti e accenti vivaci.
Restano disponibili ``silver`` (storico, in stile dBASE 5.5) e ``dark``.
Gli alias ``light`` e ``bright`` puntano ad Aurora; ``silver-dark`` a Dark.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import Template

Palette = dict[str, str]

DEFAULT_THEME = "aurora"
TARGET_THEME = "aurora"


@dataclass(frozen=True)
class FontSpec:
    family: str
    size_pt: float


@dataclass(frozen=True)
class Metrics:
    """Misure condivise da shell, designer e canvas (px logici)."""

    icon_size: int = 16
    toolbar_height: int = 24
    row_height: int = 18
    field_height: int = 20
    grid_step: int = 8
    ruler_size: int = 18
    navigator_width: int = 110
    status_height: int = 22
    border: int = 1
    padding: int = 4
    form_min_width: int = 320
    form_min_height: int = 200


METRICS = Metrics()

UI_FONT = FontSpec("MS Sans Serif", 8.0)
UI_FONT_FALLBACKS = ("Segoe UI", "Noto Sans", "DejaVu Sans", "sans-serif")
REPORT_FONT = FontSpec("Times New Roman", 10.0)
CODE_FONT = FontSpec("Courier New", 9.0)

# Serie dei grafici: colori leggibili sia a schermo sia in stampa.
CHART_COLORS = (
    "#3b7ea8",
    "#d97757",
    "#6a994e",
    "#c9a227",
    "#7b6cb0",
    "#4f9e94",
)

# Tinta delle icone del Navigator: tre accenti del tema, alternati per categoria.
NAV_CATEGORY_ACCENTS = {
    "all": "nav_icon_3",
    "database": "nav_icon_1",
    "tables": "nav_icon_1",
    "queries": "nav_icon_1",
    "forms": "nav_icon_3",
    "reports": "nav_icon_2",
    "labels": "nav_icon_1",
    "menus": "nav_icon_3",
    "scripts": "nav_icon_2",
}

FONTS = {
    "ui": UI_FONT,
    "report": REPORT_FONT,
    "code": CODE_FONT,
}


# --------------------------------------------------------------------- palette
AURORA: Palette = {
    "name": "aurora",
    "font_size": "12px",
    # superfici
    "window_bg": "#f5f7ff",
    "window_bg_alt": "#eef2ff",
    "text": "#172033",
    "disabled": "#8a94a6",
    "workspace": "#fffdf7",
    "report_band": "#fff7ed",
    "report_band_active": "#ffe4e6",
    "panel": "#f8fafc",
    "panel_alt": "#eef2ff",
    "panel_light": "#ffffff",
    "panel_shadow": "#c7d2fe",
    "panel_dark": "#6366f1",
    "focus": "#db2777",
    "grid_dot": "#c7d2fe",
    "ruler_bg": "#e0e7ff",
    "ruler_bg_alt": "#f5d0fe",
    "ruler_text": "#4338ca",
    # menu e barre
    "menu_bar_bg": "#312e81",
    "menu_bar_bg_alt": "#7c3aed",
    "menu_bar_text": "#f8fafc",
    "menu_bg": "#ffffff",
    "menu_bg_alt": "#f5f3ff",
    "menu_border": "#a5b4fc",
    "menu_selected": "#7c3aed",
    "menu_selected_text": "#ffffff",
    "menu_item_selected": "#ec4899",
    "menu_item_selected_alt": "#7c3aed",
    "menu_item_selected_text": "#ffffff",
    "menu_item_text": "#1e293b",
    "menu_item_desc": "#64748b",
    "menu_item_desc_selected": "#fce7f3",
    "toolbar_bg": "#dbeafe",
    "toolbar_bg_alt": "#ede9fe",
    "toolbutton_hover": "#ffffff",
    "toolbutton_radius": "8px",
    "status_bg": "#312e81",
    "status_bg_alt": "#0f766e",
    "status_border": "#4338ca",
    "status_text": "#f8fafc",
    # schede e dock
    "tab_pane_bg": "#ffffff",
    "tab_bg": "#e0e7ff",
    "tab_bg_alt": "#f5f3ff",
    "tab_border": "#a5b4fc",
    "tab_selected_bg": "#fdf2f8",
    "tab_selected_bg_alt": "#ede9fe",
    "tab_text": "#312e81",
    "dock_title_bg": "#c7d2fe",
    "dock_title_bg_alt": "#a5f3fc",
    # campi
    "input_bg": "#ffffff",
    "input_border": "#a5b4fc",
    "input_border_dark": "#818cf8",
    "input_border_light": "#ffffff",
    "input_radius": "6px",
    "selection_bg": "#4f46e5",
    "selection_text": "#ffffff",
    "alternate_bg": "#f0f9ff",
    "grid_line": "#cbd5e1",
    # tabelle
    "header_bg": "#0f766e",
    "header_bg_alt": "#0891b2",
    "header_border": "#0e7490",
    "header_text": "#ffffff",
    # pulsanti
    "button_bg": "#e0f2fe",
    "button_bg_alt": "#ede9fe",
    "button_border": "#93c5fd",
    "button_light": "#ffffff",
    "button_dark": "#6366f1",
    "button_radius": "8px",
    "button_hover": "#f0f9ff",
    "button_text": "#1e3a8a",
    "default_button_bg": "#db2777",
    "default_button_text": "#ffffff",
    "default_button_border": "#be185d",
    "default_button_hover": "#ec4899",
    "groupbox_border": "#c7d2fe",
    "groupbox_radius": "8px",
    "splitter_bg": "#c7d2fe",
    "palette_button_bg": "#f5f3ff",
    "palette_button_border": "#c4b5fd",
    "palette_button_hover": "#ede9fe",
    # zone applicative
    "nav_bg": "#eef2ff",
    "nav_bg_alt": "#fae8ff",
    "nav_button_bg": "#ffffff",
    "nav_button_bg_alt": "#e0e7ff",
    "nav_button_border": "#a5b4fc",
    "nav_button_hover": "#fdf2f8",
    "nav_button_text": "#312e81",
    "nav_icon_1": "#7c3aed",
    "nav_icon_2": "#ec4899",
    "nav_icon_3": "#0891b2",
    "mdi_bg": "#eef2ff",
    "mdi_bg_alt": "#ecfeff",
    "command_bg": "#f8fafc",
    "command_bg_alt": "#f0fdfa",
    "inspector_bg": "#faf5ff",
    "inspector_bg_alt": "#eff6ff",
    "palette_bg": "#f0fdfa",
    "palette_bg_alt": "#ede9fe",
    # tooltip e stati
    "tooltip_bg": "#1e1b4b",
    "tooltip_text": "#f8fafc",
    "tooltip_border": "#7c3aed",
    "error": "#be123c",
    "success": "#047857",
    "warning": "#b45309",
    # brand e icone
    "accent": "#7c3aed",
    "accent2": "#ec4899",
    "accent3": "#0891b2",
    "accent_text": "#ffffff",
    "icon_color": "#1e293b",
    "title_active": "#7c3aed",
    "title_inactive": "#c7d2fe",
}


SILVER: Palette = {
    "name": "silver",
    "font_size": "12px",
    # superfici
    "window_bg": "#c0c0c0",
    "window_bg_alt": "#d4d4d4",
    "text": "#000000",
    "disabled": "#808080",
    "workspace": "#ffffff",
    "report_band": "#fbfcf9",
    "report_band_active": "#f3f6ef",
    "panel": "#c0c0c0",
    "panel_alt": "#c8c8c8",
    "panel_light": "#dfdfdf",
    "panel_shadow": "#808080",
    "panel_dark": "#404040",
    "focus": "#000000",
    "grid_dot": "#808080",
    "ruler_bg": "#c0c0c0",
    "ruler_bg_alt": "#c8c8c8",
    "ruler_text": "#000000",
    # menu e barre
    "menu_bar_bg": "#c0c0c0",
    "menu_bar_bg_alt": "#d4d4d4",
    "menu_bar_text": "#000000",
    "menu_bg": "#c0c0c0",
    "menu_bg_alt": "#d4d4d4",
    "menu_border": "#808080",
    "menu_selected": "#000080",
    "menu_selected_text": "#ffffff",
    "menu_item_selected": "#000080",
    "menu_item_selected_alt": "#000080",
    "menu_item_selected_text": "#ffffff",
    "menu_item_text": "#000000",
    "menu_item_desc": "#404040",
    "menu_item_desc_selected": "#d0d0d0",
    "toolbar_bg": "#c0c0c0",
    "toolbar_bg_alt": "#d4d4d4",
    "toolbutton_hover": "#d0d0d0",
    "toolbutton_radius": "0px",
    "status_bg": "#c0c0c0",
    "status_bg_alt": "#d4d4d4",
    "status_border": "#808080",
    "status_text": "#000000",
    # schede e dock
    "tab_pane_bg": "#dfdfdf",
    "tab_bg": "#c0c0c0",
    "tab_bg_alt": "#d4d4d4",
    "tab_border": "#808080",
    "tab_selected_bg": "#dfdfdf",
    "tab_selected_bg_alt": "#e8e8e8",
    "tab_text": "#000000",
    "dock_title_bg": "#c0c0c0",
    "dock_title_bg_alt": "#d4d4d4",
    # campi
    "input_bg": "#ffffff",
    "input_border": "#808080",
    "input_border_dark": "#808080",
    "input_border_light": "#ffffff",
    "input_radius": "0px",
    "selection_bg": "#000080",
    "selection_text": "#ffffff",
    "alternate_bg": "#f0f0f0",
    "grid_line": "#808080",
    # tabelle
    "header_bg": "#c0c0c0",
    "header_bg_alt": "#d4d4d4",
    "header_border": "#808080",
    "header_text": "#000000",
    # pulsanti
    "button_bg": "#c0c0c0",
    "button_bg_alt": "#d4d4d4",
    "button_border": "#808080",
    "button_light": "#ffffff",
    "button_dark": "#404040",
    "button_radius": "0px",
    "button_hover": "#d0d0d0",
    "button_text": "#000000",
    "default_button_bg": "#000080",
    "default_button_text": "#ffffff",
    "default_button_border": "#000080",
    "default_button_hover": "#0000a0",
    "groupbox_border": "#808080",
    "groupbox_radius": "0px",
    "splitter_bg": "#c0c0c0",
    "palette_button_bg": "#c0c0c0",
    "palette_button_border": "#808080",
    "palette_button_hover": "#d0d0d0",
    # zone applicative
    "nav_bg": "#c0c0c0",
    "nav_bg_alt": "#d4d4d4",
    "nav_button_bg": "#c0c0c0",
    "nav_button_bg_alt": "#d4d4d4",
    "nav_button_border": "#808080",
    "nav_button_hover": "#d0d0d0",
    "nav_button_text": "#000000",
    "nav_icon_1": "#000080",
    "nav_icon_2": "#8b0000",
    "nav_icon_3": "#006666",
    "mdi_bg": "#c0c0c0",
    "mdi_bg_alt": "#d4d4d4",
    "command_bg": "#c0c0c0",
    "command_bg_alt": "#dfdfdf",
    "inspector_bg": "#c0c0c0",
    "inspector_bg_alt": "#dfdfdf",
    "palette_bg": "#c0c0c0",
    "palette_bg_alt": "#dfdfdf",
    # tooltip e stati
    "tooltip_bg": "#ffffe1",
    "tooltip_text": "#000000",
    "tooltip_border": "#808080",
    "error": "#800000",
    "success": "#006000",
    "warning": "#806000",
    # brand e icone
    "accent": "#000080",
    "accent2": "#000080",
    "accent3": "#000080",
    "accent_text": "#ffffff",
    "icon_color": "#000000",
    "title_active": "#000080",
    "title_inactive": "#808080",
}


SILVER_DARK: Palette = {
    "name": "dark",
    "font_size": "12px",
    # superfici
    "window_bg": "#2b2b2b",
    "window_bg_alt": "#242424",
    "text": "#e8e8e8",
    "disabled": "#808080",
    "workspace": "#1e1e1e",
    "report_band": "#202020",
    "report_band_active": "#262626",
    "panel": "#2b2b2b",
    "panel_alt": "#333333",
    "panel_light": "#4a4a4a",
    "panel_shadow": "#555555",
    "panel_dark": "#1a1a1a",
    "focus": "#e8e8e8",
    "grid_dot": "#555555",
    "ruler_bg": "#2b2b2b",
    "ruler_bg_alt": "#333333",
    "ruler_text": "#e8e8e8",
    # menu e barre
    "menu_bar_bg": "#242424",
    "menu_bar_bg_alt": "#333333",
    "menu_bar_text": "#e8e8e8",
    "menu_bg": "#2b2b2b",
    "menu_bg_alt": "#333333",
    "menu_border": "#555555",
    "menu_selected": "#2f5d8a",
    "menu_selected_text": "#ffffff",
    "menu_item_selected": "#2f5d8a",
    "menu_item_selected_alt": "#3a6ea5",
    "menu_item_selected_text": "#ffffff",
    "menu_item_text": "#e8e8e8",
    "menu_item_desc": "#a0a0a0",
    "menu_item_desc_selected": "#dbeafe",
    "toolbar_bg": "#2b2b2b",
    "toolbar_bg_alt": "#333333",
    "toolbutton_hover": "#3a3a3a",
    "toolbutton_radius": "0px",
    "status_bg": "#242424",
    "status_bg_alt": "#333333",
    "status_border": "#555555",
    "status_text": "#e8e8e8",
    # schede e dock
    "tab_pane_bg": "#333333",
    "tab_bg": "#333333",
    "tab_bg_alt": "#3a3a3a",
    "tab_border": "#555555",
    "tab_selected_bg": "#3d3d3d",
    "tab_selected_bg_alt": "#454545",
    "tab_text": "#e8e8e8",
    "dock_title_bg": "#333333",
    "dock_title_bg_alt": "#3d3d3d",
    # campi
    "input_bg": "#1e1e1e",
    "input_border": "#555555",
    "input_border_dark": "#1a1a1a",
    "input_border_light": "#4a4a4a",
    "input_radius": "0px",
    "selection_bg": "#2f5d8a",
    "selection_text": "#ffffff",
    "alternate_bg": "#262626",
    "grid_line": "#444444",
    # tabelle
    "header_bg": "#333333",
    "header_bg_alt": "#3d3d3d",
    "header_border": "#555555",
    "header_text": "#e8e8e8",
    # pulsanti
    "button_bg": "#333333",
    "button_bg_alt": "#3a3a3a",
    "button_border": "#555555",
    "button_light": "#4a4a4a",
    "button_dark": "#1a1a1a",
    "button_radius": "0px",
    "button_hover": "#3d3d3d",
    "button_text": "#e8e8e8",
    "default_button_bg": "#2f5d8a",
    "default_button_text": "#ffffff",
    "default_button_border": "#2f5d8a",
    "default_button_hover": "#3a6ea5",
    "groupbox_border": "#555555",
    "groupbox_radius": "0px",
    "splitter_bg": "#444444",
    "palette_button_bg": "#333333",
    "palette_button_border": "#555555",
    "palette_button_hover": "#3a3a3a",
    # zone applicative
    "nav_bg": "#2b2b2b",
    "nav_bg_alt": "#333333",
    "nav_button_bg": "#333333",
    "nav_button_bg_alt": "#3a3a3a",
    "nav_button_border": "#555555",
    "nav_button_hover": "#3d3d3d",
    "nav_button_text": "#e8e8e8",
    "nav_icon_1": "#8ab4f8",
    "nav_icon_2": "#f48fb1",
    "nav_icon_3": "#4dd0e1",
    "mdi_bg": "#242424",
    "mdi_bg_alt": "#2b2b2b",
    "command_bg": "#2b2b2b",
    "command_bg_alt": "#333333",
    "inspector_bg": "#2b2b2b",
    "inspector_bg_alt": "#333333",
    "palette_bg": "#2b2b2b",
    "palette_bg_alt": "#333333",
    # tooltip e stati
    "tooltip_bg": "#3a3a3a",
    "tooltip_text": "#e8e8e8",
    "tooltip_border": "#666666",
    "error": "#ff8080",
    "success": "#6ee7b7",
    "warning": "#fbbf24",
    # brand e icone
    "accent": "#2f5d8a",
    "accent2": "#3a6ea5",
    "accent3": "#2f5d8a",
    "accent_text": "#ffffff",
    "icon_color": "#e8e8e8",
    "title_active": "#1f4e79",
    "title_inactive": "#555555",
}

# Alias storici: ``light`` e ``bright`` sono il nuovo tema Aurora. Il vecchio
# tema scuro resta disponibile come ``dark``/``silver-dark``.
THEMES: dict[str, Palette] = {
    "aurora": AURORA,
    "bright": AURORA,
    "light": AURORA,
    "silver": SILVER,
    "dark": SILVER_DARK,
    "silver-dark": SILVER_DARK,
}


def normalize_theme(name: str | None) -> str:
    """Restituisce un nome di tema valido, ricadendo sul default."""
    key = str(name or DEFAULT_THEME).strip().lower()
    return key if key in THEMES else DEFAULT_THEME


def palette(name: str | None = None) -> Palette:
    return THEMES[normalize_theme(name)]


def icon_color(name: str | None = None) -> str:
    return palette(name)["icon_color"]


def brand(name: str | None = None) -> tuple[str, str]:
    """Colore di accento e colore del testo per splash e icona applicazione."""
    current = palette(name)
    return current["accent"], current["accent_text"]


def category_color(category: str, name: str | None = None) -> str:
    """Colore dell'icona di una categoria del Navigator, coerente col tema."""
    current = palette(name)
    token = NAV_CATEGORY_ACCENTS.get(category, "nav_icon_1")
    return current.get(token, current["accent"])


# ------------------------------------------------------------------------- QSS
_QSS = Template(
    """
* { font-size: $font_size; }
QMainWindow, QDialog, QWizard, QWizardPage { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $window_bg, stop:1 $window_bg_alt); }
QWidget { color: $text; }
QWidget#navigator, QWidget#data_view, QWidget#command_window,
QWidget#form_designer, QWidget#report_designer, QWidget#script_editor,
QWidget#menu_designer, QWidget#project_editor, QWidget#form_runtime {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $window_bg, stop:1 $window_bg_alt);
}
QWidget#property_inspector {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $inspector_bg, stop:1 $inspector_bg_alt);
    border: 1px solid $panel_shadow; border-radius: 10px;
}
QWidget#palette_panel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $palette_bg, stop:1 $palette_bg_alt);
    border: 1px solid $panel_shadow; border-radius: 10px;
}
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $menu_bar_bg, stop:1 $menu_bar_bg_alt);
    color: $menu_bar_text; border-bottom: 1px solid $menu_border; padding: 2px 4px;
}
QMenuBar::item { padding: 6px 12px; margin: 1px 2px; background: transparent; border-radius: 7px; color: $menu_bar_text; }
QMenuBar::item:selected { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $menu_selected, stop:1 $accent2); color: $menu_selected_text; }
QMenuBar::item:pressed { background: $menu_selected; color: $menu_selected_text; }
QMenu { background: $menu_bg; border: 2px solid $menu_border; border-radius: 10px; padding: 5px; }
QMenu::separator { height: 1px; background: $menu_border; margin: 4px 8px; }
QToolBar { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $toolbar_bg, stop:1 $toolbar_bg_alt); border: 0; border-bottom: 1px solid $panel_shadow; spacing: 1px; padding: 4px; }
QToolBar::separator { width: 2px; background: transparent; border-left: 1px solid $panel_shadow; border-right: 1px solid $panel_light; margin: 2px 5px; }
QToolButton { padding: 4px 6px; border: 1px solid transparent; border-radius: $toolbutton_radius; color: $text; }
QToolButton:hover { background: $toolbutton_hover; }
QToolButton:focus, QPushButton:focus, QTabBar::tab:focus { border: 1px dotted $focus; }
QToolButton:pressed, QToolButton:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $accent, stop:1 $accent2);
    color: $accent_text; border: 1px solid $accent; padding: 3px 5px;
}
QFrame#nav_categories {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 $nav_bg, stop:1 $nav_bg_alt);
    border-right: 2px solid $panel_shadow;
}
QScrollArea#nav_categories_scroll, QWidget#nav_categories_body,
QScrollArea#dialog_editor_scroll,
QScrollArea#nav_categories_scroll > QWidget#qt_scrollarea_viewport,
QScrollArea#dialog_editor_scroll > QWidget#qt_scrollarea_viewport {
    background: transparent; border: 0;
}
QToolButton[nav_category] {
    background: transparent;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 7px;
    color: $nav_button_text;
    padding: 4px 8px;
    margin: 1px 3px;
    text-align: left;
}
QToolButton[nav_category]:hover {
    background: $nav_button_hover;
    border-left-color: $nav_icon_3;
}
QToolButton[nav_category]:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $nav_button_bg, stop:1 $nav_button_bg_alt);
    border-left-color: $nav_icon_1;
    color: $nav_button_text;
    font-weight: 700;
}
QToolButton[nav_category]:disabled {
    color: $disabled;
    background: transparent;
    border-left-color: transparent;
}
QScrollArea#nav_categories_scroll QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px 1px;
}
QScrollArea#nav_categories_scroll QScrollBar::handle:vertical {
    background: $nav_button_border;
    border-radius: 3px;
    min-height: 24px;
}
QScrollArea#nav_categories_scroll QScrollBar::add-line:vertical,
QScrollArea#nav_categories_scroll QScrollBar::sub-line:vertical,
QScrollArea#nav_categories_scroll QScrollBar::add-page:vertical,
QScrollArea#nav_categories_scroll QScrollBar::sub-page:vertical {
    background: transparent; border: 0; height: 0;
}
QMdiArea {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $mdi_bg, stop:1 $mdi_bg_alt);
    border-top: 1px solid $panel_shadow;
}
QMdiSubWindow { background: $workspace; border: 1px solid $panel_shadow; }
QLabel#status_field { padding: 0 10px; border-left: 1px solid $status_border; color: $status_text; }
QLabel#nav_header, QLabel#browse_header, QLabel#pane_title {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $header_bg, stop:1 $header_bg_alt);
    color: $header_text; border: 0; border-radius: 6px; padding: 5px 8px; font-weight: 700;
}
QLabel#nav_hint { color: $disabled; padding: 2px; }
QLabel#palette_section {
    font-weight: 700; color: $accent; padding: 1px 2px;
    border-bottom: 1px solid $panel_shadow;
}
QFrame#command_pane, QFrame#results_pane {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $command_bg, stop:1 $command_bg_alt);
    border: 1px solid $panel_shadow; border-radius: 8px;
}
QFrame#table_meta {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $panel, stop:1 $panel_alt);
    border: 1px solid $panel_shadow; border-radius: 8px;
}
QLabel#table_type { font-weight: 700; color: $accent; }
QLabel#command_status[state="error"] { color: $error; }
QTabWidget::pane { border: 1px solid $tab_border; background: $tab_pane_bg; border-radius: 8px; }
QTabBar::tab {
    padding: 6px 14px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $tab_bg, stop:1 $tab_bg_alt);
    color: $tab_text; border: 1px solid $tab_border; border-bottom: 0;
    border-top-left-radius: 7px; border-top-right-radius: 7px; margin-right: 2px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $tab_selected_bg, stop:1 $tab_selected_bg_alt);
    font-weight: 700;
}
QDockWidget { titlebar-close-icon: none; }
QDockWidget::title {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $dock_title_bg, stop:1 $dock_title_bg_alt);
    padding: 6px; border-bottom: 1px solid $tab_border; border-radius: 6px;
}
QTreeView, QTableView, QTableWidget, QListView, QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: $input_bg;
    border: 1px solid $input_border;
    border-top-color: $input_border_dark;
    border-left-color: $input_border_dark;
    border-bottom-color: $input_border_light;
    border-right-color: $input_border_light;
    border-radius: $input_radius;
    selection-background-color: $selection_bg;
    selection-color: $selection_text;
}
QTableView { alternate-background-color: $alternate_bg; gridline-color: $grid_line; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid $accent;
}
QLineEdit[state="error"] {
    border: 2px solid $error;
    background: $input_bg;
}
QListView:focus, QTreeView:focus, QTableView:focus {
    border: 1px solid $accent;
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $header_bg, stop:1 $header_bg_alt);
    color: $header_text; border: 1px solid $header_border;
    padding: 4px; font-weight: 700;
}
QTableCornerButton::section {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $header_bg, stop:1 $header_bg_alt);
    border: 1px solid $header_border;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $button_bg, stop:1 $button_bg_alt);
    border: 1px solid $button_border;
    border-top-color: $button_light;
    border-left-color: $button_light;
    border-bottom-color: $button_dark;
    border-right-color: $button_dark;
    border-radius: $button_radius;
    color: $button_text;
    padding: 5px 12px;
}
QPushButton:hover { background: $button_hover; }
QPushButton:pressed {
    background: $button_bg_alt;
    border-top-color: $button_dark;
    border-left-color: $button_dark;
    border-bottom-color: $button_light;
    border-right-color: $button_light;
}
QPushButton:default {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 $default_button_bg, stop:1 $accent2);
    color: $default_button_text; border-color: $default_button_border;
}
QPushButton:default:hover { background: $default_button_hover; }
QPushButton:focus { border: 1px dotted $focus; }
QStatusBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 $status_bg, stop:1 $status_bg_alt);
    color: $status_text; border-top: 1px solid $status_border;
}
QStatusBar QLabel { color: $status_text; }
QGroupBox { border: 1px solid $groupbox_border; border-radius: $groupbox_radius; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: $accent; }
QFrame#qbe_box {
    background: $tab_pane_bg; border: 1px solid $groupbox_border;
    border-radius: $groupbox_radius;
}
QLabel#qbe_title { color: $accent; font-weight: 700; padding: 2px 6px; }
QSplitter { background: transparent; }
QSplitter::handle { background: $splitter_bg; }
QToolTip { background: $tooltip_bg; color: $tooltip_text; border: 1px solid $tooltip_border; padding: 4px 6px; border-radius: 6px; }
QPushButton[palette="true"] { text-align: left; padding: 5px 10px; }
QGroupBox QPushButton[palette="true"] { border: 1px solid $palette_button_border; background: $palette_button_bg; }
QPushButton[palette="true"]:hover { background: $palette_button_hover; }
QScrollArea { border: 0; }
"""
)


def qss(name: str | None = None) -> str:
    """Foglio di stile Qt generato dai token del tema richiesto."""
    return _QSS.substitute(palette(name))
