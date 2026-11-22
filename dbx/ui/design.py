"""Token di design di dBX.

Unica fonte di verità per colori, metriche e tipografia. I temi disponibili
sono ``silver`` (default, in stile dBASE 5.5) e ``dark``. Gli alias ``light``
e ``silver-dark`` restano per compatibilità con configurazioni esistenti.
"""

from __future__ import annotations

from dataclasses import dataclass
from string import Template

Palette = dict[str, str]

DEFAULT_THEME = "silver"
TARGET_THEME = "silver"


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

FONTS = {
    "ui": UI_FONT,
    "report": REPORT_FONT,
    "code": CODE_FONT,
}


# --------------------------------------------------------------------- palette
SILVER: Palette = {
    "name": "silver",
    "font_size": "12px",
    # superfici
    "window_bg": "#c0c0c0",
    "text": "#000000",
    "disabled": "#808080",
    "workspace": "#ffffff",
    "panel": "#c0c0c0",
    "panel_light": "#dfdfdf",
    "panel_shadow": "#808080",
    "panel_dark": "#404040",
    "focus": "#000000",
    "grid_dot": "#808080",
    "ruler_bg": "#c0c0c0",
    "ruler_text": "#000000",
    # menu e barre
    "menu_bg": "#c0c0c0",
    "menu_border": "#808080",
    "menu_selected": "#000080",
    "menu_selected_text": "#ffffff",
    "menu_item_selected": "#000080",
    "menu_item_selected_text": "#ffffff",
    "toolbar_bg": "#c0c0c0",
    "toolbutton_hover": "#d0d0d0",
    "toolbutton_radius": "0px",
    "status_bg": "#c0c0c0",
    "status_border": "#808080",
    # schede e dock
    "tab_pane_bg": "#dfdfdf",
    "tab_bg": "#c0c0c0",
    "tab_border": "#808080",
    "tab_selected_bg": "#dfdfdf",
    "dock_title_bg": "#c0c0c0",
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
    "header_border": "#808080",
    # pulsanti
    "button_bg": "#c0c0c0",
    "button_border": "#808080",
    "button_light": "#ffffff",
    "button_dark": "#404040",
    "button_radius": "0px",
    "button_hover": "#d0d0d0",
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
    # tooltip
    "tooltip_bg": "#ffffe1",
    "tooltip_text": "#000000",
    "tooltip_border": "#808080",
    # brand e icone
    "accent": "#000080",
    "accent_text": "#ffffff",
    "icon_color": "#000000",
    "title_active": "#000080",
    "title_inactive": "#808080",
}

SILVER_DARK: Palette = {
    "name": "dark",
    "font_size": "12px",
    "window_bg": "#2b2b2b",
    "text": "#e8e8e8",
    "disabled": "#808080",
    "workspace": "#1e1e1e",
    "panel": "#2b2b2b",
    "panel_light": "#4a4a4a",
    "panel_shadow": "#555555",
    "panel_dark": "#1a1a1a",
    "focus": "#e8e8e8",
    "grid_dot": "#555555",
    "ruler_bg": "#2b2b2b",
    "ruler_text": "#e8e8e8",
    "menu_bg": "#2b2b2b",
    "menu_border": "#555555",
    "menu_selected": "#2f5d8a",
    "menu_selected_text": "#ffffff",
    "menu_item_selected": "#2f5d8a",
    "menu_item_selected_text": "#ffffff",
    "toolbar_bg": "#2b2b2b",
    "toolbutton_hover": "#3a3a3a",
    "toolbutton_radius": "0px",
    "status_bg": "#2b2b2b",
    "status_border": "#555555",
    "tab_pane_bg": "#333333",
    "tab_bg": "#333333",
    "tab_border": "#555555",
    "tab_selected_bg": "#3d3d3d",
    "dock_title_bg": "#333333",
    "input_bg": "#1e1e1e",
    "input_border": "#555555",
    "input_border_dark": "#1a1a1a",
    "input_border_light": "#4a4a4a",
    "input_radius": "0px",
    "selection_bg": "#2f5d8a",
    "selection_text": "#ffffff",
    "alternate_bg": "#262626",
    "grid_line": "#444444",
    "header_bg": "#333333",
    "header_border": "#555555",
    "button_bg": "#333333",
    "button_border": "#555555",
    "button_light": "#4a4a4a",
    "button_dark": "#1a1a1a",
    "button_radius": "0px",
    "button_hover": "#3d3d3d",
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
    "tooltip_bg": "#3a3a3a",
    "tooltip_text": "#e8e8e8",
    "tooltip_border": "#666666",
    "accent": "#2f5d8a",
    "accent_text": "#ffffff",
    "icon_color": "#e8e8e8",
    "title_active": "#1f4e79",
    "title_inactive": "#555555",
}

# Alias storici: il vecchio tema chiaro era una variante moderna; ora punta
# al tema dBASE. Il vecchio tema scuro è sostituito dal dark dBASE.
THEMES: dict[str, Palette] = {
    "silver": SILVER,
    "dark": SILVER_DARK,
    "light": SILVER,
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


# ------------------------------------------------------------------------- QSS
_QSS = Template(
    """
* { font-size: $font_size; }
QMainWindow, QDialog { background: $window_bg; }
QWidget { color: $text; }
QMenuBar { background: $menu_bg; border-bottom: 1px solid $menu_border; }
QMenuBar::item { padding: 4px 8px; background: transparent; }
QMenuBar::item:selected { background: $menu_selected; color: $menu_selected_text; }
QMenu { background: $menu_bg; border: 1px solid $menu_border; }
QMenu::item { padding: 4px 24px 4px 20px; }
QMenu::item:selected { background: $menu_item_selected; color: $menu_item_selected_text; }
QMenu::separator { height: 1px; background: $menu_border; margin: 3px 6px; }
QToolBar { background: $toolbar_bg; border: 0; border-bottom: 1px solid $menu_border; spacing: 2px; padding: 3px; }
QToolButton { padding: 3px 7px; border-radius: $toolbutton_radius; }
QToolButton:hover { background: $toolbutton_hover; }
QTabWidget::pane { border: 1px solid $tab_border; background: $tab_pane_bg; }
QTabBar::tab {
    padding: 5px 12px; background: $tab_bg; border: 1px solid $tab_border; border-bottom: 0;
    border-top-color: $button_light; border-left-color: $button_light;
}
QTabBar::tab:selected { background: $tab_selected_bg; }
QDockWidget { titlebar-close-icon: none; }
QDockWidget::title { background: $dock_title_bg; padding: 5px; border-bottom: 1px solid $tab_border; }
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
QHeaderView::section {
    background: $header_bg; border: 1px solid $header_border;
    border-top-color: $button_light; border-left-color: $button_light;
    padding: 3px;
}
QPushButton {
    background: $button_bg;
    border: 1px solid $button_border;
    border-top-color: $button_light;
    border-left-color: $button_light;
    border-bottom-color: $button_dark;
    border-right-color: $button_dark;
    border-radius: $button_radius;
    padding: 4px 12px;
}
QPushButton:hover { background: $button_hover; }
QPushButton:pressed {
    border-top-color: $button_dark;
    border-left-color: $button_dark;
    border-bottom-color: $button_light;
    border-right-color: $button_light;
}
QPushButton:default { background: $default_button_bg; color: $default_button_text; border-color: $default_button_border; }
QPushButton:default:hover { background: $default_button_hover; }
QStatusBar { background: $status_bg; border-top: 1px solid $status_border; }
QGroupBox { border: 1px solid $groupbox_border; border-radius: $groupbox_radius; margin-top: 10px; padding-top: 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QSplitter::handle { background: $splitter_bg; }
QToolTip { background: $tooltip_bg; color: $tooltip_text; border: 1px solid $tooltip_border; padding: 2px; }
QPushButton[palette="true"] { text-align: left; padding: 5px 10px; }
QGroupBox QPushButton[palette="true"] { border: 1px solid $palette_button_border; background: $palette_button_bg; }
QPushButton[palette="true"]:hover { background: $palette_button_hover; }
"""
)


def qss(name: str | None = None) -> str:
    """Foglio di stile Qt generato dai token del tema richiesto."""
    return _QSS.substitute(palette(name))
