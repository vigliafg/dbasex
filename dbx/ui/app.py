"""Bootstrap Qt: applicazione, icona, splash e gestione errori (A2, A5)."""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from .. import APP_NAME, APP_TITLE, ORGANIZATION, __version__
from ..config import config_dir
from .theme import apply_theme


def app_icon(size: int = 128) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#2f6f4f"))
    painter = QPainter(pixmap)
    try:
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(int(size * 0.28))
        painter.setFont(font)
        painter.drawText(pixmap.rect(), int(Qt.AlignmentFlag.AlignCenter), "dBX")
    finally:
        painter.end()
    return QIcon(pixmap)


def splash() -> QSplashScreen:
    pixmap = QPixmap(460, 220)
    pixmap.fill(QColor("#2f6f4f"))
    painter = QPainter(pixmap)
    try:
        painter.setPen(QColor("#ffffff"))
        font = QFont()
        font.setBold(True)
        font.setPointSize(34)
        painter.setFont(font)
        painter.drawText(24, 96, APP_NAME)
        font.setPointSize(11)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(24, 132, "Personal database · SQLite · ispirato a dBASE 5.5")
        painter.drawText(24, 186, f"versione {__version__}")
    finally:
        painter.end()
    screen = QSplashScreen(pixmap)
    screen.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    return screen


def install_exception_hook() -> None:
    log_path = config_dir() / "errori.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        try:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n{detail}")
        except OSError:
            pass
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("dBX — errore imprevisto")
        box.setText(str(exc_value) or "Errore imprevisto")
        box.setDetailedText(detail)
        box.setInformativeText(f"Dettagli salvati in {log_path}" if log_path.exists() else "Impossibile scrivere il log")
        box.exec()

    sys.excepthook = hook


def create_application(argv: list[str] | None = None, theme: str = "light") -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_TITLE)
    app.setOrganizationName(ORGANIZATION)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    apply_theme(app, theme)
    install_exception_hook()
    return app


def log_path() -> Path:
    return config_dir() / "errori.log"
