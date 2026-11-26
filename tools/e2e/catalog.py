"""Catalogo delle funzioni coperte dagli scenari E2E.

Le costanti del motore e dei designer sono la fonte primaria: aggiungere un
tipo campo, un operatore, un'azione script o un controllo form senza uno
scenario che lo dichiari rende il test del catalogo rosso.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from dbx.core import types as T
from dbx.core.form_model import BUTTON_ACTIONS, CONTROL_EVENTS, CONTROL_KINDS, FORM_EVENTS
from dbx.core.label_model import ALIGNMENTS, LABEL_PRESETS
from dbx.core.metadata import ON_DELETE_ACTIONS
from dbx.core.query_model import AGGREGATE_FUNCTIONS, ALL_OPERATORS, JOIN_KINDS, SORT_DIRECTIONS
from dbx.designers.menu_builder import MENU_ACTIONS
from dbx.runtime.report_engine import BAND_NAMES, CHART_TYPES, CONTROL_KINDS as REPORT_CONTROLS
from dbx.runtime.script_engine import ACTIONS
from dbx.ui.navigator import NAV_CATEGORIES

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Feature:
    id: str
    area: str
    label: str
    phase: int = 1


FEATURES: dict[str, Feature] = {}


def add(feature_id: str, area: str, label: str, phase: int = 1) -> None:
    FEATURES.setdefault(feature_id, Feature(feature_id, area, label, phase))


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in text.upper()).strip("-").replace("--", "-")


# --------------------------------------------------------------------------- #
# Derivazione dalle costanti del motore
# --------------------------------------------------------------------------- #
for _type in T.ALL_TYPES:
    add(f"TB-TYPE-{_type.upper()}", "tables", f"Tipo campo {_type}")
for _action in ON_DELETE_ACTIONS:
    add(f"TB-ONDELETE-{_slug(_action)}", "tables", f"ON DELETE {_action}")
for _op in ALL_OPERATORS:
    add(f"QRY-OP-{_op.upper()}", "queries", f"Operatore {_op}", 2)
for _agg in AGGREGATE_FUNCTIONS:
    add(f"QRY-AGG-{_agg.upper()}", "queries", f"Aggregato {_agg}", 2)
for _join in JOIN_KINDS:
    add(f"QRY-JOIN-{_join.upper()}", "queries", f"Join {_join}", 2)
for _direction in SORT_DIRECTIONS:
    add(f"QRY-SORT-{_direction.upper()}", "queries", f"Ordinamento {_direction}", 2)
for _kind in CONTROL_KINDS:
    add(f"FRM-CONTROL-{_kind.upper()}", "forms", f"Controllo form {_kind}", 2)
for _action in BUTTON_ACTIONS:
    add(f"FRM-BUTTON-{_action.upper()}", "forms", f"Pulsante {_action}", 2)
for _event in CONTROL_EVENTS:
    add(f"FRM-EVENT-{_event.upper()}", "forms", f"Evento controllo {_event}", 2)
for _event in FORM_EVENTS:
    add(f"FRM-EVENT-{_event.upper()}", "forms", f"Evento form {_event}", 2)
add("FRM-METHOD-SAVE", "forms", "Metodo save", 2)
add("FRM-METHOD-CLOSE", "forms", "Metodo close", 2)
for _band in BAND_NAMES:
    add(f"REP-BAND-{_band.upper()}", "reports", f"Banda {_band}", 2)
for _kind in REPORT_CONTROLS:
    add(f"REP-CONTROL-{_kind.upper()}", "reports", f"Controllo report {_kind}", 2)
for _chart in CHART_TYPES:
    add(f"REP-CHART-{_chart.upper()}", "reports", f"Grafico {_chart}", 2)
for _preset in LABEL_PRESETS:
    add(f"LBL-PRESET-{_preset.upper()}", "labels", f"Preset {_preset}", 2)
for _align in ALIGNMENTS:
    add(f"LBL-ALIGN-{_align.upper()}", "labels", f"Allineamento {_align}", 2)
for _action, _meta in ACTIONS.items():
    add(f"SCR-ACTION-{_action.upper()}", "scripts", f"Azione {_action}", 2)
for _action in MENU_ACTIONS:
    add(f"MENU-ACTION-{_action.upper()}", "menus", f"Azione menu {_action}", 3)
for _key, _label, _glyph, _available in NAV_CATEGORIES:
    add(f"NAV-CATEGORY-{_key.upper()}", "shell", f"Categoria {_label}", 3)


def _shell_actions() -> list[str]:
    source = (ROOT / "dbx" / "ui" / "main_window.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    labels: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if not isinstance(function, ast.Attribute) or function.attr != "make_action":
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            labels.append(str(node.args[0].value))
    return labels


for _label in _shell_actions():
    add(f"SHELL-ACTION-{_slug(_label)}", "shell", f"Azione shell {_label}", 3)


# --------------------------------------------------------------------------- #
# Catalogo manuale della fase 1
# --------------------------------------------------------------------------- #
_MANUAL: dict[str, tuple[str, str]] = {
    # Progetto
    "PROJ-NEW": ("project", "Nuovo progetto vuoto"),
    "PROJ-DEMO": ("project", "Progetto demo"),
    "PROJ-SETTINGS": ("project", "Impostazioni progetto"),
    "PROJ-COMPAT": ("project", "Compatibilità artefatti legacy"),
    "PROJ-SAVE": ("project", "Salvataggio e riapertura"),
    "PROJ-CLI": ("project", "Avvio da riga di comando"),
    "PROJ-THEME": ("project", "Temi Aurora/Silver/Dark"),
    "PROJ-RECENT": ("project", "Progetti recenti"),
    # Table Builder
    "TB-NEW": ("tables", "Nuova tabella"),
    "TB-CAPTION": ("tables", "Didascalia tabella"),
    "TB-SAVE-AS": ("tables", "Save As"),
    "TB-PRINT": ("tables", "Stampa struttura"),
    "TB-DDL": ("tables", "Anteprima DDL"),
    "TB-INDEX": ("tables", "Indice semplice"),
    "TB-INDEX-UNIQUE": ("tables", "Indice univoco"),
    "TB-INDEX-COMPOSITE": ("tables", "Indice composto"),
    "TB-FK": ("tables", "Chiave esterna"),
    "TB-REORDER": ("tables", "Riordino campi"),
    "TB-REMOVE": ("tables", "Rimozione campo"),
    "TB-MIGRATE": ("tables", "Migrazione struttura"),
    "TB-BACKUP": ("tables", "Backup prima della migrazione"),
    "TB-STATS": ("tables", "Metadati Updated/Bytes/Records"),
    "TB-ADD-RECORDS": ("tables", "Aggiunta record dalla struttura"),
    "TB-FIELD-REQUIRED": ("tables", "Campo obbligatorio"),
    "TB-FIELD-DEFAULT": ("tables", "Valore predefinito"),
    "TB-FIELD-CAPTION": ("tables", "Didascalia campo"),
    "TB-FIELD-FORMAT": ("tables", "Formato campo"),
    "TB-FIELD-CALCULATED": ("tables", "Campo calcolato"),
    "TB-FIELD-AUTOENTER": ("tables", "Auto-enter"),
    "TB-FIELD-INCREMENT": ("tables", "Incremento"),
    "TB-FIELD-AUTODATE": ("tables", "Data automatica"),
    "TB-FIELD-CASE": ("tables", "Normalizzazione maiuscole"),
    "TB-FIELD-MASK": ("tables", "Maschera input"),
    "TB-FIELD-RULE": ("tables", "Regola di validazione"),
    "TB-FIELD-RULE-MSG": ("tables", "Messaggio regola"),
    "TB-FIELD-REQUIRED-IF": ("tables", "Obbligatorietà condizionale"),
    "TB-FIELD-SKIP-IF": ("tables", "Salto condizionale"),
    "TB-FIELD-DOMAIN": ("tables", "Dominio numerico"),
    "TB-FIELD-DOMAIN-RANGES": ("tables", "Intervalli di dominio"),
    "TB-FIELD-CHOICE-STATIC": ("tables", "Scelta statica"),
    "TB-FIELD-CHOICE-LABELS": ("tables", "Etichette Scelta"),
    "TB-FIELD-CHOICE-CASE": ("tables", "Scelta con maiuscole"),
    "TB-FIELD-CHOICE-BLANK": ("tables", "Scelta con vuoto"),
    "TB-FIELD-CHOICE-OTHER": ("tables", "Scelta con testo libero"),
    "TB-FIELD-CHOICE-DYNAMIC": ("tables", "Scelta dinamica"),
    "TB-FIELD-CHOICE-COMBINE": ("tables", "Combinazione valori Scelta"),
    "TB-EXPERT": ("tables", "Table Expert"),
    "TB-EXPERT-TEMPLATE": ("tables", "Template Table Expert"),
    "TB-EXPERT-FIELDS": ("tables", "Campi Table Expert"),
    "TB-EXPERT-INDEXES": ("tables", "Indici Table Expert"),
    # Browse / DataView
    "DV-CRUD": ("browse", "CRUD nella griglia"),
    "DV-NAV": ("browse", "Navigazione record"),
    "DV-VALIDATION": ("browse", "Validazione per cella"),
    "DV-EDIT-CELL": ("browse", "Editing in-place"),
    "DV-CHOICE": ("browse", "Editor Scelta"),
    "DV-CALCULATED": ("browse", "Calcolati in sola lettura"),
    "DV-FIND": ("browse", "Find mode"),
    "DV-FIND-AND": ("browse", "Criteri AND"),
    "DV-FIND-OR": ("browse", "Criteri OR"),
    "DV-FIND-OMIT": ("browse", "Criterio Ometti"),
    "DV-REPLACE": ("browse", "Sostituzione"),
    "DV-REPLACE-CASE": ("browse", "Sostituzione con maiuscole"),
    "DV-SAVED-FINDS": ("browse", "Ricerche salvate"),
    "DV-SORT": ("browse", "Ordinamento"),
    "DV-FILTER": ("browse", "Filtro rapido"),
    "DV-STATUS": ("browse", "Stato record"),
    "DV-COLUMNS": ("browse", "Larghezza colonne persistente"),
    "DV-OPTIONS": ("browse", "Editing Options"),
    "DV-NEW-DIALOG": ("browse", "Dialogo nuovo record"),
    "DV-DELETE": ("browse", "Eliminazione record"),
    "DV-EMPTY": ("browse", "Tabella vuota"),
    "DV-REFRESH": ("browse", "Aggiornamento griglia"),
    # CSV
    "CSV-DETECT-DELIM": ("data", "Rilevamento delimitatore"),
    "CSV-DETECT-ENCODING": ("data", "Rilevamento codifica"),
    "CSV-HEADER": ("data", "Gestione intestazione"),
    "CSV-MAPPING": ("data", "Mappatura colonne"),
    "CSV-TYPES": ("data", "Conversione tipi"),
    "CSV-CALCULATED": ("data", "Calcolati in import"),
    "CSV-REJECTS": ("data", "Scarti di import"),
    "CSV-CLEAR-BACKUP": ("data", "Svuotamento con backup"),
    "CSV-EXPORT": ("data", "Export CSV"),
    "CSV-EXPORT-CALC": ("data", "Export dei calcolati"),
    # Database Designer
    "ER-VIEW": ("data", "Vista schema ER"),
    "ER-LAYOUT": ("data", "Auto-layout"),
    "ER-ZOOM": ("data", "Zoom diagramma"),
    "ER-EXPORT-PNG": ("data", "Export PNG"),
    "ER-EXPORT-SVG": ("data", "Export SVG"),
    "ER-RELATION": ("data", "Creazione relazione"),
    "ER-SCHEMA-EDIT": ("data", "Modifica schema dal diagramma"),
    "ER-CARD": ("data", "Card tabella compatta"),
    "ER-INSPECTOR": ("data", "Ispettore tabella/relazione"),
    # Manutenzione
    "MNT-RENAME-REFS": ("data", "Rinomina con riferimenti"),
    "MNT-DUPLICATE": ("data", "Duplicazione oggetti"),
    "MNT-DUPLICATE-DATA": ("data", "Duplicazione tabella con dati"),
    "MNT-COMPACT": ("data", "Compattazione"),
    "MNT-INTEGRITY": ("data", "Verifica integrità"),
    "MNT-REEVALUATE": ("data", "Riapplica regole"),
    "MNT-BACKUP": ("data", "Backup"),
}

for _id, (_area, _label) in _MANUAL.items():
    add(_id, _area, _label, 1)


# --------------------------------------------------------------------------- #
# Validazione e copertura
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Coverage:
    phase: int
    required: int
    covered: int
    missing: tuple[str, ...]

    @property
    def percent(self) -> float:
        return 100.0 if not self.required else 100.0 * self.covered / self.required


def validate_scenarios(scenarios) -> list[str]:
    """Restituisce gli errori di coerenza tra catalogo e scenari."""

    errors: list[str] = []
    declared: dict[str, list[str]] = {feature_id: [] for feature_id in FEATURES}
    for scenario in scenarios:
        if not scenario.features:
            errors.append(f"{scenario.name}: nessuna feature dichiarata")
        for feature_id in scenario.features:
            if feature_id not in FEATURES:
                errors.append(f"{scenario.name}: feature sconosciuta {feature_id}")
                continue
            declared[feature_id].append(scenario.name)
    phase_one = [item for item in FEATURES.values() if item.phase == 1]
    for feature in phase_one:
        if not declared.get(feature.id):
            errors.append(f"feature non coperta: {feature.id} — {feature.label}")
    return errors


def coverage(scenarios, phase: int = 1) -> Coverage:
    required = {item.id for item in FEATURES.values() if item.phase <= phase}
    covered = {feature_id for scenario in scenarios for feature_id in scenario.features}
    missing = tuple(sorted(required - covered))
    return Coverage(phase, len(required), len(required & covered), missing)


def features_for(scenario) -> list[Feature]:
    return [FEATURES[item] for item in scenario.features if item in FEATURES]


__all__ = [
    "FEATURES",
    "Feature",
    "Coverage",
    "coverage",
    "features_for",
    "validate_scenarios",
]
