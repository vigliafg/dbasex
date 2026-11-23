# Diario di implementazione — dBX UI 0.2

> File **append-only**. Non riscrivere le voci precedenti.
> La verità sullo stato è qui e in `PLAN.md`.

## Stato ondate

| Ondata | Stato | Checkpoint |
|---|---|---|
| O0 — Baseline e design token | completata (2026-11-22) | — |
| O1 — Shell/MDI/menu/tema | completata (2026-11-22) | — |
| O2 — Navigator/Command/Browse | completata (2026-11-22) | — |
| O3 — Table Structure | completata (2026-11-22) | A |
| O4 — Form Designer/Expert/Runtime | completata (2026-11-22) | — |
| O5 — Report Designer/Preview | completata (2026-11-22) | — |
| O6 — Script/Menu/Project | completata (2026-11-22) | B |
| O7 — QA e release 0.2 | completata (2026-11-22) | C |
| UI 0.2.1 — Tema Aurora e menu descrittivi | completata (2026-11-22) | — |
| 0.3.0 — O0 Preparazione | completata (2026-11-22) | — |
| 0.3.0 — O1 Schema graph | completata (2026-11-22) | — |
| 0.3.0 — O2 Canvas ER | completata (2026-11-22) | — |
| 0.3.0 — O3 Editing schema | completata (2026-11-22) | A |
| 0.3.0 — O4 Motore Query | completata (2026-11-22) | — |
| 0.3.0 — O5 Query Designer | completata (2026-11-22) | — |
| 0.3.0 — O6 Query Results/sorgente | completata (2026-11-22) | B |
| 0.3.0 — O7 Release | completata (2026-11-22) | C |

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

### 2026-11-22 — Ondata 3 — avvio
- **Stato:** in corso
- **Obiettivo:** sostituire la struttura a schede con la finestra `Table Structure` a griglia unica, con metadati, toolbar e strumenti secondari.

### 2026-11-22 — Ondata 3 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** griglia unica dei campi, header e metadati dBASE, toolbar, proprietà estese, integrazione con Browse e Navigator.
- **File toccati:** `dbx/designers/table_builder.py` (riscritto), `dbx/ui/data_view.py`, `dbx/ui/navigator.py`, `dbx/ui/main_window.py`, `dbx/ui/design.py`, `tests/test_ui_table_builder.py` (nuovo), `tests/test_ui_designers.py`, `docs/ui-parity.md`.
- **Scelte/deviazioni:**
  - Griglia principale unica con le colonne `Field · Name · Type · Width · Decimal · Index`; niente più schede per i campi.
  - `Decimal` è mappato sul formato `.Nf` del campo (il modello non ha un attributo separato) e resta retrocompatibile.
  - Campi estesi (Obbligatorio, Default, Didascalia, Formato, Regola, Lookup) nel pannello inferiore `Proprietà`; la chiave primaria e gli altri attributi non esposti sono preservati per id.
  - Indici e relazioni restano nelle griglie del pannello inferiore e alimentano la colonna `Index`; le modifiche alla colonna vengono applicate allo stesso modello, senza duplicarlo.
  - Riordino con trascinamento della colonna `Field`; `Tab`/`Invio` sull'ultima cella crea il campo successivo; riga attiva alta il doppio.
  - Metadati `Updated`, `Bytes Used`, `Records`, `Bytes Left` calcolati dal progetto (SQLite); `Bytes Left` è a livello di database.
  - Toolbar: `Open Exclusive` interpretato come blocco/sblocco della modifica strutturale, `Add Records`, `Save As…`, `Stampa…`, più i pulsanti per gli strumenti secondari.
  - Migrazione distruttiva con conferma e backup (il backup era già in `Project.apply_table`); `Save Table` come dialog dedicato.
  - `Save As…` crea una copia con nuovo id tabella; la rinomina di una tabella esistente è rifiutata con messaggio esplicativo, perché il motore non ha ancora una primitiva di rename e non si vuole creare una tabella vuota al posto della vecchia.
  - `Struttura…` della Browse ora emette un segnale e viene aperta in MDI; dopo l'applicazione la Browse ricarica schema, combo di ordinamento e griglia.
- **Test:** `116 passed`; smoke headless OK; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `04-table-structure.png` aggiornato; gli altri rendering rigenerati.
- **Problemi aperti:**
  - Rinomina tabella rimandata a una futura ondata (richiede supporto nel motore).
  - La stampa della struttura è minimale (DDL testuale).
  - `Add Records` genera valori segnaposto per i campi obbligatori senza default.
- **Prossimo passo:** **Checkpoint A**, poi Ondata 4 — Form Designer, Inspector, Form Expert e runtime form.

### 2026-11-22 — Ondata 4 — avvio
- **Stato:** in corso
- **Obiettivo:** portare il Form Designer allo schema a tre zone con interazione completa, Inspector ad albero, Form Expert a cinque passi, eventi runtime e anteprima dentro l'MDI.
- **File previsti:** `dbx/designers/form_builder.py`, `dbx/designers/form_expert.py` (nuovo), `dbx/ui/widgets.py`, `dbx/core/form_model.py`, `dbx/runtime/form_runtime.py`, `dbx/ui/main_window.py`, `dbx/ui/editor_host.py`, `dbx/ui/theme.py`, test, diario.

### 2026-11-22 — Ondata 4 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** Form Designer a tre zone, Object Inspector ad albero, Form Expert, dispatcher eventi e runtime nell'MDI.
- **File toccati:** `dbx/designers/form_builder.py` (riscritto), `dbx/designers/form_expert.py` (nuovo), `dbx/ui/widgets.py`, `dbx/ui/theme.py`, `dbx/ui/main_window.py`, `dbx/ui/editor_host.py`, `dbx/core/form_model.py`, `dbx/runtime/form_runtime.py`, `dbx/smoke.py`, `tools/capture_ui.py`, `tests/test_form_events.py` (nuovo), `tests/test_ui_form_designer.py` (nuovo), `tests/test_ui_form_runtime.py` (nuovo), `tests/test_ui_designers.py`, `docs/ui-parity.md`, rendering.
- **Scelte/deviazioni:**
  - `FormBuilderDialog` diventa `FormDesignerWidget` (`QWidget`) e vive nell'MDI; l'alias `FormBuilderDialog` resta per test, smoke e harness di cattura, senza doppia implementazione.
  - Modello esteso in modo additivo e retrocompatibile: `FormControl.events`, `FormControl.methods`, `FormSpec.events`, `FormSpec.methods`, `backcolor`, `forecolor`, `font_name`. I JSON esistenti si caricano senza migrazione con valori vuoti.
  - Eventi come **azione singola** dello stesso dispatcher dei pulsanti (`save`, `next`, `close`, `script:nome`, `report:nome`, `message:testo`): nessun linguaggio nuovo. Un `onClick` valorizzato sostituisce l'azione predefinita del pulsante; gli errori finiscono in `event_log` e nella status line, mai un crash.
  - Inspector ad albero con gruppi `Font Properties`, `Geometry`, `Data`, `Behavior`, `Layout`, combo in-cell per scelte e booleani `.T./.F.`, `Quick Filter`, schede `Proprietà` / `Eventi` / `Metodi` editabili.
  - Canvas con snap a 8 px, otto maniglie reali disegnate su un overlay trasparente, selezione multipla con Ctrl, spostamento con frecce a 8 px e Shift per il passo fine di 1 px, taglia/copia/incolla/duplica, allinea/distribuisci, porta avanti/indietro, undo/redo a snapshot.
  - Pagine del form come tab strip con aggiunta, rinomina ed eliminazione; lo stato inferiore mostra `Object · Page · Top · Left · Height · Width`.
  - Palette `Controls` con nomi dBASE compatti (`TEXT`, `ENTRYFIELD`, `MEMO`, `CHECKBOX`, …), schede `Standard` / `Custom`, pulsanti dBASE (`OKBUTTON`, `CLOSEBUTTON`, …) mappati sulle azioni runtime; palette `Field` con doppio clic e trascinamento tramite MIME `application/x-dbx-field`.
  - Form Expert come `QWizard` a cinque passi (assistito o vuoto, tabella, campi, layout, font/colori/stile) integrato in `Oggetto → Nuovo form…`; genera un `FormSpec` valido con pulsanti di navigazione.
  - Runtime con azioni estese (`cancel`, `help`, `info`, `browse`, `message:`), eventi `onOpen`/`onClose`, stato del record e log; anteprima aperta nell'MDI e non come dialog modale.
  - `apply_theme` registra `dbx_theme` sull'applicazione: i canvas leggono i token del tema attivo e non più sempre Silver (corretto il contrasto del tema Dark).
  - Nei subwindow MDI stretti le palette restano leggibili e il canvas usa le scrollbar: la palette non è ancora una finestra flottante come nell'originale.
- **Test:** `146 passed`; smoke headless OK con Form Designer, Form Expert e Form Runtime; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `05-form-designer.png` e `06-form-runtime.png` aggiornati; `10-desktop-mdi.png` mostra il designer a tre zone nell'MDI.
- **Problemi aperti:**
  - Palette in pannello ridimensionabile, non flottante/dockabile come in dBASE.
  - Miniatura del Form Expert strutturale, non un rendering del form.
  - Eventi limitati ad azione singola; i corpi dei metodi sono descrittivi e non eseguiti.
  - La rinomina del form tramite `Name` rinomina l'artefatto ma non aggiorna eventuali riferimenti nei menu.
  - Form molto larghi restano scrollabili dentro subwindow MDI strette.
- **Prossimo passo:** Ondata 5 — Report Designer a bande impilate e Preview.

### 2026-11-22 — Ondata 5 — avvio
- **Stato:** in corso
- **Obiettivo:** sostituire il canvas a banda singola con il foglio a bande impilate, due toolbar, dialoghi Insert Field / Sort Order e anteprima completa.
- **File previsti:** `dbx/runtime/report_engine.py`, `dbx/designers/report_builder.py`, `dbx/ui/report_preview.py`, `dbx/io/pdf_export.py`, `dbx/ui/main_window.py`, `dbx/ui/design.py`, test.

### 2026-11-22 — Ondata 5 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** report designer a foglio unico con bande etichettate, formattazione, ordinamenti, gruppi e anteprima completa.
- **File toccati:** `dbx/runtime/report_engine.py`, `dbx/designers/report_builder.py` (riscritto), `dbx/ui/report_preview.py`, `dbx/io/pdf_export.py`, `dbx/ui/main_window.py`, `dbx/ui/design.py`, `dbx/ui/icons.py`, `dbx/smoke.py`, `tools/capture_ui.py`, `tests/test_report_engine.py`, `tests/test_ui_report_designer.py` (nuovo), `tests/test_ui_designers.py`, `docs/ui-parity.md`, rendering.
- **Scelte/deviazioni:**
  - `ReportSpec` esteso in modo additivo: `band_order`, `band_heights`, `band_visible`, `sort_fields`, `groups`; `Control` acquisisce `underline` e `font_name`. I JSON esistenti si caricano con default vuoti e il vecchio `group_by` resta valido.
  - Renderer: `band_visible` e `band_heights` sono rispettati; `sort_fields` ordina in memoria con chiavi multiple; `groups` supporta più livelli con header/footer e totali per livello, mentre `group_by` equivale a un gruppo singolo.
  - L'ordine personalizzato delle bande governa titolo/intestazione e riepilogo; le bande di flusso (`group_header`, `detail`, `group_footer`) mantengono la sequenza di paginazione, perché invertirle romperebbe il flusso dei record. Deviazione annotata.
  - Report Designer convertito in `ReportDesignerWidget` (`QWidget`) e aperto nell'MDI; alias `ReportBuilderDialog` mantenuto per smoke, test e capture.
  - Canvas a foglio unico: gutters con etichette inglesi (`Title`, `Page header`, …), griglia puntinata, delimitatori trascinabili, otto maniglie di resize, selezione singola, allineamento nella banda, zoom 50–200%, stato `L:R:` in pollici.
  - Due toolbar: standard (nuovo, apri, salva, stampa, taglia/copia/incolla, undo/redo, inserisci campo, ordinamento, testo, totali, gruppo, bande) e formattazione (font, corpo, B/I/U, allineamenti, bordo, colore, zoom).
  - Dialoghi funzionanti: `Insert Database Field` con `Browse Field Data…`, `Edit Text Field`, `Record Sort Order` (Add/Remove, direzione, riordino), `Insert Group`, `Total`.
  - Inspector ad albero riusato da O4: gruppi Layout, Data, Format e proprietà del report quando non c'è selezione.
  - I campi sono mostrati come `TABELLA->CAMPO`; `Insert Group` aggiunge anche un campo nel `group_header` per rendere visibile il valore.
  - Preview: toolbar inferiore con primo/precedente/successivo/ultimo, `1 di N`, zoom, `Totale: N`, aggiorna, stampa, PDF, chiudi; pagina singola/continua; fit-width all'apertura; zoom ricordato per sessione.
  - Aggiunti ai token `report_band` / `report_band_active`, così il canvas resta leggibile anche in tema Dark.
  - I pulsanti icona non sono più `autoDefault` per evitare il fondo navy sui pulsanti disabilitati delle toolbar.
- **Test:** `174 passed`; smoke headless OK con report designer a bande e anteprima; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `07-report-designer.png` e `08-report-preview.png` aggiornati; `10-desktop-mdi.png` rigenerato.
- **Problemi aperti:**
  - Selezione singola: allineamento nella banda, non allineamento/distribuzione fra più controlli.
  - L'ordine personalizzato delle bande non inverte le bande di flusso dei record.
  - `Insert Group` non genera automaticamente un totale di gruppo, che si aggiunge con `Total`.
  - Il canvas non visualizza immagini né anteprime reali dei dati.
- **Prossimo passo:** Ondata 6 — Script, Menu, Project Builder; poi **Checkpoint B**.

### 2026-11-22 — Ondata 6 — avvio
- **Stato:** in corso
- **Obiettivo:** allineare Program Editor, Menu Designer e Project Editor, poi fermarsi al Checkpoint B.
- **File previsti:** `dbx/designers/script_builder.py`, `dbx/designers/menu_builder.py`, `dbx/designers/project_builder.py`, `dbx/ui/main_window.py`, `dbx/smoke.py`, `tools/capture_ui.py`, test.

### 2026-11-22 — Ondata 6 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'ondata
- **Obiettivo:** Program Editor con numeri di riga e sintassi, Menu Designer ad albero con anteprima, Project Editor con validazione e build.
- **File toccati:** `dbx/designers/script_builder.py` (riscritto), `dbx/designers/menu_builder.py` (riscritto), `dbx/designers/project_builder.py`, `dbx/ui/main_window.py`, `dbx/smoke.py`, `tools/capture_ui.py`, `tests/test_ui_script_editor.py` (nuovo), `tests/test_ui_menu_designer.py` (nuovo), `tests/test_ui_project_editor.py` (nuovo), `docs/ui-parity.md`, rendering.
- **Scelte/deviazioni:**
  - `ScriptBuilderDialog` diventa `ScriptBuilderWidget` (`QWidget`) in MDI, con alias storico. L'editor usa un `CodeEditor` con area dei numeri di riga, riga corrente evidenziata, tab a due spazi e `ScriptHighlighter` per parole chiave, stringhe, commenti e numeri.
  - La vista azioni e la vista sorgente restano bidirezionali: l'albero rigenera il testo, «Dal testo alle azioni» lo reimporta; il log di esecuzione sta sotto l'editor. L'Inspector a destra modifica i parametri del passo selezionato.
  - I dati del passo sono indirizzati con un percorso `(contenitore, indice)` invece dell'oggetto Python: Qt copia i dizionari nei `QVariant`, quindi l'identità non è affidabile. Il percorso rende stabili modifiche, spostamenti e rimozioni anche nei blocchi annidati.
  - `MenuBuilderDialog` diventa `MenuBuilderWidget`: albero voci/separatori, proprietà tipizzate, destinazione filtrata per azione, spostamento su/giù, anteprima come `QMenuBar` con conteggio voci.
  - Nuovo `ProjectEditorWidget`: albero oggetti per categoria con doppio clic verso l'oggetto, impostazioni (`title`, `main_form`, `main_menu`), validazione visiva e build distribuibile con zip invariato.
  - `Progetto → Modifica progetto…` apre il Project Editor in MDI; l'azione di build globale del menu resta disponibile.
  - Program Editor, Menu Designer e Project Editor usano lo stesso chrome dei designer O4/O5: toolbar icona+testo, `status_message`, `saved`, chiusura con conferma se `is_dirty()`.
  - I dizionari di Qt importati in `project_builder` sono a livello di modulo: il modulo resta importabile senza QApplication e la build headless non cambia.
- **Test:** `197 passed`; smoke headless OK con Program Editor, Menu Designer e Project Editor; `tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** nuovi `11-script-editor.png`, `12-menu-designer.png`, `13-project-editor.png`; gli altri rendering rigenerati.
- **Problemi aperti:**
  - L'anteprima del menu mostra la barra con il titolo; le voci compaiono nel popup, non in un pannello sempre visibile.
  - La build del Project Editor è sincrona e non ha barra di avanzamento.
  - Il Program Editor non offre esecuzione passo-passo né breakpoint.
  - Il Project Editor non modifica le proprietà degli oggetti: apre i rispettivi designer.
- **Prossimo passo:** **Checkpoint B**; poi Ondata 7 — QA e release 0.2.

## Checkpoint B — fine Ondata 6 (2026-11-22)

- **Stato ondate:** O0–O6 completate; O7 da iniziare.
- **Test eseguiti:** `197 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK; `python tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** `11-script-editor.png`, `12-menu-designer.png`, `13-project-editor.png` aggiunti; rendering `01`–`10` rigenerati.
- **Decisioni rimandate all'utente:** nessuna bloccante.
- **RIPRESA:** checkpoint B attivo. Dopo il comando `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare `git status`/`git log` e iniziare l'**Ondata 7 — QA e release 0.2**, senza ripartire da O1–O6. O7 chiude con il Checkpoint C.

## Checkpoint A — fine Ondata 3 (2026-11-22)

- **Stato ondate:** O0, O1, O2, O3 completate; O4, O5, O6, O7 da iniziare.
- **Test eseguiti:** `116 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK; `python tools/capture_ui.py` OK in Silver e Dark.
- **Screenshot:** rendering `01`–`10` aggiornati; `04-table-structure.png` riflette la nuova finestra.
- **Decisioni rimandate all'utente:** nessuna.
- **RIPRESA:** checkpoint A attivo. Dopo il comando `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare `git status`/`git log` e iniziare l'**Ondata 4 — Form Designer, Inspector, Form Expert e runtime form**, senza ripartire da O1–O3. Non superare O6 senza il Checkpoint B.

## Checkpoint

- **A** — raggiunto il 2026-11-22 (fine O3).
- **B** — raggiunto il 2026-11-22 (fine O6).
- **C** — raggiunto il 2026-11-22 (release 0.2.0).

## Ripresa

**Release 0.2.0 pubblicata.** Nessuna ondata successiva prevista nel piano 0.2; Query/Label Designer e Tutor restano per la 0.3.


### 2026-11-22 — Ondata 7 — avvio
- **Stato:** in corso
- **Obiettivo:** QA visiva e funzionale, accessibilità, HiDPI, prestazioni, CI e release 0.2.0.
- **File previsti:** README, CHANGELOG, `docs/ui-parity.md`, `docs/reference/dbase55/ui-spec.md`, `docs/qa-0.2.md`, CI, token/QSS, engine report, test, diario.

### 2026-11-22 — Ondata 7 — chiusura
- **Stato:** completata
- **Branch/commit:** `main` — commit di release; tag `v0.2.0`
- **Obiettivo:** passata finale sulla parità, accessibilità, HiDPI, prestazioni, documentazione e release.
- **File toccati:** `README.md` (riscritto), `CHANGELOG.md` (nuovo), `docs/qa-0.2.md` (nuovo), `docs/ui-parity.md`, `docs/reference/dbase55/ui-spec.md`, `docs/reference/dbx-ui/README.md` (nuovo), `docs/reference/dbx-ui/renders/*`, `.github/workflows/ci.yml`, `pyproject.toml`, `dbx/__init__.py`, `dbx/runtime/report_engine.py`, `dbx/samples.py`, `dbx/ui/app.py`, `dbx/ui/design.py`, `dbx/ui/icons.py`, `dbx/ui/navigator.py`, `dbx/ui/widgets.py`, `dbx/ui/data_view.py`, `dbx/ui/command_window.py`, `dbx/designers/form_builder.py`, `dbx/designers/report_builder.py`, `dbx/designers/script_builder.py`, `dbx/designers/menu_builder.py`, `dbx/designers/project_builder.py`, `tests/test_ui_shell.py`, `tests/test_report_engine.py`, `tests/test_performance.py` (nuovo), `PLAN.md`, `DIARIO.md`.
- **Scelte/deviazioni:**
  - Versione portata a **0.2.0** in `dbx/__init__.py` e `pyproject.toml`; `PyQt6` fissato a `6.10.2` per riproducibilità della CI.
  - Correzione funzionale dei report: i testi fissi interpolano `[campo]` (l'intestazione gruppo mostra il valore, non il segnaposto); i totali accettano nomi di campo nudi; il conteggio conta anche valori non numerici. Il progetto demo usa `[numero]` per il totale fatture.
  - QA visiva: palette del Form Designer compattata (altezza 22 px, font 8 px, splitter 420/260) così tutti i pulsanti dBASE e tutti i campi restano visibili nel pannello; nessuna modifica al modello.
  - Accessibilità: nomi accessibili su Navigator, Command Window, Inspector, canvas, griglie ed editor; ordine di tabulazione in Navigator e designer; focus tratteggiato su pulsanti, tool button e schede; guida `F1` e README con le scorciatoie.
  - HiDPI: politica di scala `PassThrough`, icone già multi-risoluzione 16–48 px; verifica visiva a 150% con rendering nitido di desktop, Form Designer e Report Designer.
  - Prestazioni: nuovo `tests/test_performance.py` con budget 2 s per apertura demo e form con 100 controlli; misura reale ampiamente sotto il budget.
  - CI: test headless con `QT_QPA_PLATFORM=offscreen` su Linux/Windows/macOS, smoke, cattura screenshot su Linux e artifact `dbx-screenshots-silver`.
  - Documentazione: README riscritto per la 0.2 (funzioni, scorciatoie, accessibilità, HiDPI, limiti); `CHANGELOG.md` con note di rilascio; `docs/qa-0.2.md` con checklist finestra per finestra; `ui-spec.md` aggiornata nella sezione di corrispondenza.
  - Rimossi i sette screenshot obsoleti della 0.1 in `docs/reference/dbx-ui/` (restano nella storia git); aggiunto un indice che punta a `renders/` come fonte canonica.
  - Query Designer, Query Results, Label Designer e Interactive Tutor restano fuori scope 0.2 e sono dichiarati come tali, con categorie Navigator disabilitate.
- **Test:** `205 passed`; smoke headless OK; cattura Silver e Dark OK; verifica HiDPI a 150% OK.
- **Screenshot:** tutti i rendering `01`–`13` rigenerati in Silver; cattura Dark verificata. Versione 0.2.0 visibile nella barra di stato.
- **Problemi aperti:**
  - Palette non flottante e Report Designer a selezione singola.
  - Ordine personalizzato delle bande di flusso non invertibile.
  - Build sincrona; nessun debugger passo-passo.
  - Anteprima menu come barra, non popup sempre aperto.
  - La CI su Windows/macOS va confermata al primo push del workflow aggiornato.
- **Prossimo passo:** nessuna ondata 0.2; aprire la 0.3 con Query Designer, Query Results e Label Designer.

## Checkpoint C — release 0.2.0 (2026-11-22)

- **Stato ondate:** O0–O7 completate; piano 0.2 chiuso.
- **Versione:** `0.2.0`; tag `v0.2.0`.
- **Test eseguiti:** `205 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK; `python tools/capture_ui.py` OK in Silver e Dark; verifica HiDPI a 150%.
- **Screenshot:** `01`–`13` in `docs/reference/dbx-ui/renders/`; indice in `docs/reference/dbx-ui/README.md`.
- **Documenti:** `README.md`, `CHANGELOG.md`, `docs/qa-0.2.md`, `docs/ui-parity.md`, `docs/reference/dbase55/ui-spec.md`.
- **Decisioni rimandate all'utente:**
  - Confermare la pubblicazione GitHub della release `v0.2.0` se il tag locale non basta.
  - Decidere se la 0.3 debba partire da Query Designer o da Label Designer.
- **RIPRESA:** piano 0.2 concluso. Per una nuova sessione leggere `PLAN.md` e questo diario; la prima attività non completata è la **0.3 — Query Designer, Query Results e Label Designer**. Non ripartire da O0–O7.


### 2026-11-22 — UI 0.2.1 — Tema Aurora e menu icona + descrizione
- **Stato:** completata
- **Branch/commit:** `main` — commit dell'aggiornamento grafico; tag `v0.2.1`
- **Obiettivo:** sostituire lo sfondo grigio con un tema colorato e brillante, colorare ogni zona
  dell'interfaccia e rifare i menu con icona + descrizione.
- **File toccati:** `dbx/ui/design.py` (tema Aurora e QSS a gradienti), `dbx/ui/menu.py` (nuovo:
  `MenuEntry`, `DescriptiveMenu`, `add_entry`), `dbx/ui/main_window.py` (menu descrittivi, sfondo
  MDI, icone), `dbx/ui/theme.py`, `dbx/ui/navigator.py`, `dbx/ui/widgets.py`, `dbx/ui/data_view.py`,
  `dbx/ui/command_window.py`, `dbx/designers/form_builder.py`, `dbx/designers/report_builder.py`,
  `dbx/designers/script_builder.py`, `dbx/designers/menu_builder.py`, `dbx/designers/project_builder.py`,
  `dbx/runtime/form_runtime.py`, `dbx/config.py`, `dbx/__main__.py`, `dbx/__init__.py`, `pyproject.toml`,
  `tools/capture_ui.py`, test, README, CHANGELOG, docs, rendering.
- **Scelte/deviazioni:**
  - Nuovo tema **Aurora** come predefinito: superfici chiare, menu bar indaco/viola, toolbar azzurro/lavanda,
    Navigator con pastiglie colorate, area MDI azzurro/ciano, status bar indaco/teal, tabelle con
    intestazioni teal, pannelli e inspector con gradienti pastello.
  - `light` e `bright` puntano ad Aurora; `silver` resta selezionabile per il confronto storico e
    `dark` conserva il tema scuro. La configurazione esistente con tema `light` passa automaticamente
    al nuovo aspetto.
  - Menu principali ricostruiti con un widget per voce: icona, titolo in grassetto, descrizione,
    scorciatoia e checkmark; `MenuEntry` mantiene sincronizzati abilitazione, testo, icona e stato
    con gli `QAction` originali. Gli alias dei menu restano compatibili con test e API esistenti.
  - Aggiunta `DescriptiveMenu` per il focus sulla prima voce all'apertura, navigazione con frecce,
    Invio e Invio a capo; menu contestuali di Navigator, pagine del Form Designer e bande del Report
    Designer usano lo stesso sistema.
  - Lo sfondo `QMdiArea` viene impostato con un `QLinearGradient` e segue il tema attivo anche dopo
    un cambio a runtime; prima il grigio predefinito ignorava il QSS.
  - Focus dei campi e delle viste cambiato da tratteggio rosa a bordo pieno nel colore d'accento, più
    leggibile; restano focus visibili su pulsanti e schede.
  - Icone multi-risoluzione e tema Dark aggiornati con i nuovi token; verificati a 150%.
- **Test:** `209 passed`; smoke headless OK; cattura Aurora e Dark OK.
- **Screenshot:** serie `01`–`13` rigenerata in Aurora; nuovo `14-menu-progetto.png`; cattura Dark
  verificata.
- **Problemi aperti:**
  - Le submenu standard (es. Progetti recenti) hanno icona + titolo ma non la descrizione su due righe.
  - Il tema Aurora è più ricco del tema Silver: i testi lunghi nelle palette restano elisi.
  - La CI Windows/macOS va confermata al primo run dopo il push.
- **Prossimo passo:** 0.3 — Query Designer, Query Results e Label Designer.

## Checkpoint UI 0.2.1
- **Versione:** `0.2.1`; tag `v0.2.1`.
- **Test:** `209 passed`, smoke OK, cattura Aurora/Dark OK.
- **RIPRESA:** piano 0.2 concluso con aggiornamento grafico 0.2.1. La prima attività non completata
  resta la **0.3 — Query Designer, Query Results e Label Designer**.

### 2026-11-22 — UI 0.2.2 — correzione voci menu non responsive
- **Stato:** completata
- **Obiettivo:** rendere reattive le voci dei menu a discesa della barra principale.
- **File toccati:** `dbx/ui/menu.py`, `tests/test_ui_shell.py`, `CHANGELOG.md`, `docs/qa-0.2.md`.
- **Correzioni:**
  - Il passaggio del mouse su una voce sposta il focus sulla voce, evitando due righe evidenziate
    contemporaneamente (prima la prima voce restava selezionata mentre il mouse ne evidenziava un'altra).
  - Il menu viene chiuso **prima** di eseguire l'azione, così non resta aperto sopra dialoghi o finestre
    e le voci non sembrano bloccate.
  - I sottomenu hanno descrizione, freccia, apertura con clic, freccia destra o hover breve.
  - Aggiunti test di regressione: clic su una voce reale della barra principale e spostamento del
    focus con il mouse.
- **Test:** `209 passed`; smoke OK; cattura Aurora/Dark OK.
- **Prossimo passo:** 0.3 — Query Designer, Query Results e Label Designer.

### 2026-11-22 — Ondata 0.3.0 — avvio e preparazione
- **Stato:** in corso
- **Obiettivo:** preparare il piano 0.3.0 con Database Designer ER al posto del Label Designer,
  Query Designer, Query Results e query come sorgente dati.
- **Decisioni:**
  - Label Designer ed Etichette rimossi; il Navigator sostituisce la categoria con **Schema**.
  - Nuova categoria progetto `diagrams` con artefatto canonico `schema.diagram.json`.
  - Il grafo ER deriva da `Table`/`ForeignKey`; il diagramma salva solo layout, zoom e note.
  - Editing tabelle/campi riusa `TableBuilderDialog`; relazioni e layout sono gestiti dal canvas.
  - Applicazione delle modifiche con `Project.apply_table`, backup e conferma.
  - Query SELECT in sola lettura, INNER/LEFT JOIN; query come sorgente di form/report.
  - Form su query in sola lettura nella 0.3.
  - Export diagramma PNG/SVG.
- **Prossimo passo:** O1 — schema graph e layout ER.


### 2026-11-22 — Ondata 0.3.0 — O0 chiusura
- **Stato:** completata
- **Obiettivo:** preparazione del piano 0.3.0 e baseline.
- **Scelte:** Label Designer rimosso; Navigator con categoria Schema; diagramma `schema` come artefatto
  `diagrams`; grafo derivato dai metadati; query come sorgente dati in O6.
- **Test:** baseline `224 passed` dopo le modifiche O1–O3.
- **Prossimo passo:** O1.

### 2026-11-22 — Ondata 0.3.0 — O1 schema graph e layout
- **Stato:** completata
- **File:** `dbx/core/schema_graph.py`, `dbx/core/diagram_model.py`, `dbx/core/project.py`,
  `tests/test_schema_graph.py`, `tests/test_diagram_model.py`.
- **Scelte:** nodi = `Table` reali; archi = `ForeignKey`; cardinalità 1:1 se le colonne figlio sono
  PK o indice unico, altrimenti 1:N; layout salvato in `diagrams/schema.diagram.json` con posizioni,
  zoom e note; auto-layout deterministico.
- **Test:** 11 nuovi test sul grafo, cardinalità, validazione, roundtrip e layout.

### 2026-11-22 — Ondata 0.3.0 — O2 Database Designer
- **Stato:** completata
- **File:** `dbx/designers/database_designer.py`, `dbx/ui/navigator.py`, `dbx/ui/main_window.py`,
  `dbx/samples.py`, `tools/capture_ui.py`, test.
- **Scelte:** card tabella con PK/FK, tipi e caption; archi ortogonali crow’s foot con cardinalità e
  `ON DELETE`; pan, zoom 25–200%, griglia, auto-layout; export PNG/SVG; Inspector condiviso.
  Categoria Navigator **Schema** al posto di Etichette; `Oggetto → Database Designer…`; diagramma
  demo nel progetto Rubrica.
- **Test:** apertura MDI, drag/zoom, layout persistente, export PNG/SVG, Navigator aggiornato.
- **Screenshot:** `15-database-designer.png`.

### 2026-11-22 — Ondata 0.3.0 — O3 editing schema
- **Stato:** completata
- **File:** `dbx/designers/database_designer.py`, test.
- **Scelte:** nuova tabella e modifica campi via `TableBuilderDialog`; creazione relazione con dialog
  figlio/padre e campi PK/unique; eliminazione relazione e tabella con conferma; applicazione tramite
  `Project.apply_table`/`drop_table` con backup; blocco della cancellazione di tabelle referenziate.
- **Test:** nuova relazione, eliminazione relazione, eliminazione tabella, schema persistente;
  `224 passed`; smoke OK; cattura Aurora/Dark OK.
- **Prossimo passo:** **Checkpoint A**, poi O4 — motore Query.

## Checkpoint A — fine O3 (2026-11-22)

- **Stato ondate:** O0, O1, O2, O3 completate; O4–O7 da iniziare.
- **Test eseguiti:** `224 passed`; smoke headless OK; cattura screenshot OK.
- **Screenshot:** `15-database-designer.png` aggiunto; `01`–`14` rigenerati in Aurora.
- **Decisioni:** Label Designer rimosso; Database Designer ER è la sostituzione ufficiale.
- **RIPRESA:** checkpoint A attivo. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l'**Ondata 4 — motore Query**. Non ripartire da O0–O3; fermarsi
  al **Checkpoint B** dopo O6.

### 2026-11-22 — Ondata 0.3.0 — O4 motore Query
- **Stato:** in corso
- **Obiettivo:** modello delle query statiche e motore di esecuzione riutilizzabile da Query Designer,
  Query Results, form e report.
- **Scope:** SELECT in sola lettura, campi, INNER/LEFT JOIN, filtri con valori letterali, ordinamento,
  risultato tipizzato. Nessun parametro interattivo.
- **File:** `dbx/core/query_model.py`, `dbx/core/query_engine.py`, `dbx/core/project.py`,
  `dbx/designers/project_builder.py`, `tests/test_query_model.py`, `tests/test_query_engine.py`.
- **Scelte:** query = tabella base + campi + join INNER/LEFT + filtri letterali + ordinamento;
  operatori `eq/ne/gt/ge/lt/le/contains/starts/ends/null/notnull`; SQL sempre parametrizzato con
  `?`, valori convertiti secondo il tipo del campo; `QueryResult` con colonne tipizzate
  (`key`, `table`, `field`, `caption`, `type`, `size`, `fmt`) e righe come dizionari; alias espliciti
  e nomi output qualificati in caso di campi omonimi; `preview_sql` per l'anteprima; nuova categoria
  progetto `queries` con suffisso `.query.json`.
- **Test:** 18 nuovi test su modello, validazione, SQL, join, filtri, booleani, LIKE con escape,
  DISTINCT, NULL, parametri, risultato tipizzato e persistenza. Suite completa verde.
- **Prossimo passo:** O5 — Query Designer.

### 2026-11-22 — Ondata 0.3.0 — O5 Query Designer
- **Stato:** in corso
- **Obiettivo:** designer visuale delle query sul modello O4, con tabelle, join, campi, filtri,
  ordinamento, anteprima SQL e risultato; salvataggio come artefatto `queries`.
- **File:** `dbx/designers/query_builder.py` (nuovo), `dbx/ui/navigator.py`,
  `dbx/ui/main_window.py`, `dbx/samples.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_ui_query_designer.py` (nuovo), test Navigator/Samples.
- **Scelte:** designer a due zone con albero tabelle/campi a spunta e schede Campi / Filtri /
  Ordinamento / SQL / Risultato; join aggiunti da dialog che propone i campi dalle foreign key;
  query di esempio `fatture_clienti` (INNER JOIN) e `clienti_attivi` (filtro) nel progetto demo;
  nuova query da `Oggetto → Nuova query…` e dal Navigator; categoria Query abilitata con filtro
  `*.query.json`; anteprima risultato limitata a 500 righe; rinomina con `Project.put_object`
  e `previous_name`.
- **Test:** 10 test del designer (caricamento, campi/alias, filtri/ordinamento, join, suggerimento
  FK, salvataggio/rinomina, salvataggio bloccato, nuova query, apertura MDI); suite completa verde;
  smoke con Query Designer; catture Aurora e Dark.
- **Screenshot:** `16-query-designer.png`.
- **Prossimo passo:** O6 — Query Results, query come sorgente dati di form/report, validazione,
  build, QA e Checkpoint B.


### 2026-11-22 — Ondata 0.3.0 — O6 Query Results e query come sorgente
- **Stato:** completata
- **Obiettivo:** chiudere il flusso delle query con Query Results, form e report alimentati da query,
  validazione di progetto e QA del Checkpoint B.
- **File:** `dbx/ui/query_results.py`, `dbx/runtime/query_rowset.py` (nuovi),
  `dbx/designers/query_builder.py`, `dbx/designers/form_expert.py`,
  `dbx/designers/form_builder.py`, `dbx/designers/report_builder.py`,
  `dbx/runtime/form_runtime.py`, `dbx/runtime/report_engine.py`, `dbx/ui/report_preview.py`,
  `dbx/ui/main_window.py`, `dbx/ui/navigator.py`, `dbx/core/form_model.py`,
  `dbx/core/query_engine.py`, `dbx/core/types.py`, `dbx/designers/project_builder.py`,
  `dbx/samples.py`, `dbx/smoke.py`, `tools/capture_ui.py`, test e documentazione.
- **Scelte:**
  - `QueryResult.as_table()` e `query_table()` espongono colonne, tipi e didascalie come una `Table`
    sintetica, riusata da form, report, designer ed export senza duplicare il modello.
  - `QueryRowset` fornisce navigazione read-only con la stessa interfaccia minima di `Rowset`;
    `save`/`delete` sollevano `RowsetError` e i pulsanti Nuovo/Salva/Elimina sono disabilitati.
  - `FormSpec` e `ReportSpec` hanno `source_type`/`query` additivi, con default `table`.
  - Form Expert sceglie tabella o query; su query genera solo campi e navigazione, senza CRUD.
  - Il nuovo report sceglie tabella o query; il Report Designer usa una tabella sintetica per i
    dialoghi Insert Field / Group / Total / Sort Order; anteprima, filtri e ordinamento lavorano
    sulle righe della query.
  - Query Results è una griglia read-only con formattazione dBX, aggiornamento ed export CSV.
  - `validate_project` valida le `QuerySpec` e i riferimenti `query` di form e report.
  - Corretto `types.python_format`: il formato data predefinito ora viene tradotto in strftime.
  - Demo: `form_clienti_attivi` (query read-only) e `fatture_clienti_report` (report su query), più
    due voci nel menu principale.
- **Test:** 269 test; nuovi test su cursore read-only, Query Results, export CSV, form/report su
  query, Form Expert query, validazione delle sorgenti. Suite completa, smoke e catture verdi.
- **Screenshot:** `17-query-results.png`, `18-form-query.png`, `19-report-query.png`.
- **Prossimo passo:** Checkpoint B, poi O7 — release 0.3.0.

## Checkpoint B — fine O6 (2026-11-22)

- **Stato ondate:** O0–O6 completate; O7 da iniziare. Database Designer, Query Designer, Query Results
  e query come sorgente di form/report sono funzionanti.
- **Test eseguiti:** `269 passed`; smoke headless OK con Query Designer, Query Results, form e report
  su query; catture Aurora e Dark OK.
- **Screenshot:** serie `01`–`19`; nuovi `17-query-results.png`, `18-form-query.png`,
  `19-report-query.png`.
- **Decisioni:** form su query in sola lettura nella 0.3; query statiche senza parametri interattivi;
  report su query con filtro/ordine applicati alle righe; version resta 0.2.2 fino a O7.
- **RIPRESA:** Checkpoint B attivo. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l'**Ondata 7 — release 0.3.0**: QA finale, versione 0.3.0,
  CHANGELOG, tag `v0.3.0`, note di rilascio. Non ripartire da O0–O6.

### 2026-11-22 — Ondata 0.3.0 — O7 Release 0.3.0
- **Stato:** in corso
- **Obiettivo:** QA finale, versione 0.3.0, CHANGELOG, note di aggiornamento, tag `v0.3.0`.
- **Scope:** bump versione, documentazione di release, verifica completa test/smoke/screenshot,
  checkpoint C.
- **File:** `dbx/__init__.py`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `PLAN.md`,
  `docs/qa-0.3.md`, `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`,
  `tests/test_ui_shell.py`, rendering `01`–`19`.
- **Scelte:**
  - versione `0.3.0` in `dbx/__init__.py`, `pyproject.toml`, README e test di release;
  - CHANGELOG 0.3.0 con sezioni Aggiunto / Cambiato / Corretto / Note di aggiornamento e link al tag;
  - README aggiornato al flusso query (Database Designer → Query Designer → Query Results → form e
    report su query) e all'architettura con `query_model`, `query_engine`, `query_rowset`,
    `query_builder`, `query_results`, `database_designer`;
  - `docs/ui-parity.md` e `docs/reference/dbx-ui/README.md` riallineati alla release 0.3.0;
  - `docs/qa-0.3.md` chiuso come collaudo di release.
- **Test:** `269 passed`; smoke headless OK; catture Aurora e Dark OK; `dbx --version` = 0.3.0.
- **Screenshot:** serie canonica `01`–`19` rigenerata in Aurora; Dark verificato.
- **Problemi aperti:** nessuno bloccante; restano i limiti dichiarati della 0.3.
- **Prossimo passo:** Checkpoint C e attesa di nuove istruzioni.

## Checkpoint C — release 0.3.0 (2026-11-22)

- **Stato ondate:** O0–O7 completate. Release 0.3.0 con Database Designer ER, motore Query,
  Query Designer, Query Results e query come sorgente di form e report.
- **Test eseguiti:** `269 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python tools/capture_ui.py` OK; `python tools/capture_ui.py --theme dark` OK.
- **Screenshot:** serie `01`–`19` in Aurora; nuovi `16-query-designer.png`, `17-query-results.png`,
  `18-form-query.png`, `19-report-query.png`.
- **Rilascio:** versione `0.3.0`, tag `v0.3.0`, CHANGELOG e note di aggiornamento; progetti 0.1/0.2
  compatibili senza migrazione.
- **Decisioni rimandate all'utente:** eventuale 0.4 (aggregazioni, parametri query, più diagrammi,
  form su query modificabili, RIGHT/FULL JOIN, Label Designer alternativo) da pianificare.
- **RIPRESA:** piano 0.3.0 concluso con il Checkpoint C. La prima attività non completata è la
  definizione della prossima release; non ripartire da O0–O7 senza una nuova pianificazione.

### 2026-11-22 — Ondata 0.4.0 — O0 Preparazione: esperti Paradox e passi script FileMaker
- **Stato:** completata
- **Branch/commit:** `main`; commit documentale O0.
- **Obiettivo:** documentare le fonti e fissare le decisioni di trapianto per la 0.4.0
  (esperti Paradox + QBE) e la 0.5.0 (passi script predefiniti in stile FileMaker).
- **File toccati:** `PLAN.md`, `DIARIO.md`,
  `docs/reference/inspirations/paradox-experts-qbe.md` (nuovo),
  `docs/reference/inspirations/filemaker-script-steps.md` (nuovo).
- **Scelte:**
  - due release separate: 0.4.0 esperti + QBE, 0.5.0 azioni script;
  - QBE in sola lettura, con modello additivo `QueryFilter.value2`/`group` e operatori
    `between`/`like`/`ref`; example elements nella forma `_nome`;
  - esperti come generatori di artefatti normali, poi aperti nei designer esistenti;
  - catalogo `ACTIONS` categorizzato con descrizioni e Step Picker, senza nuovo linguaggio;
  - scritture script immediate per passo, con log e `revert_record`;
  - fuori scope: query di modifica, crosstab/CALC, parametri interattivi, trigger, account,
    server, plugin, Label/Chart/Launcher Expert.
- **Test:** `269 passed`; smoke headless OK. Nessuna modifica al codice.
- **Screenshot:** nessuno; O0 è documentale.
- **Problemi aperti:** nessuno.
- **Prossimo passo:** O1 — shell esperti e Table Expert.

### 2026-11-22 — Ondata 0.4.0 — O1 Shell esperti e Table Expert
- **Stato:** completata
- **Branch/commit:** `main`; commit O1.
- **Obiettivo:** introdurre lo shell comune degli esperti e il primo wizard completo
  (tabella), con ingresso da menu e Navigator.
- **File toccati:** `dbx/designers/expert_common.py` (nuovo), `dbx/designers/table_expert.py`
  (nuovo), `dbx/ui/main_window.py`, `dbx/ui/navigator.py`, `dbx/ui/icons.py`,
  `dbx/smoke.py`, `tools/capture_ui.py`, `tests/test_table_expert.py` (nuovo),
  `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - `ExpertWizard` minimale (pulsanti, aiuto, stile) e `FieldEditor` riusabile; nessun framework
    di wizard.
  - Table Expert in 4 passi: nome/template, campi, indici, riepilogo con DDL.
  - Template: Vuota, Contatti, Fatture, Inventario, Attività; campi con id nuovi a ogni apertura.
  - Indici semplici per campo (con flag unico); la modifica avanzata resta nel Table Builder.
  - La creazione usa `Project.apply_table`, quindi backup e migrazioni restano nel motore.
  - Nome tabella normalizzato con `slugify`; didascalia libera.
  - Icona `esperto` (bacchetta) disegnata a runtime; nessun asset nuovo.
  - Ingresso: `Oggetto → Nuovo con esperto → Tabella…` e menu contestuale del Navigator.
- **Test:** `275 passed`; smoke headless OK con voce `table expert`; cattura Aurora OK.
- **Screenshot:** `20-table-expert.png`.
- **Problemi aperti:** nessuno; Query/Report Expert e QBE restano nelle ondate successive.
- **Prossimo passo:** O2 — Query Expert e Report Expert.

### 2026-11-22 — Ondata 0.4.0 — O2 Query Expert e Report Expert
- **Stato:** completata
- **Branch/commit:** `main`; commit O2.
- **Obiettivo:** completare gli esperti di query e report e allineare il Form Expert allo shell comune.
- **File toccati:** `dbx/designers/query_expert.py` (nuovo), `dbx/designers/report_expert.py`
  (nuovo), `dbx/designers/expert_common.py`, `dbx/designers/form_expert.py`,
  `dbx/ui/main_window.py`, `dbx/ui/navigator.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_query_expert.py` (nuovo), `tests/test_report_expert.py` (nuovo),
  `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - `FieldTransfer` condiviso per la scelta dei campi; niente duplicazione tra query e report.
  - Query Expert: tabella base, join suggeriti dalle FK in entrambe le direzioni, campi,
    criteri AND, ordinamento, riepilogo SQL. Gli OR restano nella modalità QBE di O3.
  - Report Expert: sorgente tabella o query, layout tabellare/colonnare/riepilogo, campi,
    gruppo, ordinamento, orientamento/font e riepilogo.
  - Il layout Riepilogo richiede un gruppo al momento di Avanti/Fine; il modello senza gruppo
    resta un report tabellare valido.
  - `ReportSpec` viene popolato con le bande esistenti (titolo, page header, dettaglio,
    gruppo, page footer) e validate con lo stesso motore.
  - Form Expert ora eredita da `ExpertWizard`; comportamento invariato.
  - Voci `Nuovo con esperto` per tabella, query, form e report nel menu Oggetto e nel
    menu contestuale del Navigator.
- **Test:** `286 passed`; smoke headless OK con `query expert` e `report expert`; cattura
  Aurora OK.
- **Screenshot:** `21-query-expert.png`, `22-report-expert.png`.
- **Problemi aperti:** nessuno bloccante; QBE e OR sono il scope di O3.
- **Prossimo passo:** O3 — modello e motore QBE, poi Checkpoint A.

### 2026-11-22 — Ondata 0.4.0 — O3 Modello e motore QBE
- **Stato:** completata
- **Branch/commit:** `main`; commit O3.
- **Obiettivo:** estendere il modello e il motore delle query per il QBE read-only:
  righe OR, intervalli, pattern QBE ed example elements.
- **File toccati:** `dbx/core/query_model.py`, `dbx/core/query_engine.py`,
  `tests/test_query_model.py`, `tests/test_qbe_model.py` (nuovo), `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - `QueryFilter` acquisisce `value2` (secondo estremo di `between`) e `group`
    (stesso gruppo = AND, gruppi diversi = OR), con default retrocompatibili.
  - Nuovi operatori: `between` (`BETWEEN ? AND ?`), `like` (pattern QBE con `*`/`?`
    e `%`/`_` letterali) e `ref` (confronto tra due campi già presenti, traduzione
    degli example elements).
  - Compilazione `WHERE (gruppo 0) OR (gruppo 1)` con AND interno; parametri ordinati
    per gruppo.
  - Validazione: intervallo completo, gruppo non negativo, riferimento esistente e
    tipi compatibili per `ref`; nessuna modifica ai JSON 0.3.
  - Il QBE resta in sola lettura: nessuna query Insert/Delete/Set/ChangeTo.
- **Test:** `296 passed`; smoke headless OK; catture Aurora e Dark OK.
- **Screenshot:** serie `01`–`22` invariata; nessuna nuova UI in O3.
- **Problemi aperti:** nessuno bloccante; l’interfaccia QBE arriva in O4.
- **Prossimo passo:** O4 — UI QBE, sincronizzazione e release 0.4.0.

## Checkpoint A — fine O3 (2026-11-22)

- **Stato ondate:** 0.4.0 O0–O3 completate. Esperti Table/Query/Report e Form Expert
  allineato; modello e motore QBE pronti (OR, between, like, ref).
- **Test eseguiti:** `296 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python tools/capture_ui.py` OK; `python tools/capture_ui.py --theme dark` OK.
- **Screenshot:** serie `01`–`22`; nuovi `20-table-expert.png`, `21-query-expert.png`,
  `22-report-expert.png` nelle ondate precedenti. Nessun rendering nuovo in O3.
- **Decisioni:** QBE solo ricerca; example elements come `ref`; `group` additivo;
  OR su LEFT JOIN da documentare/avvisare in O4.
- **RIPRESA:** Checkpoint A attivo. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`,
  controllare `git status`/`git log` e iniziare l’**Ondata 4 — UI QBE e release 0.4.0**:
  toggle QBE/Guidato, query image, sincronizzazione, aiuto, avviso LEFT JOIN, test UI,
  screenshot `23-qbe-mode.png`, QA e versione 0.4.0. Non ripartire da O0–O3.

### 2026-11-22 — Ondata 0.4.0 — O4 UI QBE e release 0.4.0
- **Stato:** completata
- **Branch/commit:** `main`; commit O4 e tag `v0.4.0`.
- **Obiettivo:** portare il QBE nel Query Designer, sincronizzarlo con le schede guidate,
  documentare la sintassi e chiudere la release 0.4.0.
- **File toccati:** `dbx/core/qbe.py` (nuovo), `dbx/designers/qbe_panel.py` (nuovo),
  `dbx/designers/query_builder.py`, `dbx/ui/design.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_qbe_core.py` (nuovo), `tests/test_ui_qbe.py` (nuovo), `tests/test_ui_shell.py`,
  `dbx/__init__.py`, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `docs/qa-0.4.md` (nuovo),
  `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - Grammatica QBE pura in `dbx/core/qbe.py`: valore nudo, operatori, `a..b`, `blank`/`not blank`,
    jolly `*`/`?`, `_nome`; nessuna dipendenza dalla UI.
  - `QbePanel` con una query image per tabella: riga Includi, tre righe Criteri, riga Ordinamento.
    Il pannello legge e scrive lo stesso `QuerySpec`; nessun modello parallelo.
  - Toggle **QBE | Guidato** con due pulsanti checkable e le schede esistenti, invece di uno
    `QStackedWidget` separato: SQL e Risultato restano raggiungibili da entrambe le viste.
  - Sincronizzazione bidirezionale: le modifiche guidate ricostruiscono la vista QBE; le modifiche
    QBE riallineano albero, campi, filtri e ordinamento.
  - Example elements `_nome`: stesso nome in due celle produce un filtro `ref`; la vista li
    rimostra come `_rifN` dopo il salvataggio.
  - Celle non valide: bordo d'errore, messaggio nella vista, filtro precedente conservato.
  - La scheda Filtri mostra la colonna **Gruppo** e conserva gli OR del QBE.
  - Avviso non bloccante per OR su campi di tabelle in LEFT JOIN.
  - Pannello di aiuto con grammatica e collegamento a `docs/reference/inspirations/paradox-experts-qbe.md`.
  - Le query image usano un `QFrame` con titolo invece di `QGroupBox`: il tema Qt ridisegnava due
    volte il titolo del group box, con un artefatto visivo.
  - Versione `0.4.0` in `dbx/__init__.py`, `pyproject.toml`, README e test di release; CHANGELOG
    con sezione 0.4.0 e note di aggiornamento.
- **Test:** `326 passed`; smoke headless OK con voce `qbe mode`; `dbx --version` = 0.4.0;
  catture Aurora e Dark OK.
- **Screenshot:** `23-qbe-mode.png`.
- **Problemi aperti:** nessuno bloccante; restano i limiti dichiarati della 0.4 (QBE read-only,
  example elements con tabella già presente, avviso OR su LEFT JOIN).
- **Prossimo passo:** O5 — catalogo azioni script e Step Picker.

### 2026-11-22 — Ondata 0.5.0 — O5 Catalogo azioni e Step Picker
- **Stato:** completata
- **Branch/commit:** `main`; commit O5.
- **Obiettivo:** categorizzare il catalogo `ACTIONS`, aggiungere descrizioni e introdurre il
  selettore visuale dei passi senza cambiare il comportamento del motore.
- **File toccati:** `dbx/runtime/script_engine.py`, `dbx/designers/step_picker.py` (nuovo),
  `dbx/designers/script_builder.py`, `tests/test_step_catalog.py` (nuovo),
  `tests/test_ui_script_editor.py`, `tools/capture_ui.py`, `README.md`, `CHANGELOG.md`,
  `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - `ACTIONS` resta il dizionario unico; ogni voce ha `label`, `category`, `description` e `params`.
  - Categorie nell’ordine del piano: Controllo, Navigazione, Dati, Record, Ricerche, Interfaccia,
    Stampa/File, Script, Variabili, Avanzate; le categorie senza azioni non compaiono.
  - `StepPickerDialog` con albero per categoria, filtro su nome/categoria/descrizione, riepilogo
    dell’azione e pulsante **Aggiungi**; `Aggiungi azione` lo usa al posto dell’elenco piatto.
  - L’Inspector mostra `Categoria` e `Descrizione` del passo; `ActionDialog` mostra la descrizione.
  - Nessuna azione nuova e nessuna modifica a `to_text`/`from_text` o all’interprete.
  - Nuovo rendering `24-script-step-picker.png`.
- **Test:** `331 passed`; smoke headless OK; catture Aurora e Dark OK.
- **Screenshot:** `24-script-step-picker.png`.
- **Problemi aperti:** nessuno; i ~16 passi core e il runtime sono il scope di O6.
- **Prossimo passo:** O6 — passi core e runtime, poi Checkpoint B.

### 2026-11-22 — Ondata 0.5.0 — O6 Passi core e runtime
- **Stato:** completata
- **Branch/commit:** `main`; commit O6.
- **Obiettivo:** implementare i passi core dello script (controllo, tabelle, record, campi,
  query/report, dialoghi) con cursore dati, forma testuale bidirezionale, validazione e
  adattatore del Form Runtime.
- **File toccati:** `dbx/runtime/script_engine.py`, `dbx/runtime/form_runtime.py`,
  `dbx/designers/script_builder.py`, `dbx/designers/project_builder.py`, `dbx/smoke.py`,
  `tests/test_script_actions.py` (nuovo), `README.md`, `CHANGELOG.md`, `docs/ui-parity.md`,
  `tools/capture_ui.py`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - Nuove azioni: `comment`, `loop`, `exit_loop_if`, `exit_script`, `halt`, `select_table`,
    `go_record`, `set_field`, `new_record`, `duplicate_record`, `delete_record`, `commit_record`,
    `revert_record`, `open_query`, `open_report`, `custom_dialog`, `beep`.
  - Cursore `Rowset` nello `ScriptEngine`: tabella corrente, record corrente, filtro, ordinamento,
    id interno; `select_table` apre il cursore e `go_record` lo naviga (numero 1-based).
  - Scritture immediate per passo con log; `set_field`, `new_record`, `duplicate_record` e
    `delete_record` passano da `Rowset`, quindi validazione, regole e indici restano nel motore.
  - `loop` protetto da `max_steps`; `exit_loop_if` interrompe solo il ciclo corrente;
    `exit_script` e `halt` fermano lo script.
  - Forma testuale completa per le nuove azioni; `ELSE IF` è zucchero sintattico e diventa un
    `if` annidato nell’`else` senza aggiungere un’azione al motore.
  - Validazione progetto estesa a tabelle, campi (con contesto della tabella corrente), form,
    report, query, script e modalità `GO RECORD`.
  - Adattatore `FormScriptUI`: messaggi, conferme, dialoghi, apertura form/query/report, beep e
    ricarica del record dopo l’esecuzione da un evento form.
  - `NEW RECORD` inserisce subito i default: con campi obbligatori senza default l’azione fallisce
    con un errore chiaro; limite documentato.
  - Nessuna transazione implicita: `REVERT RECORD` ricarica dal database ma non annulla una
    scrittura già eseguita.
- **Test:** `345 passed`; smoke headless OK con `script core actions`; catture Aurora e Dark OK.
- **Screenshot:** `11-script-editor.png` e `24-script-step-picker.png` rigenerati; nessun nuovo file.
- **Problemi aperti:** nessuno bloccante; restano i limiti dichiarati su record obbligatori e
  assenza di transazioni.
- **Prossimo passo:** Checkpoint B, poi O7 — QA e release 0.5.0.

## Checkpoint B — fine O6 (2026-11-22)

- **Stato ondate:** 0.4.0 O0–O4 completate e rilasciate come `0.4.0` (tag `v0.4.0`);
  0.5.0 O5–O6 completate. Catalogo azioni categorizzato, Step Picker, 17 passi core, cursore dati,
  forma testuale, validazione e adattatore Form Runtime sono pronti.
- **Test eseguiti:** `345 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK con
  `script core actions`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`24`; `24-script-step-picker.png` è il nuovo rendering della 0.5.
- **Decisioni:** scritture immediate per passo, nessuna transazione implicita; `NEW RECORD` usa i
  default e fallisce sui campi obbligatori senza default; `ELSE IF` è zucchero sintattico.
- **Decisioni rimandate all’utente:** eventuale release 0.5.0 con questi limiti, import CSV come
  estensione separabile, script trigger e transazioni esplicite in una release futura.
- **RIPRESA:** Checkpoint B attivo. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l’**Ondata 7 — QA e release 0.5.0**: QA finale, test completi,
  smoke, screenshot Aurora/Dark, documentazione e `docs/qa-0.5.md`, versione `0.5.0` in
  `dbx/__init__.py`/`pyproject.toml`/README/test, CHANGELOG con data, tag `v0.5.0`, Checkpoint C.
  Non ripartire da O0–O6.

### 2026-11-22 — Ondata 0.5.0 — O7 QA e release 0.5.0
- **Stato:** in corso
- **Branch/commit:** `main`, da `3cc7e4c`.
- **Obiettivo:** collaudo finale della 0.5.0, documentazione QA, versione `0.5.0`, tag e Checkpoint C.
- **File previsti:** `docs/qa-0.5.md` (nuovo), `dbx/__init__.py`, `pyproject.toml`,
  `tests/test_ui_shell.py`, `README.md`, `CHANGELOG.md`, `docs/ui-parity.md`,
  `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.

### 2026-11-22 — Ondata 0.5.0 — O7 chiusura e release 0.5.0
- **Stato:** completata
- **Branch/commit:** `main`; commit O7 e tag `v0.5.0`.
- **Obiettivo:** collaudo finale, documentazione QA e release 0.5.0.
- **File toccati:** `docs/qa-0.5.md` (nuovo), `dbx/__init__.py`, `pyproject.toml`,
  `tests/test_ui_shell.py`, `README.md`, `CHANGELOG.md`, `docs/ui-parity.md`,
  `docs/reference/dbx-ui/README.md`, `PLAN.md`, `DIARIO.md`.
- **Scelte:**
  - Versione `0.5.0` in `dbx/__init__.py`, `pyproject.toml`, README e test di release.
  - CHANGELOG con sezione `[0.5.0] — 2026-11-22`, riepilogo della release e note di aggiornamento
    su script esistenti e scritture immediate.
  - `docs/qa-0.5.md` con automazione, collaudo manuale, screenshot e limiti accettati.
  - `docs/ui-parity.md` aggiornato a 0.5 e ai passi core; indice render aggiornato.
  - README riallineato: introduzione 0.5, limiti noti 0.5 e riferimento a `docs/qa-0.5.md`.
  - Nessuna migrazione: gli script JSON e testuali 0.4 restano validi.
- **Test:** `345 passed`; smoke headless OK con `program editor` e `script core actions`;
  `dbx --version` = 0.5.0; catture Aurora e Dark OK.
- **Screenshot:** `11-script-editor.png` e `24-script-step-picker.png` rigenerati in Aurora e Dark.
- **Problemi aperti:** nessuno bloccante; restano i limiti dichiarati (nessuna transazione implicita,
  `NEW RECORD` con default, nessun debugger o script trigger).
- **Prossimo passo:** release chiusa; eventuali estensioni future (import CSV, transazioni esplicite,
  trigger) da pianificare in una nuova ondata.

## Checkpoint C — fine O7 e release 0.5.0 (2026-11-22)

- **Stato ondate:** 0.4.0 O0–O4 rilasciata come `0.4.0` (tag `v0.4.0`); 0.5.0 O5–O7 completata e
  rilasciata come `0.5.0` (tag `v0.5.0`). Catalogo azioni, Step Picker, 17 passi core, cursore dati,
  forma testuale, validazione e runtime form sono pronti.
- **Test eseguiti:** `345 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python -m dbx --version` = `0.5.0`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`24`; `11-script-editor.png` e `24-script-step-picker.png` aggiornati.
- **Decisioni:** release 0.5.0 con scritture immediate per passo, nessuna transazione implicita,
  `NEW RECORD` sui default e `ELSE IF` come zucchero sintattico.
- **Decisioni rimandate all’utente:** import CSV, transazioni esplicite, script trigger,
  debugger/passo-passo e motore di calcolo completo restano fuori dalla 0.5.
- **RIPRESA:** nessuna ondata aperta. Per ripartire, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e concordare con l’utente la prossima release; non ripartire da O0–O7.

### 2026-11-22 — Ondata 0.6.0 — O1 Find mode, sostituzione e ricerche salvate
- **Stato:** completata
- **Branch/commit:** `main`; commit `554d506` (O1–O2).
- **Obiettivo:** portare nella Browse la ricerca guidata in stile Find mode, la sostituzione e le
  ricerche salvate.
- **File toccati:** `dbx/core/search.py` (nuovo), `dbx/ui/find_dialog.py` (nuovo),
  `dbx/ui/data_view.py`, `tests/test_search.py` (nuovo), `tests/test_ui_search.py` (nuovo),
  `dbx/smoke.py`.
- **Scelte:**
  - `SearchRequest` con criteri combinati in AND (`all`) o OR (`any`); `omit` per criterio esclude
    le righe corrispondenti.
  - Operatori: contiene, uguale, diverso, inizia/finisce, maggiore/maggiore uguale, minore/minore
    uguale, vuoto/non vuoto; i jolly `%` e `_` sono trattati come testo.
  - Ricerche salvate in `project.settings["saved_finds"]` per tabella, con caricamento ed
    eliminazione dal dialogo.
  - Sostituzione con ambito su tutti i campi testuali o su un campo, distinzione maiuscole e parole
    intere; agisce sui record visibili dopo filtro e ricerca.
  - Scorciatoie `Ctrl+F` e `Ctrl+H`; la status bar riporta criteri e record trovati.
- **Test:** `tests/test_search.py` e `tests/test_ui_search.py` verdi; smoke con `find mode`.
- **Screenshot:** `25-find-dialog.png`.
- **Problemi aperti:** nessuna ricerca globale tra oggetti; la sostituzione non tocca i record
  esclusi dal filtro.
- **Prossimo passo:** O2 — importazione CSV.

### 2026-11-22 — Ondata 0.6.0 — O2 Import CSV guidato
- **Stato:** completata
- **Branch/commit:** `main`; commit `554d506` (O1–O2).
- **Obiettivo:** importare CSV/TXT in una tabella esistente con anteprima e mappatura.
- **File toccati:** `dbx/io/csv_io.py`, `dbx/ui/import_wizard.py` (nuovo),
  `dbx/ui/data_view.py`, `dbx/ui/icons.py`, `tests/test_csv_import.py` (nuovo), `dbx/smoke.py`.
- **Scelte:**
  - Rilevamento automatico di delimitatore (`;`, `,`, tab, `|`) e codifica (`utf-8-sig`, fallback
    `latin-1`), con selezione manuale nel wizard.
  - Anteprima delle prime 50 righe e mappatura colonna → campo suggerita per nome o didascalia.
  - Conversione nei tipi dBX tramite `Rowset`, quindi regole e indici restano applicati; l’errore
    riporta la riga del file e l’intera importazione viene annullata.
  - Svuotamento opzionale della tabella con conferma e backup; nessuna creazione automatica di
    tabelle dal file.
  - Le colonne possono essere ignorate; due colonne non possono scrivere lo stesso campo.
- **Test:** `tests/test_csv_import.py` verde; smoke con `import csv: 2 record`.
- **Screenshot:** `26-import-csv.png`.
- **Problemi aperti:** l’import Excel/XML e la creazione tabella da CSV restano fuori scope.
- **Prossimo passo:** O3 — manutenzione e release 0.6.0.

### 2026-11-22 — Ondata 0.6.0 — O3 Manutenzione e release 0.6.0
- **Stato:** completata
- **Branch/commit:** `main`; commit O3 e tag `v0.6.0`.
- **Obiettivo:** rinomina, duplicazione, compattazione/verifica, QA e release 0.6.0.
- **File toccati:** `dbx/core/refactor.py` (nuovo), `dbx/core/project.py`,
  `dbx/designers/table_builder.py`, `dbx/ui/navigator.py`, `dbx/ui/main_window.py`,
  `tests/test_refactor.py` (nuovo), `tests/test_ui_maintenance.py` (nuovo), `dbx/smoke.py`,
  `tools/capture_ui.py`, documentazione.
- **Scelte:**
  - Rinomina tabella con `ALTER TABLE`, aggiornamento di FK, lookup, query (`base`, join, campi,
    filtri `ref`, ordinamenti), form, report, script, diagrammi e ricerche salvate.
  - Duplicazione dal Navigator: copia JSON per gli oggetti, struttura e dati per le tabelle, nomi
    univoci con suffisso.
  - Compattazione con backup e verifica `PRAGMA integrity_check` nel menu Progetto.
  - Corretto `Project.apply_table` sul caso “nessuna modifica”: ora passa `previous_name` e non
    segnala più un falso oggetto duplicato.
  - Versione `0.6.0`, CHANGELOG datato, `docs/qa-0.6.md`, README, parity e indice render aggiornati.
- **Test:** `374 passed`; smoke OK con `find mode`, `import csv` e `duplicazione oggetti +
  integrità`; `dbx --version` = `0.6.0`; catture Aurora e Dark OK.
- **Screenshot:** `25-find-dialog.png` e `26-import-csv.png`; serie `01`–`26` rigenerata.
- **Problemi aperti:** le finestre già aperte non seguono la rinomina; compattazione e verifica sono
  sincrone; restano le sette funzionalità delle ondate O4–O11.
- **Prossimo passo:** Checkpoint D; dopo `continua`, O4 — campi calcolati e auto-enter.

## Checkpoint D — fine O3 e release 0.6.0 (2026-11-22)

- **Stato ondate:** 0.6.0 O1–O3 completata e rilasciata come `0.6.0` (tag `v0.6.0`). Find mode,
  sostituzione, ricerche salvate, import CSV, rinomina/duplicazione e manutenzione sono pronti.
- **Test eseguiti:** `374 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python -m dbx --version` = `0.6.0`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`26`; nuovi `25-find-dialog.png` e `26-import-csv.png`.
- **Decisioni:** ricerca per tabella (non globale), import in tabella esistente, rinomina con
  aggiornamento dei riferimenti noti, duplicazione con copia dati per le tabelle.
- **Decisioni rimandate all’utente:** import Excel/XML, creazione tabella da CSV, ricerca globale,
  grafici interattivi e automazione avanzata.
- **RIPRESA:** nessuna ondata aperta. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l’**Ondata 4 — Campi calcolati e auto-enter**; non ripartire da
  O1–O3.

### 2026-11-22 — Ondata 0.7.0 — O4 Campi calcolati e auto-enter
- **Stato:** completata
- **Branch/commit:** `main`; commit O4.
- **Obiettivo:** introdurre campi calcolati virtuali e compilazioni automatiche (serie, date,
  espressioni) senza rompere i progetti 0.6.
- **File toccati:** `dbx/core/metadata.py`, `dbx/core/ddl.py`, `dbx/runtime/rowset.py`,
  `dbx/core/query_model.py`, `dbx/core/search.py`, `dbx/core/refactor.py`,
  `dbx/designers/table_builder.py`, `dbx/designers/query_builder.py`,
  `dbx/designers/query_expert.py`, `dbx/ui/data_view.py`, `dbx/ui/find_dialog.py`,
  `dbx/ui/import_wizard.py`, `dbx/runtime/form_runtime.py`, `dbx/runtime/script_engine.py`,
  `dbx/io/csv_io.py`, `tests/test_calculated_fields.py` (nuovo),
  `tests/test_ui_calculated.py` (nuovo), `dbx/smoke.py`, `tools/capture_ui.py`.
- **Scelte:**
  - `Field` esteso in modo additivo con `calculated`, `auto_enter`, `auto_serial` e `auto_date`
    (`insert`/`update`). I progetti 0.6 restano validi perché tutti i nuovi campi hanno default.
  - I campi calcolati restano in `fields` per designer, form, report e import, ma non hanno colonna
    fisica: DDL, migrazioni e Rowset usano `Table.stored_fields`.
  - Il calcolo avviene nel `Rowset` a ogni lettura, dopo la conversione dei tipi, in ordine di campo:
    un calcolato può quindi riferirsi a un altro calcolato. Le regole di validazione possono usare
    il risultato.
  - `auto_serial` richiede Intero e assegna `MAX + 1`; `auto_date` richiede Data/Data-ora; le
    espressioni auto-enter vengono valutate solo alla creazione, se il campo è vuoto, dopo serie e
    date.
  - I campi calcolati sono esclusi da indici, relazioni, query, ricerca, sostituzione, import e
    SET FIELD; la Browse li mostra in sola lettura con il suggerimento dell'espressione.
  - La Browse e il Table Builder espongono le nuove proprietà nella scheda Proprietà; la rinomina
    tabella riscrive i riferimenti qualificati anche in calcoli e auto-enter.
  - Le modifiche parziali del `Rowset` ora conservano i campi non indicati, evitando di azzerare
    serie, date e auto-enter durante un aggiornamento mirato.
- **Test:** `389 passed`; smoke OK con `import csv: 2 record + calcolati`; test dedicati su
  migrazioni additive, catene di calcolo, serie, date, auto-enter, query/search rifiutate,
  Table Builder, Browse e RecordDialog.
- **Screenshot:** `27-table-calculated.png` (proprietà del campo calcolato) e
  `28-browse-calculated.png` (totale e serie calcolati nella Browse).
- **Problemi aperti:** le query SQL non leggono campi calcolati (saranno disponibili negli
  aggregati di O5 come campi di output); i calcolati non sono ordinabili né filtrabili via SQL.
- **Prossimo passo:** O5 — aggregati `GROUP BY` nella query.

### 2026-11-22 — Ondata 0.7.0 — O5 Aggregati nella query
- **Stato:** completata
- **Branch/commit:** `main`; commit O5.
- **Obiettivo:** aggiungere `GROUP BY` e colonne aggregate SUM/COUNT/AVG/MIN/MAX alle query statiche.
- **File toccati:** `dbx/core/query_model.py`, `dbx/core/query_engine.py`,
  `dbx/designers/query_builder.py`, `tests/test_query_aggregates.py` (nuovo),
  `tests/test_ui_query_aggregates.py` (nuovo), `dbx/smoke.py`, `tools/capture_ui.py`.
- **Scelte:**
  - `QuerySpec` esteso in modo additivo con `group_by` (riferimenti `tabella.campo`) e
    `aggregates` (`QueryAggregate`: funzione, tabella, campo, alias).
  - Il motore genera `COUNT(*)`, `COUNT(campo)`, `SUM`, `AVG`, `MIN`, `MAX`, con alias stabili e
    deduplicati rispetto ai campi; `COUNT(*)` è disponibile senza campo.
  - Nei raggruppamenti i campi selezionati devono comparire in `GROUP BY`; gli aggregati possono
    essere ordinati tramite alias, anche in combinazione con join.
  - Nuova scheda **Raggruppa** nel Query Designer: righe di raggruppamento, aggregati con funzione,
    campo e alias, suggerimento sui campi da raggruppare. Lo SQL e l'anteprima si aggiornano subito.
  - `Query Results`, form e report leggono le colonne aggregate come normali colonne tipizzate;
    COUNT è intero, SUM/AVG decimali, MIN/MAX ereditano il tipo del campo.
  - I campi calcolati virtuali restano esclusi da SELECT, GROUP BY e aggregati SQL.
- **Test:** `400 passed`; smoke OK con `aggregati query`; test dedicati su aggregati globali,
  GROUP BY, join, ordinamento per alias, validazione, JSON e Query Designer/Query Results.
- **Screenshot:** `29-query-aggregates.png`.
- **Problemi aperti:** niente HAVING, niente aggregati sulle espressioni e niente sottoquery; i
  filtri restano applicati prima del raggruppamento.
- **Prossimo passo:** O6 — crosstab read-only e release 0.7.0.

### 2026-11-22 — Ondata 0.7.0 — O6 Crosstab e release 0.7.0
- **Stato:** completata
- **Branch/commit:** `main`; commit O6 e tag `v0.7.0`.
- **Obiettivo:** tabella incrociata read-only dai risultati di query, QA e release 0.7.0.
- **File toccati:** `dbx/core/crosstab.py` (nuovo), `dbx/ui/crosstab_dialog.py` (nuovo),
  `dbx/ui/query_results.py`, `dbx/designers/query_builder.py`, `dbx/smoke.py`,
  `tests/test_crosstab.py` (nuovo), `tests/test_ui_crosstab.py` (nuovo), `tools/capture_ui.py`,
  versione, CHANGELOG, README, PLAN, parity, `docs/qa-0.7.md` (nuovo).
- **Scelte:**
  - Il Crosstab non è un nuovo oggetto di progetto: legge un `QueryResult` già aggregato, quindi
    non duplica SQL né richiede migrazioni.
  - Righe e colonne sono i valori distinti di due colonne del risultato, il valore è una colonna
    numerica; i duplicati vengono sommati, i totali sono calcolati in Python con `float` e
    formattati secondo il tipo dBX della colonna valore.
  - Finestra con combo Righe/Colonne/Valore, matrice read-only, totali di riga, colonna e generale,
    esportazione CSV con delimitatore `;`.
  - Si apre da Query Results e dal Query Designer; il designer usa il risultato corrente, anche se
    la query non è ancora salvata.
  - Release `0.7.0`: versione, CHANGELOG, README, parity, indice render, QA 0.7 e tag.
- **Test:** `407 passed`; smoke OK con `calcolati`, `aggregati query` e `crosstab read-only`;
  `dbx --version` = `0.7.0`; catture Aurora e Dark OK.
- **Screenshot:** `30-crosstab.png`; serie `01`–`30` rigenerata, con `27`, `28`, `29` della 0.7.
- **Problemi aperti:** niente HAVING, sottoquery o grafici; il Crosstab non è persistito come
  oggetto e non applica funzioni diverse dalla somma.
- **Prossimo passo:** Checkpoint E; dopo `continua`, O7 — etichette e mail merge.

## Checkpoint E — fine O6 e release 0.7.0 (2026-11-22)

- **Stato ondate:** 0.7.0 O4–O6 completata e rilasciata come `0.7.0` (tag `v0.7.0`). Campi
  calcolati, auto-enter, aggregati `GROUP BY` e Crosstab read-only sono pronti.
- **Test eseguiti:** `407 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python -m dbx --version` = `0.7.0`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`30`; nuovi `27-table-calculated.png`, `28-browse-calculated.png`,
  `29-query-aggregates.png`, `30-crosstab.png`.
- **Decisioni:** calcolati virtuali nel Rowset; auto-enter solo alla creazione; aggregati con
  `GROUP BY` e alias; Crosstab come vista non persistita.
- **Decisioni rimandate all’utente:** HAVING, aggregati su espressioni, Crosstab persistito,
  grafici interattivi, etichette e mail merge (0.8).
- **RIPRESA:** nessuna ondata aperta. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l’**Ondata 7 — Etichette e mail merge**; non ripartire da
  O1–O6.

### 2026-11-22 — Ondata 0.8.0 — O7 Etichette e mail merge
- **Stato:** completata
- **Branch/commit:** `main`; commit O7.
- **Obiettivo:** introdurre etichette e mail merge leggeri riusando record, query e anteprima esistenti,
  senza un nuovo linguaggio e senza toccare il motore dati.
- **File toccati:** `dbx/core/label_model.py` (nuovo), `dbx/core/page_sizes.py` (nuovo),
  `dbx/runtime/label_engine.py` (nuovo), `dbx/designers/label_builder.py` (nuovo),
  `dbx/ui/label_preview.py` (nuovo), `dbx/ui/report_preview.py`, `dbx/core/project.py`,
  `dbx/core/refactor.py`, `dbx/designers/project_builder.py`, `dbx/ui/navigator.py`,
  `dbx/ui/main_window.py`, `dbx/ui/icons.py`, `dbx/runtime/report_engine.py`, `dbx/smoke.py`,
  `tools/capture_ui.py`, `tests/test_label_model.py` (nuovo), `tests/test_label_engine.py` (nuovo),
  `tests/test_ui_label_designer.py` (nuovo), `tests/test_ui_navigator.py`,
  `tests/test_ui_project_editor.py`, PLAN, CHANGELOG, README render, parity, DIARIO.
- **Scelte:**
  - Nuova categoria di progetto `labels` (suffisso `.label.json`) accanto a `diagrams`: Schema ed
    Etichette convivono. I progetti 0.7 si aprono senza migrazione perché la categoria viene creata
    vuota al primo salvataggio.
  - `LabelSpec` descrive formato pagina, griglia, margini, distanze, corpo, allineamento, bordo,
    sorgente (`table`/`query`), filtro, ordine, salto iniziale e modello di testo. I preset A4/Avery
    sono dati puri, non oggetti salvati.
  - Il modello usa `[campo]` per i valori e `{{[campo] * 2}}` per le espressioni, così non serve un
    nuovo linguaggio: la valutazione passa dal motore `Expression` esistente.
  - `label_engine` legge i record con `Rowset` (tabella, anche campi calcolati) o `run_query` (query,
    anche aggregati), applica filtro/ordine e dispone una etichetta per record su una griglia
    regolare; i fogli sono `Page`/`Op` del motore report.
  - L'anteprima riusa `ReportPreviewDialog` con un hook `build_pages`: stampa, zoom, pagina singola,
    PDF e navigazione restano identici. `LabelPreviewDialog` sostituisce solo il costruttore delle
    pagine e le etichette dei messaggi.
  - Il Label Designer è volutamente leggero: form di geometria, elenco campi e modello testuale, con
    salvataggio, nuova/apri, anteprima e stampa. Non è un editor a controlli liberi.
  - La rinomina tabella riscrive `table`, filtro e riferimenti qualificati nel modello; la
    validazione di progetto controlla tabella/query e geometria.
  - Test esistenti aggiornati: il Navigator ora ha 9 filtri (aggiunta Etichette) e il Project Editor
    8 categorie. Il cambiamento è voluto e coperto dai nuovi test.
- **Test:** `431 passed`; smoke OK con `etichette e mail merge`; `python -m dbx --version` resta
  `0.7.0` (la release 0.8 arriva in O9). Test dedicati su preset, validazione, filtri, query,
  griglia, paginazione, salto etichette, formattazione, calcolati, rinomina, designer, anteprima e
  integrazione MDI.
- **Screenshot:** `31-label-designer.png` e `32-label-preview.png`; serie `01`–`32` rigenerata.
- **Problemi aperti:** niente barcode/QR, niente etichette a più colonne di testo o immagini, niente
  selezione manuale dei record oltre a filtro/ordine, nessun designer a controlli liberi.
- **Prossimo passo:** O8 — grafici nel report (barre, linee, torta da gruppi e totali).

### 2026-11-22 — Ondata 0.8.0 — O8 Grafici nel report
- **Stato:** completata
- **Branch/commit:** `main`; commit O8.
- **Obiettivo:** aggiungere barre, linee e torta ai report, alimentati dai gruppi e dai totali,
  visibili in anteprima, stampa e PDF senza grafici interattivi né dipendenze nuove.
- **File toccati:** `dbx/runtime/report_engine.py`, `dbx/io/pdf_export.py`, `dbx/ui/design.py`,
  `dbx/designers/report_builder.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_report_charts.py` (nuovo), `tests/test_ui_report_chart.py` (nuovo),
  PLAN, CHANGELOG, README, parity, indice render, DIARIO.
- **Scelte:**
  - Nuovo tipo di controllo `chart` accanto a testo, campi, totali, linee, rettangoli e immagini:
    `chart_type` (`bar`/`line`/`pie`), `category`, `expr`, `func` e `text` come titolo.
  - Il motore aggrega i record per la categoria indicata (per default il primo gruppo del report)
    con SUM/COUNT/AVG/MIN/MAX; COUNT può non avere espressione e conta i record.
  - Il grafico in **group footer** considera solo i record del gruppo corrente; nel Summary usa
    tutto il report. L'ordine delle categorie segue l'ordinamento del report.
  - `Op` trasporta `chart_type` e `series` già calcolate: il modello è testabile senza Qt e il
    disegno resta confinato in `pdf_export`.
  - Barre, linee e torta sono disegnate con `QPainter` e la palette `design.CHART_COLORS`; nessuna
    immagine temporanea, nessun file esterno, nessun grafico interattivo.
  - Report Designer: pulsante **Grafico**, dialogo con tipo/titolo/categoria/valore/funzione/banda,
    campi Chart e Category nell'Inspector e anteprima stilizzata sul foglio.
  - La validazione rifiuta tipo sconosciuto, espressione mancante (tranne COUNT) e funzione non
    valida; i report 0.7 restano validi perché i nuovi campi hanno default.
- **Test:** `443 passed`; smoke OK con `grafici report` e PDF del grafico; test dedicati su
  aggregazione per gruppo, torta, linee, COUNT, group footer, validazione, serializzazione, query,
  dialogo, inserimento nel designer, Inspector e rendering della pagina.
- **Screenshot:** `33-report-chart.png` e `34-report-chart-designer.png`; serie `01`–`34` rigenerata.
- **Problemi aperti:** niente grafici interattivi, tooltip, assi con scale configurabili, legenda
  completa oltre 8 voci o esportazione in immagine separata; il grafico non filtra da solo i record.
- **Prossimo passo:** O9 — vista Lista del form, portale e release 0.8.0 (Checkpoint F).

### 2026-11-22 — Ondata 0.8.0 — O9 Vista Lista, portale e release 0.8.0
- **Stato:** completata
- **Branch/commit:** `main`; commit O9 e tag `v0.8.0`.
- **Obiettivo:** aggiungere la vista Lista ai form, ordinamento e filtro ai portali uno-a-molti, QA e
  release 0.8.0.
- **File toccati:** `dbx/core/form_model.py`, `dbx/runtime/form_runtime.py`,
  `dbx/designers/form_builder.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_form_list_portal.py` (nuovo), `tests/test_ui_form_list_portal.py` (nuovo),
  `tests/test_ui_shell.py`, pyproject, `dbx/__init__.py`, README, CHANGELOG, PLAN, parity,
  indice render, `docs/qa-0.8.md` (nuovo), DIARIO.
- **Scelte:**
  - `FormSpec` esteso in modo additivo con `view_mode` (`form`/`list`) e `list_fields` (elenco
    separato da virgole). Default innocui: scheda e tutte le colonne.
  - Il runtime impila scheda e lista; il pulsante **Lista/Scheda** alterna le viste. La lista è di
    consultazione (celle non editabili), la selezione di una riga carica il record nella scheda e
    sincronizza lo stato. Su query la lista eredita la sola lettura.
  - Nuovo/elimina/salva passano dalla scheda; dopo il salvataggio e l'eliminazione la lista viene
    ricostruita. `list_fields` ignora nomi inesistenti e ricade su tutti i campi.
  - Il controllo `grid` (sottomaschera/portale) accetta `order` e `filter` additivi: l'ordine è SQL
    sulla tabella figlia, il filtro è un'espressione dBX valutata per riga dopo il collegamento
    padre-figlio. Un ordine o filtro non valido resta confinato al portale e viene riportato nello
    stato/event log, senza bloccare il form.
  - `create_master_detail` ora posiziona il portale sotto il contenuto reale della scheda, evitando
    la sovrapposizione con i pulsanti generati.
  - Form Designer: proprietà View/List fields tra le proprietà del form e Portal order/filter tra
    quelle del controllo; le modifiche sono serializzate senza conversioni speciali.
  - Release `0.8.0`: versione, CHANGELOG, README, parity, indice render, QA 0.8 e tag.
- **Test:** `455 passed`; smoke OK con `etichette e mail merge`, `grafici report`,
  `form vista lista` e `portale ordinato e filtrato`; `dbx --version` = `0.8.0`; catture Aurora e
  Dark OK. Aggiornato il test di versione della shell.
- **Screenshot:** `35-form-list.png` e `36-form-portal.png`; serie `01`–`36` rigenerata, con `31`–`34`
  delle ondate O7–O8.
- **Problemi aperti:** la lista non consente modifica inline; i portali non hanno layout/azioni per
  riga; niente grafici interattivi.
- **Prossimo passo:** Checkpoint F; dopo `continua`, O10 — parametri script, variabili globali e
  transazioni esplicite.

## Checkpoint F — fine O9 e release 0.8.0 (2026-11-22)

- **Stato ondate:** 0.8.0 O7–O9 completata e rilasciata come `0.8.0` (tag `v0.8.0`). Etichette,
  mail merge, grafici, vista Lista e portali sono pronti.
- **Test eseguiti:** `455 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python -m dbx --version` = `0.8.0`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`36`; nuovi `31-label-designer.png`, `32-label-preview.png`,
  `33-report-chart.png`, `34-report-chart-designer.png`, `35-form-list.png`, `36-form-portal.png`.
- **Decisioni:** etichette con modello testuale e preset, non designer a controlli liberi; grafici
  non interattivi disegnati da `pdf_export`; lista di consultazione; portali con ordine/filtro ma
  senza layout per riga.
- **Decisioni rimandate all’utente:** barcode/QR, grafici interattivi, portali con azioni, parametri
  interattivi delle query e automazione 0.9.
- **RIPRESA:** nessuna ondata aperta. Dopo `continua`, leggere `PLAN.md` e `DIARIO.md`, controllare
  `git status`/`git log` e iniziare l’**Ondata 10 — Automazione (parametri script, variabili
  globali, transazioni esplicite)**; non ripartire da O1–O9.

### 2026-11-22 — Ondata 0.9.0 — O10 Automazione: parametri, globali e transazioni
- **Stato:** completata
- **Branch/commit:** `main`; commit O10.
- **Obiettivo:** rendere gli script riutilizzabili e transazionali: parametri dichiarati, variabili
  globali persistite e transazioni esplicite, senza introdurre un nuovo linguaggio.
- **File toccati:** `dbx/core/project.py`, `dbx/runtime/script_engine.py`,
  `dbx/designers/script_builder.py`, `dbx/designers/project_builder.py`,
  `dbx/ui/script_params.py` (nuovo), `dbx/ui/main_window.py`, `dbx/ui/project_runner.py`,
  `dbx/samples.py`, `dbx/smoke.py`, `tools/capture_ui.py`,
  `tests/test_script_automation.py` (nuovo), `tests/test_ui_script_params.py` (nuovo),
  `tests/test_samples.py`, PLAN, CHANGELOG, README, parity, indice render, DIARIO.
- **Scelte:**
  - I parametri sono un elenco additivo nell'oggetto script: `{"name", "label", "default"}`.
    `script_parameters` accetta anche la forma abbreviata a lista di nomi, così gli script 0.8
    restano validi; `parameter_values` applica i predefiniti e le sostituzioni.
  - `run_named(..., params=...)` e `run(..., params=...)` immettono i valori in `variables`; nel
    Program Editor valgono i predefiniti, nel Navigator/menu/Project Runner un dialogo chiede i
    valori. Il dialogo dei parametri è separato da quello dei valori e non contiene logica dati.
  - Filtri e ordinamenti SQL usano una sostituzione dedicata (`:variabile` e `[campo]`) che non
    valuta il testo come espressione: un filtro `anni >= :eta` non può diventare `True`.
  - Le variabili globali vivono in `project.settings["globals"]` tramite `Project.globals`,
    `set_global` e `unset_global`; sono salvate nel manifest con valori JSON-compatibili (le date
    diventano testo). Il motore le espone a espressioni e messaggi; le variabili locali hanno la
    precedenza, ma `SET GLOBAL` rimuove l'eventuale locale omonimo così il nuovo valore è visibile.
  - Nuove azioni `set_global`, `unset_global`, `begin_transaction`, `commit_transaction`,
    `rollback_transaction`; la forma testuale usa `SET GLOBAL`, `CLEAR GLOBAL`, `BEGIN/COMMIT/ROLLBACK
    TRANSACTION`.
  - Le transazioni usano la connessione SQLite del progetto (`BEGIN`/`COMMIT`/`ROLLBACK`) e quindi
    includono anche `Rowset` e l'azione SQL. Doppio `BEGIN`, commit/rollback senza transazione sono
    errori espliciti; una transazione rimasta aperta viene annullata automaticamente alla fine dello
    script, anche in caso di errore.
  - Il rollback rilegge il cursore corrente, così la scheda mostra i valori ripristinati.
  - Script demo `fatture_sopra_soglia` con parametro `soglia` (default 1000), filtro parametrizzato e
    variabile globale `ultima_soglia`; voce nel menu del progetto.
  - La validazione di progetto controlla nome e unicità dei parametri.
- **Test:** `481 passed`; smoke OK con `parametri e variabili globali` e `transazioni script`;
  `python -m dbx --version` resta `0.8.0` (la release 0.9 arriva in O11). Test dedicati su
  dichiarazione/valori, filtri parametrizzati, globali condivise e persistenti, date, shadowing,
  commit/rollback, rollback automatico, errori di stato, cursore, forma testuale, validazione,
  dialoghi, Program Editor, Navigator e Project Runner.
- **Screenshot:** `37-script-parameters.png`; serie `01`–`37` rigenerata.
- **Problemi aperti:** parametri solo testuali (la conversione numerica resta a `VAL`), nessuna
  esecuzione passo-passo o breakpoint, transazioni annidate non supportate, globali senza tipi o
  scoping per utente.
- **Prossimo passo:** O11 — QA, documentazione, screenshot, release 0.9.0 e Checkpoint G.

### 2026-11-22 — Ondata 0.9.0 — O11 QA e release 0.9.0
- **Stato:** completata
- **Branch/commit:** `main`; commit di release e tag `v0.9.0`.
- **Obiettivo:** chiudere il ciclo 0.6–0.9 con QA, documentazione, screenshot e release 0.9.0.
- **File toccati:** `pyproject.toml`, `dbx/__init__.py`, `tests/test_ui_shell.py`, README, CHANGELOG,
  PLAN, `docs/ui-parity.md`, `docs/reference/dbx-ui/README.md`, `docs/qa-0.9.md` (nuovo), DIARIO.
- **Scelte:**
  - Versione `0.9.0`; nessuna nuova funzionalità in O11, solo consolidamento e documentazione.
  - README riordinato: la 0.9 è la release corrente, la 0.8 e la 0.7 sono descritte al passato;
    rimossi i limiti ormai superati su Label Designer, grafici, campi calcolati e transazioni.
  - `docs/qa-0.9.md` documenta i 13 controlli di automazione, i test dedicati e i limiti accettati.
  - La compatibilità è esplicita: `params` assente equivale a nessun parametro e le globali nascono
    solo al primo `SET GLOBAL`; i progetti 0.8 si aprono senza migrazione.
- **Test:** `481 passed`; smoke OK con `parametri e variabili globali` e `transazioni script`;
  `dbx --version` = `0.9.0`; catture Aurora e Dark OK; serie `01`–`37` rigenerata.
- **Screenshot:** `37-script-parameters.png` (nuovo); `11-script-editor.png` aggiornato con il
  pulsante Parametri.
- **Problemi aperti:** restano i limiti dichiarati in `docs/qa-0.9.md` e nel README (query statiche,
  grafici non interattivi, portali senza azioni, parametri testuali, transazioni non annidate).
- **Prossimo passo:** nessuna ondata prevista nel piano 0.6–0.9; il ciclo è completo.

## Checkpoint G — fine O11 e release 0.9.0 (2026-11-22)

- **Stato ondate:** 0.9.0 O10–O11 completata e rilasciata come `0.9.0` (tag `v0.9.0`). Il piano
  0.6–0.9 è interamente completato: 0.6.0, 0.7.0, 0.8.0 e 0.9.0.
- **Test eseguiti:** `481 passed`; `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK;
  `python -m dbx --version` = `0.9.0`; `python tools/capture_ui.py` OK; `--theme dark` OK.
- **Screenshot:** serie `01`–`37`; nuovo `37-script-parameters.png`; aggiornato
  `11-script-editor.png`.
- **Decisioni:** parametri testuali con dialogo dedicato; globali nel manifest; transazioni esplicite
  sulla connessione SQLite con rollback automatico a fine script.
- **Decisioni rimandate all’utente:** parametri tipizzati o interattivi nelle query, transazioni
  annidate, breakpoint/esecuzione passo-passo, barcode/QR, grafici interattivi e portali con azioni.
- **RIPRESA:** nessuna ondata aperta e nessun checkpoint successivo. Il piano 0.6–0.9 è concluso;
  eventuali nuove richieste vanno pianificate come release successive.

### 2026-11-22 — Harness E2E completo e esecuzione programmata
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato al harness.
- **Obiettivo:** rendere ripetibile in un solo comando il collaudo completo di tutte le funzionalità,
  con esiti leggibili, log, JUnit, screenshot e codici di uscita affidabili per un'esecuzione non
  presidiata.
- **File toccati:** `tools/e2e_harness.py` (nuovo), `tools/e2e_scenarios.py` (nuovo),
  `tools/run_e2e.sh` (nuovo), `docs/e2e.md` (nuovo), `tests/test_e2e_harness.py` (nuovo),
  `.github/workflows/ci.yml`, README, DIARIO.
- **Scelte:**
  - Un unico entry-point `tools/e2e_harness.py` esegue in ordine **pytest completo**, **smoke
    headless** e **10 scenari E2E**; `tools/run_e2e.sh` è il wrapper per l'avvio rapido.
  - Ogni scenario usa un progetto temporaneo isolato; i progetti dell'utente non vengono toccati.
    In caso di fallimento la cartella temporanea viene conservata per il debug.
  - Gli scenari coprono tabelle e CRUD, Find mode e CSV, query/aggregati/QBE/Crosstab, form e
    portali, report/grafici/etichette, script con parametri/globali/transazioni, manutenzione,
    shell MDI e designer, menu runtime e build ZIP.
  - I dialoghi modali sono neutralizzati; i warning del plugin Qt offscreen durante gli screenshot
    sono silenziati. Ogni scenario ha un timeout (dove `SIGALRM` è disponibile).
  - Il report è sia macchina-leggibile (`report.json`) sia leggibile (`report.md`), con commit Git,
    versioni, tempi, controlli, traceback, percorsi di log e screenshot.
  - Output predefinito `build/e2e/<timestamp>/` (ignorato da Git), con `latest.txt`; `--output`
    consente una cartella dedicata. La console stampa l'esito e il percorso del report.
  - `--only`, `--skip-pytest`, `--skip-smoke`, `--no-screenshots`, `--keep`, `--fail-fast`,
    `--timeout`, `--pytest-args`, `--list` e `--quiet/--verbose` coprono esecuzioni mirate e
    diagnostica.
  - La CI esegue il harness su Linux/Python 3.12 con pytest e smoke già eseguiti a parte, e pubblica
    la cartella `build/e2e-ci` come artifact.
  - `tests/test_e2e_harness.py` verifica l'elenco, un'esecuzione minima isolata e l'errore per
    scenari sconosciuti, così il harness stesso resta coperto dalla suite.
- **Test:** `484 passed` (481 + 3 del harness); harness completo `PASS` con 10/10 scenari,
  187+ controlli, smoke e pytest verdi; esecuzione mirata `--only ui_designers` verde.
- **Screenshot:** 18 immagini in `build/e2e/<timestamp>/screenshots/` a ogni esecuzione, separate
  dalla galleria canonica `docs/reference/dbx-ui/renders/`.
- **Problemi aperti:** il timeout per scenario su Windows non usa `SIGALRM`; i tempi dipendono dalla
  macchina; PyInstaller resta un test opzionale non incluso nel harness.
- **Prossimo passo:** lanciare `./tools/run_e2e.sh` domani e conservare `build/e2e/<timestamp>/`.

### 2026-11-23 — Workflow E2E realistici
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato ai workflow E2E.
- **Obiettivo:** aggiungere al harness scenari che simulino percorsi di lavoro reali, non singole
  funzionalità: stato che passa dall'interfaccia al database, artefatti prodotti e verifica dopo un
  riavvio del progetto.
- **File toccati:** `tools/e2e_scenarios.py`, `tests/test_e2e_harness.py`, `docs/e2e.md`, `README.md`,
  DIARIO.
- **Scelte:**
  - Quattro workflow narrativi, ognuno su un progetto temporaneo isolato:
    `workflow_nuova_applicazione` (da progetto vuoto a build distribuita e riaperta),
    `workflow_sportello` (ricerca, riattivazione cliente, nuova fattura e incasso dalla griglia,
    riepilogo, etichette e report, verifica dopo riavvio),
    `workflow_import_bonifica` (import CSV con mappatura automatica, normalizzazione città,
    eliminazione di inattivi e duplicati, ricerca salvata, export pulito, mailing e report),
    `workflow_chiusura_mensile` (script parametrizzato lanciato dal menu runtime, tabella chiusure,
    solleciti su query con join, PDF, backup, compattazione e riapertura).
  - I workflow usano le superfici reali: `DataView` e dialogo «Nuovo record», form runtime,
    `ImportCsvDialog`, `ProjectRunner`, anteprima report, build ZIP. Solo i dialoghi modali sono
    neutralizzati, come per gli altri scenari.
  - Aggiunte due utility condivise (`_typed_record`, `_reopen`) e la verifica dei totali dopo il
    riavvio; nessuna modifica al motore o al comportamento dell'applicazione.
  - `tests/test_e2e_harness.py` elenca i nuovi scenari e ne esegue quattro in isolamento; la suite
    pytest resta quindi a copertura del harness stesso.
- **Test:** `485 passed`; harness completo `PASS` con 14/14 scenari, 295/295 controlli e 31
  screenshot; smoke headless verde. Esecuzioni mirate dei quattro workflow verdi.
- **Screenshot:** nuovi `e2e-wf-new-app-*`, `e2e-wf-sportello-*`, `e2e-wf-import-*`,
  `e2e-wf-chiusura-*` in `build/e2e/<timestamp>/screenshots/`; la galleria canonica resta invariata.
- **Problemi aperti:** i workflow dipendono dai dati del progetto demo e dai formati italiani di
  numeri/date; un cambio di demo richiede l'aggiornamento dei valori attesi. Restano i limiti già
  noti del harness (timeout per scenario senza `SIGALRM` su Windows, PyInstaller fuori scope).
- **Prossimo passo:** usare `./tools/run_e2e.sh` come collaudo di accettazione prima di ogni
  release; aggiungere un workflow quando nasce un percorso utente nuovo.

### 2026-11-23 — Correzione shell e Navigator: doppio clic, stato, nomi e icone
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato alle correzioni di shell e Navigator.
- **Obiettivo:** correggere i difetti segnalati nell'uso reale: doppio clic che apriva due finestre,
  barra di stato che copriva il fondo su schermi bassi, categoria «Schema» da rinominare e
  distinguere da «Tabelle», pulsanti del Navigator troppo grandi e datati.
- **File toccati:** `dbx/ui/navigator.py`, `dbx/ui/editor_host.py`, `dbx/ui/main_window.py`,
  `dbx/ui/icons.py`, `dbx/ui/design.py`, `dbx/designers/form_builder.py`,
  `dbx/designers/project_builder.py`, test UI, README, `docs/ui-parity.md`, rendering canonici,
  DIARIO.
- **Scelte:**
  - **Doppio clic:** `itemActivated` copre già doppio clic e Invio; il collegamento aggiuntivo a
    `itemDoubleClicked` faceva partire due volte `new_object` (due finestre Table Builder). Rimosso
    in Navigator e nello stesso schema del Form Designer, dove aggiungeva due controlli.
  - **Schermi bassi:** i 13 pulsanti categoria imponevano un'altezza minima di 634 px alla shell
    (757 px col resto), oltre l'area utile di molti portatili. La colonna è ora in un `QScrollArea`
    con barra sottile; il minimo della shell scende a 332 px. I `QDialog` legacy dentro l'MDI sono
    ospitati in un `QScrollArea` (`DialogEditor`), quindi la finestra non cresce oltre lo schermo e
    i dialoghi lunghi restano raggiungibili con lo scorrimento. Aggiunto un test a 1024×600 che
    verifica che la barra di stato resti sotto l'area centrale.
  - **Nome e ordine:** «Schema» diventa **Database**, sopra **Tabelle**, in Navigator, filtro file,
    Project Editor e modalità della status bar.
  - **Icone:** nuova icona a cilindro `database`, distinta dalla griglia `tabella`, usata per
    categoria, oggetti, menu e finestra del Database Designer.
  - **Stile:** pulsanti da 34 px con icona a sinistra e testo accanto, fondo piatto, hover tenue,
    selezione con barra di accento e gradiente leggero. Icone delle categorie tinte con tre accenti
    del tema (`nav_icon_1..3`), con varianti leggibili in Aurora, Silver e Dark.
- **Test:** `490 passed`; harness completo `PASS` con 14/14 scenari, 295/295 controlli e 31
  screenshot; smoke headless verde. Nuovi test per ordine/nome/icone del Navigator, scorrimento
  della colonna, doppia attivazione e shell a 1024×600 con Table Builder.
- **Screenshot:** rendering canonici rigenerati in Aurora (`01-desktop`, `02-navigator`,
  `04-table-structure`, `10-desktop-mdi`, `13-project-editor`, `26-import-csv`,
  `27-table-calculated`, `28-browse-calculated`); verifica visiva anche in Dark.
- **Problemi aperti:** su schermi molto bassi il Table Builder richiede lo scorrimento per
  raggiungere «Applica/Annulla»; la correzione strutturale del dialogo (contenuto comprimibile)
  resta un miglioramento successivo. Il cambio tema a runtime non ridisegna le icone già create nel
  Navigator.
- **Prossimo passo:** valutare un layout responsive del Table Builder e il refresh delle icone al
  cambio tema.

### 2026-11-23 — Finestre adattive allo schermo
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato all'adattamento automatico delle finestre.
- **Obiettivo:** evitare che la finestra principale, i dialoghi e le sottofinestre MDI escano
  dallo schermo o restino più grandi dell'area utile su portatili e monitor piccoli.
- **File toccati:** `dbx/ui/window_fit.py` (nuovo), `dbx/ui/app.py`, `dbx/ui/main_window.py`,
  `dbx/ui/editor_host.py`, `tools/capture_ui.py`, `tools/e2e_scenarios.py`,
  `tests/test_ui_window_fit.py` (nuovo), rendering canonici, DIARIO.
- **Scelte:**
  - `fit_to_available()` riduce una finestra entro `QScreen.availableGeometry()` e la riporta
    dentro l'area utile solo se ne esce; non ingrandisce mai una finestra già piccola.
  - La `MainWindow` si adatta al primo `show` (default 1180×780, ridotto su schermi minori).
  - I dialoghi modali vengono adattati prima di `exec()` tramite un aggancio unico su
    `QDialog.exec`; niente filtro globale sugli eventi `Show`, che destabilizzava la distruzione
    degli oggetti Qt a fine sessione (crash intermittenti in uscita dal harness).
  - Le sottofinestre MDI vengono ricontrollate quando cambia il viewport dell'area: se la shell
    si restringe, le finestre si riducono e rientrano nei bordi. I minimi scendono a 240×160 in
    caso di area molto piccola; `DialogEditor` continua a offrire lo scorrimento.
  - Gli strumenti QA (`capture_ui.py` e `ctx.capture` del harness) impongono la dimensione della
    baseline dopo `show`, così le immagini canoniche restano 1280×800 anche con schermo virtuale
    offscreen 800×800.
- **Test:** `494 passed`; harness completo `PASS` con 14/14 scenari, 295/295 controlli e 31
  screenshot; smoke headless verde. Nuovi test: riduzione entro lo schermo, `MainWindow` al primo
  show, dialogo modale dentro lo schermo, sottofinestra MDI che segue il ridimensionamento.
- **Screenshot:** rendering canonici rigenerati; `01-desktop.png` resta 1280×800.
- **Problemi aperti:** l'adattamento avviene al primo show e all'apertura dei dialoghi modali; non
  insegue lo spostamento della finestra su un altro monitor. I dialoghi aperti con `show()` e non
  con `exec()` non passano dall'aggancio.
- **Prossimo passo:** gestire il cambio di schermo a runtime e uniformare i dialoghi non modali.

### 2026-11-23 — Workspace a schede e Database unificato
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato alla nuova struttura della shell.
- **Obiettivo:** sostituire il desktop MDI con un layout razionale: Navigator nel quinto sinistro,
  finestre nei quattro quinti destri, schede orizzontali per più documenti; unificare creazione e
  modifica di database e tabelle in un'unica entità.
- **File toccati:** `dbx/ui/editor_host.py` (riscritto), `dbx/ui/main_window.py`,
  `dbx/ui/navigator.py`, `dbx/ui/design.py`, `dbx/designers/database_designer.py`,
  `dbx/designers/project_builder.py`, `dbx/smoke.py`, test UI, documentazione e rendering, DIARIO.
- **Scelte:**
  - **Layout**: un `QSplitter` divide la shell in 1:4; il Navigator occupa il quinto sinistro con
    barra verticale a icone da 64 px e lista oggetti. A ogni ridimensionamento il rapporto viene
    riapplicato; sulla sinistra resta un minimo leggibile di 200 px.
  - **Schede**: `EditorHost` non usa più `QMdiArea`; ospita un `QTabWidget` con etichette
    orizzontali, icone, chiusura e riordino. Ogni editor occupa tutta l'area a destra. La chiusura
    chiede conferma se l'editor è sporco. `EditorTab` mantiene l'API `find`/`windows`/`widget`/
    `property` usata dai chiamanti.
  - **Database unico**: scompare la categoria utente «Tabelle» separata dal diagramma. Il Navigator
    ha una sola categoria **Database** che elenca le tabelle; il doppio clic apre i dati, il menu
    contestuale porta a «Progetta tabella…». Il Database Designer è l'unica superficie di
    progettazione: nuova tabella, modifica, eliminazione, relazioni, proprietà e nuovo pulsante
    **Dati** per aprire il Browse.
  - **Comandi**: la toolbar ha una sola voce Database; «Nuova tabella» e «Struttura» aprono il
    Database e selezionano la tabella, senza finestre di struttura separate. Il Table Builder resta
    il dialogo interno riutilizzato. Il Project Editor mostra sette categorie, con Database al posto
    di Tabelle e senza il diagramma separato.
  - **Menu Finestra**: rimosse «Sovrapponi» e «Affianca»; il menu elenca le schede aperte e offre
    «Chiudi scheda» / «Chiudi tutte le schede».
- **Test:** `494 passed`; harness completo `PASS` con 14/14 scenari, 296/296 controlli e 31
  screenshot; smoke headless verde. Aggiornati i test dell'host, della shell, del Navigator, del
  Project Editor, del Table Builder e del Database Designer.
- **Screenshot:** nuovo `10-desktop-tabs.png`; rimossi `10-desktop-mdi.png` e i riferimenti MDI;
  rigenerati `01-desktop`, `02-navigator`, `10-desktop-tabs`, `15-database-designer`,
  `13-project-editor` e le catture E2E delle schede.
- **Problemi aperti:** il Navigator a un quinto è stretto per nomi lunghi (ellissi); la barra a
  icone usa i tooltip per le etichette. Il rapporto 1:4 viene riapplicato a ogni resize, quindi il
  trascinamento manuale del divisore non persiste.
- **Prossimo passo:** valutare un pannello oggetti espandibile e una scorciatoia per il Database.

### 2026-11-23 — Schede Modifica/Dati per la tabella nel Database
- **Stato:** completata
- **Branch/commit:** `main`; commit dedicato al dettaglio tabellare nel Database Designer.
- **Obiettivo:** associare a ogni tabella del diagramma ER due schede integrate: modifica della
  struttura e consultazione/modifica dei dati, evitando finestre separate e il flusso centrato solo
  sul diagramma.
- **File toccati:** `dbx/designers/database_designer.py`, `dbx/designers/table_builder.py`,
  `dbx/ui/main_window.py`, `dbx/smoke.py`, test del Database Designer e del Table Builder,
  `tools/capture_ui.py`, `tools/e2e_scenarios.py`, documentazione, rendering, DIARIO.
- **Scelte:**
  - Il Database Designer ora ha tre ingressi coordinati: **elenco tabelle** a sinistra,
    **diagramma ER** al centro e **ispettore** a destra; in basso compare l'area di dettaglio della
    tabella selezionata.
  - L'area di dettaglio contiene due schede: **Modifica** (TableBuilderDialog incorporato, non più
    modale) e **Dati** (DataView con editing tabellare). I pulsanti «Modifica» e «Dati» della
    toolbar selezionano la scheda; il doppio clic sulla card o sull'elenco apre il dettaglio.
  - `TableBuilderDialog` accetta un parametro `embedded`: «Applica» salva senza chiudere,
    «Annulla» ricarica la tabella dal progetto. In questo modo la struttura resta modificabile
    dentro il Database.
  - Le modifiche strutturali aggiornano ER, ispettore, elenco e scheda Dati; una rinomina ricrea il
    dettaglio con il nuovo nome ed emette `table_changed` verso la shell per ricaricare eventuali
    Browse aperti.
  - La tabella selezionata resta visibile contemporaneamente in elenco, canvas, ispettore e schede:
    non è più necessario passare esclusivamente dal diagramma.
- **Test:** `495 passed`; harness completo `PASS` con 14/14 scenari, 301/301 controlli e 32
  screenshot; smoke headless verde. Nuovo test per le due schede, l'elenco tabelle e la struttura
  incorporata; aggiornato il round-trip struttura → Browse.
- **Screenshot:** `15-database-designer.png` rigenerato con elenco tabelle e schede Modifica/Dati;
  nuovo `e2e-database-tabs.png` nel harness.
- **Problemi aperti:** la scheda Modifica incorpora un editor alto e su finestre basse richiede
  scorrimento; l'area di dettaglio ricrea gli editor quando cambia tabella, quindi non conserva
  modifiche non applicate passando a un'altra tabella.
- **Prossimo passo:** mantenere una bozza per tabella o avvisare quando si cambia tabella con
  modifiche non applicate.
