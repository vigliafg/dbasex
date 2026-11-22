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
- **Test:** `207 passed`; smoke headless OK; cattura Aurora e Dark OK.
- **Screenshot:** serie `01`–`13` rigenerata in Aurora; nuovo `14-menu-progetto.png`; cattura Dark
  verificata.
- **Problemi aperti:**
  - Le submenu standard (es. Progetti recenti) hanno icona + titolo ma non la descrizione su due righe.
  - Il tema Aurora è più ricco del tema Silver: i testi lunghi nelle palette restano elisi.
  - La CI Windows/macOS va confermata al primo run dopo il push.
- **Prossimo passo:** 0.3 — Query Designer, Query Results e Label Designer.

## Checkpoint UI 0.2.1
- **Versione:** `0.2.1`; tag `v0.2.1`.
- **Test:** `207 passed`, smoke OK, cattura Aurora/Dark OK.
- **RIPRESA:** piano 0.2 concluso con aggiornamento grafico 0.2.1. La prima attività non completata
  resta la **0.3 — Query Designer, Query Results e Label Designer**.
