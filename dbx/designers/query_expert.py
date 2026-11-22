"""Query Expert: crea una query guidata e la apre nel Query Designer (0.4/O2).

La procedura produce un normale :class:`QuerySpec`. I join sono suggeriti
dalle foreign key del progetto; i criteri restano in AND, mentre la modalità
QBE (O3) aggiunge le righe OR. Nessuna SQL viene scritta a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

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

from ..core.metadata import Table, slugify
from ..core.project import Project
from ..core.query_engine import preview_sql
from ..core.query_model import (
    OPERATOR_LABELS,
    SORT_DIRECTIONS,
    QueryError,
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
)
from ..ui import icons
from .expert_common import ExpertWizard, FieldTransfer


@dataclass(frozen=True)
class RelationCandidate:
    table: str
    left: str
    right: str
    label: str


def relation_candidates(project: Project, base: str) -> list[RelationCandidate]:
    """Relazioni suggerite dalle FK, in entrambe le direzioni.

    ``QueryJoin`` esprime una sola coppia di campi: per una FK composta viene
    proposta la prima colonna, che l'utente può correggere nel Query Designer.
    """
    base_table = project.table(base)
    if base_table is None:
        return []
    seen: set[str] = set()
    result: list[RelationCandidate] = []
    for fk in base_table.foreign_keys:
        target = fk.ref_table
        if target.lower() == base.lower() or target.lower() in seen:
            continue
        target_table = project.table(target)
        if target_table is None or not fk.columns or not fk.ref_columns:
            continue
        left_field = fk.columns[0]
        right_field = fk.ref_columns[0]
        seen.add(target.lower())
        result.append(
            RelationCandidate(
                table=target,
                left=f"{base}.{left_field}",
                right=f"{target}.{right_field}",
                label=f"{base}.{left_field} = {target}.{right_field}",
            )
        )
    for name in project.names("tables"):
        if name.lower() == base.lower() or name.lower() in seen:
            continue
        table = project.table(name)
        if table is None:
            continue
        for fk in table.foreign_keys:
            if fk.ref_table.lower() != base.lower():
                continue
            if not fk.columns or not fk.ref_columns:
                continue
            left_field = fk.ref_columns[0]
            right_field = fk.columns[0]
            seen.add(name.lower())
            result.append(
                RelationCandidate(
                    table=name,
                    left=f"{base}.{left_field}",
                    right=f"{name}.{right_field}",
                    label=f"{base}.{left_field} = {name}.{right_field}",
                )
            )
            break
    return result


class QueryExpert(ExpertWizard):
    """Procedura guidata in cinque passi per creare una query statica."""

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        suggested_name: str = "query",
    ) -> None:
        self.project = project
        self.suggested_name = suggested_name or "query"
        super().__init__(parent, "Query Expert")
        self.set_finish_text("Crea query")
        self.resize(820, 620)
        self._build_pages()
        self._refresh_relations()
        self._refresh_fields()
        self._refresh_summary()

    # ------------------------------------------------------------------ pagine
    def _build_pages(self) -> None:
        self._source_page = self._page_source()
        self._relations_page = self._page_relations()
        self._fields_page = self._page_fields()
        self._criteria_page = self._page_criteria()
        self._sort_page = self._page_sort()
        self._summary_page = self._page_summary()
        for page in (
            self._source_page,
            self._relations_page,
            self._fields_page,
            self._criteria_page,
            self._sort_page,
            self._summary_page,
        ):
            self.addPage(page)

    def _page_source(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Query Expert")
        page.setSubTitle(
            "Scegli la tabella base. Potrai aggiungere tabelle collegate, campi, "
            "criteri e ordinamento nei passi successivi."
        )
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.suggested_name)
        self.name_edit.setPlaceholderText("es. clienti_attivi")
        form.addRow("Nome", self.name_edit)
        self.caption_edit = QLineEdit()
        self.caption_edit.setPlaceholderText("Descrizione mostrata nel Navigator")
        form.addRow("Didascalia", self.caption_edit)
        self.base_combo = QComboBox()
        for name in self.project.names("tables"):
            table = self.project.table(name)
            if table is not None:
                self.base_combo.addItem(table.display_name(), name)
        form.addRow("Tabella base", self.base_combo)
        layout.addLayout(form)
        hint = QLabel(
            "La query è in sola lettura. I valori dei criteri sono statici e "
            "non modificabili da chi esegue la query."
        )
        hint.setWordWrap(True)
        hint.setObjectName("nav_hint")
        layout.addWidget(hint)
        layout.addStretch(1)
        self.base_combo.currentIndexChanged.connect(self._on_base_changed)
        return page

    def _page_relations(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Tabelle collegate")
        page.setSubTitle(
            "I join sono suggeriti dalle foreign key. Spunta le tabelle da includere."
        )
        layout = QVBoxLayout(page)
        self.relations_table = QTableWidget(0, 4)
        self.relations_table.setHorizontalHeaderLabels(["Includi", "Tabella", "Condizione", "Tipo"])
        self.relations_table.verticalHeader().setVisible(False)
        self.relations_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.relations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.relations_table, 1)
        self.relations_hint = QLabel("")
        self.relations_hint.setWordWrap(True)
        self.relations_hint.setObjectName("nav_hint")
        layout.addWidget(self.relations_hint)
        return page

    def _page_fields(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Campi")
        page.setSubTitle("Sposta i campi dalla sorgente alla query.")
        layout = QVBoxLayout(page)
        self.field_transfer = FieldTransfer(page)
        layout.addWidget(self.field_transfer, 1)
        return page

    def _page_criteria(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Criteri")
        page.setSubTitle("Le condizioni sono combinate in AND. Per gli OR usa la modalità QBE.")
        layout = QVBoxLayout(page)
        self.criteria_table = QTableWidget(0, 3)
        self.criteria_table.setHorizontalHeaderLabels(["Campo", "Operatore", "Valore"])
        self.criteria_table.verticalHeader().setVisible(False)
        self.criteria_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        header = self.criteria_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.criteria_table, 1)
        bar = QVBoxLayout()
        bar.setSpacing(2)
        bar.addWidget(
            icons.make_button(
                "Aggiungi criterio", "nuovo", self.add_criterion, page, "Aggiunge una condizione"
            )
        )
        bar.addWidget(
            icons.make_button(
                "Rimuovi criterio",
                "elimina",
                self.remove_criterion,
                page,
                "Rimuove la condizione selezionata",
            )
        )
        layout.addLayout(bar)
        return page

    def _page_sort(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Ordinamento")
        page.setSubTitle("I criteri sono applicati nell'ordine dell'elenco.")
        layout = QVBoxLayout(page)
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

    def _page_summary(self) -> QWizardPage:
        page = QWizardPage()
        page.setTitle("Riepilogo")
        page.setSubTitle("Controlla la query e l'SQL prima di crearla.")
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
        if page is self._relations_page:
            self._refresh_relations()
        elif page is self._fields_page:
            self._refresh_fields()
        elif page is self._criteria_page:
            self._refresh_criteria_fields()
        elif page is self._sort_page:
            self._refresh_sort_fields()
        elif page is self._summary_page:
            self._refresh_summary()

    def validateCurrentPage(self) -> bool:  # noqa: N802 - API Qt
        if self.currentPage() in (
            self._fields_page,
            self._criteria_page,
            self._sort_page,
            self._summary_page,
        ):
            try:
                self.build_spec()
            except (QueryError, ValueError) as exc:
                QMessageBox.warning(self, "Query non valida", str(exc))
                return False
        return super().validateCurrentPage()

    # ------------------------------------------------------------------ dati
    def base_table_name(self) -> str:
        return str(self.base_combo.currentData() or "")

    def base_table(self) -> Table | None:
        return self.project.table(self.base_table_name())

    def _on_base_changed(self, _index: int) -> None:
        self._refresh_relations()
        if hasattr(self, "field_transfer"):
            self.field_transfer.set_available(self._available_refs(), selected=[])
        self._refresh_fields()

    def _refresh_relations(self) -> None:
        if not hasattr(self, "relations_table"):
            return
        previous: dict[str, tuple[bool, str]] = {}
        for row in range(self.relations_table.rowCount()):
            table_item = self.relations_table.item(row, 1)
            check_item = self.relations_table.item(row, 0)
            combo = self.relations_table.cellWidget(row, 3)
            if table_item is not None:
                previous[table_item.text().lower()] = (
                    check_item.checkState() == Qt.CheckState.Checked if check_item else False,
                    str(combo.currentData()) if isinstance(combo, QComboBox) else "inner",
                )
        candidates = relation_candidates(self.project, self.base_table_name())
        self.relations_table.setRowCount(0)
        for candidate in candidates:
            row = self.relations_table.rowCount()
            self.relations_table.insertRow(row)
            check_item = QTableWidgetItem("")
            check_item.setFlags(
                (check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            checked, kind = previous.get(candidate.table.lower(), (False, "inner"))
            check_item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self.relations_table.setItem(row, 0, check_item)
            table_item = QTableWidgetItem(candidate.table)
            table_item.setFlags(table_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.relations_table.setItem(row, 1, table_item)
            condition_item = QTableWidgetItem(candidate.label)
            condition_item.setFlags(condition_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.relations_table.setItem(row, 2, condition_item)
            combo = QComboBox()
            combo.addItem("INNER JOIN", "inner")
            combo.addItem("LEFT JOIN", "left")
            combo.setCurrentIndex(max(0, combo.findData(kind)))
            self.relations_table.setCellWidget(row, 3, combo)
        if candidates:
            self.relations_hint.setText(
                "Le tabelle spuntate entrano nella query con la condizione mostrata."
            )
        else:
            self.relations_hint.setText(
                "Nessuna relazione rilevata dalle foreign key. Potrai aggiungere un join "
                "manualmente nel Query Designer."
            )

    def relations(self) -> list[QueryJoin]:
        if not hasattr(self, "relations_table"):
            return []
        candidates = {
            (candidate.table.lower(), candidate.left, candidate.right): candidate
            for candidate in relation_candidates(self.project, self.base_table_name())
        }
        joins: list[QueryJoin] = []
        for row in range(self.relations_table.rowCount()):
            check_item = self.relations_table.item(row, 0)
            table_item = self.relations_table.item(row, 1)
            combo = self.relations_table.cellWidget(row, 3)
            if check_item is None or table_item is None:
                continue
            if check_item.checkState() != Qt.CheckState.Checked:
                continue
            table = table_item.text()
            candidate = next(
                (
                    item
                    for item in candidates.values()
                    if item.table.lower() == table.lower()
                ),
                None,
            )
            if candidate is None:
                continue
            kind = str(combo.currentData()) if isinstance(combo, QComboBox) else "inner"
            if candidate is not None:
                joins.append(
                    QueryJoin(kind=kind, table=candidate.table, left=candidate.left, right=candidate.right)
                )
        return joins

    def _available_refs(self) -> list[tuple[str, str]]:
        names = [self.base_table_name()]
        names.extend(join.table for join in self.relations())
        result: list[tuple[str, str]] = []
        for name in names:
            table = self.project.table(name)
            if table is None:
                continue
            for field in table.fields:
                ref = f"{table.name}.{field.name}"
                result.append((ref, f"{table.display_name()} · {field.display_name()} ({field.type})"))
        return result

    def _refresh_fields(self) -> None:
        if not hasattr(self, "field_transfer"):
            return
        refs = self._available_refs()
        selected = self.field_transfer.selected_keys()
        if not selected:
            selected = [
                ref for ref, _label in refs if ref.split(".", 1)[0].lower() == self.base_table_name().lower()
            ]
        self.field_transfer.set_available(refs, selected=selected)

    def _refresh_criteria_fields(self) -> None:
        refs = self._available_refs()
        for row in range(self.criteria_table.rowCount()):
            combo = self.criteria_table.cellWidget(row, 0)
            if not isinstance(combo, QComboBox):
                continue
            current = str(combo.currentData() or "")
            combo.blockSignals(True)
            combo.clear()
            for ref, label in refs:
                combo.addItem(label, ref)
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.blockSignals(False)

    def _refresh_sort_fields(self) -> None:
        refs = self._available_refs()
        for row in range(self.sort_table.rowCount()):
            combo = self.sort_table.cellWidget(row, 0)
            if not isinstance(combo, QComboBox):
                continue
            current = str(combo.currentData() or "")
            combo.blockSignals(True)
            combo.clear()
            for ref, label in refs:
                combo.addItem(label, ref)
            combo.setCurrentIndex(max(0, combo.findData(current)))
            combo.blockSignals(False)

    def add_criterion(self) -> None:
        row = self.criteria_table.rowCount()
        self.criteria_table.insertRow(row)
        combo = QComboBox()
        for ref, label in self._available_refs():
            combo.addItem(label, ref)
        self.criteria_table.setCellWidget(row, 0, combo)
        operator = QComboBox()
        for key, label in OPERATOR_LABELS.items():
            operator.addItem(label, key)
        self.criteria_table.setCellWidget(row, 1, operator)
        value = QLineEdit()
        self.criteria_table.setCellWidget(row, 2, value)

    def remove_criterion(self) -> None:
        row = self.criteria_table.currentRow()
        if row >= 0:
            self.criteria_table.removeRow(row)

    def criteria(self) -> list[QueryFilter]:
        filters: list[QueryFilter] = []
        for row in range(self.criteria_table.rowCount()):
            field_combo = self.criteria_table.cellWidget(row, 0)
            op_combo = self.criteria_table.cellWidget(row, 1)
            value_edit = self.criteria_table.cellWidget(row, 2)
            if not isinstance(field_combo, QComboBox) or not isinstance(op_combo, QComboBox):
                continue
            ref = str(field_combo.currentData() or "")
            if not ref:
                continue
            value = value_edit.text().strip() if isinstance(value_edit, QLineEdit) else ""
            op = str(op_combo.currentData() or "eq")
            if op in ("null", "notnull"):
                value = ""
            filters.append(QueryFilter(field=ref, op=op, value=value))
        return filters

    def add_sort(self) -> None:
        row = self.sort_table.rowCount()
        self.sort_table.insertRow(row)
        combo = QComboBox()
        for ref, label in self._available_refs():
            combo.addItem(label, ref)
        self.sort_table.setCellWidget(row, 0, combo)
        direction = QComboBox()
        direction.addItem("Crescente", "asc")
        direction.addItem("Decrescente", "desc")
        self.sort_table.setCellWidget(row, 1, direction)

    def remove_sort(self) -> None:
        row = self.sort_table.currentRow()
        if row >= 0:
            self.sort_table.removeRow(row)

    def sorts(self) -> list[QuerySort]:
        result: list[QuerySort] = []
        for row in range(self.sort_table.rowCount()):
            combo = self.sort_table.cellWidget(row, 0)
            direction = self.sort_table.cellWidget(row, 1)
            if not isinstance(combo, QComboBox):
                continue
            ref = str(combo.currentData() or "")
            if not ref:
                continue
            result.append(
                QuerySort(
                    field=ref,
                    direction=(
                        str(direction.currentData())
                        if isinstance(direction, QComboBox)
                        and str(direction.currentData()) in SORT_DIRECTIONS
                        else "asc"
                    ),
                )
            )
        return result

    # ------------------------------------------------------------------ output
    def build_spec(self) -> QuerySpec:
        base = self.base_table_name()
        if not base:
            raise QueryError("Scegli una tabella base")
        fields: list[QueryField] = []
        for ref in self.field_transfer.selected_keys():
            if "." not in ref:
                continue
            table, field = ref.split(".", 1)
            fields.append(QueryField(table=table, field=field))
        if not fields:
            raise QueryError("La query non seleziona alcun campo")
        spec = QuerySpec(
            name=slugify(self.name_edit.text().strip() or self.suggested_name),
            caption=self.caption_edit.text().strip() or f"Query {self.base_table().display_name()}",
            base=base,
            fields=fields,
            joins=self.relations(),
            filters=self.criteria(),
            sorts=self.sorts(),
        )
        errors = spec.validate(self.project.tables())
        if errors:
            raise QueryError("\n".join(errors))
        return spec

    def _refresh_summary(self) -> None:
        try:
            spec = self.build_spec()
        except (QueryError, ValueError) as exc:
            self.summary_label.setText("Query non valida")
            self.summary_view.setPlainText(f"-- Errore:\n{exc}")
            return
        self.summary_label.setText(
            f"{spec.caption or spec.name} · {len(spec.fields)} campi · "
            f"{len(spec.joins)} join · {len(spec.filters)} criteri · {len(spec.sorts)} ordinamenti"
        )
        try:
            self.summary_view.setPlainText(preview_sql(self.project, spec))
        except Exception as exc:  # pragma: no cover - difensivo
            self.summary_view.setPlainText(f"-- Errore SQL:\n{exc}")

    def help_text(self) -> str:
        return (
            "1. Scegli nome, didascalia e tabella base.\n"
            "2. Spunta le tabelle collegate suggerite dalle foreign key.\n"
            "3. Scegli i campi da includere.\n"
            "4. Aggiungi i criteri (AND).\n"
            "5. Aggiungi l'ordinamento e controlla l'SQL.\n\n"
            "Dopo la creazione potrai aggiungere OR, between ed example elements "
            "nella modalità QBE del Query Designer."
        )


__all__ = ["QueryExpert", "RelationCandidate", "relation_candidates"]
