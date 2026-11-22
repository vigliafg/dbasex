"""Voci di menu dBX: icona, titolo, descrizione e scorciatoia.

Il tema colorato usa un widget per ogni voce, così ogni riga può mostrare
l'icona a sinistra, il titolo in grassetto, la descrizione sotto e la
scorciatoia a destra. Gli ``QAction`` originali restano la fonte di verità:
abilitazione, stato selezionato e scorciatoie continuano a funzionare.
"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMenu, QWidget, QWidgetAction

from . import design

ENTRY_HEIGHT = 50
ENTRY_MIN_WIDTH = 440


class DescriptiveMenu(QMenu):
    """Menu che porta il focus sulla prima voce descrittiva all'apertura."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def showEvent(self, event) -> None:  # noqa: N802 - API Qt
        super().showEvent(event)
        for action in self.actions():
            if isinstance(action, QWidgetAction):
                widget = action.defaultWidget()
                if isinstance(widget, MenuEntry):
                    widget._sync()
        self._focus_first()

    def _focus_first(self) -> None:
        if not self.isVisible():
            return
        for action in self.actions():
            if not isinstance(action, QWidgetAction):
                continue
            widget = action.defaultWidget()
            if isinstance(widget, MenuEntry) and widget.isEnabled():
                widget.setFocus(Qt.FocusReason.OtherFocusReason)
                return


def _theme() -> str:
    app = QApplication.instance()
    name = app.property("dbx_theme") if app is not None else None
    return name if isinstance(name, str) else design.DEFAULT_THEME


def _point_size(font: QFont) -> float:
    size = font.pointSizeF()
    return size if size > 0 else 8.0


class MenuEntry(QWidget):
    """Riga di menu con icona, titolo, descrizione e scorciatoia."""

    def __init__(
        self,
        action,
        description: str,
        parent: QWidget | None = None,
        submenu: QMenu | None = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.description = str(description or "")
        self.submenu = submenu
        self._hover = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(ENTRY_MIN_WIDTH)
        self.setFixedHeight(ENTRY_HEIGHT)
        self.setAccessibleName(action.text().replace("&", ""))
        self.setAccessibleDescription(self.description)
        self._sync()

    # ------------------------------------------------------------------ stato
    def _sync(self) -> None:
        try:
            self.setEnabled(self.action.isEnabled())
            self.setAccessibleName(self.action.text().replace("&", ""))
            self.setToolTip(self.action.toolTip())
        except RuntimeError:
            return
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - API Qt
        return QSize(ENTRY_MIN_WIDTH, ENTRY_HEIGHT)

    def enterEvent(self, _event) -> None:  # noqa: D102 - API Qt
        self._hover = True
        if self.isEnabled():
            self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.update()

    def leaveEvent(self, _event) -> None:  # noqa: D102 - API Qt
        self._hover = False
        self.update()

    # ------------------------------------------------------------------ mouse
    def mouseReleaseEvent(self, event) -> None:  # noqa: D102 - API Qt
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.action.isEnabled():
            return
        if self.submenu is not None:
            self._open_submenu()
            return
        self._close_menu()
        self.action.trigger()

    def _open_submenu(self) -> None:
        if self.submenu is None or not self.isEnabled():
            return
        if not self.submenu.isVisible():
            self.submenu.popup(self.mapToGlobal(QPoint(self.width() - 4, 0)))

    def _close_current(self) -> None:
        try:
            window = self.window()
        except RuntimeError:
            return
        if isinstance(window, QMenu):
            window.close()

    def _close_menu(self) -> None:
        try:
            window = self.window()
        except RuntimeError:
            return
        while isinstance(window, QMenu):
            parent = window.parentWidget()
            window.close()
            window = parent if isinstance(parent, QMenu) else None

    # --------------------------------------------------------------- tastiera
    def keyPressEvent(self, event) -> None:  # noqa: D102 - API Qt
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self.action.isEnabled():
                if self.submenu is not None:
                    self._open_submenu()
                else:
                    self._close_menu()
                    self.action.trigger()
            return
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Left):
            self._close_current()
            return
        if key == Qt.Key.Key_Right and self.submenu is not None:
            self._open_submenu()
            return
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self._focus_sibling(1 if key == Qt.Key.Key_Down else -1)
            return
        super().keyPressEvent(event)

    def _focus_sibling(self, delta: int) -> None:
        menu = self.window()
        if not isinstance(menu, QMenu):
            return
        entries = [
            action.defaultWidget()
            for action in menu.actions()
            if isinstance(action, QWidgetAction) and isinstance(action.defaultWidget(), MenuEntry)
        ]
        if len(entries) < 2 or self not in entries:
            return
        index = (entries.index(self) + delta) % len(entries)
        entries[index].setFocus(Qt.FocusReason.OtherFocusReason)
        entries[index].update()
        self.update()

    # ----------------------------------------------------------------- disegno
    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        palette = design.palette(_theme())
        selected = self._hover or self.hasFocus()
        enabled = self.action.isEnabled()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(3, 2, -3, -2)
        if selected and enabled:
            gradient = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.topRight()))
            gradient.setColorAt(0.0, QColor(palette["menu_item_selected"]))
            gradient.setColorAt(1.0, QColor(palette["menu_item_selected_alt"]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(rect, 7, 7)

        title_color = QColor(
            palette["menu_item_selected_text"] if selected and enabled
            else (palette["menu_item_text"] if enabled else palette["disabled"])
        )
        description_color = QColor(
            palette["menu_item_desc_selected"] if selected and enabled
            else (palette["menu_item_desc"] if enabled else palette["disabled"])
        )
        title = self.action.text().replace("&", "")
        description = self.description
        shortcut = self.action.shortcut().toString()

        icon_rect = QRect(rect.left() + 9, rect.top() + (rect.height() - 24) // 2, 24, 24)
        if not self.action.icon().isNull():
            mode = QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled
            painter.drawPixmap(icon_rect, self.action.icon().pixmap(24, 24, mode))

        text_left = rect.left() + 46
        right_reserve = 112 if shortcut else 26
        width = max(80, rect.right() - text_left - right_reserve)

        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSizeF(max(8.0, _point_size(self.font()) + 0.5))
        title_metrics = QFontMetrics(title_font)
        painter.setFont(title_font)
        painter.setPen(QPen(title_color))
        painter.drawText(
            QRect(text_left, rect.top() + 5, width, 19),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            title_metrics.elidedText(title, Qt.TextElideMode.ElideRight, width),
        )

        description_font = QFont(self.font())
        description_font.setPointSizeF(max(7.0, _point_size(self.font()) - 0.8))
        description_metrics = QFontMetrics(description_font)
        painter.setFont(description_font)
        painter.setPen(QPen(description_color))
        painter.drawText(
            QRect(text_left, rect.top() + 25, width, 17),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            description_metrics.elidedText(description, Qt.TextElideMode.ElideRight, width),
        )

        if shortcut:
            shortcut_font = QFont(self.font())
            shortcut_font.setPointSizeF(max(7.0, _point_size(self.font()) - 0.5))
            painter.setFont(shortcut_font)
            painter.setPen(QPen(description_color))
            painter.drawText(
                QRect(rect.right() - 104, rect.top() + 5, 96, 19),
                int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter),
                shortcut,
            )

        if self.action.isCheckable() and self.action.isChecked():
            check = QRect(rect.right() - 20, rect.top() + (rect.height() - 14) // 2, 14, 14)
            painter.setPen(
                QPen(title_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            painter.drawLine(
                check.left() + 2, check.center().y(), check.left() + 6, check.bottom() - 3
            )
            painter.drawLine(
                check.left() + 6, check.bottom() - 3, check.right() - 1, check.top() + 3
            )
        if self.submenu is not None:
            arrow = QRect(rect.right() - 22, rect.center().y() - 6, 12, 12)
            painter.setPen(
                QPen(title_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            painter.drawLine(
                arrow.left() + 3, arrow.top() + 2, arrow.right() - 2, arrow.center().y()
            )
            painter.drawLine(
                arrow.right() - 2, arrow.center().y(), arrow.left() + 3, arrow.bottom() - 2
            )
        painter.end()


def add_entry(menu: QMenu, action, description: str) -> QWidgetAction:
    """Aggiunge una voce icona + descrizione al menu."""
    entry = MenuEntry(action, description)
    wrapper = QWidgetAction(menu)
    wrapper.setDefaultWidget(entry)
    wrapper.setText(action.text())
    wrapper.setIcon(action.icon())
    wrapper.setEnabled(action.isEnabled())
    wrapper.setCheckable(action.isCheckable())
    wrapper.setChecked(action.isChecked())
    wrapper.setData(action.data())

    def sync_wrapper() -> None:
        try:
            wrapper.setText(action.text())
            wrapper.setIcon(action.icon())
            wrapper.setEnabled(action.isEnabled())
            wrapper.setCheckable(action.isCheckable())
            wrapper.setChecked(action.isChecked())
        except RuntimeError:
            return

    menu.addAction(wrapper)
    return wrapper


def add_submenu_entry(parent: QMenu, submenu: QMenu, description: str) -> QWidgetAction:
    """Aggiunge un sottomenu come voce icona + descrizione con freccia."""
    action = submenu.menuAction()
    entry = MenuEntry(action, description, submenu=submenu)
    wrapper = QWidgetAction(parent)
    wrapper.setDefaultWidget(entry)
    wrapper.setText(action.text())
    wrapper.setIcon(action.icon())
    wrapper.setEnabled(action.isEnabled())
    parent.addAction(wrapper)
    return wrapper


def show_menu_at(menu: QMenu, widget: QWidget, point: QPoint) -> None:
    """Apre ``menu`` sotto ``widget`` e porta il focus sulla prima voce."""
    menu.popup(widget.mapToGlobal(point))
    entries = [
        action.defaultWidget()
        for action in menu.actions()
        if isinstance(action, QWidgetAction) and isinstance(action.defaultWidget(), MenuEntry)
    ]
    if entries:
        entries[0].setFocus(Qt.FocusReason.OtherFocusReason)
