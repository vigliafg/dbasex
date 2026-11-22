# Piano di ristrutturazione UI e struttura — dBX 0.2

**Stato:** approvato il 2026-11-22
**Esecuzione:** a ondate, con diario append-only e checkpoint ogni 3 ondate
**Obiettivo:** portare dBX da prototipo funzionante a clone coerente di **dBASE 5.5 for Windows**, mantenendo il motore SQLite e l'architettura testabile senza GUI.

---

## 1. Obiettivo e criterio di fedeltà

Il target è un **clone strutturale con chrome dBASE**, non un clone pixel-perfect Win16.

Significa:

- stessa anatomia delle finestre: menu, toolbar, pannelli, palette, status bar, bande;
- stessa sequenza e stessa gerarchia delle azioni;
- colori argento, bordi netti, tipografia compatta, selezione navy, focus tratteggiato;
- widget Qt nativi, layout manager, ridimensionamento e HiDPI;
- nessun confronto pixel-diff: il criterio è “stessa struttura e stessa disposizione”, verificato visivamente con gli screenshot di riferimento.

Non significa:

- ridisegnare ogni widget per imitare i bordi 3D Win16;
- font bitmap o icone 16 colori;
- layout a coordinate fisse non responsivo;
- compatibilità pixel a pixel a 96 DPI.

### Rubrica di fedeltà

| Livello | Criterio |
|---|---|
| **Struttura** | Stessa finestra, stessi pannelli, stessa disposizione, stesse azioni |
| **Chrome** | Palette argento, bordi, header, toolbar, status bar, focus |
| **Dettaglio** | Spaziature, font, icone, allineamenti coerenti con lo screenshot |
| **Interazione** | Stessi flussi: doppio clic, drag, Tab/Invio, menu contestuale, scorciatoie |

---

## 2. Decisioni approvate

| Decisione | Scelta |
|---|---|
| Fedeltà | Clone **strutturale + chrome dBASE** |
| Tema | **Silver** default; **Dark** opzionale non bloccante |
| Query Designer / Label Designer | **Fuori dalla 0.2**; categorie visibili ma disabilitate |
| Categorie Navigator non implementate | Visibili e disabilitate, con tooltip |
| Immagini Borland | Mantenute come documentazione con disclaimer di provenienza; rivalutare prima della release pubblica |
| MDI | `QMdiArea` + conversione graduale dei designer da `QDialog` a `QWidget` |
| Eventi form | Dispatcher minimale (`onClick`, `onEnter`, `onExit`, `onOpen`, `onClose`), non un nuovo linguaggio |
| Report | Estensione additiva di `ReportSpec` con default retrocompatibili |

---

## 3. Design system

### 3.1 Token

Nuovo modulo `dbx/ui/design.py`, unica fonte di verità per colori, metriche e font.

Palette Silver di base:

| Token | Valore | Uso |
|---|---|---|
| `window` | `#c0c0c0` | sfondo finestre e pannelli |
| `panel_light` | `#dfdfdf` | bordo chiaro in rilievo |
| `panel_shadow` | `#808080` | bordo scuro |
| `panel_dark` | `#404040` | bordo profondo |
| `workspace` | `#ffffff` | area documento |
| `text` | `#000000` | testo |
| `disabled` | `#808080` | testo disabilitato |
| `selection` | `#000080` | selezione navy |
| `selection_text` | `#ffffff` | testo su selezione |
| `focus` | `#000000` | focus tratteggiato |
| `title_active` | `#000080` | barra titolo attiva |
| `title_inactive` | `#808080` | barra titolo inattiva |

Metriche:

| Token | Valore |
|---|---|
| `icon_size` | 16 px |
| `toolbar_height` | 24 px |
| `row_height` | 18 px |
| `field_height` | 20 px |
| `grid_step` | 8 px |
| `ruler_size` | 18 px |
| `navigator_width` | 110 px |
| `status_height` | 22 px |
| `border` | 1 px |
| `padding` | 3–4 px |

Font:

| Contesto | Font |
|---|---|
| Interfaccia | `MS Sans Serif`, fallback `Segoe UI`, `Noto Sans`, sans-serif, 8–9 pt |
| Report | `Times New Roman`, 10 pt |
| Codice | `Courier New`, monospace, 9 pt |

Dark: palette derivata con gli stessi token, non un tema verde moderno. Il Dark è “best effort”: deve restare usabile, ma il QA bloccante è su Silver.

### 3.2 Regole

1. Nessun colore hard-coded nei widget; i canvas leggono i token.
2. `dbx/ui/theme.py` genera il QSS dai token, non contiene stringhe duplicate.
3. Le icone in `dbx/ui/icons.py` usano il colore corrente del tema.
4. I widget custom (`Ruler`, `FormCanvas`, `ReportCanvas`) rispettano tema, griglia e selezione.
5. Il default all'avvio è `silver`; `dark` resta selezionabile da `--theme dark` e dal menu Visualizza.

---

## 4. Architettura UI target

### 4.1 Host dei documenti

Nuovo `dbx/ui/editor_host.py`:

- `EditorWidget`: interfaccia comune per i designer (`title`, `dirty`, `save()`, `close_requested`);
- `EditorHost`: wrapper che inserisce un editor in un `QMdiSubWindow`;
- adapter temporaneo per i `QDialog` non ancora convertiti;
- i designer migrano a `QWidget` nelle ondate 3–5, mantenendo un sottile wrapper `QDialog` per test e compatibilità.

### 4.2 Main window

`dbx/ui/main_window.py`:

- `QMdiArea` al posto di `QTabWidget`;
- menu, toolbar e status bar costruiti da descrittori;
- gestione finestre: cascade, tile, chiudi, passa a;
- `self.tabs` resta solo come adapter deprecato durante la transizione, poi rimosso.

### 4.3 Modello dati

Modifiche solo additive e retrocompatibili:

| Modello | Aggiunta | Default |
|---|---|---|
| `FormControl` | `events: dict[str, str]` | `{}` |
| `FormControl` | `methods: dict[str, str]` | `{}` |
| `ReportSpec` | `band_order`, `band_heights`, `band_visible` | ordine e altezze attuali |
| `ReportSpec` | `sort_fields`, `groups` | liste vuote |

Ogni `from_dict` deve accettare i JSON esistenti senza migrazione manuale; ogni `to_dict` deve produrre JSON compatibile.

---

## 5. Ondate

### Ondata 0 — Baseline, design token e rete di sicurezza

**Durata:** 1 sessione. **Prerequisiti:** nessuno.

**Obiettivo:** congelare lo stato attuale, introdurre i token e rendere misurabile il progresso.

**Attività**

1. Creare `dbx/ui/design.py` con palette, metriche, font e funzioni `qss(theme)`.
2. Rifattorizzare `dbx/ui/theme.py` per usare i token.
3. Aggiornare `dbx/ui/app.py` (splash/icona) per leggere i token.
4. Creare `tools/capture_ui.py`:
   - `QT_QPA_PLATFORM=offscreen`;
   - progetto demo;
   - cattura di MainWindow, Navigator, DataView, Table/Form/Report builder, Command Window, anteprima report;
   - output in `docs/reference/dbx-ui/renders/`.
5. Creare `docs/ui-parity.md` con la matrice finestra → modulo → stato (`fatto` / `parziale` / `mancante`).
6. Aggiungere test UI headless:
   - `tests/test_ui_shell.py`;
   - `tests/test_ui_navigator.py`;
   - `tests/test_ui_designers.py`.
7. Aggiungere a `docs/reference/dbase55/README.md` una nota di provenienza/uso delle immagini.

**File toccati:** `dbx/ui/design.py` (nuovo), `dbx/ui/theme.py`, `dbx/ui/app.py`, `dbx/ui/icons.py`, `tools/capture_ui.py` (nuovo), `tests/test_ui_*.py` (nuovi), `docs/ui-parity.md` (nuovo), `docs/reference/dbase55/README.md`.

**Test e verifiche**
- `python -m pytest` verde.
- `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK.
- `python tools/capture_ui.py` produce i PNG senza errori.
- `grep` sui widget: nessun colore hard-coded residuo, esclusi i canvas.

**Criteri di accettazione**
- `design.py` è l'unica fonte di colori/metriche.
- Almeno 7 rendering generati.
- I test UI istanziano le finestre chiave senza dialoghi modali.
- Nessuna modifica funzionale visibile all'utente.

**Fuori scope:** restyling, MDI, modifiche ai designer.

---

### Ondata 1 — Shell desktop: MDI, menu, SpeedBar, status bar, tema

**Durata:** 2–3 sessioni. **Prerequisiti:** O0.

**Obiettivo:** sostituire la shell a schede con una shell dBASE.

**Attività**

1. **MDI**
   - `QMdiArea` in `MainWindow`;
   - `QMdiSubWindow` per tabelle, form, report, script, menu;
   - cascade, tile, chiudi, passa a;
   - menu Finestra popolato dinamicamente;
   - adapter per i dialog esistenti.

2. **Menu**
   - sequenza: `Progetto · Modifica · Visualizza · Oggetto · Procedure · Proprietà · Finestra · ?`;
   - `Modifica`: Annulla, Ripeti, Taglia, Copia, Incolla, Elimina;
   - `Visualizza`: SpeedBar, Status bar, Zoom, Aggiorna;
   - `Oggetto`: Nuova tabella/form/report/script/menu;
   - `Procedure`: Esegui progetto, Valida, Build, Command Window;
   - `Proprietà`: Impostazioni;
   - `Finestra`: Cascade, Tile, Chiudi;
   - `?`: Informazioni, Guida.

3. **SpeedBar**
   - pulsanti solo icona, 16×16, raggruppati da separatori;
   - gruppi: file · clipboard · undo · oggetti · allineamento · esegui · comandi · guida;
   - tooltip e shortcut;
   - nuovi glifi in `icons.py` per taglia/copia/incolla/allinea/distribuisci.

4. **Status bar**
   - riquadri permanenti: `Pos`, `Oggetto`, `Record`, `Modalità`, versione;
   - messaggi temporanei a sinistra;
   - aggiornamento da DataView, designer e Navigator.

5. **Tema**
   - default `silver`;
   - QSS per pannelli infossati, pulsanti in rilievo, tab, menu, toolbar, header;
   - focus tratteggiato e selezione navy;
   - Dark derivato dai token, non bloccante.

6. **Finestre**
   - titoli nel formato `Table Structure (Untitled)`, `Form Designer (nome)`, `Report Designer (nome)`;
   - icona, riduci/ingrandisci, chiusura con conferma se `dirty`.

**File toccati:** `dbx/ui/main_window.py`, `dbx/ui/editor_host.py` (nuovo), `dbx/ui/theme.py`, `dbx/ui/design.py`, `dbx/ui/icons.py`, `dbx/ui/app.py`, `dbx/smoke.py`, test UI.

**Test e verifiche**
- Aprire due oggetti: due finestre MDI, cascade/tile funzionanti.
- Menu completi; azioni non disponibili disabilitate.
- SpeedBar senza testo, tooltip presenti.
- Screenshot desktop confrontabile con `01-desktop-navigator-command.gif` per struttura.
- `pytest` e smoke verdi.

**Criteri di accettazione**
- Nessun `QTabWidget` come contenitore documenti.
- I designer si aprono in MDI o in dialog solo tramite adapter.
- Tema Silver applicato a tutte le finestre.
- I test non dipendono da `self.tabs`.

**Rischi**
- Riferimenti a `self.tabs` sparsi: introdurre un adapter e aggiornare test nello stesso commit.
- I dialog modali non entrano in MDI: conversione graduale, non big-bang.

---

### Ondata 2 — Navigator, Command Window, Browse/DataView

**Durata:** 4–5 sessioni. **Prerequisiti:** O1.

**Obiettivo:** rendere fedeli le tre finestre di uso quotidiano.

#### 2.1 Navigator

- Colonna verticale: icona sopra, testo sotto.
- Categorie nell'ordine: `Tutti`, `Tabelle`, `Query`, `Form`, `Report`, `Etichette`, `Programmi`, `Immagini`, `Suoni`, `Cataloghi`, `Personalizzati`.
- Categorie non implementate visibili e disabilitate con tooltip.
- Riga `Current Directory` con campo e pulsante `…`.
- Combo filtro coerente con gli artefatti reali:
  - `Tutti i file (*.*)`;
  - `Tabelle (*.table.json)`;
  - `Form (*.form.json)`;
  - `Report (*.report.json)`;
  - `Programmi (*.script.json)`;
  - `Menu (*.menu.json)`.
- Lista con `[Untitled]` in cima, icona per tipo, intestazione, doppio clic, menu contestuale.
- Stato vuoto e suggerimento contestuale.

#### 2.2 Command Window

- Due riquadri con titolo proprio: `Command` e `Command Results`.
- Finestra non modale dentro l'MDI, non dialog separato.
- Cronologia comandi con ↑/↓.
- Output monospace, scroll, `CLEAR`.
- Comandi: `HELP`, `TABELLE`, `USE`, `RECORD`, `CLEAR`, espressioni.
- Status separato per comando riuscito/errore.

#### 2.3 Browse / DataView

- Intestazione scura, colonna selettore record, righe alternate.
- Barra navigazione: primo, precedente, successivo, ultimo, nuovo, elimina, aggiorna.
- Status `Record n di m`, filtro e ordinamento visibili.
- Editing in-place con validazione e rollback.
- Dialog `Editing Options` minimale.
- Persistenza larghezza colonne per tabella.
- Export CSV invariato.

**File toccati:** `dbx/ui/navigator.py`, `dbx/ui/command_window.py`, `dbx/ui/data_view.py`, `dbx/ui/icons.py`, `dbx/ui/main_window.py`, test UI.

**Test e verifiche**
- Navigator filtra le categorie reali e mostra `[Untitled]`.
- Command Window resta aperta mentre si lavora su un form.
- Browse naviga i record da tastiera e mantiene lo stato.
- Test `Rowset` e DataView esistenti verdi.

**Criteri di accettazione**
- Le tre finestre usano lo stesso chrome delle altre.
- Nessun riferimento a estensioni `.dbf/.rep` legacy nell'interfaccia.
- Lo stato del record è sempre coerente dopo modifica/eliminazione.

**Fuori scope:** Query Designer, Browse Inspector completo.

---

### Ondata 3 — Table Structure

**Durata:** 2–3 sessioni. **Prerequisiti:** O1; può procedere in parallelo a O4.

**Obiettivo:** sostituire l'impostazione a schede con la finestra `Table Structure` dell'originale.

**Attività**

1. Intestazione:
   - `Name: [____]`;
   - `Type: DBASE (SQLite)`;
   - `Didascalia: [____]`.
2. Blocco metadati: `Updated`, `Bytes Used`, `Records`, `Bytes Left`.
3. Griglia unica: `Field · Name · Type · Width · Decimal · Index`.
4. Interazione:
   - riga attiva alta il doppio;
   - `Tab`/`Invio` crea il campo successivo;
   - drag del bordo sinistro per riordinare;
   - editing in-place di nome, tipo, larghezza, decimali, indice.
5. Toolbar finestra: `Open Exclusive`, `Add Records`, `Save As`, stampa.
6. Strumenti secondari in pannello inferiore o dialoghi:
   - Indici;
   - Relazioni;
   - Anteprima DDL;
   - Proprietà tabella.
7. Dialoghi:
   - `Save Table`;
   - `Editing Options` minimale;
   - conferma migrazione distruttiva con backup.
8. Integrazione con “Struttura…” della Browse e con Navigator.

**File toccati:** `dbx/designers/table_builder.py`, `dbx/ui/editor_host.py`, `dbx/ui/data_view.py`, `dbx/ui/icons.py`, test.

**Test e verifiche**
- Creare una tabella con campi, indici e relazioni produce lo stesso DDL di prima.
- Migrazioni e backup invariati.
- `test_ddl`, `test_metadata`, smoke verdi.
- Screenshot confrontabile con `08`, `09`, `13` per gerarchia.

**Criteri di accettazione**
- La griglia principale è una sola e contiene i campi.
- Indici e relazioni restano modificabili senza duplicare il modello.
- Il reorder non interferisce con l'editing delle celle.
- `TableBuilderDialog` funziona in MDI e in test headless.

**Rischi**
- Drag reorder vs editing: usare un handle dedicato.
- Doppia fonte per gli indici: la colonna `Index` deve derivare dallo stesso modello degli indici avanzati.

---

### Ondata 4 — Form Designer, Inspector, Form Expert, runtime form

**Durata:** 6–8 sessioni. **Prerequisiti:** O1, O3 consigliata.

**Obiettivo:** portare il Form Designer allo schema a tre zone con interazione completa.

#### 4.1 Shell del designer

- Convertire `FormBuilderDialog` in `FormDesignerWidget` + host MDI.
- Superficie bianca su grigio, griglia di punti ogni 8 px.
- Righelli orizzontale e verticale: tacche ogni 5, etichette ogni 10.
- Maniglie di ridimensionamento reali (8 punti).
- Selezione con bordo tratteggiato, snap 8 px, frecce per spostare, Shift per passo fine.
- Comandi: taglia, copia, incolla, duplica, elimina, allinea, distribuisci, porta avanti/indietro.
- Undo/redo locale al designer.
- Pagine del form come tab strip, con aggiunta/rinomina/rimozione.

#### 4.2 Palette

- Due palette affiancate o dockabili: `Controls` e `Field`.
- `Controls`: `Pointer` + pulsanti con icona e nome dBASE:
  `OKBUTTON`, `CLOSEBUTTON`, `CANCELBUTTON`, `HELPBUTTON`, `NOBUTTON`, `NEXTBUTTON`, `PREVBUTTON`, `INFOBUTTON`, `TOOLBUTTON`, `REPORTBUTTON`, `BROWSEBUTTON`, `NEXTRECORD`, `PREVRECORD`, `ADDRECORD`.
- Tab `Standard` / `Custom`.
- `Field`: elenco campi con icona; doppio clic o drag inserisce il controllo con etichetta automatica.

#### 4.3 Object Inspector

- Combo oggetto: `form.entryfield1`, `form.commandbutton2`, ecc.
- Albero raggruppato:
  - `• Font Properties`;
  - `• Geometry`;
  - `• Data`;
  - `• Behavior`;
  - `• Layout`.
- Editing in-place: testo, numeri, `.T./.F.`, combo.
- Schede `Properties` / `Events` / `Methods` con contenuti editabili.
- Riga `Quick Filter`.

#### 4.4 Eventi e metodi

- `FormControl` acquisisce `events` e `methods` (default vuoti).
- Runtime: dispatcher per `onClick`, `onEnter`, `onExit`, `onOpen`, `onClose`.
- Errori mostrati nel log, mai crash.
- Editor eventi: piccolo editor testuale, nessun linguaggio nuovo.
- Test di caricamento di form esistenti senza i nuovi campi.

#### 4.5 Form Expert

Nuovo `dbx/designers/form_expert.py`, wizard a 5 passi:

1. Expert Assistance / Blank Form.
2. Tabella o query.
3. Scelta campi (sorgente → destinazione).
4. Layout con radio e miniatura.
5. Font, colori, stile.

Genera un `FormSpec` valido e lo apre nel designer. Integrato in `MainWindow.new_object("forms")`.

#### 4.6 Runtime form

- Pulsanti di navigazione: first, prev, next, last, new, save, delete, close.
- Status record e messaggi di validazione.
- Sottomaschere uno-a-molti con collegamento padre/figlio.
- Anteprima dentro MDI, non dialog modale.

**File toccati:** `dbx/designers/form_builder.py`, `dbx/designers/form_expert.py` (nuovo), `dbx/ui/widgets.py`, `dbx/core/form_model.py`, `dbx/runtime/form_runtime.py`, `dbx/ui/editor_host.py`, `dbx/ui/icons.py`, test.

**Test e verifiche**
- Creare un form da zero, trascinare 5 controlli, ridimensionarli, allinearli, salvare e riaprire conserva tutto.
- Form Expert genera un form apribile e modificabile.
- Inspector modifica proprietà con effetto immediato.
- Eventi `onClick` eseguiti nel runtime con errori gestiti.
- `test_form_model` esteso; nuovo `test_form_events`; smoke aggiornato.

**Criteri di accettazione**
- Maniglie funzionanti, non solo disegnate.
- Griglia 8 px, righelli coerenti, status `Object · Page · Top · Left · Height · Width`.
- Inspector ad albero, non modulo piatto.
- Form esistenti apribili senza migrazione.
- Nessun crash su eventi mancanti o errati.

**Rischi**
- Scope creep sul linguaggio eventi: fermarsi al dispatcher di azioni.
- Conversione dialog → widget: commit isolato “designer host” prima delle feature.

---

### Ondata 5 — Report Designer Crystal Reports e Preview

**Durata:** 7–9 sessioni. **Prerequisiti:** O4 per il riuso di Inspector e maniglie.

**Obiettivo:** sostituire il canvas “una banda alla volta” con il foglio a bande impilate.

#### 5.1 Modello

Estendere `ReportSpec`:

- `band_order`, `band_heights`, `band_visible`;
- `sort_fields: list[{field, direction}]`;
- `groups: list[{field, label}]`;
- campi con nome visualizzato `TABELLA->CAMPO`.

Default retrocompatibili; i JSON attuali devono caricarsi senza modifiche. Aggiornare `ReportRenderer` per rispettare ordine, altezze, visibilità e sort.

#### 5.2 Canvas

- Foglio unico con bande etichettate a sinistra:
  - `Page header`;
  - `Details`;
  - `Page footer`;
  - `Title`;
  - `Group header/footer`;
  - `Summary`.
- Righello in alto, griglia tratteggiata, delimitatori di banda trascinabili.
- Controlli ridimensionabili con maniglie, selezione, allineamento.
- Zoom 50–200%.
- Status `L:1.00 R:4.46` aggiornata alla selezione.

#### 5.3 Toolbar

- Toolbar standard: nuovo, apri, salva, stampa, taglia, copia, incolla, annulla, inserisci campo, ordinamento, totali.
- Toolbar formattazione: font, corpo, grassetto/corsivo/sottolineato, allineamenti, bordi, colore.

#### 5.4 Dialoghi

- `Insert Database Field`: elenco `TABELLA->CAMPO`, `Insert`, `Done`, `Browse Field Data…`.
- `Edit Text Field`: testo, font, bordo, allineamento.
- `Record Sort Order`: `Report Fields` / `Add` / `<- Remove` / `Sort Fields` / `Sort Direction`.
- `Insert Group` e `Total` minimi, coerenti con il modello.

#### 5.5 Preview

- Toolbar inferiore completa: primo, precedente, successivo, ultimo.
- `1 of N`, zoom, stampa, esporta PDF, `Close`, `Total: N`, percentuale.
- Anteprima a pagina singola o continua; fit-width all'apertura.
- Persistenza zoom per sessione.

**File toccati:** `dbx/runtime/report_engine.py`, `dbx/designers/report_builder.py`, `dbx/ui/report_preview.py`, `dbx/ui/widgets.py`, `dbx/io/pdf_export.py` (solo integrazione), test.

**Test e verifiche**
- Report con Title + Page header + Details + Page footer visibile e modificabile sul foglio unico.
- Aggiungere/rimuovere un sort field cambia l'ordine in anteprima.
- Report demo esistenti si aprono, renderizzano ed esportano senza migrazioni manuali.
- `test_report_engine` esteso con bande/sort/gruppi; smoke con PDF > 1 KB.

**Criteri di accettazione**
- Bande impilate ed etichettate, non combo “una banda per volta”.
- Due toolbar visibili.
- Dialoghi Insert Field e Sort Order funzionanti.
- Retrocompatibilità completa dei JSON report.

**Rischi**
- Schema `ReportSpec`: versionare e testare i file demo attuali.
- Canvas a bande: non trasformarlo in un framework; restare su `QWidget` + paint event se sufficiente.

---

### Ondata 6 — Script, Menu, Project Builder

**Durata:** 4–6 sessioni. **Prerequisiti:** O1, O2.

**Obiettivo:** allineare gli strumenti residui e chiudere i buchi visibili della 0.2.

**Attività**

1. **Script Builder**
   - Program Editor con numeri di riga;
   - evidenziazione parole chiave;
   - pannello proprietà;
   - vista sorgente bidirezionale;
   - log di esecuzione.

2. **Menu Builder**
   - albero voci/separatori;
   - azioni tipizzate (apri form, esegui script, apri report, esci);
   - anteprima menu.

3. **Project Builder**
   - Project Editor con Navigator, impostazioni, validazione;
   - dialog `Build distribuibile`;
   - output cartella + zip invariato.

4. **Query Designer / Label Designer**
   - **Fuori scope 0.2**; categorie Navigator disabilitate;
   - rimandati a 0.3 con piano dedicato.

**File toccati:** `dbx/designers/script_builder.py`, `dbx/designers/menu_builder.py`, `dbx/designers/project_builder.py`, `dbx/ui/editor_host.py`, `dbx/ui/navigator.py`, test.

**Test e verifiche**
- Script e Menu builder usano lo stesso chrome.
- Build del progetto demo invariato.
- Smoke verde.

**Criteri di accettazione**
- Nessuna regressione su script engine, menu runtime, build.
- Le finestre sono coerenti con il design system.
- Query/Label chiaramente indicate come non disponibili.

---

### Ondata 7 — QA visiva, accessibilità, documentazione, release

**Durata:** 2–3 sessioni. **Prerequisiti:** tutte le precedenti.

**Obiettivo:** passata finale e release 0.2.

**Attività**

1. Confronto sistematico con le 43 schermate:
   - checklist per finestra;
   - correzione spaziature, font, bordi, colori;
   - aggiornamento `docs/ui-parity.md`.
2. Rigenerare `docs/reference/dbx-ui/*.png` con la nuova UI.
3. Aggiornare `README.md`, `ui-spec.md`, changelog.
4. Accessibilità:
   - tab order, focus visibile, label accessibili;
   - scorciatoie documentate.
5. HiDPI: icone e righelli nitidi a 125%/150%.
6. Prestazioni:
   - apertura progetto demo < 2 s;
   - form con 100 controlli fluido.
7. CI:
   - test UI offscreen;
   - artifact degli screenshot;
   - versione PyQt6 fissata.
8. Release `0.2.0`.

**Criteri di accettazione**
- Tutte le finestre della specifica hanno stato `fatto` o `parziale` motivato.
- `pytest`, smoke e cattura screenshot verdi su Linux; CI verde su Windows/macOS.
- README e screenshot corrispondono all'app reale.
- Tag `v0.2.0` e note di rilascio.

**Esito 2026-11-22:** release 0.2.0. `205 passed`; smoke e cattura Silver/Dark verdi. Query Designer,
Query Results e Label Designer restano esplicitamente fuori scope 0.2, con categorie disabilitate nel
Navigator. Checklist in `docs/qa-0.2.md`; note in `CHANGELOG.md`; tag `v0.2.0`.

---

## 6. Checkpoint e protocollo di ripresa

L'Ondata 0 è preparatoria e non conta nel ciclo di checkpoint. Le ondate di implementazione sono O1–O6.

| Checkpoint | Quando | Cosa fare |
|---|---|---|
| **A** | Fine Ondata 3 | Fermarsi, aggiornare diario, test, screenshot. Chiedere all'utente di compattare il contesto. |
| **B** | Fine Ondata 6 | Fermarsi, aggiornare diario, test, screenshot. Chiedere all'utente di compattare il contesto. |
| **C** | Fine Ondata 7 | QA finale, release 0.2. |

### Regole del checkpoint

1. L'agente **non inizia** l'ondata successiva prima del checkpoint.
2. Alla fine dell'ultima ondata del gruppo:
   - esegue `pytest`, smoke e `tools/capture_ui.py`;
   - aggiorna `DIARIO.md` con una sezione `CHECKPOINT`;
   - scrive nel diario il blocco `RIPRESA` con il prossimo passo esatto;
   - comunica all'utente: “Checkpoint A/B raggiunto: compatta il contesto e scrivi **continua**”.
3. Alla ripresa l'utente scrive **solo** `continua`.
4. L'agente, ricevuto `continua`:
   - legge `PLAN.md` e `DIARIO.md`;
   - controlla `git status` e `git log`;
   - trova la prima ondata non completata;
   - riparte da lì senza rileggere la conversazione precedente.

---

## 7. Diario di implementazione

File: `DIARIO.md` nella radice del progetto.

Regole:

- **Append-only**: non si riscrive la storia, si aggiungono voci.
- Una voce per ondata, più voci per sotto-attività se utile.
- Ogni voce contiene:
  - data;
  - ondata;
  - stato;
  - branch/commit;
  - obiettivo;
  - file toccati;
  - scelte e deviazioni dal piano;
  - test eseguiti;
  - screenshot/render;
  - problemi aperti;
  - prossimo passo.
- A ogni checkpoint, sezione `CHECKPOINT` con stato delle ondate e blocco `RIPRESA`.
- Il diario è versionato e incluso nei commit dell'ondata.

---

## 8. Definition of Done comune

1. Commit atomici su `main` (max 3–4 per ondata); branch dedicato solo per O4/O5 se utile.
2. `python -m pytest` verde.
3. `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` OK.
4. `python tools/capture_ui.py` rigenera i PNG senza errori.
5. Nessuna modifica non retrocompatibile a `core/` o `runtime/`.
6. `docs/ui-parity.md` aggiornato.
7. Screenshot prima/dopo allegati al commit o alla PR.
8. `DIARIO.md` aggiornato.

---

## 9. Matrice di test

| Tipo | Comando | Quando |
|---|---|---|
| Unit test motore | `python -m pytest` | ogni commit |
| Smoke end-to-end | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | ogni ondata |
| UI headless | `python -m pytest tests/test_ui_*.py` | ogni ondata |
| Rendering | `python tools/capture_ui.py` | ogni ondata |
| Manuale Silver | apertura demo + visita finestre | ogni ondata |
| Manuale Dark | apertura demo + visita finestre | a checkpoint |
| CI matrix | GitHub Actions | push/PR |

---

## 10. Risk register

| Rischio | Impatto | Mitigazione |
|---|---|---|
| Conversione MDI rompe riferimenti a `self.tabs` | Alto | Adapter + aggiornamento test nello stesso commit |
| Dialog → widget rompe smoke/test | Alto | Commit isolato “editor host” prima delle feature |
| Schema `ReportSpec` rompe report esistenti | Alto | Campi additivi, default, test sui JSON demo |
| Scope creep eventi form | Medio | Solo dispatcher di azioni, niente linguaggio |
| Font MS Sans Serif assente su Linux/macOS | Medio | Fallback dichiarati in `design.py` |
| HiDPI e righelli sfocati | Medio | Token in px logici, test a 125%/150% |
| Dark trascurato | Basso | QA bloccante solo su Silver |
| Immagini Borland coperte da copyright | Medio | Disclaimer, valutare link/rimozione prima della release |
| Ondate troppo grandi | Medio | Checkpoint ogni 3, commit atomici, diario |

---

## 11. Stato di avanzamento

| Ondata | Stato | Checkpoint |
|---|---|---|
| O0 — Baseline e design token | `[x]` completata (2026-11-22) | — |
| O1 — Shell/MDI/menu/tema | `[x]` completata (2026-11-22) | — |
| O2 — Navigator/Command/Browse | `[x]` completata (2026-11-22) | — |
| O3 — Table Structure | `[x]` completata (2026-11-22) | **A** |
| O4 — Form Designer/Expert/Runtime | `[x]` completata (2026-11-22) | — |
| O5 — Report Designer/Preview | `[x]` completata (2026-11-22) | — |
| O6 — Script/Menu/Project | `[x]` completata (2026-11-22) | **B** |
| O7 — QA e release 0.2 | `[x]` completata (2026-11-22) — versione 0.2.0 | **C** |
| UI 0.2.1 — Tema Aurora e menu icona + descrizione | `[x]` completata (2026-11-22) | — |

---

## 12. Mappatura finestre → moduli

| Finestra dBASE | Modulo dBX | Ondata |
|---|---|---|
| Desktop + menu + SpeedBar | `dbx/ui/main_window.py` | O1 |
| Navigator | `dbx/ui/navigator.py` | O2 |
| Command Window | `dbx/ui/command_window.py` | O2 |
| Browse / Table | `dbx/ui/data_view.py` | O2 |
| Table Structure | `dbx/designers/table_builder.py` | O3 |
| Form Designer | `dbx/designers/form_builder.py` | O4 |
| Form Expert | `dbx/designers/form_expert.py` | O4 |
| Properties Inspector | `dbx/ui/widgets.py` | O4 |
| Report Designer | `dbx/designers/report_builder.py` | O5 |
| Report Preview | `dbx/ui/report_preview.py` | O5 |
| Program Editor | `dbx/designers/script_builder.py` | O6 |
| Menu Designer | `dbx/designers/menu_builder.py` | O6 |
| Project Editor/Builder | `dbx/designers/project_builder.py` | O6 |
| Query Designer | `dbx/designers/query_builder.py` | 0.3 |
| Query Results | `dbx/ui/query_results.py` | 0.3 |
| Database Designer ER | `dbx/designers/database_designer.py` | 0.3 |
| Label Designer | — | rimosso |

---

## 13. Riferimenti

- `docs/reference/dbase55/ui-spec.md`
- `docs/reference/dbase55/README.md`
- `docs/reference/dbase55/images/`
- `docs/reference/dbx-ui/`
- `docs/ui-parity.md` (creato in O0)
- `DIARIO.md`
- `AGENTS.md`

---

## 14. Piano 0.3.0 — Database Designer ER e Query

**Obiettivo:** sostituire il Label Designer con un **Database Designer visuale ER**, aggiungere il
Query Designer e usare le query come sorgente dati di form e report.

**Fuori scope:** Label Designer/Etichette, barcode/QR, RIGHT/FULL JOIN, parametri interattivi delle
query, modifica del motore per la rinomina tabella, Interactive Tutor.

| Ondata | Scope | Checkpoint |
|---|---|---|
| O0 — Preparazione | `[x]` completata (2026-11-22) | — |
| O1 — Schema graph e layout ER | `[x]` completata (2026-11-22) | — |
| O2 — Canvas Database Designer | `[x]` completata (2026-11-22) | — |
| O3 — Editing schema | `[x]` completata (2026-11-22) | **A** |
| O4 — Motore Query | `[x]` completata (2026-11-22) | — |
| O5 — Query Designer | `[x]` completata (2026-11-22) | — |
| O6 — Query Results e sorgente dati | `[x]` completata (2026-11-22) | **B** |
| O7 — Release 0.3.0 | `[x]` completata (2026-11-22) — versione 0.3.0 | **C** |

### Decisioni di 0.3.0

- Il Navigator sostituisce `Etichette` con **Schema**; `Query` diventa attiva.
- Il diagramma ER è persistito come artefatto `diagrams/schema.diagram.json` (posizioni, zoom, note).
- Il grafo deriva sempre dai metadati reali (`Table`, `ForeignKey`); il diagramma non duplica lo schema.
- Le modifiche a tabelle e relazioni usano `Project.apply_table` con backup e conferma.
- La creazione/modifica avanzata dei campi riusa `TableBuilderDialog`; il canvas gestisce relazioni e
  layout.
- Le query sono SELECT parametrizzate, in sola lettura, con INNER/LEFT JOIN.
- Form e report possono scegliere `table` o `query` come sorgente; i form su query sono read-only
  nella 0.3.
- Export diagramma in PNG e SVG.
