# dBX — personal database in stile dBASE 5.5

**Versione 0.2.0** — dBX è un personal database desktop multipiattaforma scritto in **Python + PyQt6**
con motore **SQLite**, ispirato a *dBASE 5.5 for Windows* (Borland). Riunisce in un'unica applicazione
i costruttori visivi che resero celebre dBASE: tabelle, form, report, script, menu e progetto.

La 0.2 realizza il **clone strutturale + chrome dBASE** concordato nel piano: desktop MDI, Navigator a
categorie, Table Structure a griglia unica, Form Designer a tre zone, Report Designer a bande impilate,
Program Editor, Menu Designer e Project Editor. Non è un clone pixel-perfect di Win16.

## Funzioni

| Strumento | Cosa fa |
|---|---|
| **Desktop MDI** | Finestre documento dentro `QMdiArea`, menu `Progetto · Modifica · Visualizza · Oggetto · Procedure · Proprietà · Finestra · ?`, SpeedBar a icone raggruppate, barra di stato con coordinate, oggetto, record e modalità |
| **Navigator** | Categorie con icona, `[Untitled]` in cima, filtro file, directory corrente, azioni contestuali; Query/Etichette/Immagini/Suoni/Cataloghi/Personalizzati visibili ma disabilitate |
| **Command Window** | Riquadri `Command` / `Command Results` nell'MDI, cronologia con ↑/↓, comandi `HELP`, `TABELLE`, `USE`, `RECORD`, `CLEAR` ed espressioni |
| **Browse / Vista Dati** | Griglia editabile, selettore di record, barra di navigazione, filtro, ordinamento, nuovo/elimina, export CSV, opzioni di editing e larghezze colonna persistenti |
| **Table Builder** | Struttura a griglia unica (`Field · Name · Type · Width · Decimal · Index`), tipi, obbligatorietà, default, didascalie, formati, regole, lookup, indici, relazioni, anteprima DDL, `Save As`, stampa, migrazioni con backup |
| **Form Expert** | Wizard a cinque passi: assistito o vuoto, tabella, scelta campi, layout, font/colori/stile |
| **Form Designer** | Palette `Controls` / `Field`, canvas con righelli e griglia 8 px, otto maniglie reali, selezione multipla, clipboard, undo/redo, allineamento, distribuzione, z-order, pagine a schede, Object Inspector ad albero, eventi e metodi |
| **Form Runtime** | Navigazione, CRUD, stato del record, sottomaschere uno-a-molti, script, report e messaggi; apertura nell'MDI con dati reali |
| **Report Designer** | Foglio unico a bande impilate ed etichettate, delimitatori trascinabili, due toolbar, zoom 50–200%, dialoghi Insert Field / Edit Text / Record Sort Order / Insert Group / Total |
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
python -m dbx --theme dark
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
  objects/forms/*.form.json
  objects/reports/*.report.json
  objects/scripts/*.script.json
  objects/menus/*.menu.json
  backups/                      # copie del database prima delle migrazioni distruttive
```

I metadati (didascalie, formati, regole, relazioni) vivono nei JSON, versionabili con git;
il database fisico è generato e migrato dal Table Builder. I JSON 0.1 si aprono senza migrazione:
i campi introdotti nella 0.2 hanno default vuoti.

## Flusso di lavoro tipico

1. **Progetto → Nuovo progetto**, poi **Oggetto → Nuova tabella**: definisci campi, indici e relazioni.
2. **Oggetto → Nuovo form**: parti dal Form Expert o da un form vuoto, trascina i controlli, regola
   le proprietà a destra e premi **Anteprima** per provare inserimento/modifica con dati reali.
3. **Oggetto → Nuovo report**: scegli tabella, filtro, ordinamento, gruppi e bande; anteprima e PDF.
4. **Oggetto → Nuovo script**: concatena azioni, prova con **Esegui**, salva.
5. **Oggetto → Nuovo menu**: componi le voci e le azioni del menu runtime.
6. **Progetto → Modifica progetto…**: imposta titolo, form e menu principale, valida e crea la build.
7. **Procedure → Esegui progetto** per la prova finale, **Procedure → Build distribuibile** per
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
- **Form Expert** e **Form Designer** a tre zone: palette `Controls` + `Field` a sinistra, anteprima
  live al centro con righelli e griglia di punti, Object Inspector a destra con schede
  Proprietà / Eventi / Metodi; stato `Object · Page · Top · Left · Height · Width`.
- **Report Designer**: foglio a bande impilate con gutter etichettato, due toolbar, Inspector e
  zoom; **Preview** con navigazione pagine, zoom, stampa, PDF e chiusura nella barra inferiore.
- **Program Editor**: albero azioni, sorgente con numeri di riga e sintassi, inspector e log.
- **Menu Designer**: albero voci, proprietà tipizzate e anteprima del menu.
- **Project Editor**: albero oggetti, impostazioni, validazione e build.

Rendering aggiornati in [`docs/reference/dbx-ui/renders/`](docs/reference/dbx-ui/renders/).

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
- Tema **Silver** predefinito e tema **Dark** opzionale, entrambi leggibili; i canvas leggono i token
  del tema attivo.

## Architettura

```
dbx/
  core/       db.py · metadata.py · types.py · ddl.py · expressions.py · form_model.py · project.py
  runtime/    rowset.py · form_runtime.py · report_engine.py · script_engine.py
  designers/  table_builder.py · form_builder.py · form_expert.py · report_builder.py
              script_builder.py · menu_builder.py · project_builder.py
  ui/         main_window.py · editor_host.py · navigator.py · data_view.py · report_preview.py
              command_window.py · project_runner.py · widgets.py · theme.py · design.py · icons.py
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
python tools/capture_ui.py                 # Silver
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

Lo stato finestra-per-finestra è in [`docs/ui-parity.md`](docs/ui-parity.md); la checklist di
collaudo della release è in [`docs/qa-0.2.md`](docs/qa-0.2.md).

## Limiti noti della 0.2

- **Query Designer**, **Query Results** e **Label Designer** sono fuori dalla 0.2 e previsti per la 0.3;
  le categorie corrispondenti restano visibili ma disabilitate.
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
