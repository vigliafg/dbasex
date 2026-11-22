# Diario di implementazione — dBX UI 0.2

> File **append-only**. Non riscrivere le voci precedenti.
> La verità sullo stato è qui e in `PLAN.md`.

## Stato ondate

| Ondata | Stato | Checkpoint |
|---|---|---|
| O0 — Baseline e design token | completata (2026-11-22) | — |
| O1 — Shell/MDI/menu/tema | completata (2026-11-22) | — |
| O2 — Navigator/Command/Browse | completata (2026-11-22) | — |
| O3 — Table Structure | da iniziare | A |
| O4 — Form Designer/Expert/Runtime | da iniziare | — |
| O5 — Report Designer/Preview | da iniziare | — |
| O6 — Script/Menu/Project | da iniziare | B |
| O7 — QA e release 0.2 | da iniziare | C |

## Registro

### 2026-11-22 — Pianificazione
- **Stato:** completata (solo pianificazione, nessuna ondata avviata)
- **Branch/commit:** `main` — documentazione del piano
- **Obiettivo:** definire il piano a ondate e le regole di ingaggio
- **File toccati:** `PLAN.md`, `AGENTS.md`, `DIARIO.md`
- **Scelte:**
  - clone strutturale + chrome dBASE, non pixel-perfect Win16;
  - Silver default, Dark opzionale non bloccante;
  - Query/Label Designer fuori dalla 0.2;
  - categorie Navigator non implementate visibili e disabilitate;
  - immagini Borland mantenute con disclaimer, da rivalutare prima della release.
- **Test:** non applicabili (solo documentazione)
- **Screenshot:** non applicabili
- **Problemi aperti:** nessuno
- **Prossimo passo:** avviare l'Ondata 0

### 2026-11-22 — Ondata 0 — avvio
- **Stato:** in corso
- **Obiettivo:** introdurre i token di design, il tema Silver, l'harness di cattura UI e i test headless della shell.
- **File previsti:** `dbx/ui/design.py`, `dbx/ui/theme.py`, `dbx/ui/icons.py`, `dbx/ui/app.py`, `dbx/config.py`, `dbx/__main__.py`, `dbx/ui/main_window.py`, `tools/capture_ui.py`, `tests/test_ui_*.py`, `docs/ui-parity.md`, `docs/reference/dbase55/README.md`.
- **Nota:** il tema Silver viene attivato già in O0 come default, in coerenza con `AGENTS.md`; la struttura delle finestre resta invariata.

### 2026-11-22 — Ondata 0 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** token di design, tema Silver, harness screenshot, test UI.
- **File toccati:** `dbx/ui/design.py` (nuovo), `dbx/ui/theme.py`, `dbx/ui/icons.py`, `dbx/ui/app.py`, `dbx/config.py`, `dbx/__main__.py`, `dbx/ui/main_window.py`, `tools/capture_ui.py` (nuovo), `tests/conftest.py` (nuovo), `tests/test_ui_shell.py` (nuovo), `tests/test_ui_navigator.py` (nuovo), `tests/test_ui_designers.py` (nuovo), `docs/ui-parity.md` (nuovo), `docs/reference/dbase55/README.md`, `docs/reference/dbx-ui/renders/*.png` (nuovi).
- **Scelte/deviazioni:**
  - tema Silver attivato come default già in O0 (il piano lo collocava in O1) per allinearsi a `AGENTS.md`;
  - alias `light` → Silver e `dark` → dark dBASE, così le configurazioni esistenti restano valide;
  - 9 rendering baseline generati in Silver; il tema Dark è stato catturato in prova e non committato.
- **Test:** `85 passed`; smoke headless OK; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `docs/reference/dbx-ui/renders/01-desktop.png` … `09-command-window.png`.
- **Problemi aperti:**
  - la toolbar usa ancora testo accanto all'icona (target O1);
  - il menu non ha ancora la sequenza completa (target O1);
  - i designer restano dialog modali (target O1/O3–O5).
- **Prossimo passo:** Ondata 1 — shell MDI, menu, SpeedBar, status bar.

### 2026-11-22 — Ondata 1 — avvio
- **Stato:** in corso
- **Obiettivo:** sostituire la shell a schede con il desktop MDI di dBASE: area documenti, menu completi, SpeedBar a sole icone, status bar a riquadri, gestione finestre.
- **File previsti:** `dbx/ui/main_window.py`, `dbx/ui/editor_host.py` (nuovo), `dbx/ui/design.py`, `dbx/ui/icons.py`, `dbx/ui/theme.py`, titoli dei designer, test UI, `tools/capture_ui.py`.

### 2026-11-22 — Ondata 1 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** desktop MDI con menu, SpeedBar, status bar e gestione finestre.
- **File toccati:** `dbx/ui/main_window.py` (riscritto), `dbx/ui/editor_host.py` (nuovo), `dbx/ui/design.py`, `dbx/ui/icons.py`, `dbx/ui/theme.py`, `dbx/designers/table_builder.py`, `dbx/designers/form_builder.py`, `dbx/designers/report_builder.py`, `tools/capture_ui.py`, `tests/test_ui_shell.py`, `tests/test_ui_editor_host.py` (nuovo), `docs/ui-parity.md`, `docs/reference/dbx-ui/renders/*.png`.
- **Scelte/deviazioni:**
  - `QMdiArea` sostituisce `QTabWidget`; `self.tabs` è stato **rimosso**, non mantenuto come adapter deprecato: tutti i chiamanti e i test usano ora `EditorHost`.
  - Nuovo `EditorHost` con deduplica per chiave, cascade/tile, chiusura singola e globale; `EditorSubWindow` impone una dimensione preferita alla sottofinestra, evitando che il `sizeHint` del designer la faccia crescere oltre l'area.
  - I `QDialog` non ancora convertiti entrano nell'MDI tramite `DialogEditor`, un adapter che li rende figli della sottofinestra e collega `accepted`/`rejected` alla chiusura. La conversione a `QWidget` resta nelle ondate 3–5.
  - Hook `editor_dirty()` e conferma di chiusura già presenti; nessun designer dichiara ancora `is_dirty()`, quindi la conferma diventerà effettiva con le conversioni O3–O5.
  - Menu nell'ordine `Progetto · Modifica · Visualizza · Oggetto · Procedure · Proprietà · Finestra · ?`; `Impostazioni` solo in Proprietà; `Finestra` popolato dinamicamente.
  - SpeedBar a sole icone 16×16, non flottante, con gruppi separati e tooltip con scorciatoie. Clipboard e undo/redo agiscono sul widget con focus; allinea/distribuisci restano disabilitati fino a O4.
  - Status bar a riquadri permanenti `Pos · Oggetto · Record · Modalità · versione`, con tracciamento della posizione del mouse e aggiornamento da DataView.
  - Titoli dei designer allineati al formato `Table Structure (nome)`, `Form Designer (nome)`, `Report Designer (nome)`.
  - Command Window resta un dialog non modale separato: il passaggio all'MDI è in O2.
- **Test:** `91 passed`; smoke headless OK; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `01-desktop.png` aggiornato; nuovo `10-desktop-mdi.png` con Browse e Form Designer in MDI.
- **Problemi aperti:**
  - I designer legacy mantengono i propri minimi interni: in finestre MDI strette compaiono scrollbar interne (previsto).
  - Le azioni allinea/distribuisci e la stampa globale si attivano solo quando l'editor le espone.
  - Navigator, Command Window e Browse restano da rifinire in O2.
- **Prossimo passo:** Ondata 2 — Navigator, Command Window, Browse/DataView.

### 2026-11-22 — Ondata 2 — avvio
- **Stato:** in corso
- **Obiettivo:** rendere fedeli Navigator, Command Window e Browse/DataView.

### 2026-11-22 — Ondata 2 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** Navigator completo, Command Window dentro l'MDI, Browse con selettore record e navigazione.
- **File toccati:** `dbx/ui/navigator.py` (riscritto), `dbx/ui/command_window.py` (riscritto), `dbx/ui/data_view.py` (riscritto), `dbx/ui/main_window.py`, `dbx/ui/design.py`, `tests/test_ui_navigator.py`, `tests/test_ui_designers.py`, `tests/test_ui_shell.py`, `tests/test_ui_workspace.py` (nuovo), `docs/ui-parity.md`.
- **Scelte/deviazioni:**
  - Navigator con le categorie originali (`Tutti`, `Tabelle`, `Query`, `Form`, `Report`, `Menu`, `Etichette`, `Programmi`, `Immagini`, `Suoni`, `Cataloghi`, `Personalizzati`): **Menu** è inserito dopo Report perché in dBX è un oggetto reale e deve restare raggiungibile; le altre categorie non implementate sono visibili e disabilitate con tooltip.
  - Pulsanti categoria come `QToolButton` con icona sopra e testo sotto, altezza fissa; filtro con le estensioni reali del progetto (`.table.json`, `.form.json`, …).
  - `[Untitled]` sostituisce le vecchie voci `[Nuovo …]`; intestazione della lista e suggerimento contestuale.
  - Command Window convertita da `QDialog` a `QWidget` e aperta in MDI; due riquadri con titolo, cronologia ↑/↓, stato con esito ok/errore distinto dai token del tema.
  - Browse con barra di navigazione primo/precedente/successivo/ultimo, colonna selettore record, intestazione della tabella, stato `Record n di m · filtro · ordine`; editing in-place con rollback invariato.
  - `Editing Options` minimale e persistenza delle larghezze colonna per progetto/tabella nella configurazione utente.
  - `Struttura…` della Browse resta un dialog modale: l'integrazione con l'MDI è esplicitamente in O3.
- **Test:** `102 passed`; smoke headless OK; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `01-desktop.png`, `02-navigator.png`, `03-browse-clienti.png`, `09-command-window.png` aggiornati; nuovo `10-desktop-mdi.png` da O1.
- **Problemi aperti:**
  - Query/Label/Immagini/Suoni/Cataloghi/Personalizzati restano disabilitate (fuori 0.2).
  - `Struttura…` della Browse apre ancora un dialog modale (O3).
  - La selezione della categoria non filtra fisicamente i file su disco: usa il catalogo del progetto.
- **Prossimo passo:** Ondata 3 — Table Structure, poi **Checkpoint A**.

## Checkpoint

Nessun checkpoint raggiunto.

## Ripresa

Nessun checkpoint attivo. Prossima azione: **Ondata 3 — Table Structure**. Al termine fermarsi per il **Checkpoint A**.
