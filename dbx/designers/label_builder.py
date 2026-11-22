"""Label Designer leggero e dialogo di creazione (0.8 O7).

Il designer produce e consuma lo stesso JSON di ``LabelSpec``: non esegue SQL e
non contiene logica dati. L'anteprima usa ``label_engine`` sui record reali,
quindi stampa e mail merge condividono un unico layout.
"""

from __future__ import annotations

import copy
from math import ceil
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core.label_model import (
    DEFAULT_PRESET,
    LabelSpec,
    preset_data,
    preset_labels,
)
from ..core.metadata import slugify
from ..core.project import Project, ProjectError
from ..core.query_engine import QueryError, query_table
from ..runtime.label_engine import label_field_choices, load_label_rows
from ..ui import icons


class NewLabelDialog(QDialog):
    """Sceglie nome, titolo, sorgente e formato del nuovo foglio di etichette."""

    def __init__(
        self, project: Project, parent: QWidget | None = None, suggested_name: str = ""
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Nuova etichetta")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(suggested_name)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Titolo dell'etichetta o del mail merge")
        self.source_combo = QComboBox()
        for name in project.names("tables"):
            self.source_combo.addItem(f"Tabella · {name}", ("table", name))
        for name in project.names("queries"):
            self.source_combo.addItem(f"Query · {name}", ("query", name))
        self.preset_combo = QComboBox()
        for key, label in preset_labels():
            self.preset_combo.addItem(label, key)
        index = self.preset_combo.findData(DEFAULT_PRESET)
        self.preset_combo.setCurrentIndex(max(0, index))
        form.addRow("Nome", self.name_edit)
        form.addRow("Titolo", self.title_edit)
        form.addRow("Sorgente", self.source_combo)
        form.addRow("Formato", self.preset_combo)
        layout.addLayout(form)
        hint = QLabel(
            "Ogni record produce un'etichetta; filtro e ordinamento si impostano "
            "nel designer. Usa una query per stampare totali o colonne calcolate."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(500, 260)

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Nuova etichetta", "Indica un nome per l'etichetta.")
            return
        if not self.source_combo.currentData():
            QMessageBox.warning(
                self, "Nuova etichetta", "Crea prima una tabella o una query."
            )
            return
        super().accept()

    def spec(self) -> LabelSpec:
        kind, name = self.source_combo.currentData()
        kind, name = str(kind), str(name)
        title = self.title_edit.text().strip()
        label_name = self.name_edit.text().strip()
        preset = str(self.preset_combo.currentData() or DEFAULT_PRESET)
        if kind == "query":
            try:
                table = query_table(self.project, name)
            except QueryError:
                table = None
            fields = [field.name for field in table.fields] if table else []
            return LabelSpec.create_for_query(
                label_name,
                name,
                fields,
                title or f"Etichette {name}",
                preset=preset,
            )
        table = self.project.require_table(name)
        fields = [field.name for field in table.fields]
        return LabelSpec.create(
            label_name,
            table.name,
            fields,
            title or f"Etichette {table.display_name()}",
            preset=preset,
        )


class LabelDesignerWidget(QWidget):
    """Designer compatto: sorgente, geometria del foglio e modello di testo."""

    saved = pyqtSignal(str)
    preview_requested = pyqtSignal(object)
    status_message = pyqtSignal(str)
    new_requested = pyqtSignal()
    open_requested = pyqtSignal()

    def __init__(
        self, project: Project, spec: LabelSpec, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("label_designer")
        self.project = project
        self.spec = spec
        self.original_name = spec.name
        self.preview_handler = None
        self._saved_state = copy.deepcopy(spec.to_dict())
        self._loading = True
        self._count_cache: dict[tuple[Any, ...], int | str] = {}
        self.setWindowTitle(f"Label Designer ({spec.name})")
        self.resize(1060, 680)
        self._build_ui()
        self._load()
        self._loading = False
        self._update_status()

    # ------------------------------------------------------------------ fonte
    def _source_entries(self) -> list[tuple[str, str, str]]:
        entries = [
            ("table", name, f"Tabella · {name}") for name in self.project.names("tables")
        ]
        entries += [
            ("query", name, f"Query · {name}") for name in self.project.names("queries")
        ]
        return entries

    def _source_key(self) -> tuple[str, str]:
        if self.spec.source_type == "query":
            return ("query", self.spec.query)
        return ("table", self.spec.table)

    def _source_index(self, key: tuple[str, str]) -> int:
        for index in range(self.source_combo.count()):
            if self.source_combo.itemData(index) == key:
                return index
        return -1

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        header = QHBoxLayout()
        header.setSpacing(3)
        self.name_edit = QLineEdit(self.spec.name)
        self.name_edit.setPlaceholderText("nome_etichetta")
        self.title_edit = QLineEdit(self.spec.title)
        self.title_edit.setPlaceholderText("Titolo")
        self.source_combo = QComboBox()
        for kind, name, label in self._source_entries():
            self.source_combo.addItem(label, (kind, name))
        self.source_combo.setCurrentIndex(max(0, self._source_index(self._source_key())))
        self.filter_edit = QLineEdit(self.spec.filter)
        self.filter_edit.setPlaceholderText("Filtro")
        self.order_edit = QLineEdit(self.spec.order)
        self.order_edit.setPlaceholderText("Ordine")
        for label, widget, stretch in (
            ("Nome:", self.name_edit, 2),
            ("Titolo:", self.title_edit, 3),
            ("Sorgente:", self.source_combo, 2),
            ("Filtro:", self.filter_edit, 3),
            ("Ordine:", self.order_edit, 2),
        ):
            header.addWidget(QLabel(label))
            header.addWidget(widget, stretch)
        layout.addLayout(header)

        layout.addLayout(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_layout_panel())
        splitter.addWidget(self._build_template_panel())
        splitter.setSizes([460, 560])
        layout.addWidget(splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("nav_hint")
        layout.addWidget(self.status_label)

        self.name_edit.editingFinished.connect(self._collect)
        self.title_edit.editingFinished.connect(self._collect)
        self.filter_edit.editingFinished.connect(self._collect)
        self.order_edit.editingFinished.connect(self._collect)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)

    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(2)
        bar.addWidget(
            icons.make_button("", "nuovo", self.new_requested.emit, self, "Nuova etichetta")
        )
        bar.addWidget(
            icons.make_button("", "apri", self.open_requested.emit, self, "Apri etichetta…")
        )
        self.save_button = icons.make_button(
            "Salva", "salva", self.save, self, "Salva l'etichetta nel progetto"
        )
        self.preview_button = icons.make_button(
            "Anteprima", "anteprima", self.preview, self, "Mostra tutte le etichette"
        )
        self.print_button = icons.make_button(
            "Stampa", "stampa", self.print_pages, self, "Stampa il mail merge"
        )
        for button in (self.save_button, self.preview_button, self.print_button):
            bar.addWidget(button)
        bar.addSpacing(8)
        bar.addWidget(
            icons.make_button(
                "Inserisci campo", "campo", self.insert_field, self,
                "Inserisce il campo selezionato nel modello",
            )
        )
        bar.addStretch(1)
        return bar

    def _build_layout_panel(self) -> QWidget:
        panel = QWidget()
        form = QFormLayout(panel)
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(3)

        self.preset_combo = QComboBox()
        for key, label in preset_labels():
            self.preset_combo.addItem(label, key)
        self.preset_combo.addItem("Personalizzato", "")
        self.preset_combo.activated.connect(self._on_preset_chosen)
        form.addRow("Formato", self.preset_combo)

        self.page_combo = QComboBox()
        self.page_combo.addItem("A4", "A4")
        self.page_combo.addItem("Letter", "Letter")
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItem("Verticale", "portrait")
        self.orientation_combo.addItem("Orizzontale", "landscape")
        page_row = QHBoxLayout()
        page_row.addWidget(self.page_combo, 1)
        page_row.addWidget(self.orientation_combo, 1)
        form.addRow("Pagina", page_row)

        self.width_spin = self._mm_spin(5.0, 300.0)
        self.height_spin = self._mm_spin(5.0, 300.0)
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("L"))
        size_row.addWidget(self.width_spin, 1)
        size_row.addWidget(QLabel("A"))
        size_row.addWidget(self.height_spin, 1)
        form.addRow("Etichetta (mm)", size_row)

        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 12)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 20)
        grid_row = QHBoxLayout()
        grid_row.addWidget(QLabel("Colonne"))
        grid_row.addWidget(self.columns_spin, 1)
        grid_row.addWidget(QLabel("Righe"))
        grid_row.addWidget(self.rows_spin, 1)
        form.addRow("Griglia", grid_row)

        self.gutter_x_spin = self._mm_spin(0.0, 30.0)
        self.gutter_y_spin = self._mm_spin(0.0, 30.0)
        gutter_row = QHBoxLayout()
        gutter_row.addWidget(QLabel("Orizz."))
        gutter_row.addWidget(self.gutter_x_spin, 1)
        gutter_row.addWidget(QLabel("Vert."))
        gutter_row.addWidget(self.gutter_y_spin, 1)
        form.addRow("Distanza (mm)", gutter_row)

        self.margin_top_spin = self._mm_spin(0.0, 60.0)
        self.margin_bottom_spin = self._mm_spin(0.0, 60.0)
        self.margin_left_spin = self._mm_spin(0.0, 60.0)
        self.margin_right_spin = self._mm_spin(0.0, 60.0)
        margin_row = QHBoxLayout()
        for side, spin in (
            ("T", self.margin_top_spin),
            ("B", self.margin_bottom_spin),
            ("S", self.margin_left_spin),
            ("D", self.margin_right_spin),
        ):
            margin_row.addWidget(QLabel(side))
            margin_row.addWidget(spin, 1)
        form.addRow("Margini (mm)", margin_row)

        self.padding_spin = self._mm_spin(0.0, 30.0)
        form.addRow("Margine interno (mm)", self.padding_spin)

        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(0, 200)
        self.offset_spin.setToolTip("Etichette già usate sul primo foglio")
        form.addRow("Etichette da saltare", self.offset_spin)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(6, 48)
        self.bold_check = QCheckBox("Grassetto")
        font_row = QHBoxLayout()
        font_row.addWidget(self.font_spin, 1)
        font_row.addWidget(self.bold_check, 1)
        form.addRow("Corpo", font_row)

        self.align_combo = QComboBox()
        self.align_combo.addItem("Sinistra", "left")
        self.align_combo.addItem("Centro", "center")
        self.align_combo.addItem("Destra", "right")
        self.border_check = QCheckBox("Bordo etichetta")
        align_row = QHBoxLayout()
        align_row.addWidget(self.align_combo, 1)
        align_row.addWidget(self.border_check, 1)
        form.addRow("Allineamento", align_row)

        for widget in (
            self.page_combo,
            self.orientation_combo,
            self.align_combo,
        ):
            widget.currentIndexChanged.connect(self._collect)
        for spin in (
            self.width_spin,
            self.height_spin,
            self.gutter_x_spin,
            self.gutter_y_spin,
            self.margin_top_spin,
            self.margin_bottom_spin,
            self.margin_left_spin,
            self.margin_right_spin,
            self.padding_spin,
        ):
            spin.valueChanged.connect(self._collect)
        for spin in (
            self.columns_spin,
            self.rows_spin,
            self.offset_spin,
            self.font_spin,
        ):
            spin.valueChanged.connect(self._collect)
        for box in (self.bold_check, self.border_check):
            box.toggled.connect(self._collect)
        form.addRow(QLabel(""))
        hint = QLabel(
            "Il modello viene ripetuto per ogni record. Filtro e ordine "
            "selezionano i record del mail merge."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        form.addRow(hint)
        return panel

    def _build_template_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        layout.addWidget(QLabel("Modello dell'etichetta (usa [campo] o {{[campo] * 2}})"))
        self.template_edit = QPlainTextEdit(self.spec.template)
        self.template_edit.setPlaceholderText("[nome]\n[citta]")
        self.template_edit.textChanged.connect(self._collect)
        layout.addWidget(self.template_edit, 2)
        layout.addWidget(QLabel("Campi della sorgente"))
        self.fields_list = QListWidget()
        self.fields_list.setAlternatingRowColors(True)
        self.fields_list.itemDoubleClicked.connect(
            lambda _item: self.insert_field()
        )
        layout.addWidget(self.fields_list, 1)
        return panel

    @staticmethod
    def _mm_spin(minimum: float, maximum: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(1)
        spin.setSingleStep(0.5)
        spin.setSuffix(" mm")
        return spin

    # ---------------------------------------------------------------- caricamento
    def _load(self) -> None:
        self.name_edit.setText(self.spec.name)
        self.title_edit.setText(self.spec.title)
        self.filter_edit.setText(self.spec.filter)
        self.order_edit.setText(self.spec.order)
        self.page_combo.setCurrentIndex(max(0, self.page_combo.findData(self.spec.page_size)))
        self.orientation_combo.setCurrentIndex(
            max(0, self.orientation_combo.findData(self.spec.orientation))
        )
        self.width_spin.setValue(self.spec.label_width)
        self.height_spin.setValue(self.spec.label_height)
        self.columns_spin.setValue(self.spec.columns)
        self.rows_spin.setValue(self.spec.rows)
        self.gutter_x_spin.setValue(self.spec.gutter_x)
        self.gutter_y_spin.setValue(self.spec.gutter_y)
        self.margin_top_spin.setValue(self.spec.margin("top"))
        self.margin_bottom_spin.setValue(self.spec.margin("bottom"))
        self.margin_left_spin.setValue(self.spec.margin("left"))
        self.margin_right_spin.setValue(self.spec.margin("right"))
        self.padding_spin.setValue(self.spec.padding)
        self.offset_spin.setValue(self.spec.start_offset)
        self.font_spin.setValue(self.spec.font_size)
        self.bold_check.setChecked(self.spec.bold)
        self.align_combo.setCurrentIndex(max(0, self.align_combo.findData(self.spec.align)))
        self.border_check.setChecked(self.spec.border)
        self.template_edit.setPlainText(self.spec.template)
        self._sync_preset_combo()
        self._refresh_fields()

    def _refresh_fields(self) -> None:
        self.fields_list.clear()
        for name, label in label_field_choices(self.project, self.spec):
            item = QListWidgetItem(f"{name} — {label}" if label and label != name else name)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.fields_list.addItem(item)

    def _sync_preset_combo(self) -> None:
        key = self.spec.preset_key()
        index = self.preset_combo.findData(key) if key else -1
        if index < 0:
            index = self.preset_combo.findData("")
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(max(0, index))
        self.preset_combo.blockSignals(False)

    # ------------------------------------------------------------------- eventi
    def _on_source_changed(self) -> None:
        self._collect()
        self._refresh_fields()

    def _on_preset_chosen(self, index: int) -> None:
        key = str(self.preset_combo.itemData(index) or "")
        data = preset_data(key)
        if data is None:
            return
        self.page_combo.setCurrentIndex(
            max(0, self.page_combo.findData(str(data["page_size"])))
        )
        self.orientation_combo.setCurrentIndex(
            max(0, self.orientation_combo.findData(str(data["orientation"])))
        )
        self.width_spin.setValue(float(data["label_width"]))
        self.height_spin.setValue(float(data["label_height"]))
        self.columns_spin.setValue(int(data["columns"]))
        self.rows_spin.setValue(int(data["rows"]))
        self.gutter_x_spin.setValue(float(data["gutter_x"]))
        self.gutter_y_spin.setValue(float(data["gutter_y"]))
        margins = data.get("margins") or {}
        self.margin_top_spin.setValue(float(margins.get("top", 0.0)))
        self.margin_bottom_spin.setValue(float(margins.get("bottom", 0.0)))
        self.margin_left_spin.setValue(float(margins.get("left", 0.0)))
        self.margin_right_spin.setValue(float(margins.get("right", 0.0)))
        self._collect()

    def _collect(self) -> None:
        if self._loading:
            return
        data = self.source_combo.currentData()
        if data:
            self.spec.source_type = str(data[0])
            if self.spec.source_type == "query":
                self.spec.query = str(data[1])
                self.spec.table = ""
            else:
                self.spec.table = str(data[1])
                self.spec.query = ""
        self.spec.name = self.name_edit.text().strip()
        self.spec.title = self.title_edit.text().strip()
        self.spec.filter = self.filter_edit.text().strip()
        self.spec.order = self.order_edit.text().strip()
        self.spec.page_size = str(self.page_combo.currentData() or "A4")
        self.spec.orientation = str(self.orientation_combo.currentData() or "portrait")
        self.spec.label_width = self.width_spin.value()
        self.spec.label_height = self.height_spin.value()
        self.spec.columns = self.columns_spin.value()
        self.spec.rows = self.rows_spin.value()
        self.spec.gutter_x = self.gutter_x_spin.value()
        self.spec.gutter_y = self.gutter_y_spin.value()
        self.spec.margins = {
            "top": self.margin_top_spin.value(),
            "bottom": self.margin_bottom_spin.value(),
            "left": self.margin_left_spin.value(),
            "right": self.margin_right_spin.value(),
        }
        self.spec.padding = self.padding_spin.value()
        self.spec.start_offset = self.offset_spin.value()
        self.spec.font_size = self.font_spin.value()
        self.spec.bold = self.bold_check.isChecked()
        self.spec.align = str(self.align_combo.currentData() or "left")
        self.spec.border = self.border_check.isChecked()
        self.spec.template = self.template_edit.toPlainText()
        self._sync_preset_combo()
        self._update_status()

    def _update_status(self) -> None:
        key = (
            self.spec.source_type,
            self.spec.table,
            self.spec.query,
            self.spec.filter,
            self.spec.order,
        )
        if key not in self._count_cache:
            try:
                self._count_cache[key] = len(load_label_rows(self.project, self.spec))
            except ValueError as exc:
                self._count_cache[key] = str(exc)
        count = self._count_cache[key]
        if isinstance(count, str):
            self.status_label.setText(count)
            return
        pages = max(
            1,
            ceil((self.spec.start_offset + max(1, count)) / self.spec.labels_per_page),
        )
        self.status_label.setText(
            f"{count} record · {self.spec.labels_per_page} etichette per foglio · "
            f"{pages} fogli · sola stampa"
        )

    # ------------------------------------------------------------------ azioni
    def insert_field(self) -> None:
        item = self.fields_list.currentItem()
        if item is None:
            return
        name = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if not name:
            return
        self.template_edit.insertPlainText(f"[{name}]")
        self.template_edit.setFocus()

    def preview(self) -> None:
        self._collect()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Etichetta non valida", "\n".join(errors))
            return
        if self.preview_handler is not None:
            self.preview_handler(self.spec)
            return
        self.preview_requested.emit(self.spec)

    def print_pages(self) -> None:
        from ..ui.label_preview import LabelPreviewDialog

        self._collect()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Etichetta non valida", "\n".join(errors))
            return
        dialog = LabelPreviewDialog(self.project, self.spec, self)
        dialog.print_pages()
        dialog.deleteLater()

    def save(self) -> bool:
        self._collect()
        errors = self.spec.validate()
        if errors:
            QMessageBox.warning(self, "Etichetta non valida", "\n".join(errors))
            return False
        if not self.spec.name:
            self.spec.name = f"etichette_{slugify(self.spec.table or self.spec.query)}"
            self.name_edit.setText(self.spec.name)
        try:
            self.project.put_object(
                "labels", self.spec.to_dict(), previous_name=self.original_name
            )
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self.original_name = self.spec.name
        self._saved_state = copy.deepcopy(self.spec.to_dict())
        self.saved.emit(self.spec.name)
        self.status_message.emit(f"Etichetta {self.spec.name} salvata")
        return True

    def is_dirty(self) -> bool:
        self._collect()
        return self.spec.to_dict() != self._saved_state


__all__ = ["LabelDesignerWidget", "NewLabelDialog"]
