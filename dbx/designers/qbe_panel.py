"""Vista QBE del Query Designer (0.4/O4).

Il pannello mostra una *query image* per ogni tabella della query, come nel
QBE di Paradox: una riga ``Includi``, più righe di criteri e una riga di
ordinamento. La vista non ha un modello proprio: legge e scrive lo stesso
``QuerySpec`` del designer guidato. Le celle non valide sono evidenziate e
non vengono applicate.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..core import types as T
from ..core.metadata import Table
from ..core.project import Project
from ..core.qbe import QbeCell, QbeError, example_name, format_cell, is_example_element, parse_cell
from ..core.query_model import JOIN_LABELS, QueryField, QueryFilter, QuerySort, QuerySpec, type_family
from ..ui import icons

CRITERIA_ROWS = 3
SORT_LABELS = (("", "(nessuno)"), ("asc", "Crescente"), ("desc", "Decrescente"))

HELP_HTML = """
<b>Sintassi delle celle QBE</b><br>
Valore nudo = uguale · <code>=  &lt;&gt;  &gt;  &gt;=  &lt;  &lt;=</code> ·
<code>10..20</code> intervallo (numeri e date) ·
<code>blank</code> / <code>not blank</code> ·
<code>*testo*</code> e <code>te?t</code> jolly per il testo ·
<code>_nome</code> example element.<br>
Stessa riga = AND, righe diverse = OR. Gli example elements con lo stesso nome
mettono in relazione i campi.
<a href="docs">Apri la guida QBE</a>
"""


def _set_error(widget: QLineEdit, error: bool) -> None:
    widget.setProperty("state", "error" if error else "")
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def _doc_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "inspirations"
        / "paradox-experts-qbe.md"
    )


def _ordered(existing: list, new: list, key) -> list:
    """Mantiene l'ordine esistente per gli elementi riconosciuti, poi aggiunge i nuovi."""
    remaining = list(new)
    result: list = []
    for old in existing:
        wanted = key(old)
        for index, item in enumerate(remaining):
            if key(item) == wanted:
                result.append(remaining.pop(index))
                break
    result.extend(remaining)
    return result


class QbeImage(QFrame):
    """Griglia QBE di una singola tabella."""

    changed = pyqtSignal()

    def __init__(
        self,
        project: Project,
        spec: QuerySpec,
        table: Table,
        parent: QWidget | None = None,
    ) -> None:
        join = next(
            (item for item in spec.joins if item.table.lower() == table.name.lower()),
            None,
        )
        role = "BASE" if table.name.lower() == spec.base.lower() else (
            JOIN_LABELS.get(join.kind, join.kind) if join is not None else "TABELLA"
        )
        super().__init__(parent)
        self.setObjectName("qbe_box")
        self.title_text = f"{table.display_name()} · {role}"
        self.project = project
        self.spec = spec
        self.table = table
        self._loading = False
        self._edits: dict[tuple[int, int], QLineEdit] = {}
        self._checks: list[QCheckBox] = []
        self._sorts: list[QComboBox] = []
        self._criteria_rows = self._criteria_row_count()
        self._build()

    # ------------------------------------------------------------------ build
    def _criteria_row_count(self) -> int:
        prefix = self.table.name.lower() + "."
        groups = [
            int(item.group)
            for item in self.spec.filters
            if item.op != "ref" and item.field.lower().startswith(prefix)
        ]
        return max(CRITERIA_ROWS, max(groups, default=0) + 1)

    def _build(self) -> None:
        self._loading = True
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(2)
            title = QLabel(self.title_text)
            title.setObjectName("qbe_title")
            layout.addWidget(title)
            rows = 1 + self._criteria_rows + 1
            grid = QTableWidget(rows, len(self.table.fields))
            self.grid = grid
            grid.setObjectName("qbe_image")
            grid.verticalHeader().setVisible(True)
            grid.horizontalHeader().setVisible(True)
            grid.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            grid.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            labels = ["Includi"]
            labels.extend(f"Criteri {index + 1}" for index in range(self._criteria_rows))
            labels.append("Ordinamento")
            grid.setVerticalHeaderLabels(labels)
            for column, field in enumerate(self.table.fields):
                header = f"{field.display_name()}\n{field.name}"
                tooltip = f"{self.table.name}.{field.name} · {T.label(field.type)}"
                item = QTableWidgetItem(header)
                item.setToolTip(tooltip)
                grid.setHorizontalHeaderItem(column, item)

                check = QCheckBox()
                check.setToolTip(f"Includi {self.table.name}.{field.name} nel risultato")
                check.setAccessibleName(f"Includi {self.table.name}.{field.name}")
                check.setChecked(
                    any(
                        item.field.lower() == field.name.lower()
                        and item.table.lower() == self.table.name.lower()
                        for item in self.spec.fields
                    )
                )
                check.stateChanged.connect(self._on_edited)
                self._checks.append(check)
                holder = QWidget()
                holder_layout = QHBoxLayout(holder)
                holder_layout.setContentsMargins(0, 0, 0, 0)
                holder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                holder_layout.addWidget(check)
                grid.setCellWidget(0, column, holder)

                for group in range(self._criteria_rows):
                    edit = QLineEdit()
                    edit.setPlaceholderText("valore")
                    edit.setToolTip(
                        "=, <>, >, >=, <, <= · a..b · blank · *jolly* · _nome"
                    )
                    edit.setAccessibleName(
                        f"Criterio {group + 1} {self.table.name}.{field.name}"
                    )
                    edit.editingFinished.connect(self._on_edited)
                    self._edits[(group, column)] = edit
                    grid.setCellWidget(1 + group, column, edit)

                combo = QComboBox()
                for value, label in SORT_LABELS:
                    combo.addItem(label, value)
                combo.currentIndexChanged.connect(self._on_edited)
                combo.setAccessibleName(f"Ordinamento {self.table.name}.{field.name}")
                self._sorts.append(combo)
                grid.setCellWidget(rows - 1, column, combo)

            self._fill_values()
            header = grid.horizontalHeader()
            header.setMinimumSectionSize(60)
            grid.setMinimumHeight(50 + 30 * rows)
            layout.addWidget(grid)
            self._warn = QLabel("")
            self._warn.setObjectName("nav_hint")
            self._warn.setWordWrap(True)
            layout.addWidget(self._warn)
        finally:
            self._loading = False

    def _fill_values(self) -> None:
        prefix = self.table.name.lower() + "."
        refs = [item for item in self.spec.filters if item.op == "ref"]
        ref_names: dict[int, str] = {}
        for index, item in enumerate(refs):
            if not (
                item.field.lower().startswith(prefix)
                or item.value.lower().startswith(prefix)
            ):
                continue
            name = f"_rif{index + 1}"
            ref_names[index] = name
            for ref in (item.field, item.value):
                table_name, field_name = ref.split(".", 1)
                if table_name.lower() != self.table.name.lower():
                    continue
                column = self._column(field_name)
                if column is None:
                    continue
                edit = self._edits.get((0, column))
                if edit is not None and not edit.text().strip():
                    edit.setText(name)

        for (group, column), edit in self._edits.items():
            field = self.table.fields[column]
            ref = f"{self.table.name}.{field.name}"
            matches = [
                item
                for item in self.spec.filters
                if item.op != "ref"
                and item.group == group
                and item.field.lower() == ref.lower()
            ]
            if not matches:
                continue
            first = matches[0]
            edit.setText(format_cell(QbeCell(first.op, first.value, first.value2)))
            if len(matches) > 1:
                edit.setToolTip(
                    "Più criteri sullo stesso campo e riga: la cella mostra il primo; "
                    "finché non la modifichi restano tutti."
                )

        for column, combo in enumerate(self._sorts):
            field = self.table.fields[column]
            ref = f"{self.table.name}.{field.name}"
            item = next(
                (entry for entry in self.spec.sorts if entry.field.lower() == ref.lower()),
                None,
            )
            combo.blockSignals(True)
            combo.setCurrentIndex(
                max(0, combo.findData(item.direction if item is not None else ""))
            )
            combo.blockSignals(False)

    def _column(self, field_name: str) -> int | None:
        for index, field in enumerate(self.table.fields):
            if field.name.lower() == field_name.lower():
                return index
        return None

    # ------------------------------------------------------------------ API
    def column(self, field_name: str) -> int | None:
        return self._column(field_name)

    def set_cell(self, group: int, field_name: str, text: str) -> None:
        column = self._column(field_name)
        if column is None:
            raise KeyError(f"campo sconosciuto: {field_name}")
        edit = self._edits.get((int(group), column))
        if edit is None:
            raise KeyError(f"riga di criterio sconosciuta: {group}")
        edit.setText(str(text))

    def cell_text(self, group: int, field_name: str) -> str:
        column = self._column(field_name)
        if column is None:
            return ""
        edit = self._edits.get((int(group), column))
        return edit.text() if edit is not None else ""

    def set_included(self, field_name: str, checked: bool) -> None:
        column = self._column(field_name)
        if column is not None:
            self._checks[column].setChecked(bool(checked))

    def is_included(self, field_name: str) -> bool:
        column = self._column(field_name)
        return bool(self._checks[column].isChecked()) if column is not None else False

    def set_sort(self, field_name: str, direction: str) -> None:
        column = self._column(field_name)
        if column is None:
            return
        combo = self._sorts[column]
        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(direction)))
        combo.blockSignals(False)

    # ------------------------------------------------------------------ eventi
    def _on_edited(self, *_args) -> None:
        if not self._loading:
            self.changed.emit()

    # ------------------------------------------------------------------ lettura
    def values(
        self,
    ) -> tuple[
        list[QueryField],
        list[QueryFilter],
        list[QuerySort],
        list[str],
        dict[str, list[str]],
        list[tuple[str, int]],
    ]:
        warnings: list[str] = []
        invalid: list[tuple[str, int]] = []
        examples: dict[str, list[str]] = {}
        existing = {
            (item.table.lower(), item.field.lower()): item for item in self.spec.fields
        }
        fields: list[QueryField] = []
        filters: list[QueryFilter] = []
        sorts: list[QuerySort] = []
        prefix = self.table.name.lower() + "."

        for column, check in enumerate(self._checks):
            if not check.isChecked():
                continue
            field = self.table.fields[column]
            key = (self.table.name.lower(), field.name.lower())
            fields.append(existing.get(key) or QueryField(self.table.name, field.name))

        for (group, column), edit in self._edits.items():
            _set_error(edit, False)
            text = edit.text().strip()
            field = self.table.fields[column]
            ref = f"{self.table.name}.{field.name}"
            if not text:
                continue
            if is_example_element(text):
                refs = examples.setdefault(example_name(text), [])
                if ref not in refs:
                    refs.append(ref)
                continue
            previous = [
                item
                for item in self.spec.filters
                if item.op != "ref"
                and item.group == group
                and item.field.lower() == ref.lower()
            ]
            if previous and format_cell(
                QbeCell(previous[0].op, previous[0].value, previous[0].value2)
            ) == text:
                filters.extend(previous)
                continue
            try:
                cell = parse_cell(text, field.type)
            except QbeError as exc:
                _set_error(edit, True)
                invalid.append((ref, group))
                warnings.append(f"{ref}: {exc}")
                filters.extend(previous)
                continue
            if cell is not None:
                filters.append(
                    QueryFilter(ref, cell.op, cell.value, cell.value2, group=group)
                )

        for column, combo in enumerate(self._sorts):
            direction = str(combo.currentData() or "")
            if direction not in ("asc", "desc"):
                continue
            field = self.table.fields[column]
            sorts.append(QuerySort(f"{self.table.name}.{field.name}", direction))

        if invalid:
            self._warn.setText("Celle non valide: " + ", ".join(sorted({ref for ref, _ in invalid})))
        else:
            self._warn.setText("")
        return fields, filters, sorts, warnings, examples, invalid


class QbePanel(QWidget):
    """Vista QBE completa, sincronizzata con il ``QuerySpec`` del designer."""

    changed = pyqtSignal()

    def __init__(self, project: Project, spec: QuerySpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self._loading = False
        self._images: list[QbeImage] = []
        self._build_ui()
        self.reload()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        title = QLabel("Query by Example — una griglia per tabella")
        title.setObjectName("browse_header")
        bar.addWidget(title, 1)
        self.help_button = icons.make_button(
            "Aiuto QBE",
            "aiuto",
            self.show_help,
            self,
            "Sintassi delle celle e example elements",
        )
        bar.addWidget(self.help_button)
        layout.addLayout(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(6)
        self.container_layout.addStretch(1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        self.hint = QLabel(
            "Stessa riga = AND, righe diverse = OR. "
            "Valore nudo = uguale; a..b intervallo; * e ? jolly; _nome example element."
        )
        self.hint.setObjectName("nav_hint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        self.help_view = QTextBrowser()
        self.help_view.setOpenLinks(False)
        self.help_view.setOpenExternalLinks(False)
        self.help_view.setHtml(HELP_HTML)
        self.help_view.setFixedHeight(104)
        self.help_view.setAccessibleName("Guida sintassi QBE")
        self.help_view.anchorClicked.connect(self._open_help_link)
        layout.addWidget(self.help_view)

    # ------------------------------------------------------------------ reload
    def reload(self) -> None:
        """Ricostruisce le query image dal ``QuerySpec`` corrente."""
        self._loading = True
        try:
            while self.container_layout.count():
                entry = self.container_layout.takeAt(0)
                widget = entry.widget()
                if widget is not None:
                    widget.deleteLater()
            self._images = []
            for name in self.spec.table_names():
                table = self.project.table(name)
                if table is None or not table.fields:
                    continue
                image = QbeImage(self.project, self.spec, table, self.container)
                image.changed.connect(self._on_edited)
                self._images.append(image)
                self.container_layout.addWidget(image)
            self.container_layout.addStretch(1)
            self.refresh_sort_labels()
            if not self._images:
                self.hint.setText("La query non contiene tabelle con campi.")
        finally:
            self._loading = False

    def refresh_sort_labels(self) -> None:
        """Aggiorna le etichette di priorità senza ricostruire le griglie."""
        priorities = {
            item.field.lower(): index + 1 for index, item in enumerate(self.spec.sorts)
        }
        for image in self._images:
            for column, combo in enumerate(image._sorts):
                field = image.table.fields[column]
                ref = f"{image.table.name}.{field.name}".lower()
                position = priorities.get(ref)
                base_label = dict(SORT_LABELS).get(str(combo.currentData() or ""), "")
                for index in range(combo.count()):
                    value = str(combo.itemData(index) or "")
                    label = dict(SORT_LABELS).get(value, "")
                    if value and value == str(combo.currentData() or "") and position:
                        label = f"{label} ({position}°)"
                    combo.setItemText(index, label)
                if position and base_label:
                    combo.setToolTip(f"Priorità {position} nell'ordinamento della query")

    def _on_edited(self) -> None:
        if self._loading:
            return
        self.apply()
        self.changed.emit()

    # ------------------------------------------------------------------ lettura
    def apply(self) -> list[str]:
        """Scrive le griglie nel ``QuerySpec`` e restituisce gli avvisi."""
        if self._loading:
            return []
        fields: list[QueryField] = []
        filters: list[QueryFilter] = []
        sorts: list[QuerySort] = []
        warnings: list[str] = []
        examples: dict[str, list[str]] = {}

        for image in self._images:
            image_fields, image_filters, image_sorts, image_warnings, image_examples, _ = (
                image.values()
            )
            fields.extend(image_fields)
            filters.extend(image_filters)
            sorts.extend(image_sorts)
            warnings.extend(image_warnings)
            for name, refs in image_examples.items():
                examples.setdefault(name, []).extend(refs)

        for name, refs in examples.items():
            if len(refs) < 2:
                warnings.append(f"Example element _{name} usato una sola volta: ignorato")
                continue
            first = refs[0]
            for other in refs[1:]:
                filters.append(QueryFilter(first, "ref", other, group=0))
            source, target = first, refs[1]
            source_field = self._field_of(source)
            target_field = self._field_of(target)
            if (
                source_field is not None
                and target_field is not None
                and type_family(source_field.type) != type_family(target_field.type)
            ):
                warnings.append(
                    f"Example element _{name}: tipi incompatibili tra {source} e {target}"
                )

        self.spec.fields = _ordered(
            self.spec.fields,
            fields,
            lambda item: (item.table.lower(), item.field.lower()),
        )
        self.spec.filters = _ordered(
            self.spec.filters,
            filters,
            lambda item: (item.field.lower(), int(item.group), item.op),
        )
        self.spec.sorts = _ordered(
            self.spec.sorts, sorts, lambda item: item.field.lower()
        )

        left_tables = {
            join.table.lower()
            for join in self.spec.joins
            if join.kind == "left"
        }
        for item in filters:
            if item.group <= 0 or item.op == "ref":
                continue
            table_name = item.field.split(".", 1)[0].lower()
            if table_name in left_tables:
                warnings.append(
                    f"OR su {table_name} in LEFT JOIN: il risultato può escludere righe senza corrispondenza"
                )
                break

        self.refresh_sort_labels()
        if warnings:
            unique = list(dict.fromkeys(warnings))
            self.hint.setText(" · ".join(unique))
        else:
            self.hint.setText(
                "Stessa riga = AND, righe diverse = OR. "
                "Valore nudo = uguale; a..b intervallo; * e ? jolly; _nome example element."
            )
        return list(dict.fromkeys(warnings))

    def _field_of(self, ref: str):
        table_name, field_name = ref.split(".", 1)
        table = self.project.table(table_name)
        return table.field(field_name) if table is not None else None

    # ------------------------------------------------------------------ API
    def images(self) -> list[QbeImage]:
        return list(self._images)

    def image(self, table_name: str) -> QbeImage | None:
        return next(
            (
                image
                for image in self._images
                if image.table.name.lower() == table_name.lower()
            ),
            None,
        )

    def set_cell(self, table: str, field: str, group: int, text: str) -> None:
        image = self.image(table)
        if image is None:
            raise KeyError(f"tabella non presente nell'immagine QBE: {table}")
        image.set_cell(group, field, text)

    def cell_text(self, table: str, field: str, group: int) -> str:
        image = self.image(table)
        return image.cell_text(group, field) if image is not None else ""

    def apply_and_notify(self) -> list[str]:
        """Applica le griglie e segnala il cambiamento, come farebbe la UI."""
        warnings = self.apply()
        self.changed.emit()
        return warnings

    # ------------------------------------------------------------------ aiuto
    def show_help(self) -> None:
        QMessageBox.information(self, "QBE — sintassi", self.help_text())

    def help_text(self) -> str:
        return (
            "Ogni tabella ha una griglia con i suoi campi.\n\n"
            "• Includi: spunta il campo per averlo nel risultato.\n"
            "• Criteri: valore nudo = uguale; =, <>, >, >=, <, <=;\n"
            "  a..b per numeri e date; blank / not blank;\n"
            "  *testo* e te?t per il testo; _nome per un example element.\n"
            "• Stessa riga = AND; righe diverse = OR.\n"
            "• Ordinamento: la priorità segue l'ordine delle colonne.\n\n"
            "Due celle con lo stesso example element, per esempio _cliente,\n"
            "mettono in relazione i due campi. La tabella collegata deve essere\n"
            "già presente nella query.\n\n"
            "La query resta in sola lettura e non modifica i dati."
        )

    def _open_help_link(self, url: QUrl) -> None:
        path = _doc_path()
        if path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


__all__ = ["QbeImage", "QbePanel", "HELP_HTML"]
