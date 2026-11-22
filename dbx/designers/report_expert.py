"""Report Expert: crea un report a bande guidato e lo apre nel designer (0.4/O2).

Il wizard produce un normale :class:`ReportSpec` con le bande esistenti; non
introduce un formato report parallelo e non contiene un motore di stampa
proprio.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QRadioButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWizardPage,
    QWidget,
)

from ..core.metadata import Table, slugify
from ..core.project import Project
from ..core.query_engine import QueryError, query_table
from ..runtime.report_engine import BAND_NAMES, Control, ReportSpec
from ..ui import icons
from .expert_common import ExpertWizard, FieldTransfer

LAYOUTS = (
    ("tabular", "Tabellare", "Un record per riga, campi affiancati."),
    ("columnar", "Colonnare", "Un record per blocco, campi in colonna."),
    ("summary", "Riepilogo", "Dettaglio tabellare con intestazione e totale di gruppo."),
)


class ReportExpert(ExpertWizard):
    """Procedura guidata in cinque passi per creare un report."""

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        suggested_name: str = "report",
    ) -> None:
        self.project = project
        self.suggested_name = suggested_name or "report"
        super().__init__(parent, "Report Expert")
        self.set_finish_text("Crea report")
        self.resize(820, 640)
        self._build_pages()
        self._refresh_fields()
        self._refresh_group_fields()
        self._refresh_summary()

    # ------------------------------------------------------------------ pagine
    def _build_pages(self) -> None:
        self._source_page = self._page_source()
        self._layout_page = self._page_layout()
        self._fields_page = self._page_fields()
        self._group_page = self._page_group()
        self._style_page = self._page_style()
        for page in (
            self._source_page,
            self._layout_page,
            self._fields_page,
            self._group_page,
            self._style_page,
        ):
            self.addPage(page)

    def _page_source(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Report Expert")
        page.setSubTitle("Scegli nome, titolo e sorgente del report.")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.suggested_name)
        self.name_edit.setPlaceholderText("es. report_clienti")
        form.addRow("Nome", self.name_edit)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Titolo stampato nel report")
        form.addRow("Titolo", self.title_edit)
        self.source_combo = QComboBox()
        for name in self.project.names("tables"):
            self.source_combo.addItem(f"Tabella · {name}", ("table", name))
        for name in self.project.names("queries"):
            self.source_combo.addItem(f"Query · {name}", ("query", name))
        form.addRow("Sorgente", self.source_combo)
        layout.addLayout(form)
        hint = QLabel(
            "La sorgente può essere una tabella o una query in sola lettura. "
            "Il report usa le colonne della sorgente come campi del dettaglio."
        )
        hint.setWordWrap(True)
        hint.setObjectName("nav_hint")
        layout.addWidget(hint)
        layout.addStretch(1)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        return page

    def _page_layout(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Layout")
        page.setSubTitle("Scegli la disposizione del dettaglio.")
        layout = QVBoxLayout(page)
        self.layout_group = QButtonGroup(page)
        self.layout_radios: dict[str, QRadioButton] = {}
        for index, (key, label, description) in enumerate(LAYOUTS):
            radio = QRadioButton(label)
            radio.setChecked(index == 0)
            radio.toggled.connect(self._update_layout_description)
            self.layout_group.addButton(radio)
            self.layout_radios[key] = radio
            layout.addWidget(radio)
            detail = QLabel(description)
            detail.setObjectName("nav_hint")
            detail.setContentsMargins(22, 0, 0, 8)
            layout.addWidget(detail)
        layout.addStretch(1)
        self.layout_description = QLabel("")
        self.layout_description.setWordWrap(True)
        self.layout_description.setObjectName("nav_hint")
        layout.addWidget(self.layout_description)
        self._update_layout_description()
        return page

    def _page_fields(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Campi")
        page.setSubTitle("Sposta i campi dalla sorgente al report, nell'ordine desiderato.")
        layout = QVBoxLayout(page)
        self.field_transfer = FieldTransfer(page)
        layout.addWidget(self.field_transfer, 1)
        return page

    def _page_group(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Gruppi e ordinamento")
        page.setSubTitle("Un gruppo facoltativo e i criteri di ordinamento.")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.group_combo = QComboBox()
        form.addRow("Raggruppa per", self.group_combo)
        self.group_label_edit = QLineEdit()
        self.group_label_edit.setPlaceholderText("Etichetta del gruppo")
        form.addRow("Etichetta gruppo", self.group_label_edit)
        layout.addLayout(form)
        self.sort_table = QTableWidget(0, 2)
        self.sort_table.setHorizontalHeaderLabels(["Campo", "Direzione"])
        self.sort_table.verticalHeader().setVisible(False)
        self.sort_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.sort_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.sort_table, 1)
        bar = QVBoxLayout()
        bar.setSpacing(2)
        bar.addWidget(
            icons.make_button(
                "Aggiungi ordinamento", "nuovo", self.add_sort, page, "Aggiunge un criterio"
            )
        )
        bar.addWidget(
            icons.make_button(
                "Rimuovi ordinamento",
                "elimina",
                self.remove_sort,
                page,
                "Rimuove il criterio selezionato",
            )
        )
        layout.addLayout(bar)
        return page

    def _page_style(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Stile e riepilogo")
        page.setSubTitle("Orientamento, font e anteprima della struttura.")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Verticale", "portrait")
        self.orientation_combo.addItem("Orizzontale", "landscape")
        form.addRow("Orientamento", self.orientation_combo)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 18)
        self.font_spin.setValue(10)
        form.addRow("Corpo del testo", self.font_spin)
        self.page_numbers_check = QCheckBox("Mostra numero di pagina")
        self.page_numbers_check.setChecked(True)
        form.addRow("", self.page_numbers_check)
        layout.addLayout(form)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        self.summary_view = QPlainTextEdit()
        self.summary_view.setReadOnly(True)
        layout.addWidget(self.summary_view, 1)
        return page

    def initializePage(self, page_id: int) -> None:  # noqa: N802 - API Qt
        super().initializePage(page_id)
        page = self.page(page_id)
        if page is self._fields_page:
            self._refresh_fields()
        elif page is self._group_page:
            self._refresh_group_fields()
        elif page is self._style_page:
            self._refresh_summary()

    def validateCurrentPage(self) -> bool:  # noqa: N802 - API Qt
        if self.currentPage() in (self._fields_page, self._group_page, self._style_page):
            if (
                self.currentPage() in (self._group_page, self._style_page)
                and self.layout_key() == "summary"
                and not self.group_field()
            ):
                QMessageBox.warning(
                    self,
                    "Report non valido",
                    "Il layout Riepilogo richiede un campo di raggruppamento.",
                )
                return False
            try:
                self.build_spec()
            except (QueryError, ValueError) as exc:
                QMessageBox.warning(self, "Report non valido", str(exc))
                return False
        return super().validateCurrentPage()

    # ------------------------------------------------------------------ dati
    def _on_source_changed(self, _index: int) -> None:
        if hasattr(self, "field_transfer"):
            self.field_transfer.set_available(self._available_fields(), selected=[])
        self._refresh_fields()
        self._refresh_group_fields()

    def source_kind_name(self) -> tuple[str, str]:
        data = self.source_combo.currentData()
        if isinstance(data, (tuple, list)) and len(data) == 2:
            return str(data[0]), str(data[1])
        return "table", ""

    def source_table(self) -> Table | None:
        kind, name = self.source_kind_name()
        if not name:
            return None
        if kind == "query":
            try:
                return query_table(self.project, name)
            except QueryError:
                return None
        return self.project.table(name)

    def source_fields(self) -> list[str]:
        table = self.source_table()
        return table.field_names if table is not None else []

    def _available_fields(self) -> list[tuple[str, str]]:
        table = self.source_table()
        if table is None:
            return []
        return [
            (field.name, f"{field.display_name()} ({field.type})")
            for field in table.fields
        ]

    def _refresh_fields(self) -> None:
        if not hasattr(self, "field_transfer"):
            return
        available = self._available_fields()
        selected = self.field_transfer.selected_keys()
        if not selected:
            selected = [key for key, _label in available]
        self.field_transfer.set_available(available, selected=selected)

    def _refresh_group_fields(self) -> None:
        if not hasattr(self, "group_combo"):
            return
        current = str(self.group_combo.currentData() or "")
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        self.group_combo.addItem("(nessuno)", "")
        table = self.source_table()
        if table is not None:
            for field in table.fields:
                self.group_combo.addItem(field.display_name(), field.name)
        self.group_combo.setCurrentIndex(max(0, self.group_combo.findData(current)))
        self.group_combo.blockSignals(False)
        for row in range(self.sort_table.rowCount()):
            combo = self.sort_table.cellWidget(row, 0)
            if not isinstance(combo, QComboBox):
                continue
            value = str(combo.currentData() or "")
            combo.blockSignals(True)
            combo.clear()
            if table is not None:
                for field in table.fields:
                    combo.addItem(field.display_name(), field.name)
            combo.setCurrentIndex(max(0, combo.findData(value)))
            combo.blockSignals(False)

    def layout_key(self) -> str:
        for key, radio in self.layout_radios.items():
            if radio.isChecked():
                return key
        return "tabular"

    def _update_layout_description(self) -> None:
        key = self.layout_key()
        description = next((item[2] for item in LAYOUTS if item[0] == key), "")
        if hasattr(self, "layout_description"):
            self.layout_description.setText(description)

    def group_field(self) -> str:
        return str(self.group_combo.currentData() or "")

    def group_label(self) -> str:
        return self.group_label_edit.text().strip()

    def add_sort(self) -> None:
        row = self.sort_table.rowCount()
        self.sort_table.insertRow(row)
        combo = QComboBox()
        table = self.source_table()
        if table is not None:
            for field in table.fields:
                combo.addItem(field.display_name(), field.name)
        self.sort_table.setCellWidget(row, 0, combo)
        direction = QComboBox()
        direction.addItem("Crescente", "asc")
        direction.addItem("Decrescente", "desc")
        self.sort_table.setCellWidget(row, 1, direction)

    def remove_sort(self) -> None:
        row = self.sort_table.currentRow()
        if row >= 0:
            self.sort_table.removeRow(row)

    def sorts(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for row in range(self.sort_table.rowCount()):
            combo = self.sort_table.cellWidget(row, 0)
            direction = self.sort_table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox):
                continue
            field = str(combo.currentData() or "")
            if not field:
                continue
            result.append(
                {
                    "field": field,
                    "direction": (
                        str(direction.currentData())
                        if isinstance(direction, QComboBox)
                        else "asc"
                    ),
                }
            )
        return result

    # ------------------------------------------------------------------ output
    def build_spec(self) -> ReportSpec:
        kind, source_name = self.source_kind_name()
        if not source_name:
            raise ValueError("Scegli una tabella o una query")
        table = self.source_table()
        if table is None:
            raise ValueError(f"Sorgente non disponibile: {source_name}")
        fields = [
            key
            for key in self.field_transfer.selected_keys()
            if table.field(key) is not None
        ]
        if not fields:
            raise ValueError("Il report non contiene campi")
        name = slugify(self.name_edit.text().strip() or self.suggested_name)
        title = self.title_edit.text().strip() or f"Report {table.display_name()}"
        if kind == "query":
            spec = ReportSpec.create_for_query(name, source_name, fields, title)
        else:
            spec = ReportSpec.create(name, source_name, title)
        spec.title = title
        spec.orientation = str(self.orientation_combo.currentData() or "portrait")
        spec.bands = {band: [] for band in BAND_NAMES}
        spec.band_order = list(BAND_NAMES)
        spec.band_heights = {
            "title": 14,
            "page_header": 8,
            "detail": 8,
            "group_header": 8,
            "group_footer": 8,
            "page_footer": 8,
        }
        spec.band_visible = {band: True for band in BAND_NAMES}
        spec.band_visible["summary"] = False
        group = self.group_field()
        if group:
            label = self.group_label() or (table.field(group).display_name() if table.field(group) else group)
            spec.groups = [{"field": group, "label": label}]
            spec.group_by = group
            spec.group_label = label
            spec.band_visible["group_header"] = True
            spec.band_visible["group_footer"] = True
        else:
            spec.groups = []
            spec.group_by = ""
            spec.group_label = ""
            spec.band_visible["group_header"] = False
            spec.band_visible["group_footer"] = False
        sorts = self.sorts()
        if group and not any(item["field"] == group for item in sorts):
            sorts.insert(0, {"field": group, "direction": "asc"})
        spec.sort_fields = sorts
        self._fill_bands(spec, table, fields, group)
        errors = spec.validate()
        if errors:
            raise ValueError("\n".join(errors))
        return spec

    def _fill_bands(self, spec: ReportSpec, table: Table, fields: list[str], group: str) -> None:
        width = 250.0 if spec.orientation == "landscape" else 170.0
        font_size = int(self.font_spin.value())
        layout = self.layout_key()

        spec.bands["title"].append(
            Control(
                id="titolo",
                kind="text",
                x=0,
                y=0,
                w=width,
                h=12,
                text=spec.title,
                font_size=16,
                bold=True,
            )
        )
        if layout == "columnar":
            spec.bands["page_header"].append(
                Control(
                    id="intestazione",
                    kind="text",
                    x=0,
                    y=0,
                    w=width,
                    h=6,
                    text="dBX — report",
                    font_size=max(6, font_size - 1),
                    color="#666666",
                )
            )
        if layout == "columnar":
            y = 0.0
            for name in fields:
                field = table.field(name)
                spec.bands["detail"].append(
                    Control(
                        id=f"etichetta_{name}",
                        kind="text",
                        x=0,
                        y=y,
                        w=42,
                        h=6,
                        text=field.display_name() if field else name,
                        font_size=max(6, font_size - 1),
                        bold=True,
                    )
                )
                spec.bands["detail"].append(
                    Control(
                        id=f"campo_{name}",
                        kind="field",
                        x=44,
                        y=y,
                        w=width - 44,
                        h=6,
                        expr=name,
                        font_size=font_size,
                        border=False,
                    )
                )
                y += 7
            spec.band_heights["detail"] = max(8, y)
        else:
            column_width = width / max(1, len(fields))
            for index, name in enumerate(fields):
                field = table.field(name)
                x = index * column_width
                actual_width = width - x if index == len(fields) - 1 else column_width
                spec.bands["page_header"].append(
                    Control(
                        id=f"intestazione_{name}",
                        kind="text",
                        x=x,
                        y=0,
                        w=actual_width,
                        h=6,
                        text=field.display_name() if field else name,
                        font_size=max(6, font_size - 1),
                        bold=True,
                    )
                )
                spec.bands["detail"].append(
                    Control(
                        id=f"campo_{name}",
                        kind="field",
                        x=x,
                        y=0,
                        w=actual_width,
                        h=6,
                        expr=name,
                        font_size=font_size,
                        border=False,
                    )
                )
        if group:
            label = spec.group_label or group
            spec.bands["group_header"].append(
                Control(
                    id="intestazione_gruppo",
                    kind="text",
                    x=0,
                    y=0,
                    w=width,
                    h=6,
                    text=f"{label}: [{group}]",
                    font_size=font_size,
                    bold=True,
                )
            )
            total_field = next(
                (name for name in fields if table.field(name) and table.field(name).type in ("integer", "decimal")),
                group,
            )
            spec.bands["group_footer"].append(
                Control(
                    id="totale_gruppo",
                    kind="total",
                    x=max(0.0, width - 70),
                    y=0,
                    w=70,
                    h=6,
                    expr=total_field,
                    func="count" if total_field == group else "sum",
                    label="Totale: ",
                    font_size=font_size,
                    align="right",
                )
            )
        if self.page_numbers_check.isChecked():
            spec.bands["page_footer"].append(
                Control(
                    id="pagina",
                    kind="text",
                    x=0,
                    y=0,
                    w=width,
                    h=6,
                    text="Pagina {PAGINA} di {PAGINE}",
                    font_size=max(6, font_size - 1),
                    align="right",
                )
            )

    def _refresh_summary(self) -> None:
        try:
            spec = self.build_spec()
        except (QueryError, ValueError) as exc:
            self.summary_label.setText("Report non valido")
            self.summary_view.setPlainText(f"-- Errore:\n{exc}")
            return
        controls = sum(len(items) for items in spec.bands.values())
        groups = ", ".join(item.get("label", item.get("field", "")) for item in spec.groups) or "nessuno"
        sorts = ", ".join(
            f"{item.get('field')} {item.get('direction')}" for item in spec.sort_fields
        ) or "nessuno"
        self.summary_label.setText(
            f"{spec.title} · {len(spec.bands['detail'])} controlli di dettaglio · "
            f"{controls} controlli totali"
        )
        self.summary_view.setPlainText(
            f"Titolo: {spec.title}\n"
            f"Sorgente: {spec.source_type} · {spec.table or spec.query}\n"
            f"Layout: {self.layout_key()}\n"
            f"Orientamento: {spec.orientation}\n"
            f"Gruppo: {groups}\n"
            f"Ordinamento: {sorts}\n"
            f"Font: {self.font_spin.value()} pt\n"
            "Bande: "
            + ", ".join(
                band for band in spec.effective_band_order() if spec.is_visible(band)
            )
        )

    def help_text(self) -> str:
        return (
            "1. Scegli nome, titolo e sorgente.\n"
            "2. Scegli il layout: tabellare, colonnare o riepilogo.\n"
            "3. Seleziona e ordina i campi.\n"
            "4. Imposta un gruppo e l'ordinamento.\n"
            "5. Scegli orientamento e font, controlla il riepilogo e crea il report.\n\n"
            "Il report prodotto è un normale ReportSpec: potrai modificare bande, "
            "controlli e stili nel Report Designer."
        )


__all__ = ["ReportExpert", "LAYOUTS"]
