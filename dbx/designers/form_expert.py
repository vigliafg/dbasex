"""Form Expert: procedura guidata a cinque passi per creare un form (O4).

La procedura produce un :class:`FormSpec` valido e lo apre nel Form Designer.
Non introduce un linguaggio: i controlli generati usano gli stessi campi del
modello e le stesse azioni del runtime.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QWidget,
)

from ..core.form_model import FormControl, FormPage, FormSpec
from ..core.metadata import Table, new_id, slugify
from ..core.query_engine import QueryError, query_table
from ..core.query_model import QuerySpec
from ..core.project import Project
from ..ui import design
from .expert_common import ExpertWizard

LAYOUTS = (
    ("labels_left", "Etichette a sinistra, campi in colonna"),
    ("labels_above", "Etichetta sopra il campo, larghezza piena"),
    ("two_columns", "Due colonne di campi"),
)

BACKCOLORS = (
    ("Bianco", "#ffffff"),
    ("Grigio dBASE", "#c0c0c0"),
    ("Azurro tenue", "#eef3fb"),
)
FORECOLORS = (
    ("Nero", "#000000"),
    ("Blu navy", "#000080"),
)

FIELD_STYLES = (
    ("standard", "Standard"),
    ("compact", "Compatto"),
)

NAV_BUTTONS = (
    ("first", "Primo"),
    ("previous", "Prec."),
    ("next", "Succ."),
    ("last", "Ultimo"),
    ("new", "Nuovo"),
    ("save", "Salva"),
    ("delete", "Elimina"),
    ("close", "Chiudi"),
)


class LayoutPreview(QWidget):
    """Miniatura del layout scelto: solo struttura, non pixel-perfect."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_name = "labels_left"
        self.field_count = 4
        self.setFixedSize(240, 150)
        palette = design.palette()
        self._surface = palette["workspace"]
        self._border = palette["panel_shadow"]
        self._text = palette["disabled"]

    def set_layout(self, name: str) -> None:
        self.layout_name = name
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: D102 - API Qt
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(self._surface))
        painter.setPen(QPen(QColor(self._border), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        painter.setPen(QPen(QColor(self._text), 1))
        inner = self.rect().adjusted(8, 8, -8, -8)
        rows = self.field_count
        if self.layout_name == "labels_above":
            row_height = max(14, inner.height() // max(1, rows + 1))
            for index in range(rows):
                top = inner.top() + index * row_height
                painter.drawRect(QRect(inner.left(), top, 60, 6))
                painter.drawRect(QRect(inner.left(), top + 8, inner.width(), 8))
        elif self.layout_name == "two_columns":
            columns = 2
            rows_per_column = max(1, (rows + 1) // columns)
            column_width = inner.width() // columns
            row_height = max(12, inner.height() // max(1, rows_per_column + 1))
            for index in range(rows):
                column = index // rows_per_column
                row = index % rows_per_column
                left = inner.left() + column * column_width
                top = inner.top() + row * row_height
                painter.drawRect(QRect(left, top, 40, 6))
                painter.drawRect(QRect(left, top + 9, column_width - 8, 8))
        else:
            row_height = max(12, inner.height() // max(1, rows + 1))
            for index in range(rows):
                top = inner.top() + index * row_height
                painter.drawRect(QRect(inner.left(), top, 40, 6))
                painter.drawRect(QRect(inner.left() + 48, top, inner.width() - 48, 10))


class FormExpert(ExpertWizard):
    """Wizard Form Expert in cinque passi."""

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        suggested_name: str = "",
    ) -> None:
        self.project = project
        self.suggested_name = suggested_name
        super().__init__(parent, "Form Expert")
        self.resize(660, 500)
        self.set_finish_text("Crea form")
        self._build_pages()

    # ------------------------------------------------------------------ pagine
    def _build_pages(self) -> None:
        self.addPage(self._page_intro())
        self.addPage(self._page_table())
        self.addPage(self._page_fields())
        self.addPage(self._page_layout())
        self.addPage(self._page_style())

    def _page_intro(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Form Expert")
        page.setSubTitle(
            "Crea un form a partire da una tabella. Puoi anche partire da un form vuoto "
            "e disegnarlo nel Form Designer."
        )
        layout = QVBoxLayout(page)
        self.expert_radio = QRadioButton("Expert Assistance: genera campi e pulsanti")
        self.expert_radio.setChecked(True)
        self.blank_radio = QRadioButton("Blank Form: solo la superficie vuota")
        self.group = QButtonGroup(page)
        self.group.addButton(self.expert_radio)
        self.group.addButton(self.blank_radio)
        layout.addWidget(self.expert_radio)
        layout.addWidget(self.blank_radio)
        layout.addSpacing(8)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.suggested_name or "form")
        self.name_edit.setPlaceholderText("nome_form")
        form.addRow("Nome del form", self.name_edit)
        self.caption_edit = QLineEdit("")
        self.caption_edit.setPlaceholderText("didascalia mostrata nel form")
        form.addRow("Didascalia", self.caption_edit)
        layout.addLayout(form)
        layout.addStretch(1)
        note = QLabel(
            "Il form generato usa la tabella del progetto e resta modificabile nel Form Designer."
        )
        note.setWordWrap(True)
        note.setObjectName("nav_hint")
        layout.addWidget(note)
        page.registerField("form_name*", self.name_edit)
        return page

    def _page_table(self) -> QWizardPage:
        page = QWizardPage()
        self._table_page = page
        page.setTitle("Tabella o query")
        page.setSubTitle("Scegli la tabella su cui lavora il form.")
        layout = QVBoxLayout(page)
        self.source_combo = QComboBox()
        self.source_combo.addItem("Tabella", "table")
        self.source_combo.addItem("Query (sola lettura)", "query")
        layout.addWidget(QLabel("Tipo di sorgente"))
        layout.addWidget(self.source_combo)
        self.table_combo = QComboBox()
        for name in self.project.names("tables"):
            table = self.project.table(name)
            label = table.display_name() if table is not None else name
            self.table_combo.addItem(f"{label} ({name})", name)
        self.table_label = QLabel("Tabella")
        layout.addWidget(self.table_label)
        layout.addWidget(self.table_combo)
        self.query_combo = QComboBox()
        for name in self.project.names("queries"):
            query = QuerySpec.from_project(self.project, name)
            label = query.caption if query is not None else name
            self.query_combo.addItem(f"{label} ({name})", name)
        self.query_label = QLabel("Query")
        layout.addWidget(self.query_label)
        layout.addWidget(self.query_combo)
        query_note = QLabel(
            "I form su query mostrano i campi calcolati e sono in sola lettura; "
            "usa una tabella per inserire e modificare i dati."
        )
        query_note.setObjectName("nav_hint")
        query_note.setWordWrap(True)
        layout.addWidget(query_note)
        layout.addSpacing(8)
        form = QFormLayout()
        self.order_combo = QComboBox()
        self.order_combo.addItem("(naturale)", "")
        form.addRow("Ordine", self.order_combo)
        layout.addLayout(form)
        layout.addStretch(1)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.table_combo.currentIndexChanged.connect(self._refresh_order_fields)
        self.table_combo.currentIndexChanged.connect(lambda _index: self._reload_fields())
        self.query_combo.currentIndexChanged.connect(self._refresh_order_fields)
        self.query_combo.currentIndexChanged.connect(lambda _index: self._reload_fields())
        self._on_source_changed()
        return page

    def _source_kind(self) -> str:
        return str(self.source_combo.currentData() or "table")

    def _source_name(self) -> str:
        if self._source_kind() == "query":
            return str(self.query_combo.currentData() or "")
        return str(self.table_combo.currentData() or "")

    def _source_table(self) -> Table | None:
        if self._source_kind() == "query":
            name = self._source_name()
            if not name:
                return None
            try:
                return query_table(self.project, name)
            except QueryError:
                return None
        return self.project.table(self._source_name())

    def _on_source_changed(self) -> None:
        is_query = self._source_kind() == "query"
        self.table_label.setVisible(not is_query)
        self.table_combo.setVisible(not is_query)
        self.query_label.setVisible(is_query)
        self.query_combo.setVisible(is_query)
        self._refresh_order_fields()
        self._reload_fields()

    def _refresh_order_fields(self) -> None:
        current = self.order_combo.currentData()
        self.order_combo.blockSignals(True)
        self.order_combo.clear()
        self.order_combo.addItem("(naturale)", "")
        table = self._source_table()
        if table is not None:
            for field in table.fields:
                self.order_combo.addItem(field.display_name(), field.name)
        index = self.order_combo.findData(current)
        self.order_combo.setCurrentIndex(max(0, index))
        self.order_combo.blockSignals(False)

    def _page_fields(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Scelta dei campi")
        page.setSubTitle("Sposta i campi dalla sorgente alla destinazione.")
        layout = QVBoxLayout(page)
        columns = QHBoxLayout()
        source_box = QVBoxLayout()
        source_box.addWidget(QLabel("Campi disponibili"))
        self.source_list = QListWidget()
        source_box.addWidget(self.source_list)
        columns.addLayout(source_box)
        buttons = QVBoxLayout()
        buttons.addStretch(1)
        for text, slot in (
            (">", self.move_selected),
            (">>", self.move_all),
            ("<", self.remove_selected),
            ("<<", self.remove_all),
        ):
            button = QPushButton(text)
            button.setFixedWidth(38)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        buttons.addStretch(1)
        columns.addLayout(buttons)
        destination_box = QVBoxLayout()
        destination_box.addWidget(QLabel("Campi del form"))
        self.destination_list = QListWidget()
        destination_box.addWidget(self.destination_list)
        columns.addLayout(destination_box)
        layout.addLayout(columns, 1)
        self.fields_page = page
        page.isComplete = self._fields_complete  # type: ignore[method-assign]
        return page

    def _fields_complete(self) -> bool:
        return (
            self.blank_radio.isChecked()
            or self.destination_list.count() > 0
        )

    def _field_items(self, table: Table | None) -> list[QListWidgetItem]:
        items: list[QListWidgetItem] = []
        if table is None:
            return items
        for field in table.fields:
            item = QListWidgetItem(field.display_name())
            item.setData(Qt.ItemDataRole.UserRole, field.name)
            item.setToolTip(f"{field.name} · {field.type}")
            items.append(item)
        return items

    def initializePage(self, page_id: int) -> None:  # noqa: N802 - API Qt
        super().initializePage(page_id)
        if self.page(page_id) is self._table_page and not self.source_list.count():
            self._reload_fields()
        if self.page(page_id) is self._layout_page:
            self._update_preview()
        self._update_finish_text()

    def _reload_fields(self) -> None:
        if not hasattr(self, "source_list"):
            return
        table = self._source_table()
        self.source_list.clear()
        self.destination_list.clear()
        for item in self._field_items(table):
            self.source_list.addItem(item)
        for index in range(self.source_list.count()):
            self.destination_list.addItem(self.source_list.item(index).clone())
        self.source_list.clear()
        if self.caption_edit.text().strip() == "" and table is not None:
            self.caption_edit.setText(table.display_name())

    # ------------------------------------------------------------------ azioni
    def move_selected(self) -> None:
        for item in self.source_list.selectedItems():
            self.destination_list.addItem(item.clone())
            self.source_list.takeItem(self.source_list.row(item))
        self._sync_fields_state()

    def move_all(self) -> None:
        while self.source_list.count():
            self.destination_list.addItem(self.source_list.takeItem(0))
        self._sync_fields_state()

    def remove_selected(self) -> None:
        for item in self.destination_list.selectedItems():
            self.source_list.addItem(item.clone())
            self.destination_list.takeItem(self.destination_list.row(item))
        self._sync_fields_state()

    def remove_all(self) -> None:
        while self.destination_list.count():
            self.source_list.addItem(self.destination_list.takeItem(0))
        self._sync_fields_state()

    def _sync_fields_state(self) -> None:
        if hasattr(self, "fields_page"):
            self.fields_page.completeChanged.emit()

    # ------------------------------------------------------------------ layout
    def _page_layout(self) -> QWizardPage:
        page = QWizardPage()
        self._layout_page = page
        page.setTitle("Layout")
        page.setSubTitle("Scegli la disposizione dei campi e guarda la miniatura.")
        layout = QHBoxLayout(page)
        options = QVBoxLayout()
        self.layout_group = QButtonGroup(page)
        self.layout_radios: dict[str, QRadioButton] = {}
        for index, (key, label) in enumerate(LAYOUTS):
            radio = QRadioButton(label)
            radio.setChecked(index == 0)
            radio.toggled.connect(self._update_preview)
            self.layout_group.addButton(radio)
            self.layout_radios[key] = radio
            options.addWidget(radio)
        options.addStretch(1)
        layout.addLayout(options, 1)
        self.layout_preview = LayoutPreview()
        layout.addWidget(self.layout_preview)
        return page

    def layout_key(self) -> str:
        for key, radio in self.layout_radios.items():
            if radio.isChecked():
                return key
        return "labels_left"

    def _update_preview(self) -> None:
        if hasattr(self, "layout_preview"):
            self.layout_preview.set_layout(self.layout_key())

    # ------------------------------------------------------------------- stile
    def _page_style(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Font, colori e stile")
        page.setSubTitle("Imposta l'aspetto dei campi generati.")
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.font_combo = QComboBox()
        for family in (
            design.UI_FONT.family,
            "Segoe UI",
            "Noto Sans",
            "DejaVu Sans",
            "Courier New",
        ):
            self.font_combo.addItem(family, family)
        form.addRow("Font", self.font_combo)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 24)
        self.size_spin.setValue(int(design.UI_FONT.size_pt))
        form.addRow("Dimensione", self.size_spin)
        self.bold_check = QCheckBox("Grassetto")
        form.addRow("", self.bold_check)
        self.background_combo = QComboBox()
        for label, color in BACKCOLORS:
            self.background_combo.addItem(label, color)
        form.addRow("Sfondo del form", self.background_combo)
        self.foreground_combo = QComboBox()
        for label, color in FORECOLORS:
            self.foreground_combo.addItem(label, color)
        form.addRow("Colore del testo", self.foreground_combo)
        self.style_combo = QComboBox()
        for key, label in FIELD_STYLES:
            self.style_combo.addItem(label, key)
        form.addRow("Stile dei campi", self.style_combo)
        layout.addLayout(form)
        layout.addStretch(1)
        return page

    def _show_help(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Form Expert",
            "1. Scegli Expert Assistance o Blank Form.\n"
            "2. Scegli la tabella del progetto.\n"
            "3. Sposta i campi nella colonna di destra.\n"
            "4. Scegli il layout.\n"
            "5. Imposta font, colori e stile, poi crea il form.",
        )

    def _update_finish_text(self) -> None:
        self.setButtonText(
            QWizard.WizardButton.FinishButton,
            "Crea form vuoto" if self.blank_radio.isChecked() else "Crea form",
        )

    # ------------------------------------------------------------------ output
    def build_spec(self) -> FormSpec:
        kind = self._source_kind()
        table = self._source_table()
        name = self.name_edit.text().strip() or self.suggested_name or "form"
        caption = self.caption_edit.text().strip() or (table.display_name() if table else name)
        source_name = self._source_name()
        spec = FormSpec(
            name=slugify(name),
            caption=caption,
            table=source_name if kind == "table" and table else "",
            source_type=kind,
            query=source_name if kind == "query" else "",
            width=620,
            height=440,
            order=str(self.order_combo.currentData() or ""),
            backcolor=str(self.background_combo.currentData() or ""),
            forecolor=str(self.foreground_combo.currentData() or ""),
        )
        if self.blank_radio.isChecked() or table is None:
            spec.pages = [FormPage(caption="Dati")]
            return spec
        fields = [
            str(self.destination_list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.destination_list.count())
        ]
        if not fields:
            fields = [field.name for field in table.fields]
        page = self._build_page(table, fields)
        if kind == "query":
            page.controls = [
                control
                for control in page.controls
                if not (
                    control.kind == "button"
                    and control.action in ("new", "save", "delete")
                )
            ]
        spec.pages = [page]
        spec.height = max(spec.height, self._required_height(fields))
        return spec

    def _style_values(self) -> dict[str, Any]:
        compact = str(self.style_combo.currentData() or "standard") == "compact"
        return {
            "font_name": str(self.font_combo.currentData() or ""),
            "font_size": int(self.size_spin.value()),
            "bold": self.bold_check.isChecked(),
            "forecolor": str(self.foreground_combo.currentData() or ""),
            "row_height": 24 if compact else 28,
            "control_height": 20 if compact else 24,
        }

    def _required_height(self, fields: list[str]) -> int:
        style = self._style_values()
        rows = len(fields)
        if self.layout_key() == "two_columns":
            rows = (rows + 1) // 2
        row_height = style["row_height"]
        if self.layout_key() == "labels_above":
            row_height += 16
        return 60 + rows * row_height + 70

    def _build_page(self, table: Table, fields: list[str]) -> FormPage:
        style = self._style_values()
        page = FormPage(caption="Dati")
        page.controls.append(
            FormControl(
                id=new_id(),
                kind="label",
                text=table.display_name(),
                x=12,
                y=8,
                w=420,
                h=26,
                font_size=max(12, style["font_size"] + 4),
                bold=True,
                forecolor=style["forecolor"],
            )
        )
        layout = self.layout_key()
        compact = str(self.style_combo.currentData() or "standard") == "compact"
        control_height = int(style["control_height"])
        row_height = int(style["row_height"])
        y = 44
        if layout == "two_columns":
            columns = 2
            rows = (len(fields) + columns - 1) // columns
            for index, field_name in enumerate(fields):
                field = table.field(field_name)
                if field is None:
                    continue
                column = index // rows
                row = index % rows
                left = 12 + column * 306
                top = 44 + row * row_height
                page.controls.append(
                    FormControl(
                        id=new_id(),
                        kind="label",
                        text=field.display_name(),
                        x=left,
                        y=top + 3,
                        w=110,
                        h=control_height,
                        font_name=style["font_name"],
                        font_size=style["font_size"],
                        bold=style["bold"],
                        forecolor=style["forecolor"],
                    )
                )
                control = self._field_control(field, left + 116, top, 180, control_height, style)
                page.controls.append(control)
            y = 44 + rows * row_height + 8
        elif layout == "labels_above":
            for field_name in fields:
                field = table.field(field_name)
                if field is None:
                    continue
                page.controls.append(
                    FormControl(
                        id=new_id(),
                        kind="label",
                        text=field.display_name(),
                        x=12,
                        y=y,
                        w=320,
                        h=16,
                        font_name=style["font_name"],
                        font_size=style["font_size"],
                        bold=style["bold"],
                        forecolor=style["forecolor"],
                    )
                )
                page.controls.append(self._field_control(field, 12, y + 17, 540, control_height, style))
                y += row_height + 16
        else:
            for field_name in fields:
                field = table.field(field_name)
                if field is None:
                    continue
                page.controls.append(
                    FormControl(
                        id=new_id(),
                        kind="label",
                        text=field.display_name(),
                        x=12,
                        y=y + 3,
                        w=150,
                        h=control_height,
                        font_name=style["font_name"],
                        font_size=style["font_size"],
                        bold=style["bold"],
                        forecolor=style["forecolor"],
                    )
                )
                page.controls.append(self._field_control(field, 170, y, 300, control_height, style))
                y += row_height
        if not compact:
            y += 10
        page.controls.append(
            FormControl(
                id=new_id(),
                kind="line",
                x=12,
                y=y,
                w=540,
                h=2,
            )
        )
        y += 12
        button_x = 12
        for action, caption in NAV_BUTTONS:
            page.controls.append(
                FormControl(
                    id=new_id(),
                    kind="button",
                    text=caption,
                    action=action,
                    x=button_x,
                    y=y,
                    w=78,
                    h=26,
                    font_size=style["font_size"],
                )
            )
            button_x += 80
        return page

    @staticmethod
    def _field_control(
        field, x: int, y: int, width: int, height: int, style: dict[str, Any] | None = None
    ) -> FormControl:
        kind = "field"
        if field.type == "memo":
            kind = "memo"
        elif field.type in ("integer", "decimal"):
            kind = "number"
        elif field.type == "boolean":
            kind = "checkbox"
        elif field.type == "date":
            kind = "date"
        elif field.lookup:
            kind = "combo"
        style = style or {}
        return FormControl(
            id=new_id(),
            kind=kind,
            field=field.name,
            x=x,
            y=y,
            w=width,
            h=max(48, height + 24) if kind == "memo" else height,
            font_name=str(style.get("font_name", "")),
            font_size=int(style.get("font_size", 10) or 10),
            bold=bool(style.get("bold", False)),
            forecolor=str(style.get("forecolor", "")),
            lookup=field.lookup,
        )
