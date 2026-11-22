"""Table Expert: crea una tabella da un template o da zero (0.4/O1).

La procedura produce un normale :class:`Table`; la creazione fisica e le
migrazioni restano di competenza di ``Project.apply_table``. Il wizard non
duplica il modello e non contiene logica SQL propria.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWizardPage,
    QWidget,
)

from ..core import ddl
from ..core import types as T
from ..core.metadata import Field, Index, MetadataError, Table, new_id, slugify
from ..core.project import Project
from .expert_common import ExpertWizard, FieldEditor


@dataclass(frozen=True)
class TableTemplate:
    key: str
    label: str
    description: str
    fields: tuple[dict[str, Any], ...]
    suggested_indexes: tuple[str, ...] = ()


TEMPLATES: tuple[TableTemplate, ...] = (
    TableTemplate(
        key="vuota",
        label="Vuota",
        description="Parti da zero e aggiungi i campi che ti servono.",
        fields=(),
    ),
    TableTemplate(
        key="contatti",
        label="Contatti",
        description="Rubrica con nome, recapiti e note.",
        fields=(
            {"name": "nome", "type": T.TEXT, "size": 40, "caption": "Nome"},
            {"name": "cognome", "type": T.TEXT, "size": 40, "caption": "Cognome"},
            {"name": "email", "type": T.TEXT, "size": 80, "caption": "Email"},
            {"name": "telefono", "type": T.TEXT, "size": 30, "caption": "Telefono"},
            {"name": "note", "type": T.MEMO, "caption": "Note"},
        ),
        suggested_indexes=("cognome", "email"),
    ),
    TableTemplate(
        key="fatture",
        label="Fatture",
        description="Documenti con numero, data, cliente, importo e stato.",
        fields=(
            {"name": "numero", "type": T.TEXT, "size": 20, "caption": "Numero"},
            {"name": "data", "type": T.DATE, "caption": "Data"},
            {"name": "cliente", "type": T.TEXT, "size": 60, "caption": "Cliente"},
            {"name": "importo", "type": T.DECIMAL, "size": 12, "fmt": ".2f", "caption": "Importo"},
            {"name": "pagato", "type": T.BOOLEAN, "caption": "Pagato"},
        ),
        suggested_indexes=("numero", "cliente"),
    ),
    TableTemplate(
        key="inventario",
        label="Inventario",
        description="Articoli con codice, quantità, prezzo e fornitore.",
        fields=(
            {"name": "codice", "type": T.TEXT, "size": 20, "caption": "Codice"},
            {"name": "descrizione", "type": T.TEXT, "size": 60, "caption": "Descrizione"},
            {"name": "quantita", "type": T.INTEGER, "caption": "Quantità"},
            {"name": "prezzo", "type": T.DECIMAL, "size": 10, "fmt": ".2f", "caption": "Prezzo"},
            {"name": "fornitore", "type": T.TEXT, "size": 60, "caption": "Fornitore"},
        ),
        suggested_indexes=("codice", "fornitore"),
    ),
    TableTemplate(
        key="attivita",
        label="Attività",
        description="Elenco di cose da fare con data, priorità e stato.",
        fields=(
            {"name": "titolo", "type": T.TEXT, "size": 60, "caption": "Titolo"},
            {"name": "data", "type": T.DATE, "caption": "Data"},
            {"name": "priorita", "type": T.INTEGER, "caption": "Priorità"},
            {"name": "fatto", "type": T.BOOLEAN, "caption": "Fatto"},
            {"name": "note", "type": T.MEMO, "caption": "Note"},
        ),
        suggested_indexes=("data", "fatto"),
    ),
)

TEMPLATES_BY_KEY = {template.key: template for template in TEMPLATES}


def template_fields(key: str) -> list[Field]:
    """Crea campi nuovi (con id nuovi) dai template, senza condividerne gli id."""
    template = TEMPLATES_BY_KEY.get(key)
    if template is None:
        return []
    return [
        Field(
            id=new_id(),
            name=str(spec["name"]),
            type=str(spec.get("type", T.TEXT)),
            size=int(spec.get("size", 0) or 0),
            caption=str(spec.get("caption", "")),
            fmt=str(spec.get("fmt", "")),
            pk=bool(spec.get("pk", False)),
        )
        for spec in template.fields
    ]


class TableExpert(ExpertWizard):
    """Procedura guidata in quattro passi per creare una tabella."""

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        suggested_name: str = "nuova_tabella",
    ) -> None:
        self.project = project
        self.suggested_name = suggested_name or "nuova_tabella"
        self._template_key = "vuota"
        super().__init__(parent, "Table Expert")
        self.set_finish_text("Crea tabella")
        self.resize(760, 560)
        self._build_pages()
        self._apply_template(self._template_key)

    # ------------------------------------------------------------------ pagine
    def _build_pages(self) -> None:
        self.addPage(self._page_intro())
        self.addPage(self._page_fields())
        self.addPage(self._page_indexes())
        self.addPage(self._page_summary())

    def _page_intro(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Table Expert")
        page.setSubTitle(
            "Scegli un template o parti da zero. Potrai modificare campi e indici "
            "anche dopo, nel Table Builder."
        )
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.suggested_name)
        self.name_edit.setPlaceholderText("es. clienti")
        self.name_edit.setAccessibleName("Nome della tabella")
        form.addRow("Nome", self.name_edit)
        self.caption_edit = QLineEdit()
        self.caption_edit.setPlaceholderText("Descrizione mostrata nel Navigator")
        form.addRow("Didascalia", self.caption_edit)
        self.template_combo = QComboBox()
        for template in TEMPLATES:
            self.template_combo.addItem(template.label, template.key)
        form.addRow("Template", self.template_combo)
        layout.addLayout(form)

        self.template_description = QLabel("")
        self.template_description.setWordWrap(True)
        self.template_description.setObjectName("nav_hint")
        layout.addWidget(self.template_description)

        note = QLabel(
            "Il template compila i campi; potrai aggiungerne, toglierne o "
            "rinominarli nel passo successivo."
        )
        note.setWordWrap(True)
        note.setObjectName("nav_hint")
        layout.addWidget(note)
        layout.addStretch(1)
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        return page

    def _page_fields(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Campi")
        page.setSubTitle("Definisci nome, tipo, lunghezza e didascalia di ogni campo.")
        layout = QVBoxLayout(page)
        self.field_editor = FieldEditor(page)
        layout.addWidget(self.field_editor, 1)
        return page

    def _page_indexes(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Indici")
        page.setSubTitle("Scegli i campi da indicizzare. Gli indici restano modificabili nel Table Builder.")
        layout = QVBoxLayout(page)
        self.index_table = QTableWidget(0, 3)
        self.index_table.setHorizontalHeaderLabels(["Campo", "Indice", "Unico"])
        self.index_table.verticalHeader().setVisible(False)
        self.index_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.index_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.index_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.index_table, 1)
        hint = QLabel(
            "Un indice accelera ricerche e ordinamenti. «Unico» impedisce valori "
            "duplicati: usalo solo se il dato è davvero univoco."
        )
        hint.setWordWrap(True)
        hint.setObjectName("nav_hint")
        layout.addWidget(hint)
        return page

    def _page_summary(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Riepilogo")
        page.setSubTitle("Controlla la struttura e il DDL prima di creare la tabella.")
        layout = QVBoxLayout(page)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.summary_view = QPlainTextEdit()
        self.summary_view.setReadOnly(True)
        self.summary_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.summary_view, 1)
        return page

    def initializePage(self, page_id: int) -> None:  # noqa: N802 - API Qt
        super().initializePage(page_id)
        page = self.page(page_id)
        if page is self.page(2):
            self._refresh_indexes()
        elif page is self.page(3):
            self._refresh_summary()

    def validateCurrentPage(self) -> bool:  # noqa: N802 - API Qt
        if self.currentPage() in (self.page(1), self.page(2), self.page(3)):
            try:
                self.build_table()
            except (MetadataError, ValueError) as exc:
                QMessageBox.warning(self, "Tabella non valida", str(exc))
                return False
        return super().validateCurrentPage()

    # ------------------------------------------------------------------ dati
    def _on_template_changed(self, _index: int) -> None:
        key = str(self.template_combo.currentData() or "vuota")
        self._apply_template(key)

    def _apply_template(self, key: str) -> None:
        template = TEMPLATES_BY_KEY.get(key)
        if template is None:
            return
        self._template_key = key
        self.template_description.setText(template.description)
        if hasattr(self, "field_editor"):
            self.field_editor.set_fields(template_fields(key))
            if hasattr(self, "index_table"):
                self._refresh_indexes()

    def _refresh_indexes(self) -> None:
        if not hasattr(self, "index_table"):
            return
        previous: dict[str, tuple[bool, bool]] = {}
        for row in range(self.index_table.rowCount()):
            name_item = self.index_table.item(row, 0)
            check_item = self.index_table.item(row, 1)
            unique_item = self.index_table.item(row, 2)
            if name_item is not None:
                previous[name_item.text().lower()] = (
                    check_item.checkState() == Qt.CheckState.Checked if check_item else False,
                    unique_item.checkState() == Qt.CheckState.Checked if unique_item else False,
                )
        suggested = set(
            TEMPLATES_BY_KEY.get(self._template_key, TEMPLATES[0]).suggested_indexes
        )
        fields = self.field_editor.fields()
        self.index_table.setRowCount(0)
        for field in fields:
            row = self.index_table.rowCount()
            self.index_table.insertRow(row)
            name_item = QTableWidgetItem(field.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.index_table.setItem(row, 0, name_item)
            check_item = QTableWidgetItem("")
            check_item.setFlags(
                (check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            checked = previous.get(field.name.lower(), (field.name in suggested, False))[0]
            check_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.index_table.setItem(row, 1, check_item)
            unique_item = QTableWidgetItem("")
            unique_item.setFlags(
                (unique_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            unique = previous.get(field.name.lower(), (False, False))[1]
            unique_item.setCheckState(Qt.CheckState.Checked if unique else Qt.CheckState.Unchecked)
            self.index_table.setItem(row, 2, unique_item)

    def _selected_indexes(self, fields: list[Field]) -> list[Index]:
        if not hasattr(self, "index_table"):
            return []
        names = {field.name.lower() for field in fields}
        indexes: list[Index] = []
        for row in range(self.index_table.rowCount()):
            name_item = self.index_table.item(row, 0)
            check_item = self.index_table.item(row, 1)
            unique_item = self.index_table.item(row, 2)
            if name_item is None or check_item is None:
                continue
            name = name_item.text()
            if name.lower() not in names:
                continue
            if check_item.checkState() != Qt.CheckState.Checked:
                continue
            indexes.append(
                Index(
                    fields=[name],
                    unique=(
                        unique_item is not None
                        and unique_item.checkState() == Qt.CheckState.Checked
                    ),
                )
            )
        return indexes

    def build_table(self) -> Table:
        """Costruisce e valida la tabella; solleva ``MetadataError`` se invalida."""
        name = slugify(self.name_edit.text().strip() or self.suggested_name)
        caption = self.caption_edit.text().strip() or name
        fields = self.field_editor.fields()
        table = Table(
            name=name,
            caption=caption,
            fields=fields,
            indexes=self._selected_indexes(fields),
        )
        table.validate()
        return table

    # ------------------------------------------------------------------ extra
    def _refresh_summary(self) -> None:
        try:
            table = self.build_table()
        except (MetadataError, ValueError) as exc:
            self.summary_label.setText("Struttura non valida")
            self.summary_view.setPlainText(f"-- Errore:\n{exc}")
            return
        old = self.project.table(table.name)
        self.summary_label.setText(
            f"{table.display_name()} · {len(table.fields)} campi · "
            f"{len(table.indexes)} indici"
            + (" · sostituirà una tabella esistente" if old is not None else "")
        )
        try:
            plan = ddl.plan_migration(old, table)
        except (MetadataError, ValueError) as exc:
            self.summary_view.setPlainText(f"-- Errore:\n{exc}")
            return
        self.summary_view.setPlainText(plan.sql or "-- Nessuna modifica")

    def help_text(self) -> str:
        return (
            "1. Scegli nome, didascalia e template.\n"
            "2. Controlla o modifica i campi.\n"
            "3. Scegli gli indici.\n"
            "4. Verifica il DDL e premi Crea tabella.\n\n"
            "La tabella creata è una normale tabella dBX: potrai modificarla "
            "in seguito con Struttura… o con il Database Designer."
        )


__all__ = ["TableExpert", "TableTemplate", "TEMPLATES", "template_fields"]
