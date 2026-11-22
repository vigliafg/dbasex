"""Command Window in stile dBASE: riquadri Command e Command Results (H3)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.expressions import Expression, ExpressionError
from ..runtime.rowset import Rowset, RowsetError


class CommandWindow(QDialog):
    """Finestra non modale con il riquadro dei comandi sopra e i risultati sotto."""

    def __init__(self, project, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.rowset: Rowset | None = None
        self.setWindowTitle(f"Command Window — {project.name}")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setModal(False)
        self.resize(760, 520)
        self._build_ui()
        self._write("dBX — Command Window. Digita HELP per l'elenco dei comandi.")

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        command_frame = self._pane("Command")
        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "espressione (2 + 2, UPPER(\"ciao\"), TODAY()) oppure comando (HELP, TABELLE, USE nome, RECORD)"
        )
        self.input.returnPressed.connect(self.execute)
        command_frame.layout().addWidget(self.input)
        layout.addWidget(command_frame)

        results_frame = self._pane("Command Results")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("font-family: monospace;")
        self.output.setMaximumBlockCount(5000)
        results_frame.layout().addWidget(self.output, 1)
        layout.addWidget(results_frame, 1)

        self.status = QLabel("Pronto")
        self.status.setStyleSheet("color: palette(mid);")
        layout.addWidget(self.status)

    def _pane(self, title: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setObjectName(f"pane_{title.lower().replace(' ', '_')}")
        box = QVBoxLayout(frame)
        box.setContentsMargins(6, 4, 6, 6)
        box.setSpacing(4)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: 600;")
        box.addWidget(heading)
        return frame

    def _write(self, text: str) -> None:
        self.output.appendPlainText(text)

    # -------------------------------------------------------------- comandi
    def execute(self) -> None:
        command = self.input.text().strip()
        self.input.clear()
        if not command:
            return
        self._write(f"> {command}")
        upper = command.upper()
        try:
            if upper == "HELP":
                self._write(
                    "HELP            questo elenco\n"
                    "TABELLE         elenca le tabelle del progetto\n"
                    "USE nome        apre una tabella come contesto\n"
                    "RECORD          mostra il record corrente\n"
                    "CLEAR           svuota i risultati\n"
                    "espressione     valuta un'espressione dBX"
                )
                self.status.setText("Help mostrato")
                return
            if upper == "CLEAR":
                self.output.clear()
                self.status.setText("Risultati cancellati")
                return
            if upper == "TABELLE":
                for name in self.project.names("tables"):
                    self._write(f"  {name}")
                self.status.setText(f"{len(self.project.names('tables'))} tabelle")
                return
            if upper.startswith("USE "):
                name = command[4:].strip()
                table = self.project.table(name)
                if table is None:
                    self._write(f"Tabella sconosciuta: {name}")
                    self.status.setText("Errore")
                    return
                self.rowset = Rowset(self.project.db, table).open()
                self._write(f"Tabella {table.name} aperta — {len(self.rowset)} record")
                self.status.setText(f"Tabella corrente: {table.name}")
                return
            if upper == "RECORD":
                record = self.rowset.current if self.rowset else None
                if record is None:
                    self._write("Nessun record corrente (usa USE nome)")
                    return
                for key, value in record.items():
                    self._write(f"  {key}: {value!r}")
                self.status.setText("Record mostrato")
                return
            record = self.rowset.current if self.rowset else None
            table = self.rowset.table.name if self.rowset else None
            value = Expression(command).evaluate(record or {}, {}, table)
            self._write(repr(value) if not isinstance(value, str) else value)
            self.status.setText("Espressione valutata")
        except (ExpressionError, RowsetError) as exc:
            self._write(f"Errore: {exc}")
            self.status.setText("Errore")

