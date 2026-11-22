"""Query Designer: tabelle, join, campi, filtri, ordinamento e anteprima (0.3).

Il designer produce e consuma lo stesso JSON del motore (``QuerySpec``): non
esegue SQL scritto a mano e non contiene logica dati. L'anteprima usa
``query_engine`` sullo schema reale del progetto.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.metadata import Table
from ..core.project import Project, ProjectError
from ..core.query_engine import QueryError, engine_for, preview_sql
from ..core.query_model import (
    AGGREGATE_FUNCTIONS,
    AGGREGATE_LABELS,
    ALL_OPERATORS,
    JOIN_KINDS,
    JOIN_LABELS,
    OPERATOR_LABELS,
    SORT_DIRECTIONS,
    QueryAggregate,
    QueryField,
    QueryFilter,
    QueryJoin,
    QuerySort,
    QuerySpec,
)
from ..ui import icons
from .qbe_panel import QbePanel

RESULT_ROW_LIMIT = 500


class NewQueryDialog(QDialog):
    """Sceglie nome, didascalia e tabella base di una nuova query."""

    def __init__(
        self,
        project: Project,
        parent: QWidget | None = None,
        suggested_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Nuova query")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(suggested_name)
        self.name_edit.setPlaceholderText("es. fatture_clienti")
        self.caption_edit = QLineEdit()
        self.caption_edit.setPlaceholderText("Descrizione mostrata nel Navigator")
        self.table_combo = QComboBox()
        for name in project.names("tables"):
            table = project.table(name)
            if table is not None:
                self.table_combo.addItem(table.display_name(), name)
        form.addRow("Nome", self.name_edit)
        form.addRow("Didascalia", self.caption_edit)
        form.addRow("Tabella base", self.table_combo)
        layout.addLayout(form)
        hint = QLabel(
            "La query seleziona solo campi e non modifica i dati. "
            "Potrai aggiungere join, filtri e ordinamento nel designer."
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
        self.resize(460, 220)

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Nuova query", "Indica un nome per la query.")
            return
        if not self.table_combo.currentData():
            QMessageBox.warning(self, "Nuova query", "Crea prima una tabella.")
            return
        super().accept()

    def spec(self) -> QuerySpec:
        table = self.project.require_table(str(self.table_combo.currentData() or ""))
        spec = QuerySpec.create(
            table,
            name=self.name_edit.text().strip(),
            caption=self.caption_edit.text().strip(),
        )
        return spec


class JoinDialog(QDialog):
    """Aggiunge una tabella alla query con una condizione di join."""

    def __init__(self, project: Project, spec: QuerySpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project = project
        self.spec = spec
        self.setWindowTitle("Aggiungi tabella alla query")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.table_combo = QComboBox()
        current = {name.lower() for name in spec.table_names()}
        for name in project.names("tables"):
            if name.lower() not in current:
                table = project.table(name)
                if table is not None:
                    self.table_combo.addItem(table.display_name(), name)
        self.kind_combo = QComboBox()
        for kind in JOIN_KINDS:
            self.kind_combo.addItem(JOIN_LABELS.get(kind, kind), kind)
        self.left_combo = QComboBox()
        self.right_combo = QComboBox()
        form.addRow("Tabella", self.table_combo)
        form.addRow("Tipo di join", self.kind_combo)
        form.addRow("Campo esistente", self.left_combo)
        form.addRow("Campo della tabella", self.right_combo)
        layout.addLayout(form)
        hint = QLabel(
            "Il join collega la tabella scelta alle tabelle già presenti. "
            "Se esiste una relazione nel database, dBX propone i campi corretti."
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
        self.table_combo.currentIndexChanged.connect(self._refresh)
        self.left_combo.currentIndexChanged.connect(self._suggest_right)
        self._refresh()
        self.resize(500, 280)

    # ------------------------------------------------------------------ combo
    def _tables_in_query(self) -> list[Table]:
        tables: list[Table] = []
        for name in self.spec.table_names():
            table = self.project.table(name)
            if table is not None:
                tables.append(table)
        return tables

    def _refresh(self) -> None:
        self.left_combo.blockSignals(True)
        self.left_combo.clear()
        for table in self._tables_in_query():
            for field in table.stored_fields:
                self.left_combo.addItem(
                    f"{table.name}.{field.name} — {field.display_name()}",
                    f"{table.name}.{field.name}",
                )
        self.left_combo.blockSignals(False)
        self._refresh_right()
        self._suggest_pair()

    def _refresh_right(self) -> None:
        table = self.project.table(str(self.table_combo.currentData() or ""))
        current = str(self.right_combo.currentData() or "")
        self.right_combo.blockSignals(True)
        self.right_combo.clear()
        if table is not None:
            for field in table.stored_fields:
                self.right_combo.addItem(
                    f"{field.name} — {field.display_name()}", field.name
                )
        index = self.right_combo.findData(current)
        if index >= 0:
            self.right_combo.setCurrentIndex(index)
        self.right_combo.blockSignals(False)

    def _suggest_pair(self) -> None:
        join_table = self.project.table(str(self.table_combo.currentData() or ""))
        if join_table is None:
            return
        available = {table.name.lower(): table for table in self._tables_in_query()}
        # Relazione dichiarata: figlio -> padre.
        for table in available.values():
            for fk in table.foreign_keys:
                if fk.ref_table.lower() != join_table.name.lower():
                    continue
                if len(fk.columns) != 1 or len(fk.ref_columns) != 1:
                    continue
                self._select(self.left_combo, f"{table.name}.{fk.columns[0]}")
                self._select(self.right_combo, fk.ref_columns[0])
                return
            for fk in join_table.foreign_keys:
                if fk.ref_table.lower() != table.name.lower():
                    continue
                if len(fk.columns) != 1 or len(fk.ref_columns) != 1:
                    continue
                self._select(self.left_combo, f"{table.name}.{fk.ref_columns[0]}")
                self._select(self.right_combo, fk.columns[0])
                return
        # Fallback: campo omonimo, poi chiave primaria.
        for candidate in available.values():
            for field in candidate.fields:
                if join_table.field(field.name) is not None:
                    self._select(self.left_combo, f"{candidate.name}.{field.name}")
                    self._select(self.right_combo, field.name)
                    return
        if self.left_combo.count():
            self.left_combo.setCurrentIndex(0)
        primary = next((field for field in join_table.fields if field.pk), None)
        if primary is not None:
            self._select(self.right_combo, primary.name)

    def _suggest_right(self) -> None:
        left = str(self.left_combo.currentData() or "")
        if "." not in left:
            return
        _, field_name = left.split(".", 1)
        index = self.right_combo.findData(field_name)
        if index >= 0:
            self.right_combo.setCurrentIndex(index)

    @staticmethod
    def _select(combo: QComboBox, data: str) -> None:
        index = combo.findData(data)
        if index >= 0:
            combo.setCurrentIndex(index)

    def join(self) -> QueryJoin | None:
        table = str(self.table_combo.currentData() or "")
        left = str(self.left_combo.currentData() or "")
        right = str(self.right_combo.currentData() or "")
        if not (table and left and right):
            return None
        return QueryJoin(
            kind=str(self.kind_combo.currentData() or "inner"),
            table=table,
            left=left,
            right=f"{table}.{right}",
        )


class QueryDesignerWidget(QWidget):
    """Designer di una query salvata nel progetto."""

    saved = pyqtSignal(str)
    status_message = pyqtSignal(str)
    results_requested = pyqtSignal(str)

    def __init__(self, project: Project, spec: QuerySpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("query_designer")
        self.project = project
        self.spec = spec
        self._saved_name = spec.name
        self._saved_state = spec.to_dict()
        self._loading_tree = False
        self._loading_fields = False
        self._loading_filters = False
        self._loading_sorts = False
        self._result_stale = True
        self.setWindowTitle(f"Query Designer — {spec.caption or spec.name}")
        self.resize(1120, 760)
        self._build_ui()
        self._reload()

    # --------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(4)
        header.addWidget(QLabel("Nome:"))
        self.name_edit = QLineEdit(self.spec.name)
        self.name_edit.setMinimumWidth(190)
        self.name_edit.editingFinished.connect(self._on_name_changed)
        header.addWidget(self.name_edit)
        header.addWidget(QLabel("Didascalia:"))
        self.caption_edit = QLineEdit(self.spec.caption)
        self.caption_edit.editingFinished.connect(self._on_name_changed)
        header.addWidget(self.caption_edit, 1)
        layout.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)
        self.save_button = icons.make_button(
            "Salva", "salva", self.save, self, "Salva la query nel progetto"
        )
        self.run_button = icons.make_button(
            "Esegui anteprima", "esegui", self.run_preview, self, "Esegue la query in sola lettura"
        )
        self.results_button = icons.make_button(
            "Query Results", "cerca", self.open_results, self,
            "Apre il risultato in una finestra dedicata",
        )
        self.add_field_button = icons.make_button(
            "Aggiungi campo", "campo", self.add_selected_field, self, "Aggiunge il campo selezionato"
        )
        self.add_table_button = icons.make_button(
            "Aggiungi tabella", "tabella", self.add_join, self, "Aggiunge una tabella con join"
        )
        self.remove_table_button = icons.make_button(
            "Rimuovi tabella", "elimina", self.remove_selected_table, self,
            "Rimuove la tabella selezionata dalla query",
        )
        self.qbe_mode_button = icons.make_button(
            "QBE", "cerca", lambda: self.set_mode("qbe"), self,
            "Vista Query by Example", checkable=True,
        )
        self.guided_mode_button = icons.make_button(
            "Guidato", "tabella", lambda: self.set_mode("guided"), self,
            "Vista guidata con schede", checkable=True,
        )
        toolbar.addWidget(self.qbe_mode_button)
        toolbar.addWidget(self.guided_mode_button)
        toolbar.addSpacing(12)
        for button in (
            self.save_button,
            self.run_button,
            self.results_button,
            self.add_field_button,
            self.add_table_button,
            self.remove_table_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("nav_hint")
        toolbar.addWidget(self.status_label)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        title = QLabel("Tabelle e campi")
        title.setObjectName("browse_header")
        left_layout.addWidget(title)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Campo", "Tipo"])
        self.tree.setRootIsDecorated(True)
        self.tree.setAlternatingRowColors(False)
        self.tree.header().setStretchLastSection(False)
        self.tree.setColumnWidth(0, 190)
        self.tree.setColumnWidth(1, 70)
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        self.tree.itemDoubleClicked.connect(self._on_tree_double_clicked)
        left_layout.addWidget(self.tree, 1)
        hint = QLabel("Spunta un campo per aggiungerlo alla query.")
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)
        splitter.addWidget(left)

        self.tabs = QTabWidget()
        self.qbe_page = QbePanel(self.project, self.spec)
        self.qbe_page.changed.connect(self._on_qbe_changed)
        self.tabs.addTab(self.qbe_page, "QBE")
        self.fields_page = self._build_fields_tab()
        self.tabs.addTab(self.fields_page, "Campi")
        self.tabs.addTab(self._build_group_tab(), "Raggruppa")
        self.tabs.addTab(self._build_filters_tab(), "Filtri")
        self.tabs.addTab(self._build_sorts_tab(), "Ordinamento")
        self.tabs.addTab(self._build_sql_tab(), "SQL")
        self.result_page = self._build_result_tab()
        self.tabs.addTab(self.result_page, "Risultato")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self.tabs)
        splitter.setSizes([360, 760])
        layout.addWidget(splitter, 1)
        self.tabs.setCurrentWidget(self.fields_page)
        self._sync_mode_buttons()

    def _build_fields_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.fields_table = QTableWidget(0, 2)
        self.fields_table.setHorizontalHeaderLabels(["Campo", "Alias"])
        self.fields_table.verticalHeader().setVisible(False)
        self.fields_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.fields_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.fields_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.fields_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.fields_table.itemChanged.connect(self._on_field_item_changed)
        layout.addWidget(self.fields_table, 1)
        buttons = QHBoxLayout()
        self.remove_field_button = icons.make_button(
            "Rimuovi campo", "elimina", self.remove_selected_field, self,
            "Toglie il campo selezionato dalla query",
        )
        buttons.addWidget(self.remove_field_button)
        buttons.addStretch(1)
        buttons.addWidget(QLabel("Doppio clic su un campo per aggiungerlo."))
        layout.addLayout(buttons)
        return page

    def _build_group_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Raggruppa per (una riga per campo)"))
        self.group_table = QTableWidget(0, 1)
        self.group_table.setHorizontalHeaderLabels(["Campo"])
        self.group_table.verticalHeader().setVisible(False)
        self.group_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.group_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.group_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.group_table, 1)
        group_bar = QHBoxLayout()
        group_bar.addWidget(
            icons.make_button(
                "Aggiungi raggruppamento", "nuovo", self.add_group_field, self,
                "Aggiunge un campo alla clausola GROUP BY",
            )
        )
        group_bar.addWidget(
            icons.make_button(
                "Rimuovi raggruppamento", "elimina", self.remove_group_field, self,
                "Toglie il raggruppamento selezionato",
            )
        )
        group_bar.addStretch(1)
        layout.addLayout(group_bar)

        layout.addWidget(QLabel("Aggregati (SUM, COUNT, AVG, MIN, MAX)"))
        self.aggregates_table = QTableWidget(0, 3)
        self.aggregates_table.setHorizontalHeaderLabels(["Funzione", "Campo", "Alias"])
        self.aggregates_table.verticalHeader().setVisible(False)
        self.aggregates_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.aggregates_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.aggregates_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.aggregates_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.aggregates_table, 1)
        agg_bar = QHBoxLayout()
        agg_bar.addWidget(
            icons.make_button(
                "Aggiungi aggregato", "somma", self.add_aggregate, self,
                "Aggiunge una colonna calcolata con funzione di aggregazione",
            )
        )
        agg_bar.addWidget(
            icons.make_button(
                "Rimuovi aggregato", "elimina", self.remove_aggregate, self,
                "Toglie l'aggregato selezionato",
            )
        )
        agg_bar.addStretch(1)
        hint = QLabel(
            "I campi selezionati devono comparire in Raggruppa per; "
            "l'alias dell'aggregato può essere usato in Ordinamento."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        agg_bar.addWidget(hint)
        layout.addLayout(agg_bar)
        return page

    def _build_filters_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.filters_table = QTableWidget(0, 4)
        self.filters_table.setHorizontalHeaderLabels(["Campo", "Operatore", "Valore", "Gruppo"])
        self.filters_table.verticalHeader().setVisible(False)
        self.filters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.filters_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.filters_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.filters_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.filters_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.filters_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.filters_table.cellChanged.connect(self._on_filter_cell_changed)
        layout.addWidget(self.filters_table, 1)
        buttons = QHBoxLayout()
        self.add_filter_button = icons.make_button(
            "Aggiungi filtro", "nuovo", self.add_filter, self, "Aggiunge una condizione"
        )
        self.remove_filter_button = icons.make_button(
            "Rimuovi filtro", "elimina", self.remove_selected_filter, self,
            "Rimuove la condizione selezionata",
        )
        buttons.addWidget(self.add_filter_button)
        buttons.addWidget(self.remove_filter_button)
        buttons.addStretch(1)
        hint = QLabel(
            "Gruppo uguale = AND, gruppi diversi = OR. "
            "I valori non sono modificabili da chi esegue la query."
        )
        hint.setObjectName("nav_hint")
        hint.setWordWrap(True)
        buttons.addWidget(hint)
        layout.addLayout(buttons)
        return page

    def _build_sorts_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.sorts_table = QTableWidget(0, 2)
        self.sorts_table.setHorizontalHeaderLabels(["Campo", "Direzione"])
        self.sorts_table.verticalHeader().setVisible(False)
        self.sorts_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sorts_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sorts_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.sorts_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.sorts_table, 1)
        buttons = QHBoxLayout()
        self.add_sort_button = icons.make_button(
            "Aggiungi ordinamento", "nuovo", self.add_sort, self, "Aggiunge un criterio"
        )
        self.remove_sort_button = icons.make_button(
            "Rimuovi ordinamento", "elimina", self.remove_selected_sort, self,
            "Rimuove il criterio selezionato",
        )
        self.up_sort_button = icons.make_button(
            "Sposta su", "su", lambda: self.move_sort(-1), self, "Sposta prima il criterio"
        )
        self.down_sort_button = icons.make_button(
            "Sposta giù", "giu", lambda: self.move_sort(1), self, "Sposta dopo il criterio"
        )
        for button in (
            self.add_sort_button,
            self.remove_sort_button,
            self.up_sort_button,
            self.down_sort_button,
        ):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return page

    def _build_sql_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        self.sql_edit = QPlainTextEdit()
        self.sql_edit.setReadOnly(True)
        self.sql_edit.setAccessibleName("Anteprima SQL della query")
        self.sql_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = self.sql_edit.font()
        font.setFamily("monospace")
        self.sql_edit.setFont(font)
        layout.addWidget(self.sql_edit, 1)
        return page

    def _build_result_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        self.result_table = QTableWidget(0, 0)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.verticalHeader().setVisible(False)
        layout.addWidget(self.result_table, 1)
        self.result_label = QLabel("Esegui l'anteprima per vedere le righe.")
        self.result_label.setObjectName("nav_hint")
        layout.addWidget(self.result_label)
        return page

    # ------------------------------------------------------------------ reload
    def _reload(self) -> None:
        self._refresh_tree()
        self._refresh_fields()
        self._refresh_filters()
        self._refresh_sorts()
        self._refresh_grouping()
        self._refresh_qbe()
        self._refresh_sql()
        self._refresh_status()

    def _refresh_qbe(self) -> None:
        if hasattr(self, "qbe_page"):
            self.qbe_page.reload()

    def _on_qbe_changed(self) -> None:
        """La vista QBE ha modificato lo stesso ``QuerySpec``: riallinea il guidato."""
        self._refresh_tree()
        self._refresh_fields()
        self._refresh_filters()
        self._refresh_sorts()
        self._refresh_grouping()
        self._mark_dirty()

    def set_mode(self, mode: str) -> None:
        """Mostra la vista QBE oppure la scheda guidata dei campi."""
        if mode == "qbe":
            self.tabs.setCurrentWidget(self.qbe_page)
        else:
            self.tabs.setCurrentWidget(self.fields_page)
        self._sync_mode_buttons()

    def _sync_mode_buttons(self) -> None:
        if not hasattr(self, "qbe_mode_button"):
            return
        qbe = self.tabs.currentWidget() is self.qbe_page
        self.qbe_mode_button.setChecked(qbe)
        self.guided_mode_button.setChecked(not qbe)

    def _refresh_tree(self) -> None:
        self._loading_tree = True
        self.tree.clear()
        included = {(item.table.lower(), item.field.lower()) for item in self.spec.fields}
        for table_name in self.spec.table_names():
            table = self.project.table(table_name)
            if table is None:
                continue
            relation = "BASE"
            join = next(
                (item for item in self.spec.joins if item.table.lower() == table.name.lower()),
                None,
            )
            if join is not None:
                relation = JOIN_LABELS.get(join.kind, join.kind).replace(" JOIN", "")
            node = QTreeWidgetItem([table.display_name(), relation])
            node.setData(0, Qt.ItemDataRole.UserRole, ("table", table.name))
            node.setToolTip(0, f"Tabella {table.name}")
            self.tree.addTopLevelItem(node)
            for field in table.stored_fields:
                child = QTreeWidgetItem([field.name, field.type.upper()])
                child.setData(0, Qt.ItemDataRole.UserRole, ("field", table.name, field.name))
                child.setData(1, Qt.ItemDataRole.UserRole, field.display_name())
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                checked = (table.name.lower(), field.name.lower()) in included
                child.setCheckState(
                    0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                )
                child.setToolTip(0, field.display_name())
                node.addChild(child)
            node.setExpanded(True)
        self._loading_tree = False

    def _refresh_fields(self) -> None:
        self._loading_fields = True
        self.fields_table.setRowCount(0)
        for item in self.spec.fields:
            row = self.fields_table.rowCount()
            self.fields_table.insertRow(row)
            label = f"{item.table}.{item.field}"
            cell = QTableWidgetItem(label)
            cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.fields_table.setItem(row, 0, cell)
            self.fields_table.setItem(row, 1, QTableWidgetItem(item.alias))
        self._loading_fields = False

    def _available_refs(self) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for table_name in self.spec.table_names():
            table = self.project.table(table_name)
            if table is None:
                continue
            for field in table.stored_fields:
                ref = f"{table.name}.{field.name}"
                result.append((ref, f"{ref} — {field.display_name()}"))
        return result

    # ------------------------------------------------------------ raggruppa
    def _refresh_grouping(self) -> None:
        if not hasattr(self, "group_table"):
            return
        options = self._available_refs()
        self.group_table.setRowCount(0)
        for ref in self.spec.group_by:
            row = self.group_table.rowCount()
            self.group_table.insertRow(row)
            combo = QComboBox()
            for value, label in options:
                combo.addItem(label, value)
            combo.setCurrentIndex(max(0, combo.findData(ref)))
            combo.currentIndexChanged.connect(lambda _index: self._collect_group_by())
            self.group_table.setCellWidget(row, 0, combo)

        self.aggregates_table.setRowCount(0)
        for aggregate in self.spec.aggregates:
            row = self.aggregates_table.rowCount()
            self.aggregates_table.insertRow(row)
            function_combo = QComboBox()
            for key, label in AGGREGATE_LABELS.items():
                function_combo.addItem(label, key)
            function_combo.setCurrentIndex(
                max(0, function_combo.findData(aggregate.function))
            )
            function_combo.currentIndexChanged.connect(
                lambda _index, r=row: self._on_aggregate_function_changed(r)
            )
            self.aggregates_table.setCellWidget(row, 0, function_combo)
            field_combo = QComboBox()
            self._populate_aggregate_fields(
                field_combo,
                aggregate.function,
                f"{aggregate.table}.{aggregate.field}" if aggregate.field else "",
            )
            field_combo.currentIndexChanged.connect(
                lambda _index: self._collect_aggregates()
            )
            self.aggregates_table.setCellWidget(row, 1, field_combo)
            alias = QLineEdit(aggregate.alias)
            alias.setPlaceholderText("alias")
            alias.textChanged.connect(lambda _text: self._collect_aggregates())
            self.aggregates_table.setCellWidget(row, 2, alias)

    def _populate_aggregate_fields(
        self, combo: QComboBox, function: str, selected: str = ""
    ) -> None:
        combo.blockSignals(True)
        combo.clear()
        if function == "count":
            combo.addItem("(tutti i record)", "")
        for value, label in self._available_refs():
            combo.addItem(label, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _on_aggregate_function_changed(self, row: int) -> None:
        function_combo = self.aggregates_table.cellWidget(row, 0)
        field_combo = self.aggregates_table.cellWidget(row, 1)
        if not isinstance(function_combo, QComboBox) or not isinstance(field_combo, QComboBox):
            return
        function = str(function_combo.currentData() or "count")
        current = str(field_combo.currentData() or "")
        self._populate_aggregate_fields(field_combo, function, current)
        self._collect_aggregates()
        self._refresh_sorts()

    def _collect_group_by(self) -> None:
        values: list[str] = []
        for row in range(self.group_table.rowCount()):
            combo = self.group_table.cellWidget(row, 0)
            if isinstance(combo, QComboBox):
                ref = str(combo.currentData() or "")
                if ref and ref not in values:
                    values.append(ref)
        self.spec.group_by = values
        self._mark_dirty()

    def _collect_aggregates(self) -> None:
        aggregates: list[QueryAggregate] = []
        for row in range(self.aggregates_table.rowCount()):
            function_combo = self.aggregates_table.cellWidget(row, 0)
            field_combo = self.aggregates_table.cellWidget(row, 1)
            alias_edit = self.aggregates_table.cellWidget(row, 2)
            if not isinstance(function_combo, QComboBox) or not isinstance(field_combo, QComboBox):
                continue
            ref = str(field_combo.currentData() or "")
            table, field = (ref.split(".", 1) + [""])[:2] if ref else ("", "")
            aggregates.append(
                QueryAggregate(
                    function=str(function_combo.currentData() or "count"),
                    table=table,
                    field=field,
                    alias=alias_edit.text().strip() if isinstance(alias_edit, QLineEdit) else "",
                )
            )
        self.spec.aggregates = aggregates
        self._mark_dirty()

    def add_group_field(self) -> None:
        options = self._available_refs()
        used = {ref.lower() for ref in self.spec.group_by}
        choice = next((ref for ref, _label in options if ref.lower() not in used), "")
        if not choice:
            return
        self.spec.group_by.append(choice)
        self._refresh_grouping()
        self._refresh_status()
        self._mark_dirty()

    def remove_group_field(self) -> None:
        row = self.group_table.currentRow()
        if 0 <= row < len(self.spec.group_by):
            self.spec.group_by.pop(row)
            self._refresh_grouping()
            self._refresh_status()
            self._mark_dirty()

    def add_aggregate(self) -> None:
        base = self.spec.base or (self.spec.table_names()[0] if self.spec.table_names() else "")
        self.spec.aggregates.append(QueryAggregate(function="count", table=base))
        self._refresh_grouping()
        self._refresh_sorts()
        self.aggregates_table.setCurrentCell(len(self.spec.aggregates) - 1, 0)
        self._refresh_status()
        self._mark_dirty()

    def remove_aggregate(self) -> None:
        row = self.aggregates_table.currentRow()
        if 0 <= row < len(self.spec.aggregates):
            self.spec.aggregates.pop(row)
            self._refresh_grouping()
            self._refresh_sorts()
            self._refresh_status()
            self._mark_dirty()

    def _refresh_filters(self) -> None:
        self._loading_filters = True
        self.filters_table.setRowCount(0)
        options = self._available_refs()
        for item in self.spec.filters:
            row = self.filters_table.rowCount()
            self.filters_table.insertRow(row)
            field_combo = QComboBox()
            for ref, label in options:
                field_combo.addItem(label, ref)
            index = field_combo.findData(item.field)
            field_combo.setCurrentIndex(max(0, index))
            field_combo.currentIndexChanged.connect(
                lambda _index, r=row: self._on_filter_combo_changed(r)
            )
            self.filters_table.setCellWidget(row, 0, field_combo)
            op_combo = QComboBox()
            for op in ALL_OPERATORS:
                op_combo.addItem(OPERATOR_LABELS[op], op)
            op_combo.setCurrentIndex(max(0, op_combo.findData(item.op)))
            op_combo.currentIndexChanged.connect(
                lambda _index, r=row: self._on_filter_combo_changed(r)
            )
            self.filters_table.setCellWidget(row, 1, op_combo)
            self.filters_table.setItem(row, 2, QTableWidgetItem(item.value))
            group_item = QTableWidgetItem(str(item.group))
            group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            group_item.setToolTip("Stesso gruppo = AND, gruppi diversi = OR")
            self.filters_table.setItem(row, 3, group_item)
        self._loading_filters = False

    def _refresh_sorts(self) -> None:
        self._loading_sorts = True
        self.sorts_table.setRowCount(0)
        options = self._available_refs()
        if self.spec.grouped:
            options.extend(
                (name, f"{name} — colonna aggregata")
                for name in self.spec.aggregate_output_names()
            )
        for item in self.spec.sorts:
            row = self.sorts_table.rowCount()
            self.sorts_table.insertRow(row)
            field_combo = QComboBox()
            for ref, label in options:
                field_combo.addItem(label, ref)
            field_combo.setCurrentIndex(max(0, field_combo.findData(item.field)))
            field_combo.currentIndexChanged.connect(
                lambda _index, r=row: self._on_sort_combo_changed(r)
            )
            self.sorts_table.setCellWidget(row, 0, field_combo)
            dir_combo = QComboBox()
            for direction, label in (("asc", "Crescente"), ("desc", "Decrescente")):
                dir_combo.addItem(label, direction)
            dir_combo.setCurrentIndex(max(0, dir_combo.findData(item.direction)))
            dir_combo.currentIndexChanged.connect(
                lambda _index, r=row: self._on_sort_combo_changed(r)
            )
            self.sorts_table.setCellWidget(row, 1, dir_combo)
        self._loading_sorts = False

    def _refresh_sql(self) -> None:
        try:
            self.sql_edit.setPlainText(preview_sql(self.project, self.spec))
            self.sql_edit.setProperty("state", "ok")
        except QueryError as exc:
            self.sql_edit.setPlainText(f"-- Query non valida:\n{exc}")
            self.sql_edit.setProperty("state", "error")

    def _refresh_status(self) -> None:
        if self._result_stale:
            state = "anteprima da aggiornare"
        else:
            state = "anteprima aggiornata"
        group_part = (
            f" · {len(self.spec.group_by)} raggruppamenti · "
            f"{len(self.spec.aggregates)} aggregati"
            if self.spec.grouped
            else ""
        )
        self.status_label.setText(
            f"{len(self.spec.fields)} campi · {len(self.spec.joins)} join · "
            f"{len(self.spec.filters)} filtri{group_part} · {state}"
        )

    # ------------------------------------------------------------------ stato
    def _mark_dirty(self) -> None:
        self._result_stale = True
        self._refresh_sql()
        self._refresh_status()

    def is_dirty(self) -> bool:
        return self.spec.to_dict() != self._saved_state

    def _on_name_changed(self) -> None:
        name = self.name_edit.text().strip()
        if name and name != self.spec.name:
            self.spec.name = name
            self._mark_dirty()
        self.spec.caption = self.caption_edit.text().strip()
        self.setWindowTitle(f"Query Designer — {self.spec.caption or self.spec.name}")
        self._mark_dirty()

    # ------------------------------------------------------------------ campi
    def _on_tree_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._loading_tree:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, tuple) or data[0] != "field":
            return
        _, table, field = data
        checked = item.checkState(0) == Qt.CheckState.Checked
        if checked:
            self.add_field(table, field, reload_tree=False)
        else:
            self.remove_field(table, field, reload_tree=False)

    def _on_tree_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, tuple) and data[0] == "field":
            item.setCheckState(
                0,
                Qt.CheckState.Unchecked
                if item.checkState(0) == Qt.CheckState.Checked
                else Qt.CheckState.Checked,
            )

    def add_selected_field(self) -> None:
        data = self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole) if self.tree.currentItem() else None
        if isinstance(data, tuple) and data[0] == "field":
            self.add_field(data[1], data[2], reload_tree=False)

    def add_field(self, table: str, field: str, reload_tree: bool = True) -> None:
        if any(
            item.table.lower() == table.lower() and item.field.lower() == field.lower()
            for item in self.spec.fields
        ):
            return
        self.spec.fields.append(QueryField(table, field))
        if reload_tree:
            self._refresh_tree()
        self._refresh_fields()
        self._refresh_filters()
        self._refresh_sorts()
        self._refresh_grouping()
        self._refresh_qbe()
        self._mark_dirty()

    def remove_selected_field(self) -> None:
        row = self.fields_table.currentRow()
        if row < 0 or row >= len(self.spec.fields):
            return
        item = self.spec.fields.pop(row)
        self.remove_field(item.table, item.field)

    def remove_field(self, table: str, field: str, reload_tree: bool = True) -> None:
        self.spec.fields = [
            item
            for item in self.spec.fields
            if not (
                item.table.lower() == table.lower() and item.field.lower() == field.lower()
            )
        ]
        prefix = f"{table}.{field}".lower()
        self.spec.filters = [
            item for item in self.spec.filters if item.field.lower() != prefix
        ]
        self.spec.sorts = [
            item for item in self.spec.sorts if item.field.lower() != prefix
        ]
        self.spec.group_by = [
            ref for ref in self.spec.group_by if ref.lower() != prefix
        ]
        self.spec.aggregates = [
            item
            for item in self.spec.aggregates
            if item.ref.lower() != prefix
        ]
        if reload_tree:
            self._refresh_tree()
        self._refresh_fields()
        self._refresh_filters()
        self._refresh_sorts()
        self._refresh_grouping()
        self._refresh_qbe()
        self._mark_dirty()

    def _on_field_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_fields or item.column() != 1:
            return
        row = item.row()
        if 0 <= row < len(self.spec.fields):
            self.spec.fields[row].alias = item.text().strip()
            self._mark_dirty()

    # ------------------------------------------------------------------ join
    def add_join(self) -> None:
        if len(self.spec.table_names()) >= len(self.project.names("tables")):
            QMessageBox.information(
                self, "Aggiungi tabella", "Tutte le tabelle sono già presenti nella query."
            )
            return
        dialog = JoinDialog(self.project, self.spec, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        join = dialog.join()
        if join is None:
            QMessageBox.warning(self, "Join non valido", "Scegli tabella e campi del join.")
            return
        self.spec.joins.append(join)
        self._reload()
        self.status_message.emit(f"Tabella {join.table} aggiunta alla query")

    def remove_selected_table(self) -> None:
        item = self.tree.currentItem()
        data = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        if not isinstance(data, tuple) or data[0] != "table":
            QMessageBox.information(
                self, "Rimuovi tabella", "Seleziona una tabella aggiunta alla query."
            )
            return
        table = str(data[1])
        if table.lower() == self.spec.base.lower():
            QMessageBox.information(
                self, "Rimuovi tabella", "La tabella base non può essere rimossa."
            )
            return
        self.spec.joins = [
            join for join in self.spec.joins if join.table.lower() != table.lower()
        ]
        prefix = table.lower() + "."
        self.spec.fields = [
            item for item in self.spec.fields if not item.ref.lower().startswith(prefix)
        ]
        self.spec.filters = [
            item for item in self.spec.filters if not item.field.lower().startswith(prefix)
        ]
        self.spec.sorts = [
            item for item in self.spec.sorts if not item.field.lower().startswith(prefix)
        ]
        self._reload()
        self.status_message.emit(f"Tabella {table} rimossa dalla query")

    # ------------------------------------------------------------------ filtri
    def add_filter(self, field: str = "", op: str = "eq", value: str = "", group: int = 0) -> None:
        if not field:
            options = self._available_refs()
            field = options[0][0] if options else ""
        self.spec.filters.append(QueryFilter(field, op, value, group=max(0, int(group))))
        self._refresh_filters()
        self._refresh_qbe()
        self._mark_dirty()

    def remove_selected_filter(self) -> None:
        row = self.filters_table.currentRow()
        if row < 0 or row >= len(self.spec.filters):
            return
        self.spec.filters.pop(row)
        self._refresh_filters()
        self._refresh_qbe()
        self._mark_dirty()

    def _on_filter_combo_changed(self, row: int) -> None:
        if self._loading_filters or not (0 <= row < len(self.spec.filters)):
            return
        field_combo = self.filters_table.cellWidget(row, 0)
        op_combo = self.filters_table.cellWidget(row, 1)
        if isinstance(field_combo, QComboBox):
            self.spec.filters[row].field = str(field_combo.currentData() or "")
        if isinstance(op_combo, QComboBox):
            self.spec.filters[row].op = str(op_combo.currentData() or "eq")
        self._refresh_qbe()
        self._mark_dirty()

    def _on_filter_cell_changed(self, row: int, column: int) -> None:
        if self._loading_filters or column != 2 or not (0 <= row < len(self.spec.filters)):
            return
        item = self.filters_table.item(row, column)
        self.spec.filters[row].value = item.text() if item is not None else ""
        self._refresh_qbe()
        self._mark_dirty()

    # ------------------------------------------------------------- ordinamento
    def add_sort(self, field: str = "", direction: str = "asc") -> None:
        if not field:
            options = self._available_refs()
            field = options[0][0] if options else ""
        self.spec.sorts.append(QuerySort(field, direction))
        self._refresh_sorts()
        self._refresh_qbe()
        self._mark_dirty()

    def remove_selected_sort(self) -> None:
        row = self.sorts_table.currentRow()
        if row < 0 or row >= len(self.spec.sorts):
            return
        self.spec.sorts.pop(row)
        self._refresh_sorts()
        self._refresh_qbe()
        self._mark_dirty()

    def move_sort(self, delta: int) -> None:
        row = self.sorts_table.currentRow()
        target = row + delta
        if row < 0 or not (0 <= target < len(self.spec.sorts)):
            return
        self.spec.sorts[row], self.spec.sorts[target] = (
            self.spec.sorts[target],
            self.spec.sorts[row],
        )
        self._refresh_sorts()
        self.sorts_table.selectRow(target)
        self._refresh_qbe()
        self._mark_dirty()

    def _on_sort_combo_changed(self, row: int) -> None:
        if self._loading_sorts or not (0 <= row < len(self.spec.sorts)):
            return
        field_combo = self.sorts_table.cellWidget(row, 0)
        dir_combo = self.sorts_table.cellWidget(row, 1)
        if isinstance(field_combo, QComboBox):
            self.spec.sorts[row].field = str(field_combo.currentData() or "")
        if isinstance(dir_combo, QComboBox):
            value = str(dir_combo.currentData() or "asc")
            self.spec.sorts[row].direction = (
                value if value in SORT_DIRECTIONS else "asc"
            )
        self._refresh_qbe()
        self._mark_dirty()

    # ------------------------------------------------------------- anteprima
    def run_preview(self) -> Any:
        self._refresh_sql()
        try:
            result = engine_for(self.project).run(self.spec)
        except QueryError as exc:
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(0)
            self.result_label.setText(f"Query non valida: {exc}")
            self.result_label.setProperty("state", "error")
            self._result_stale = True
            self._refresh_status()
            return None
        self._fill_result(result)
        self._result_stale = False
        self._refresh_status()
        self.tabs.setCurrentWidget(self.result_page)
        return result

    def _fill_result(self, result) -> None:
        headers = result.headers()
        self.result_table.setColumnCount(len(headers))
        self.result_table.setHorizontalHeaderLabels(headers)
        rows = result.rows[:RESULT_ROW_LIMIT]
        self.result_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, column in enumerate(result.columns):
                value = row.get(column.key)
                text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.result_table.setItem(row_index, column_index, item)
        self.result_table.resizeColumnsToContents()
        suffix = ""
        if len(result.rows) > RESULT_ROW_LIMIT:
            suffix = f" (mostrate {RESULT_ROW_LIMIT})"
        self.result_label.setText(f"{len(result.rows)} righe{suffix}")

    def _on_tab_changed(self, _index: int) -> None:
        self._sync_mode_buttons()
        if self.tabs.currentWidget() is self.qbe_page:
            self._refresh_qbe()
            return
        if self.tabs.currentWidget() is self.result_page:
            if self._result_stale:
                self.run_preview()

    # --------------------------------------------------------------- risultati
    def open_results(self) -> None:
        if self.is_dirty() and not self.save():
            return
        self.results_requested.emit(self.spec.name)

    # --------------------------------------------------------------- salvataggio
    def save(self) -> bool:
        self.spec.name = self.name_edit.text().strip()
        self.spec.caption = self.caption_edit.text().strip()
        errors = self.spec.validate(self.project.tables())
        if errors:
            QMessageBox.warning(self, "Query non valida", "\n".join(errors))
            return False
        try:
            self.project.put_object(
                "queries", self.spec.to_dict(), previous_name=self._saved_name
            )
            self.project.save()
        except ProjectError as exc:
            QMessageBox.critical(self, "Salvataggio non riuscito", str(exc))
            return False
        self._saved_name = self.spec.name
        self._saved_state = self.spec.to_dict()
        self._refresh_status()
        self.saved.emit(self.spec.name)
        self.status_message.emit(f"Query {self.spec.name} salvata")
        return True
