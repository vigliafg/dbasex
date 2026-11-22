# Changelog

Tutte le modifiche rilevanti di dBX. Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto usa [Semantic Versioning](https://semver.org/lang/it/).

## [0.4.0] — 2026-11-22

Release degli **Esperti** in stile Paradox e della modalità **QBE** del Query Designer. Le query
restano statiche e in sola lettura; il modello 0.3 si carica senza migrazione.

### Aggiunto

- **Table Expert**: procedura in quattro passi con template (Vuota, Contatti, Fatture, Inventario,
  Attività), campi modificabili, indici semplici e anteprima DDL; crea una normale tabella e la apre
  in Browse.
- **Query Expert**: tabella base, join suggeriti dalle foreign key in entrambe le direzioni, scelta
  campi, criteri AND, ordinamento e anteprima SQL; crea una `QuerySpec` normale e la apre nel
  Query Designer.
- **Report Expert**: sorgente tabella o query, layout tabellare/colonnare/riepilogo, campi, gruppo,
  ordinamento, orientamento, font e riepilogo; produce un normale `ReportSpec`.
- **Shell esperti**: `ExpertWizard`, `FieldEditor` e `FieldTransfer` condivisi; Form Expert allineato
  allo stesso shell. Voci **Oggetto → Nuovo con esperto** e menu contestuale del Navigator.
- **Modello QBE additivo**: `QueryFilter.value2` per gli intervalli e `QueryFilter.group` per gli OR;
  operatori `between`, `like` (jolly `*`/`?` con `%`/`_` letterali) e `ref`.
- **Example elements**: sintassi `_nome`; due celle con lo stesso nome producono un confronto `ref`
  tra i campi, con controllo della tabella presente e della compatibilità dei tipi.
- **Modalità QBE**: toggle **QBE | Guidato**, una query image per tabella con righe Includi,
  Criteri 1–3 e Ordinamento, sincronizzazione bidirezionale con le schede guidate, pannello di aiuto
  con grammatica e collegamento alla guida, evidenziazione delle celle non valide.
- **Avviso LEFT JOIN**: un OR su campi di tabelle in LEFT JOIN è permesso ma segnalato nella vista QBE.
- **QA visiva**: nuovo rendering `23-qbe-mode.png`.

### Cambiato

- La scheda **Filtri** del Query Designer mostra la colonna **Gruppo** e conserva gli OR prodotti dal
  QBE; l'ordinamento QBE segue l'ordine delle colonne.
- Il tema aggiunge gli stati visivi per le celle QBE non valide e il telaio delle query image, sempre
  tramite i token di `dbx/ui/design.py`.
- Versione dell'applicazione e del pacchetto portata a `0.4.0`.

### Note di aggiornamento

- I progetti 0.3 si aprono senza migrazione: `value2` vale stringa vuota e `group` vale `0`, quindi
  tutti i filtri esistenti restano AND.
- Gli esperti generano gli stessi artefatti dei designer: nessun formato o oggetto speciale.
- Il QBE è solo ricerca: non sono previste query di modifica, crosstab, CALC o parametri interattivi.
- Gli example elements richiedono che la tabella collegata sia già inclusa tramite un join; il
  designer segnala il caso invece di aggiungerla automaticamente.

## [0.3.0] — 2026-11-22

Release del **Database Designer ER** e del flusso completo delle **query**: progettazione visuale,
risultati in sola lettura e query come sorgente di form e report. Il Label Designer è stato rimosso.

### Aggiunto

- **Database Designer ER**: diagramma entità-relazione generato dalle tabelle reali, card con campi,
  PK/FK, didascalie, archi ortogonali con crow’s foot, cardinalità 1:1/1:N e `ON DELETE`, pan/zoom
  25–200%, auto-layout deterministico ed export PNG/SVG.
- **Modifica schema dal canvas**: nuova tabella e modifica tabella con il Table Builder, creazione e
  rimozione di relazioni con conferma, applicazione tramite `Project.apply_table` e backup del
  database; eliminazione bloccata per tabelle referenziate.
- **Categoria Schema** nel Navigator al posto di Etichette, con artefatto
  `objects/diagrams/schema.diagram.json` per posizioni, zoom e note.
- **Modello query**: `QuerySpec` serializzabile con tabella base, campi e alias, INNER/LEFT JOIN,
  filtri a valore letterale, ordinamento multiplo, `DISTINCT` e validazione dei riferimenti.
- **Motore query**: SQL sempre parametrizzato con `?`, conversione dei valori secondo il tipo reale
  del campo, operatori `eq/ne/gt/ge/lt/le/contains/starts/ends/null/notnull`, escape dei caratteri
  jolly in `LIKE` e `QueryResult` con colonne tipizzate.
- **Query Designer**: albero tabelle/campi a spunta, schede Campi / Filtri / Ordinamento / SQL /
  Risultato, join proposti dalle foreign key, anteprima SQL con parametri, risultato read-only
  limitato a 500 righe mostrate, salvataggio e rinomina come `objects/queries/*.query.json`.
- **Query Results**: finestra MDI read-only con intestazioni e formati dBX, aggiornamento,
  conteggio righe/colonne ed export CSV.
- **Query come sorgente dati**: `FormSpec` e `ReportSpec` accettano `source_type` tabella o query;
  il Form Expert e il nuovo report scelgono la sorgente. I form su query mostrano i campi calcolati
  in sola lettura, con Nuovo/Salva/Elimina disabilitati; i report su query supportano campi, gruppi,
  totali, filtro e ordinamento.
- **Demo**: query `fatture_clienti` (INNER JOIN) e `clienti_attivi` (filtro), form
  `form_clienti_attivi`, report `fatture_clienti_report` e relative voci di menu.
- **QA visiva**: nuovi rendering `16-query-designer.png` … `19-report-query.png`.

### Cambiato

- La categoria progetto `queries` entra in `CATEGORIES` e nella validazione e nella build.
- `validate_project` controlla le query e i riferimenti `query` di form e report.
- Il Navigator abilita la categoria **Query** e il filtro `*.query.json`; `Oggetto → Nuova query…`
  crea una query dal desktop.
- Il Report Designer mostra la sorgente come **Tabella · nome** o **Query · nome** e usa una tabella
  sintetica delle colonne per i dialoghi Insert Field, Group, Total e Sort Order.
- Il formato data predefinito `DD/MM/YYYY` viene tradotto correttamente in `strftime`.

### Corretto

- Le date nelle griglie e nei risultati delle query usano il formato dBX invece della rappresentazione
  ISO.
- L'ordinamento delle righe di query gestisce valori mancanti e `NULL` senza alterare l'ordine degli
  altri campi.

### Note di aggiornamento

- I progetti 0.1 e 0.2 si aprono senza migrazione: `source_type` vale `table`, `query` è vuoto e la
  categoria `queries` viene creata al primo salvataggio.
- Il Label Designer e la categoria Etichette non fanno più parte dell'applicazione; usare il
  Database Designer per lo schema e il Report Designer per la stampa.
- Le query sono statiche: niente parametri interattivi, RIGHT/FULL JOIN, aggregazioni o query annidate.
- I form su query sono in sola lettura nella 0.3; per inserire e modificare dati usare una tabella.
- Query Results è una vista di controllo, non un Browse editabile.

## [0.2.2] — 2026-11-22

Correzione della reattività delle voci dei menu a discesa della barra principale.

### Corretto

- Il passaggio del mouse su una voce sposta focus e selezione su una sola riga, evitando due voci
  evidenziate contemporaneamente.
- Il menu viene chiuso prima di eseguire l'azione: non resta aperto sopra dialoghi o finestre e le
  voci non vengono percepite come bloccate.
- I sottomenu hanno descrizione, freccia, apertura con clic, freccia destra o hover breve.
- Aggiunti test di regressione per clic su una voce reale della barra principale e per il focus
  con il mouse.

## [0.2.1] — 2026-11-22

Aggiornamento grafico completo: tema **Aurora** predefinito e menu a due righe con icona e descrizione.

### Aggiunto

- **Tema Aurora**: superfici chiare colorate con gradienti per menu bar, toolbar, Navigator, area MDI,
  schede, tabelle, status bar, inspector e pannelli dei designer. Sostituisce il grigio come tema
  predefinito.
- **Menu icona + descrizione**: ogni voce dei menu principali mostra icona, titolo in grassetto,
  descrizione e scorciatoia; navigazione da tastiera con frecce, Invio e Invio a capo.
- **Navigator colorato**: categorie con pastiglie sfumate, bordo colorato e stato attivo in gradiente
  viola/magenta.
- **Capture menu**: nuovo rendering `14-menu-progetto.png` per il QA visivo delle voci descrittive.

### Cambiato

- Il tema predefinito passa da `silver` ad `aurora`; gli alias `light` e `bright` puntano ad Aurora.
- `--theme` accetta `aurora`, `bright`, `light`, `silver`, `dark`; il tema storico Silver resta
  selezionabile per confronto.
- Il focus dei campi e delle viste usa un bordo pieno nel colore d'accento invece del tratteggio
  ad alto contrasto.
- Il tema Dark contiene i nuovi token delle zone colorate e resta leggibile; lo sfondo MDI ora segue
  il tema attivo anche dopo un cambio a runtime.

### Corretto

- I menu dinamici (Finestra, Progetti recenti) non generano più errori quando vengono ricostruiti.
- Le voci di menu con descrizione restano sincronizzate con stato abilitato, selezionato e icona
  dell'azione originale.
- La palette del Form Designer entra nelle subwindow MDI senza tagliare i pulsanti dBASE.

## [0.2.0] — 2026-11-22

Release della parità strutturale con dBASE 5.5 for Windows: desktop MDI, designer a tre zone,
report a bande impilate, program editor e project editor.

### Aggiunto

- **Desktop MDI**: `QMdiArea` con finestre documento, menu `Progetto · Modifica · Visualizza ·
  Oggetto · Procedure · Proprietà · Finestra · ?`, SpeedBar a icone raggruppate e barra di stato
  con coordinate, oggetto, record e modalità.
- **Navigator**: categorie con icona, `[Untitled]` in cima, filtro file, directory corrente,
  azioni contestuali e nuove categorie Menu; Query, Etichette, Immagini, Suoni, Cataloghi e
  Personalizzati restano visibili ma disabilitate.
- **Command Window** nell'MDI con cronologia, stato e comandi `HELP`, `TABELLE`, `USE`, `RECORD`,
  `CLEAR` ed espressioni.
- **Browse**: selettore di record, barra di navigazione, filtro, ordinamento, modifica inline con
  rollback, opzioni di editing e persistenza delle larghezze colonna.
- **Table Structure** a griglia unica (`Field · Name · Type · Width · Decimal · Index`), metadati,
  toolbar, pannello proprietà, riordino a trascinamento, `Save As`, stampa e migrazioni con backup.
- **Form Designer** a tre zone: palette `Controls` / `Field`, canvas con righelli, griglia 8 px,
  otto maniglie reali, selezione multipla, clipboard, undo/redo, allineamento, distribuzione,
  z-order, pagine a schede, Object Inspector ad albero e Form Expert a cinque passi.
- **Eventi form**: `onClick`, `onEnter`, `onExit`, `onOpen`, `onClose` come azione singola dello
  stesso dispatcher dei pulsanti; errori registrati senza crash. Nessun linguaggio di scripting.
- **Runtime form** nell'MDI con navigazione, CRUD, stato del record, sottomaschere uno-a-molti,
  script, report e messaggi.
- **Report Designer** a foglio unico con bande impilate ed etichettate, delimitatori trascinabili,
  due toolbar (standard e formattazione), zoom 50–200%, dialoghi Insert Field, Edit Text,
  Record Sort Order, Insert Group e Total.
- **Modello report** esteso con `band_order`, `band_heights`, `band_visible`, `sort_fields` e
  `groups`; renderer con più livelli di raggruppamento, ordinamenti multipli e totali per livello.
- **Report Preview** con pagina singola/continua, fit-width, zoom persistente, totale pagine,
  aggiornamento, stampa ed export PDF.
- **Program Editor** MiniScript con numeri di riga, evidenziazione di parole chiave, stringhe,
  commenti e numeri, vista azioni ↔ sorgente bidirezionale, inspector dei parametri e log.
- **Menu Designer** ad albero con separatori, azioni tipizzate, filtro delle destinazioni e
  anteprima del menu.
- **Project Editor** con albero oggetti, impostazioni (`title`, `main_form`, `main_menu`),
  validazione visiva e build distribuibile.
- **Accessibilità**: nomi accessibili sui controlli principali, focus visibile su pulsanti e
  schede, ordine di tabulazione nei pannelli chiave e scorciatoie documentate.
- **HiDPI**: icona multi-risoluzione, `PassThrough` per il fattore di scala e righelli coerenti a
  125% e 150%.
- **CI**: test UI offscreen su Linux, Windows e macOS, smoke headless e artifact degli screenshot
  su Linux; `PyQt6==6.10.2` fissato.

### Cambiato

- `FormBuilderDialog`, `ReportBuilderDialog`, `ScriptBuilderDialog` e `MenuBuilderDialog` sono ora
  widget ospitati nell'MDI; restano come alias per compatibilità con test, smoke e script esterni.
- Il progetto demo e i report usano nomi visualizzati `TABELLA->CAMPO` e riferimenti `[campo]`
  interpolati anche nei testi fissi.
- `apply_theme` registra il tema attivo sull'applicazione, così i canvas leggono i token corretti.

### Corretto

- Il tema Dark non è più forzato sui token Silver nei canvas.
- I pulsanti delle toolbar non assumono più lo stile navy dei pulsanti predefiniti quando sono
  disabilitati.
- L'intestazione di gruppo dei report mostra il valore del campo invece del segnaposto `[campo]`.
- I totali di conteggio accettano nomi di campo nudi e contano anche valori non numerici.

### Note di aggiornamento

- I JSON di progetto 0.1 si aprono senza migrazione: i nuovi campi del modello hanno default vuoti.
- Query Designer e Label Designer non fanno parte della 0.2 e restano previsti per la 0.3.
- Gli screenshot di riferimento sono in `docs/reference/dbx-ui/renders/`.

[0.3.0]: https://github.com/vigliafg/dbasex/releases/tag/v0.3.0
[0.2.2]: https://github.com/vigliafg/dbasex/releases/tag/v0.2.2
[0.2.1]: https://github.com/vigliafg/dbasex/releases/tag/v0.2.1
[0.2.0]: https://github.com/vigliafg/dbasex/releases/tag/v0.2.0
