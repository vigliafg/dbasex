# Changelog

Tutte le modifiche rilevanti di dBX. Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto usa [Semantic Versioning](https://semver.org/lang/it/).

## [Non rilasciato]

Estensione della **validazione dei campi** descritta in
[`PLAN-VALIDAZIONE.md`](PLAN-VALIDAZIONE.md): regole sul dato condivise da griglia, form, import e
script, con issue strutturate per la UI. I progetti 0.9 si aprono senza migrazione.

### Aggiunto

- **Issue strutturate**: `Rowset` restituisce `ValidationIssue` con campo, codice e severità;
  `ValidationError` estende `RowsetError` e conserva l'elenco delle issue per la UI.
- **Validazione per campo** (`validate_field`, `Rowset.update(only=)`): una cella valida si salva
  anche se un altro campo obbligatorio è ancora vuoto; il salvataggio dell'intero record continua a
  controllare tutto.
- **Obbligatorietà condizionale** (`required_expr`, `skip_expr`, `rule_message`): l'espressione vince
  sul booleano, un campo saltato non è obbligatorio e la regola può mostrare un messaggio dedicato.
- **Campo Scelta** (`choice`): valori statici con valore ed etichetta, sorgente dinamica
  `tabella.colonna`, combinazione `append`/`replace`, confronto esatto o senza maiuscole, vuoto
  ammesso o meno e testo libero opzionale. Cache, invalidazione e limite di 1000 valori; una
  sorgente mancante blocca con `choice_source`.
- **Dominio numerico**: minimo/massimo inclusivi oppure intervalli multipli, estremi aperti,
  messaggio personalizzato; vale per `INTEGER` e `DECIMAL`.
- **Input guidato**: maschera `9`/`A`/`a`/spazio, normalizzazione maiuscole/minuscole/titolo/frase e
  avanzamento automatico del focus nella griglia, nel nuovo record e nel Form Runtime.
- **Incremento** (`increment`): numero progressivo all'inserimento (`records`) o contatore di
  revisione per record (`updates`), con migrazione trasparente di `auto_serial`.
- **Riapplica regole di campo**: comando `File → Manutenzione database → Riapplica regole di
  campo…` che normalizza i valori esistenti, ricontrolla required/Scelta/dominio/regole e segnala i
  valori storici fuori elenco o dominio come avvisi `choice_stale`/`domain_stale`.
- **Import CSV a scarti**: le righe valide entrano e quelle rifiutate sono elencate con numero di
  riga e motivo.
- Rendering `27-table-calculated.png` aggiornato con Maiuscole, Maschera, Incremento e Dominio
  numerico.

### Modificato

- **Navigator**: **Database** ora è la categoria dello schema ER, mentre il nuovo gruppo **Tabelle**
  elenca le tabelle e apre la loro struttura con doppio clic; la Browse resta disponibile come
  **Sfoglia dati** nel menu contestuale.
- **Table Builder**: la nuova tabella si apre nella scheda del workspace, non in un dialogo modale,
  con lo stesso adattamento della struttura esistente; il focus iniziale va all'etichetta della
  scheda, così si passa da una finestra all'altra con la tastiera, e la larghezza minima scende
  sotto i 900 px per non debordare nei viewport da 1280 px.
- **Database Designer**: toolbar su due righe e pannelli laterali più stretti; il diagramma ER occupa
  circa il 70% della larghezza, la larghezza minima scende sotto i 900 px e l'area documenti non
  deborda più nei viewport da 1280 px.
- Il Table Builder espone i gruppi **Valori (Scelta)**, **Dominio numerico** e **Incremento** nella
  scheda Proprietà, ora con scorrimento interno.
- La Browse evidenzia la cella non valida e riporta il motivo nella barra di stato, senza dialogo
  modale; il dialogo resta per il salvataggio dell'intero record.
- Il vecchio `lookup` viene letto come `choice` con sorgente tabella; `auto_serial` viene letto come
  `increment="records"` e riscritto con il solo campo nuovo.

### Corretto

- Chiusura delle schede con il pulsante **[x]** della tab bar: `EditorHost` chiamava
  `QWidget.close` con l’argomento della scheda, provocando un `TypeError`; ora usa `close_tab` e la
  scheda si chiude regolarmente.

### Note di aggiornamento

- I metadati nuovi sono additivi con default vuoti: i file esistenti restano validi.
- I valori storici non vengono riscritti: lista e dominio valgono alla scrittura, mentre
  `Riapplica regole di campo` li segnala soltanto.
- La maschera e le maiuscole sono regole dell'editor: i valori già presenti nel database non
  cambiano finché non vengono modificati o normalizzati dal comando di manutenzione.
- `increment="updates"` è un contatore di revisione del singolo record, non una sequenza globale.

## [0.9.0] — 2026-11-22

Release dell'**automazione**: parametri riutilizzabili, variabili globali persistite e transazioni
esplicite negli script. I progetti 0.8 si aprono senza migrazione.

### Aggiunto

- **Parametri di script** (O10): ogni oggetto script può dichiarare parametri con nome, etichetta e
  valore predefinito; diventano variabili locali `:nome` e possono essere usati in espressioni,
  messaggi e filtri.
- **Esecuzione con parametri**: Navigator, menu del progetto e Program Editor chiedono i valori prima
  di eseguire lo script; in headless valgono i predefiniti. La forma testuale accetta
  `SET GLOBAL`, `CLEAR GLOBAL`, `BEGIN TRANSACTION`, `COMMIT TRANSACTION` e `ROLLBACK TRANSACTION`.
- **Variabili globali**: `SET GLOBAL :nome = espressione` salva un valore nel manifest del progetto,
  condiviso da tutti gli script e persistente tra le sessioni; `CLEAR GLOBAL :nome` lo rimuove.
- **Transazioni esplicite**: `BEGIN/COMMIT/ROLLBACK TRANSACTION` raggruppano più scritture; una
  transazione rimasta aperta viene annullata automaticamente quando lo script termina o fallisce.
- Rendering `37-script-parameters.png`.

### Note di aggiornamento

- I progetti 0.8 restano validi: `params` è un elenco vuoto negli script esistenti e le variabili
  globali vengono create solo al primo `SET GLOBAL`.
- I parametri sono testuali; usare `VAL(:nome)` per i calcoli numerici.
- Le transazioni sono esplicite e non annidate; senza `COMMIT` lo script annulla le scritture a fine
  esecuzione, anche in caso di errore.

## [0.8.0] — 2026-11-22

### Aggiunto

- **Label Designer leggero** (O7): nuovi oggetti `labels` con preset A4/Avery, griglia colonne/righe,
  distanze, margini, corpo e allineamento; modello di testo con `[campo]` e `{{[campo] * 2}}`.
- **Mail merge**: ogni record di una tabella o query produce un'etichetta, con filtro, ordinamento e
  salto delle etichette già usate sul primo foglio.
- **Anteprima, stampa e PDF** delle etichette riusando la finestra Preview dei report.
- **Navigator e menu Oggetto** espongono la categoria Etichette; il Project Editor e la validazione
  controllano sorgente e geometria dei fogli.
- **Grafici nel report** (O8): controllo `chart` con barre, linee e torta, aggregazione
  SUM/COUNT/AVG/MIN/MAX per categoria (primo gruppo del report o campo esplicito), titolo e bordo.
- **Report Designer**: dialogo Insert Chart con tipo, categoria, valore, funzione e banda; il
  grafico nel group footer è limitato al gruppo corrente.
- **Anteprima, stampa e PDF** disegnano i grafici con la palette di `design.py`, senza immagini
  esterne né dipendenze nuove.
- Rendering `31-label-designer.png`, `32-label-preview.png`, `33-report-chart.png` e
  `34-report-chart-designer.png`.
- **Vista Lista del form** (O9): `view_mode` `form`/`list` e colonne `list_fields`; la barra del
  runtime alterna scheda e lista, la selezione di una riga carica il record e la lista di una query
  resta in sola lettura.
- **Portali**: il controllo sottomaschera accetta `order` e `filter` (espressione sui campi figlio),
  applicati dopo il collegamento padre-figlio; errori di ordine o filtro sono riportati nello stato.
- **Form Designer**: proprietà View/List fields e Portal order/filter nell'Inspector.
- La sottomaschera generata da `create_master_detail` non si sovrappone più ai pulsanti del form.
- Rendering `35-form-list.png` e `36-form-portal.png`.

### Note di aggiornamento

- I progetti 0.7 restano validi: le nuove proprietà del form hanno default (`view_mode` = scheda,
  portali senza ordine/filtro).
- La vista Lista è di sola consultazione; modifiche, nuovo ed eliminazione passano dalla scheda.
- I portali leggono la tabella figlia collegata e applicano ordine SQL e filtro in sintassi dBX.
- I grafici usano la palette condivisa e non sono interattivi.


## [0.7.0] — 2026-11-22

Release del **calcolo sui dati**: campi calcolati e automatici, aggregati nelle query e tabella
incrociata. I progetti 0.6 si aprono senza migrazione; le nuove proprietà hanno default vuoti.

### Aggiunto

- **Campi calcolati**: formula in sintassi dBX (`[prezzo] * [quantita]`) valutata a ogni lettura,
  senza colonna fisica; compaiono in Browse, form e report in sola lettura e possono alimentare le
  regole di validazione.
- **Auto-enter**: espressione valutata alla creazione se il campo è vuoto, **serie automatica** su
  campi interi e **data automatica** di creazione o di modifica su campi Data/Data-ora.
- **Table Structure**: scheda Proprietà estesa con Calcolato, Auto-enter, Serie automatica e Data
  automatica; migrazioni additive e DDL che ignorano i campi virtuali.
- **Aggregati nelle query**: `GROUP BY` e colonne SUM/COUNT/AVG/MIN/MAX con alias, anche su join;
  COUNT senza campo conta i record; ordinamento per alias dell'aggregato.
- **Query Designer**: nuova scheda **Raggruppa** con campi di raggruppamento e aggregati; SQL e
  anteprima si aggiornano subito.
- **Crosstab read-only**: matrice righe × colonne con somma dei valori, totali di riga, colonna e
  generale, esportazione CSV; si apre da Query Results e dal Query Designer.
- **QA visiva**: rendering `27-table-calculated.png`, `28-browse-calculated.png`,
  `29-query-aggregates.png` e `30-crosstab.png`.

### Note di aggiornamento

- Nessun campo obbligatorio nuovo nei JSON: i progetti 0.6 restano validi.
- I campi calcolati non occupano spazio nel database e non sono indicizzabili, relazionabili,
  ricercabili via SQL o aggregabili nelle query.
- La serie automatica richiede un campo Intero; la data automatica un campo Data o Data/ora.
- Gli aggregati non supportano HAVING, sottoquery o espressioni arbitrarie; i filtri sono applicati
  prima del raggruppamento.
- Il Crosstab non è un oggetto salvato nel progetto: legge il risultato corrente di una query.

## [0.6.0] — 2026-11-22

Release delle **operazioni quotidiane**: ricerca guidata, sostituzione, importazione CSV e
manutenzione degli oggetti. I progetti 0.5 si aprono senza migrazione.

### Aggiunto

- **Find mode** nella Browse: più criteri combinati in AND o OR, operatori su testo, numeri e date,
  campo vuoto/non vuoto, opzione **Ometti** e conteggio dei record trovati. Scorciatoia `Ctrl+F`.
- **Ricerche salvate** per tabella, con nome, caricamento ed eliminazione dal dialogo di ricerca.
- **Sostituisci** (`Ctrl+H`): ambito su tutti i campi testuali o su un campo, distinzione
  maiuscole/minuscole, parole intere e sostituzione sui soli record visibili.
- **Importa CSV**: wizard con rilevamento di codifica e delimitatore, anteprima delle prime righe,
  mappatura colonna → campo suggerita per nome/didascalia, conversione nei tipi dBX, rapporto della
  riga in errore e svuotamento opzionale della tabella con backup.
- **Rinomina tabella** dal Table Structure: aggiorna schema SQLite, foreign key, query, form, report,
  script, diagrammi e ricerche salvate.
- **Duplica oggetto** dal Navigator per tabelle, query, form, report, script, menu e diagrammi; per le
  tabelle copia struttura e dati.
- **Manutenzione database** nel menu Progetto: compattazione con backup e verifica integrità.
- **QA visiva**: rendering `25-find-dialog.png` e `26-import-csv.png`.

### Note di aggiornamento

- Nessun campo nuovo obbligatorio nei JSON: i progetti 0.5 restano validi.
- La ricerca guidata e la sostituzione lavorano sulla tabella aperta nella Browse.
- L'import CSV richiede una tabella di destinazione già esistente.
- La rinomina non aggiorna le finestre già aperte: riaprirle dopo l'operazione.

## [0.5.0] — 2026-11-22

Release del **catalogo azioni script** in stile FileMaker: passi core categorizzati, Step Picker e
runtime con cursore dati. Gli script restano JSON con forma testuale bidirezionale; nessun nuovo
linguaggio e nessuna migrazione per i progetti esistenti.

### Aggiunto

- **Catalogo azioni categorizzato**: ogni azione di `ACTIONS` ha `category` e `description`;
  le categorie sono Controllo, Navigazione, Dati, Record, Ricerche, Interfaccia, Stampa/File,
  Script, Variabili e Avanzate.
- **Step Picker**: finestra con albero per categoria, filtro su nome/categoria/descrizione,
  descrizione e parametri dell'azione scelta; sostituisce l'elenco piatto in
  `Aggiungi azione`.
- **Inspector del passo**: il Program Editor mostra categoria e descrizione oltre ai parametri;
  il dialogo dei parametri riporta la descrizione dell'azione.
- **QA visiva**: nuovo rendering `24-script-step-picker.png`.

### Passi core e runtime

- Nuove azioni: `comment`, `loop`, `exit_loop_if`, `exit_script`, `halt`, `select_table`,
  `go_record`, `set_field`, `new_record`, `duplicate_record`, `delete_record`, `commit_record`,
  `revert_record`, `open_query`, `open_report`, `custom_dialog`, `beep`.
- Cursore dati nello `ScriptEngine`: tabella corrente, record corrente, filtro, ordinamento e id
  interno; `set_field` scrive subito e registra nel log.
- `loop` con limite `max_steps`, `exit_loop_if` sul ciclo corrente, `exit_script` e `halt` per
  fermare lo script.
- Forma testuale bidirezionale per tutte le nuove azioni, inclusa `ELSE IF` come `if` annidato.
- Validazione progetto di tabelle, campi, form, report, query, script e modalità `GO RECORD`.
- Adattatore UI del Form Runtime: dialoghi, messaggi, query/report e ricarica del record dopo
  l'esecuzione di uno script da un evento.

### Note di aggiornamento

- Il catalogo dello Step Picker è descrittivo; i passi core sono eseguiti dal medesimo
  `ScriptEngine`.
- Gli script JSON e testuali esistenti restano validi; nessun campo obbligatorio nuovo.
- Le scritture degli script sono immediate per passo: non c'è una transazione implicita.
- Versione dell'applicazione e del pacchetto portata a `0.5.0`.

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
