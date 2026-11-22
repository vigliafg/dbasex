"""Command Window in stile dBASE: riquadri Command e Command Results (H3)."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.expressions import Expression, ExpressionError
from ..runtime.rowset import Rowset, RowsetError
from . import design

HELP_TEXT = (
    "HELP            questo elenco\n"
    "TABELLE         elenca le tabelle del progetto\n"
    "USE nome        apre una tabella come contesto\n"
    "USE             chiude la tabella corrente\n"
    "RECORD          mostra il record corrente\n"
    "CLEAR           svuota i risultati\n"
    "espressione     valuta un'espressione dBX"
)


class CommandWindow(QWidget):
    """Finestra documento con il riquadro dei comandi sopra e i risultati sotto."""

    def __init__(self, project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("command_window")
        self.project = project
        self.rowset: Rowset | None = None
        self._history: list[str] = []
        self._history_index = 0
        self.setWindowTitle(f"Command Window — {project.name}")
        self.resize(760, 520)
        self._build_ui()
        self.input.installEventFilter(self)
        self._write("dBX — Command Window. Digita HELP per l'elenco dei comandi.")

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        command_frame, command_layout = self._pane("Command", "command_pane")
        self.input = QLineEdit()
        self.input.setAccessibleName("Comando")
        self.input.setPlaceholderText(
            "espressione (2 + 2, UPPER(\"ciao\"), TODAY()) oppure comando (HELP, TABELLE, USE nome, RECORD)"
        )
        self.input.setToolTip("↑/↓ richiamano i comandi precedenti")
        self.input.returnPressed.connect(self.execute)
        command_layout.addWidget(self.input)
        layout.addWidget(command_frame)

        results_frame, results_layout = self._pane("Command Results", "results_pane")
        self.output = QPlainTextEdit()
        self.output.setAccessibleName("Risultati dei comandi")
        self.output.setReadOnly(True)
        self.output.setFont(QFont(design.CODE_FONT.family, int(design.CODE_FONT.size_pt)))
        self.output.setMaximumBlockCount(5000)
        results_layout.addWidget(self.output, 1)
        layout.addWidget(results_frame, 1)

        self.status = QLabel("Pronto")
        self.status.setObjectName("command_status")
        self.status.setProperty("state", "ok")
        layout.addWidget(self.status)

    def _pane(self, title: str, object_name: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.NoFrame)
        frame.setObjectName(object_name)
        box = QVBoxLayout(frame)
        box.setContentsMargins(1, 1, 1, 1)
        box.setSpacing(1)
        heading = QLabel(title)
        heading.setObjectName("pane_title")
        box.addWidget(heading)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(6, 6, 6, 6)
        body_layout.setSpacing(4)
        box.addWidget(body, 1)
        return frame, body_layout

    def _write(self, text: str) -> None:
        self.output.appendPlainText(text)

    def _set_status(self, text: str, *, error: bool = False) -> None:
        self.status.setText(text)
        self.status.setProperty("state", "error" if error else "ok")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    # -------------------------------------------------------------- cronologia
    def eventFilter(self, obj, event) -> bool:  # noqa: D102 - API Qt
        if obj is self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._history_previous()
                return True
            if event.key() == Qt.Key.Key_Down:
                self._history_next()
                return True
        return super().eventFilter(obj, event)

    def _remember(self, command: str) -> None:
        if not self._history or self._history[-1] != command:
            self._history.append(command)
        self._history_index = len(self._history)

    def _history_previous(self) -> None:
        if not self._history:
            return
        self._history_index = max(0, self._history_index - 1)
        self.input.setText(self._history[self._history_index])
        self.input.setCursorPosition(len(self.input.text()))

    def _history_next(self) -> None:
        if not self._history:
            return
        self._history_index = min(len(self._history), self._history_index + 1)
        text = "" if self._history_index >= len(self._history) else self._history[self._history_index]
        self.input.setText(text)
        self.input.setCursorPosition(len(text))

    # -------------------------------------------------------------- comandi
    def execute(self) -> None:
        command = self.input.text().strip()
        self.input.clear()
        if not command:
            return
        self._remember(command)
        self._write(f"> {command}")
        upper = command.upper()
        try:
            if upper == "HELP":
                self._write(HELP_TEXT)
                self._set_status("Help mostrato")
                return
            if upper == "CLEAR":
                self.output.clear()
                self._set_status("Risultati cancellati")
                return
            if upper == "TABELLE":
                names = self.project.names("tables")
                for name in names:
                    self._write(f"  {name}")
                self._set_status(f"{len(names)} tabelle")
                return
            if upper == "USE":
                self.rowset = None
                self._write("Nessuna tabella corrente")
                self._set_status("Tabella chiusa")
                return
            if upper.startswith("USE "):
                name = command[4:].strip()
                table = self.project.table(name)
                if table is None:
                    self._write(f"Tabella sconosciuta: {name}")
                    self._set_status("Errore: tabella sconosciuta", error=True)
                    return
                self.rowset = Rowset(self.project.db, table).open()
                self._write(f"Tabella {table.name} aperta — {len(self.rowset)} record")
                self._set_status(f"Tabella corrente: {table.name}")
                return
            if upper == "RECORD":
                record = self.rowset.current if self.rowset else None
                if record is None:
                    self._write("Nessun record corrente (usa USE nome)")
                    self._set_status("Nessun record corrente", error=True)
                    return
                for key, value in record.items():
                    self._write(f"  {key}: {value!r}")
                self._set_status("Record mostrato")
                return
            record = self.rowset.current if self.rowset else None
            table = self.rowset.table.name if self.rowset else None
            value = Expression(command).evaluate(record or {}, {}, table)
            self._write(repr(value) if not isinstance(value, str) else value)
            self._set_status("Espressione valutata")
        except (ExpressionError, RowsetError) as exc:
            self._write(f"Errore: {exc}")
            self._set_status(f"Errore: {exc}", error=True)
