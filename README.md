# dBX — personal database in stile dBASE 5.5

**Versione 0.4.0** — dBX è un personal database desktop multipiattaforma scritto in **Python + PyQt6**
con motore **SQLite**, ispirato a *dBASE 5.5 for Windows* (Borland). Riunisce in un'unica applicazione
i costruttori visivi che resero celebre dBASE: tabelle, form, report, script, menu e progetto.
L'interfaccia usa il tema **Aurora**: zone colorate con gradienti, menu con icona e descrizione,
focus visibile e superfici chiare al posto del grigio Win16.

La 0.4 aggiunge gli **Esperti** per tabella, query, form e report e la modalità **QBE** del Query
Designer, con example elements, intervalli, pattern e righe OR in sola lettura. Restano il
**clone strutturale + chrome dBASE** concordato nel piano: desktop MDI, Navigator a categorie,
Table Structure a griglia unica, Form Designer a tre zone, Report Designer a bande impilate,
Program Editor, Menu Designer e Project Editor. Non è un clone pixel-perfect di Win16.

## Funzioni

| Strumento | Cosa fa |
|---|---|
| **Desktop MDI** | Finestre documento dentro `QMdiArea`, menu `Progetto · Modifica · Visualizza · Oggetto · Procedure · Proprietà · Finestra · ?`, SpeedBar a icone raggruppate, barra di stato con coordinate, oggetto, record e modalità |
| **Navigator** | Categorie con icona, `[Untitled]` in cima, filtro file, directory corrente, azioni contestuali, categorie **Schema** e **Query** con Database Designer, Query Designer e Query Results; Immagini/Suoni/Cataloghi/Personalizzati visibili e disabilitate finché non implementate |
| **Command Window** | Riquadri `Command` / `Command Results` nell'MDI, cronologia con ↑/↓, comandi `HELP`, `TABELLE`, `USE`, `RECORD`, `CLEAR` ed espressioni |
| **Browse / Vista Dati** | Griglia editabile, selettore di record, barra di navigazione, filtro, ordinamento, nuovo/elimina, export CSV, opzioni di editing e larghezze colonna persistenti |
| **Database Designer ER** | Diagramma entità-relazione delle tabelle reali, card con campi e PK/FK, archi con cardinalità e `ON DELETE`, pan/zoom, auto-layout, export PNG/SVG, creazione relazioni e modifica schema con backup |
| **Query Designer** | Tabelle e campi con spunta, INNER/LEFT JOIN suggeriti dalle foreign key, filtri AND, ordinamento multiplo, anteprima SQL parametrizzata e risultato tipizzato in sola lettura; modalità **QBE** con query image, example elements, intervalli, pattern e righe OR |
| **Esperti** | Procedure guidate per tabella (template, campi, indici, DDL), query (join dalle FK, campi, criteri, ordinamento), report (layout tabellare/colonnare/riepilogo, gruppi) e form; producono artefatti normali, poi modificabili nei designer |
| **Query Results** | Griglia read-only con tipi e formati dBX, aggiornamento, conteggio righe/colonne ed export CSV |
| **Query come sorgente** | Form generati da query in sola lettura (campi calcolati, niente inserimento/modifica) e report a bande su colonne di query con gruppi, totali, filtro e ordinamento |
| **Table Builder** | Struttura a griglia unica (`Field · Name · Type · Width · Decimal · Index`), tipi, obbligatorietà, default, didascalie, formati, regole, lookup, indici, relazioni, anteprima DDL, `Save As`, stampa, migrazioni con backup |
| **Form Expert** | Wizard a cinque passi: assistito o vuoto, tabella, scelta campi, layout, font/colori/stile |
| **Form Designer** | Palette `Controls` / `Field`, canvas con righelli e griglia 8 px, otto maniglie reali, selezione multipla, clipboard, undo/redo, allineamento, distribuzione, z-order, pagine a schede, Object Inspector ad albero, eventi e metodi |
| **Form Runtime** | Navigazione, CRUD, stato del record, sottomaschere uno-a-molti, script, report e messaggi; form su query in sola lettura |
| **Report Designer** | Foglio unico a bande impilate ed etichettate, delimitatori trascinabili, due toolbar, zoom 50–200%, dialoghi Insert Field / Edit Text / Record Sort Order / Insert Group / Total; sorgente tabella o query |
| **Report Preview** | Pagina singola o continua, fit-width, zoom persistente, totale pagine, aggiornamento, stampa ed export PDF |
| **Program Editor** | MiniScript con numeri di riga, evidenziazione di parole chiave/stringhe/commenti/numeri, vista azioni ↔ sorgente bidirezionale, inspector dei parametri e log di esecuzione |
| **Menu Designer** | Albero di voci e separatori, azioni tipizzate, filtro delle destinazioni, anteprima del menu |
| **Project Editor / Builder** | Albero oggetti, impostazioni (`title`, `main_form`, `main_menu`), validazione dei riferimenti, build in cartella + zip, helper PyInstaller |
| **Navigator, menu e status bar** | Sequenza menu dBASE, tooltip e icone coerenti, chiusura con conferma delle finestre modificate |

Linguaggio espressioni condiviso da form, report, script e regole di validazione:
`[campo]`, `[tabella.campo]`, `:variabile`, `.AND.`/`.OR.`/`.NOT.`, `IIF()`, `UPPER()`, `SUBSTR()`,
`YEAR()`, `TODAY()`, `DATEADD()` e altre funzioni, su AST validata (nessun `eval` libero).
Nei report i campi sono mostrati come `TABELLA->CAMPO` e i testi fissi interpolano `[campo]`.

## Installazione

```bash
python3 -m venv .venv && source .venv/bin/activate    # opzionale
pip install -e .            # solo runtime (PyQt6 6.10.2)
pip install -e ".[dev]"     # test e lint
```

Richiede Python 3.10+ e PyQt6 6.10.2 (versione fissata per riproducibilità della CI).

## Avvio

```bash
python -m dbx                          # finestra vuota
python -m dbx percorso/project.dbx.json
python -m dbx --demo                   # crea e apre il progetto Rubrica + Fatture
python -m dbx --theme silver           # tema storico dBASE
python -m dbx --theme dark             # tema scuro
python -m dbx --smoke                  # verifica headless end-to-end
```

In alternativa, dopo l'installazione: `dbx`. Per avviare senza attivare un virtualenv: `./start.sh`
(usa `.venv/bin/python` o `venv/bin/python` se presenti, altrimenti il `python3` di sistema con PyQt6).

## Struttura di un progetto

```
MioProgetto/
  project.dbx.json              # manifest: formato, impostazioni, indice oggetti
  data/MioProgetto.sqlite       # dati (un file per progetto)
  objects/tables/*.table.json
  objects/diagrams/*.diagram.json
  objects/queries/*.query.json
  objects/forms/*.form.json
  objects/reports/*.report.json
  objects/scripts/*.script.json
  objects/menus/*.menu.json
  backups/                      # copie del database prima delle migrazioni distruttive
```

I metadati (didascalie, formati, regole, relazioni) vivono nei JSON, versionabili con git;
il database fisico è generato e migrato dal Table Builder. I JSON 0.1 e 0.2 si aprono senza
migrazione: i campi introdotti nelle versioni successive hanno default vuoti o `table`.

## Flusso di lavoro tipico

1. **Progetto → Nuovo progetto**, poi **Oggetto → Nuova tabella**: definisci campi, indici e relazioni.
2. **Oggetto → Database Designer…** per vedere lo schema ER, creare relazioni e modificare le tabelle
   con conferma e backup.
3. **Oggetto → Nuova query**: scegli campi, join, filtri e ordinamento, prova l'SQL e il risultato,
   poi salva. **Query Results** mostra la griglia read-only con export CSV.
4. **Oggetto → Nuovo form**: parti dal Form Expert o da un form vuoto, trascina i controlli, regola
   le proprietà a destra e premi **Anteprima** per provare inserimento/modifica con dati reali.
   Scegliendo una query, il form mostra le colonne calcolate in sola lettura.
5. **Oggetto → Nuovo report**: scegli tabella o query, filtro, ordinamento, gruppi e bande;
   anteprima e PDF.
6. **Oggetto → Nuovo script**: concatena azioni, prova con **Esegui**, salva.
7. **Oggetto → Nuovo menu**: componi le voci e le azioni del menu runtime.
8. **Progetto → Modifica progetto…**: imposta titolo, form e menu principale, valida e crea la build.
9. **Procedure → Esegui progetto** per la prova finale, **Procedure → Build distribuibile** per
   ottenere cartella e zip pronti da consegnare.

## Ambienti dell'interfaccia

Ogni ambiente segue lo schema generale di dBASE 5.5 (senza imitarne i colori Win16):

- **Desktop**: menu `Progetto · Modifica · Visualizza · Oggetto · Procedure · Proprietà · Finestra · ?`,
  SpeedBar a gruppi con icona e barra di stato con oggetto, record e modalità.
- **Navigator**: colonna di categorie con icona a sinistra, directory corrente, filtro file e voce
  `[Untitled]` in cima all'elenco; doppio clic per aprire, tasto destro per le azioni.
- **Command Window** non modale dentro l'MDI: riquadro `Command` sopra, `Command Results` sotto.
- **Browse**: intestazione scura, colonna selettore, barra di navigazione, filtro, ordinamento.
- **Table Structure**: nome e tipo in alto, metadati (campi, indici, relazioni, record), griglia
  numerata dei campi, schede Indici / Relazioni / Proprietà / Anteprima DDL.
- **Database Designer**: diagramma ER con card delle tabelle, campi PK/FK, archi crow’s foot,
  cardinalità, pan/zoom, auto-layout e export PNG/SVG; creazione relazioni e modifica schema dal canvas.
- **Query Designer**: albero tabelle/campi a sinistra, schede QBE / Campi / Filtri / Ordinamento / SQL /
  Risultato a destra; join con campi proposti dalle relazioni, query statiche in sola lettura.
  Il toggle **QBE | Guidato** mostra la stessa `QuerySpec` come query image per tabella o come
  schede; la scheda Filtri riporta il gruppo per non perdere gli OR.
- **Query Results**: griglia read-only con intestazioni dBX, aggiornamento, conteggio e export CSV;
  si apre dal contesto della query o dal pulsante del Query Designer.
- **Form su query**: il Form Expert sceglie tabella o query; i campi sono le colonne della query e
  Nuovo/Salva/Elimina restano disabilitati.
- **Report su query**: il nuovo report sceglie tabella o query; campi, gruppi, totali, filtro e
  ordinamento lavorano sulle colonne della query.
- **Form Expert** e **Form Designer** a tre zone: palette `Controls` + `Field` a sinistra, anteprima
  live al centro con righelli e griglia di punti, Object Inspector a destra con schede
  Proprietà / Eventi / Metodi; stato `Object · Page · Top · Left · Height · Width`.
- **Report Designer**: foglio a bande impilate con gutter etichettato, due toolbar, Inspector e
  zoom; **Preview** con navigazione pagine, zoom, stampa, PDF e chiusura nella barra inferiore.
- **Program Editor**: albero azioni, sorgente con numeri di riga e sintassi, inspector e log.
- **Menu Designer**: albero voci, proprietà tipizzate e anteprima del menu.
- **Project Editor**: albero oggetti, impostazioni, validazione e build.

Rendering aggiornati in [`docs/reference/dbx-ui/renders/`](docs/reference/dbx-ui/renders/):
la serie `01`–`19` copre le finestre, `14-menu-progetto.png` mostra il menu icona + descrizione.

## Scorciatoie da tastiera

| Comando | Scorciatoia |
|---|---|
| Nuovo progetto / Apri progetto / Salva progetto | `Ctrl+N` / `Ctrl+O` / `Ctrl+S` |
| Annulla / Ripeti | `Ctrl+Z` / `Ctrl+Y` (anche `Ctrl+Shift+Z`) |
| Taglia / Copia / Incolla / Elimina | `Ctrl+X` / `Ctrl+C` / `Ctrl+V` / `Canc` |
| Aggiorna Navigator | `Ctrl+R` |
| Zoom avanti / indietro / 100% | `Ctrl++` / `Ctrl+-` / `Ctrl+0` |
| Chiudi finestra documento | `Ctrl+W` |
| Command Window | `Ctrl+K` |
| Guida rapida | `F1` |
| Esegui progetto | `F5` |
| Esegui script (Program Editor) | `F5` |
| Sposta controllo di 8 px / passo fine 1 px | frecce / `Shift`+frecce |

Nelle finestre con modifiche non salvate la chiusura chiede conferma. La guida rapida (`F1`) riporta
le scorciatoie principali.

## Accessibilità e HiDPI

- Nomi accessibili sui controlli principali (Navigator, Command Window, Inspector, canvas, griglie,
  editor di codice) per lettori di schermo e test automatici.
- Focus visibile tratteggiato su pulsanti, tool button, schede e campi di input.
- Ordine di tabulazione nei pannelli chiave: categorie → directory → filtro → elenco nel Navigator;
  campi → Inspector → canvas nei designer.
- Icone multi-risoluzione (16–48 px) e politica di scala `PassThrough`; righelli e griglie restano
  coerenti a 125% e 150%.
- Tema **Aurora** predefinito: menu bar, toolbar, Navigator, area MDI, schede, tabelle, status bar e
  pannelli dei designer usano gradienti e accenti vivaci; niente sfondo grigio.
- Menu con **icona + descrizione** su due righe, scorciatoia a destra e navigazione da tastiera.
- Temi **Silver** (storico dBASE) e **Dark** selezionabili con `--theme`; i canvas leggono sempre i
  token del tema attivo e lo sfondo MDI segue il tema anche dopo un cambio a runtime.

## Architettura

```
dbx/
  core/       db.py · metadata.py · types.py · ddl.py · expressions.py · form_model.py · project.py
              query_model.py · query_engine.py
  runtime/    rowset.py · query_rowset.py · form_runtime.py · report_engine.py · script_engine.py
  designers/  table_builder.py · database_designer.py · query_builder.py · form_builder.py
              form_expert.py · report_builder.py · script_builder.py · menu_builder.py
              project_builder.py
  ui/         main_window.py · editor_host.py · navigator.py · data_view.py · query_results.py
              report_preview.py · command_window.py · project_runner.py · widgets.py · theme.py
              design.py · icons.py
  io/         csv_io.py · pdf_export.py
  samples.py  progetto dimostrativo
```

I designer non contengono logica dati: producono artefatti JSON consumati da `core` e `runtime`.
Questo è l'equivalente dei *Two-Way Tools* di dBASE: ogni artefatto è leggibile e modificabile
anche come testo, e il motore è testabile senza GUI.

## Test e integrazione continua

```bash
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
python tools/capture_ui.py                 # Aurora
python tools/capture_ui.py --theme silver  # Silver storico
python tools/capture_ui.py --theme dark    # Dark
```

La suite copre DDL, migrazioni, espressioni, rowset, report, script, form, designer, shell MDI,
accessibilità, HiDPI e prestazioni (apertura demo < 2 s, form con 100 controlli < 2 s).
La CI GitHub Actions esegue i test headless su Linux, Windows e macOS (Python 3.11/3.12), lo smoke
e, su Linux, cattura e pubblica gli screenshot come artifact.

## Riferimenti visivi dBASE 5.5

`docs/reference/dbase55/` raccoglie 43 schermate originali di dBASE 5.5 for Windows
(desktop, Navigator, Command Window, Table Structure, Query Designer, Form Expert/Designer,
Properties Inspector, Crystal Reports), con indice in `README.md`, specifica di replica in
`ui-spec.md` e galleria apribile in `gallery.html`.

Le immagini Borland sono incluse con finalità di studio e confronto; i relativi diritti restano dei
titolari originali. dBX non ridistribuisce asset grafici Borland nell'applicazione.

Lo stato finestra-per-finestra è in [`docs/ui-parity.md`](docs/ui-parity.md); le checklist di
collaudo sono in `docs/qa-0.2.md`, `docs/qa-0.3.md` e `docs/qa-0.4.md`.

## Limiti noti della 0.4

- Le query sono statiche: niente parametri interattivi, RIGHT/FULL JOIN o aggregazioni nel designer.
- Il QBE è una vista di sola ricerca: niente Insert/Delete/Set/ChangeTo, crosstab o CALC; gli
  example elements richiedono che la tabella collegata sia già nella query.
- Un OR su campi di tabelle in LEFT JOIN è permesso ma segnalato: può escludere righe senza
  corrispondenza.
- I form su query sono in sola lettura nella 0.4; per modificare i dati usare un form su tabella.
- Query Results non offre modifica inline: è una vista di controllo, non un Browse.
- I report su query usano le colonne della query; i sottoreport e le query annidate non sono previsti.
- Il Label Designer è stato rimosso e sostituito dal Database Designer ER.
- Il Database Designer gestisce un solo diagramma `schema` per progetto e una relazione per volta nel
  dialog; le chiavi composite si creano dal Table Builder.
- Il Form Designer usa una palette in pannello ridimensionabile, non una finestra flottante come
  l'originale; il Report Designer ha selezione singola.
- Gli eventi form sono un dispatcher di azioni singole, non un linguaggio di scripting; i corpi dei
  metodi sono descrittivi e non vengono eseguiti.
- Il Program Editor non offre breakpoint né esecuzione passo-passo.
- La build del Project Editor è sincrona e non mostra una barra di avanzamento.
- Import `.DBF` legacy, grafici e campi calcolati persistenti sono previsti dopo la 1.0.
- Bundle PyInstaller: helper incluso (`designers/project_builder.package_with_pyinstaller`),
  richiede `pip install pyinstaller`.

## Licenza

MIT — vedi [`LICENSE`](LICENSE).
