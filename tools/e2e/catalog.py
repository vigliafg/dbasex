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
# Catalogo manuale della fase 2 — query e form (E4)
# --------------------------------------------------------------------------- #
_MANUAL_QUERY_FORM: dict[str, tuple[str, str]] = {
    # Query
    "QRY-NEW": ("queries", "Nuova query guidata"),
    "QRY-FIELD-INCLUDE": ("queries", "Inclusione dei campi"),
    "QRY-FIELD-ALIAS": ("queries", "Alias di output"),
    "QRY-JOIN-SUGGEST": ("queries", "Join suggerito dalle foreign key"),
    "QRY-FILTER-AND": ("queries", "Filtri AND"),
    "QRY-FILTER-OR": ("queries", "Filtri OR"),
    "QRY-FILTER-GROUPS": ("queries", "Gruppi di filtro"),
    "QRY-SORT-MULTI": ("queries", "Ordinamento multiplo"),
    "QRY-GROUP-BY": ("queries", "Raggruppamento GROUP BY"),
    "QRY-SQL-PREVIEW": ("queries", "Anteprima SQL"),
    "QRY-SQL-PARAMS": ("queries", "SQL parametrizzato"),
    "QRY-VALIDATE": ("queries", "Validazione della query"),
    "QRY-SAVE-REOPEN": ("queries", "Salvataggio e riapertura"),
    "QRY-SAVE-REJECT": ("queries", "Rifiuto di query invalida"),
    "QRY-QBE-IMAGE": ("queries", "Query image QBE"),
    "QRY-QBE-INCLUDE": ("queries", "Riga Includi QBE"),
    "QRY-QBE-ROWS": ("queries", "Righe di criterio QBE"),
    "QRY-QBE-EXAMPLE": ("queries", "Example element QBE"),
    "QRY-QBE-EXAMPLE-WARN": ("queries", "Avvisi example element"),
    "QRY-QBE-BETWEEN": ("queries", "Intervallo QBE"),
    "QRY-QBE-LIKE": ("queries", "Jolly QBE"),
    "QRY-QBE-NULL": ("queries", "Vuoto e non vuoto QBE"),
    "QRY-QBE-OR": ("queries", "Righe OR QBE"),
    "QRY-RESULTS-GRID": ("queries", "Griglia Query Results"),
    "QRY-RESULTS-FORMAT": ("queries", "Formati dei tipi nei risultati"),
    "QRY-RESULTS-REFRESH": ("queries", "Aggiornamento dei risultati"),
    "QRY-RESULTS-EXPORT": ("queries", "Export CSV dei risultati"),
    "QRY-CROSSTAB": ("queries", "Tabella incrociata"),
    "QRY-CROSSTAB-TOTALS": ("queries", "Totali della crosstab"),
    "QRY-CROSSTAB-EMPTY": ("queries", "Crosstab senza righe"),
    "QRY-CROSSTAB-ERROR": ("queries", "Crosstab su colonna non numerica"),
    "QRY-CROSSTAB-CSV": ("queries", "Export CSV della crosstab"),
    "QRY-EXPERT": ("queries", "Query Expert"),
    "QRY-EXPERT-RELATIONS": ("queries", "Relazioni suggerite dall'esperto"),
    "QRY-EXPERT-CRITERIA": ("queries", "Criteri dell'esperto"),
    "QRY-EXPERT-SORT": ("queries", "Ordinamento dell'esperto"),
    # Form Expert e Designer
    "FRM-EXPERT-5STEPS": ("forms", "Form Expert in cinque passi"),
    "FRM-EXPERT-FIELDS": ("forms", "Scelta dei campi nell'esperto"),
    "FRM-EXPERT-BLANK": ("forms", "Form vuoto dall'esperto"),
    "FRM-EXPERT-LAYOUTS": ("forms", "Layout dell'esperto"),
    "FRM-EXPERT-STYLE": ("forms", "Font e stile dell'esperto"),
    "FRM-EXPERT-COLORS": ("forms", "Colori dell'esperto"),
    "FRM-DESIGNER-PALETTE": ("forms", "Palette Controls"),
    "FRM-PALETTE-FIELD": ("forms", "Palette Field"),
    "FRM-AUTOLABEL": ("forms", "Etichetta automatica"),
    "FRM-FIELD-KINDS": ("forms", "Tipo controllo dal campo"),
    "FRM-GRID-SNAP": ("forms", "Griglia e snap a 8 px"),
    "FRM-HANDLES": ("forms", "Otto maniglie di ridimensionamento"),
    "FRM-KEYBOARD": ("forms", "Frecce e passo fine"),
    "FRM-MULTISELECT": ("forms", "Selezione multipla"),
    "FRM-CLIPBOARD": ("forms", "Copia, taglia e incolla"),
    "FRM-UNDO-REDO": ("forms", "Annulla e ripeti"),
    "FRM-ALIGN": ("forms", "Allineamento"),
    "FRM-DISTRIBUTE": ("forms", "Distribuzione"),
    "FRM-ZORDER": ("forms", "Porta avanti e indietro"),
    "FRM-PAGES": ("forms", "Pagine del form"),
    "FRM-INSPECTOR": ("forms", "Object Inspector"),
    "FRM-INSPECTOR-FORM": ("forms", "Proprietà del form"),
    "FRM-INSPECTOR-DATA": ("forms", "Proprietà data e comportamento"),
    "FRM-METHODS": ("forms", "Metodi save e close"),
    "FRM-RUNTIME-CRUD": ("forms", "CRUD nel runtime"),
    "FRM-RUNTIME-NAV": ("forms", "Navigazione nel runtime"),
    "FRM-RUNTIME-STATUS": ("forms", "Stato del runtime"),
    "FRM-RUNTIME-VALIDATION": ("forms", "Validazione nel runtime"),
    "FRM-RUNTIME-MESSAGES": ("forms", "Messaggi del runtime"),
    "FRM-LIST-VIEW": ("forms", "Vista Lista"),
    "FRM-LIST-FIELDS": ("forms", "Campi della vista Lista"),
    "FRM-LIST-SELECT": ("forms", "Apertura record dalla lista"),
    "FRM-PORTAL-LINK": ("forms", "Portale padre/figlio"),
    "FRM-PORTAL-ORDER": ("forms", "Ordine del portale"),
    "FRM-PORTAL-FILTER": ("forms", "Filtro del portale"),
    "FRM-QUERY-READONLY": ("forms", "Form su query in sola lettura"),
    "FRM-QUERY-CALC": ("forms", "Colonne aggregate nel form"),
    "FRM-QUERY-NAV": ("forms", "Navigazione del form su query"),
    "FRM-ROUNDTRIP": ("forms", "Round-trip del form"),
    "FRM-LEGACY-JSON": ("forms", "Compatibilità JSON legacy"),
}

for _id, (_area, _label) in _MANUAL_QUERY_FORM.items():
    add(_id, _area, _label, 2)


# --------------------------------------------------------------------------- #
# Catalogo manuale della fase 2 — report, etichette e script (E5)
# --------------------------------------------------------------------------- #
_MANUAL_REPORT_LABEL_SCRIPT: dict[str, tuple[str, str]] = {
    # Report
    "REP-NEW": ("reports", "Nuovo report"),
    "REP-SOURCE-TABLE": ("reports", "Report da tabella"),
    "REP-SOURCE-QUERY": ("reports", "Report da query"),
    "REP-FILTER": ("reports", "Filtro del report"),
    "REP-BANDS-VISIBLE": ("reports", "Visibilità delle bande"),
    "REP-BANDS-ORDER": ("reports", "Ordine delle bande"),
    "REP-BANDS-HEIGHT": ("reports", "Altezza delle bande"),
    "REP-BANDS-DRAG": ("reports", "Delimitatori trascinabili"),
    "REP-INSERT-FIELD": ("reports", "Insert Database Field"),
    "REP-FIELD-PREVIEW": ("reports", "Anteprima dati del campo"),
    "REP-EDIT-TEXT": ("reports", "Edit Text Field"),
    "REP-EXPRESSION": ("reports", "Espressione nel dettaglio"),
    "REP-SORT": ("reports", "Record Sort Order"),
    "REP-GROUP": ("reports", "Gruppi header e footer"),
    "REP-TOTAL-SUM": ("reports", "Totale somma"),
    "REP-TOTAL-COUNT": ("reports", "Totale conteggio"),
    "REP-TOTAL-AVG": ("reports", "Totale media"),
    "REP-TOTAL-MIN": ("reports", "Totale minimo"),
    "REP-TOTAL-MAX": ("reports", "Totale massimo"),
    "REP-CHART-CATEGORY": ("reports", "Categoria del grafico"),
    "REP-CHART-VALUE": ("reports", "Valore del grafico"),
    "REP-CHART-BAND": ("reports", "Banda del grafico"),
    "REP-FORMAT-FONT": ("reports", "Font del controllo"),
    "REP-FORMAT-STYLE": ("reports", "Grassetto, corsivo e sottolineato"),
    "REP-FORMAT-ALIGN": ("reports", "Allineamento del controllo"),
    "REP-FORMAT-BORDER": ("reports", "Bordo del controllo"),
    "REP-FORMAT-COLOR": ("reports", "Colore del testo"),
    "REP-ALIGN-CONTROL": ("reports", "Allinea nella banda"),
    "REP-ZOOM": ("reports", "Zoom del designer"),
    "REP-PREVIEW-PAGES": ("reports", "Anteprima multi-pagina"),
    "REP-PREVIEW-SINGLE": ("reports", "Una pagina per volta"),
    "REP-PREVIEW-FIT": ("reports", "Fit width"),
    "REP-PREVIEW-ZOOM": ("reports", "Zoom persistente"),
    "REP-PRINT": ("reports", "Stampa mock"),
    "REP-PDF": ("reports", "Export PDF"),
    "REP-QUERY": ("reports", "Report su query"),
    "REP-ROUNDTRIP": ("reports", "Round-trip del report"),
    "REP-LEGACY": ("reports", "Compatibilità JSON legacy"),
    "REP-EXPERT": ("reports", "Report Expert"),
    "REP-EXPERT-LAYOUTS": ("reports", "Layout dell'esperto"),
    "REP-EXPERT-GROUP": ("reports", "Gruppo e totali dell'esperto"),
    "REP-EXPERT-SORT": ("reports", "Ordinamento dell'esperto"),
    # Etichette
    "LBL-NEW": ("labels", "Nuova etichetta"),
    "LBL-PRESET": ("labels", "Preset del foglio"),
    "LBL-CUSTOM": ("labels", "Formato personalizzato"),
    "LBL-GRID": ("labels", "Griglia colonne e righe"),
    "LBL-MARGINS": ("labels", "Margini e distanze"),
    "LBL-TEMPLATE-FIELD": ("labels", "Campo [campo] nel modello"),
    "LBL-TEMPLATE-EXPR": ("labels", "Espressione {{...}} nel modello"),
    "LBL-FIELD-INSERT": ("labels", "Inserimento campo nel modello"),
    "LBL-STYLE": ("labels", "Font, grassetto, bordo e colore"),
    "LBL-FILTER": ("labels", "Filtro del mail merge"),
    "LBL-ORDER": ("labels", "Ordinamento del mail merge"),
    "LBL-SELECTION": ("labels", "Selezione dei record"),
    "LBL-OFFSET": ("labels", "Etichette da saltare"),
    "LBL-PREVIEW": ("labels", "Anteprima multi-foglio"),
    "LBL-PAGES": ("labels", "Pagine del foglio"),
    "LBL-PDF": ("labels", "PDF delle etichette"),
    "LBL-SAVE-REOPEN": ("labels", "Salvataggio e riapertura"),
    # Script
    "SCR-SOURCE-TEXT": ("scripts", "Sorgente e azioni"),
    "SCR-LINE-NUMBERS": ("scripts", "Numeri di riga"),
    "SCR-SYNTAX": ("scripts", "Evidenziazione della sintassi"),
    "SCR-LOG": ("scripts", "Log di esecuzione"),
    "SCR-PICKER": ("scripts", "Step Picker"),
    "SCR-PICKER-CATEGORIES": ("scripts", "Categorie dello Step Picker"),
    "SCR-PICKER-SEARCH": ("scripts", "Ricerca nello Step Picker"),
    "SCR-PICKER-DESCRIPTION": ("scripts", "Descrizioni delle azioni"),
    "SCR-PARAMS": ("scripts", "Parametri dichiarati"),
    "SCR-ARGS-DIALOG": ("scripts", "Dialogo argomenti"),
    "SCR-RUN": ("scripts", "Esecuzione dal Program Editor"),
    "SCR-SAVE-REOPEN": ("scripts", "Salvataggio e riapertura"),
    "SCR-LEGACY": ("scripts", "Compatibilità script legacy"),
    "SCR-FORM-EVENT": ("scripts", "Script da evento form"),
}

for _id, (_area, _label) in _MANUAL_REPORT_LABEL_SCRIPT.items():
    add(_id, _area, _label, 2)


# --------------------------------------------------------------------------- #
# Catalogo manuale della fase 3 — shell, progetto, journey e qualità (E6)
# --------------------------------------------------------------------------- #
_MANUAL_SHELL: dict[str, tuple[str, str]] = {
    # Navigator
    "NAV-COUNT": ("shell", "Conteggi del Navigator"),
    "NAV-FILTER": ("shell", "Filtro del Navigator"),
    "NAV-UNTITLED": ("shell", "Voce [Untitled]"),
    "NAV-CONTEXT": ("shell", "Menu contestuale del Navigator"),
    "NAV-REFRESH": ("shell", "Aggiornamento del Navigator"),
    "NAV-DISABLED": ("shell", "Categorie disabilitate"),
    # Command Window
    "CMD-HELP": ("shell", "Comando HELP"),
    "CMD-TABLES": ("shell", "Comando TABELLE"),
    "CMD-USE": ("shell", "Comando USE"),
    "CMD-RECORD": ("shell", "Comando RECORD"),
    "CMD-CLEAR": ("shell", "Comando CLEAR"),
    "CMD-EXPR": ("shell", "Espressioni nella Command Window"),
    "CMD-HISTORY": ("shell", "Cronologia dei comandi"),
    # Shell a schede
    "SHELL-TABS": ("shell", "Schede documento"),
    "SHELL-ACTIVATE": ("shell", "Attivazione delle schede"),
    "SHELL-CLOSE": ("shell", "Chiusura scheda"),
    "SHELL-CLOSE-ALL": ("shell", "Chiudi tutte le schede"),
    "SHELL-DIRTY": ("shell", "Conferma modifiche non salvate"),
    "SHELL-MENUS": ("shell", "Otto menu principali"),
    "SHELL-ACTIONS": ("shell", "Azioni dei menu"),
    "SHELL-SAFE": ("shell", "Esecuzione sicura delle azioni"),
    "SPEEDBAR": ("shell", "SpeedBar"),
    "TOOLTIPS": ("shell", "Tooltip delle azioni"),
    "TOGGLE": ("shell", "Mostra e nascondi barre"),
    "STATUS-BAR": ("shell", "Barra di stato"),
    "EDIT-CROSS": ("shell", "Copia e incolla tra editor"),
    "EDIT-UNDO-REDO": ("shell", "Annulla e ripeti nella shell"),
    "EDIT-DELETE": ("shell", "Elimina nella shell"),
    "ZOOM-IN": ("shell", "Aumenta zoom"),
    "ZOOM-OUT": ("shell", "Riduci zoom"),
    "ZOOM-RESET": ("shell", "Zoom 100%"),
    "ZOOM-PERSIST": ("shell", "Zoom persistente"),
    "SHORTCUTS": ("shell", "Scorciatoie documentate"),
    "HELP-QUICK": ("shell", "Guida rapida"),
    "ABOUT": ("shell", "Informazioni su dBX"),
    "THEME": ("shell", "Tema della shell"),
    "VERSION": ("shell", "Versione nella barra di stato"),
    # Menu Designer e runtime
    "MENU-BUILDER": ("menus", "Menu Designer"),
    "MENU-SEPARATORS": ("menus", "Separatori del menu"),
    "MENU-ACTION5": ("menus", "Cinque azioni di menu"),
    "MENU-FILTER-TARGET": ("menus", "Destinazioni filtrate"),
    "MENU-PREVIEW": ("menus", "Anteprima del menu"),
    "MENU-RUNTIME": ("menus", "Runtime del menu"),
    # Project Editor e build
    "PROJECT-EDITOR": ("project", "Project Editor"),
    "PROJECT-SETTINGS": ("project", "Impostazioni del progetto"),
    "PROJECT-EDITOR-SAVE": ("project", "Salvataggio impostazioni"),
    "PROJECT-VALIDATE": ("project", "Validazione del progetto"),
    "PROJECT-VALIDATE-MISSING": ("project", "Riferimenti mancanti"),
    "BUILD-FOLDER": ("project", "Build in cartella"),
    "BUILD-ZIP": ("project", "Build ZIP"),
    "BUILD-CONTENT": ("project", "Contenuto della build"),
    "BUILD-REOPEN": ("project", "Riapertura della build"),
    "RUNNER-F5": ("project", "F5 esegue il progetto"),
    "RUNNER-FORM": ("project", "Form principale nel runner"),
    "RUNNER-MENU": ("project", "Menu nel runner"),
    "RUNNER-CLOSE": ("project", "Chiusura del runner"),
    # Journey
    "JOURNEY-NEWAPP": ("journey", "Nuova applicazione completa"),
    "JOURNEY-SPORTELLO": ("journey", "Sportello"),
    "JOURNEY-IMPORT": ("journey", "Import e bonifica"),
    "JOURNEY-CLOSING": ("journey", "Chiusura mensile"),
    "JOURNEY-1N": ("journey", "Due tabelle uno-a-molti"),
    "JOURNEY-RESTART": ("journey", "Sessione lunga e riavvio"),
    "JOURNEY-LEGACY": ("journey", "Progetto legacy"),
    # Prestazioni e qualità
    "PERF-BROWSE": ("quality", "Prestazioni Browse 10k"),
    "PERF-QUERY": ("quality", "Prestazioni query 10k"),
    "PERF-REPORT": ("quality", "Prestazioni report 10k"),
    "PERF-PDF": ("quality", "Prestazioni PDF"),
    "PERF-FORM100": ("quality", "Form con 100 controlli"),
    "PERF-TABLE50": ("quality", "Tabella con 50 campi"),
    "PERF-REPORT200": ("quality", "Report con 200 controlli"),
    "DETERMINISM": ("quality", "Determinismo degli scenari"),
    "DOCS-COVERAGE": ("quality", "Documentazione e matrice di copertura"),
}

for _id, (_area, _label) in _MANUAL_SHELL.items():
    add(_id, _area, _label, 3)


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
