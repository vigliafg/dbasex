# dBX — personal database in stile dBASE 5.5

dBX è un personal database desktop multipiattaforma scritto in **Python + PyQt6** con motore
**SQLite**, ispirato a *dBASE 5.5 for Windows* (Borland). Riunisce in un'unica applicazione i
costruttori visivi che resero celebre dBASE: tabelle, form, report, script e progetto.

## Funzioni

| Strumento | Cosa fa |
|---|---|
| **Table Builder** | struttura a griglia (tipi, dimensioni, obbligatorietà, default, didascalie, formati, regole, lookup), indici e unique, relazioni con `ON DELETE`, anteprima DDL, migrazioni con backup automatico |
| **Vista Dati** | griglia editabile in stile Browse, filtro libero, ordinamento, nuovo/elimina record, export CSV |
| **Form / Table Builder** | canvas con trascinamento, palette di 12 controlli, Object Inspector, pagine a schede, sottomaschere uno-a-molti, pulsanti, anteprima **con dati reali** |
| **Report Builder** | layout a bande (titolo, intestazioni, dettaglio, gruppi, piè di pagina, riepilogo), raggruppamenti, totali (somma/conteggio/media/min/max), anteprima paginata, stampa ed **export PDF** |
| **MiniScript Builder** | azioni concatenabili (messaggi, variabili, condizioni, cicli su tabella, apertura form, stampa report, export CSV, SQL, chiamata script), albero con drag-free editing, **vista sorgente bidirezionale**, esecuzione con log |
| **Menu Designer** | voci con azioni (apri form/report, esegui script, separatori) |
| **Project Editor / Builder** | Navigator per categorie, impostazioni (titolo, form principale), *Esegui progetto* con menu runtime, validazione dei riferimenti, build in cartella + zip, helper PyInstaller |
| **Command Window** | espressioni dBX e comandi rapidi (`HELP`, `TABELLE`, `USE`, `RECORD`) |

Linguaggio espressioni condiviso da form, report, script e regole di validazione:
`[campo]`, `[tabella.campo]`, `:variabile`, `.AND.`/`.OR.`/`.NOT.`, `IIF()`, `UPPER()`, `SUBSTR()`,
`YEAR()`, `TODAY()`, `DATEADD()` e altre funzioni, su AST validata (nessun `eval` libero).

## Installazione

```bash
python3 -m venv .venv && source .venv/bin/activate    # opzionale
pip install -e .            # solo runtime (PyQt6)
pip install -e ".[dev]"     # test e lint
```

Richiede Python 3.10+ e PyQt6.

## Avvio

```bash
python -m dbx                          # finestra vuota
python -m dbx percorso/project.dbx.json
python -m dbx --demo                   # crea e apre il progetto Rubrica + Fatture
python -m dbx --theme dark
python -m dbx --smoke                  # verifica headless end-to-end
```

In alternativa, dopo l'installazione: `dbx`. Per avviare senza attivare un virtualenv: `./start.sh` (usa `.venv/bin/python` o `venv/bin/python` se presenti, altrimenti il `python3` di sistema con PyQt6).

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
il database fisico è generato e migrato dal Table Builder.

## Flusso di lavoro tipico

1. **Progetto → Nuovo progetto**, poi **Oggetto → Nuova tabella**: definisci campi, indici e relazioni.
2. **Oggetto → Nuovo form**: parte dal disegno sulla tabella scelta; trascina i controlli,
   regola le proprietà a destra e premi **Anteprima** per provare inserimento/modifica con dati reali.
3. **Oggetto → Nuovo report**: scegli tabella, filtro, ordine, raggruppamento e bande; anteprima e PDF.
4. **Oggetto → Nuovo script**: concatena azioni, prova con **Esegui**, salva.
5. **Procedure → Valida progetto**, poi **Procedure → Esegui progetto** (menu + form principale) e infine
   **Procedure → Build distribuibile** per ottenere cartella e zip pronti da consegnare.

## Ambienti dell'interfaccia

Ogni ambiente segue lo schema generale di dBASE 5.5 (senza imitarne i colori Win16):

- **Desktop**: menu `Progetto · Oggetto · Procedure · Visualizza · Proprietà · Finestra · ?`,
  SpeedBar a gruppi con icona + nome e barra di stato con oggetto e conteggio record.
- **Navigator**: colonna di categorie con icona a sinistra, directory corrente, filtro file e voce
  `[Nuovo …]` in cima all'elenco; doppio clic per aprire, tasto destro per le azioni.
- **Command Window** non modale: riquadro `Command` sopra, `Command Results` sotto.
- **Table Structure**: nome e tipo in alto, metadati (campi, indici, relazioni, record), griglia
  numerata dei campi, schede Indici / Relazioni / Anteprima DDL.
- **Form Designer** a tre zone: palette `Controls` + `Field` a sinistra, anteprima live al centro con
  righelli e griglia di punti, Object Inspector a destra con schede Proprietà / Eventi / Metodi;
  stato `Object · Page · Top · Left · Height · Width` come nell'originale.
- **Report Designer**: bande etichettate e strumenti con icona; **Preview** con navigazione pagine,
  zoom, stampa, PDF e chiusura nella barra inferiore.

Rendering degli ambienti in `docs/reference/dbx-ui/` (desktop, designer, anteprime).

## Architettura

```
dbx/
  core/       db.py · metadata.py · types.py · ddl.py · expressions.py · form_model.py · project.py
  runtime/    rowset.py · form_runtime.py · report_engine.py · script_engine.py
  designers/  table_builder.py · form_builder.py · report_builder.py · script_builder.py
              menu_builder.py · project_builder.py
  ui/         main_window.py · navigator.py · data_view.py · report_preview.py
              command_window.py · project_runner.py · widgets.py · theme.py
  io/         csv_io.py · pdf_export.py
  samples.py  progetto dimostrativo
```

I designer non contengono logica dati: producono artefatti JSON consumati da `core` e `runtime`.
Questo è l'equivalente dei *Two-Way Tools* di dBASE: ogni artefatto è leggibile e modificabile
anche come testo, e il motore è testabile senza GUI.

## Test

```bash
python -m pytest              # 70+ test su DDL, migrazioni, espressioni, rowset, report, script, demo
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
```

## Riferimenti visivi dBASE 5.5

`docs/reference/dbase55/` raccoglie 43 schermate originali di dBASE 5.5 for Windows
(desktop, Navigator, Command Window, Table Structure, Query Designer, Form Expert/Designer,
Properties Inspector, Crystal Reports), con indice in `README.md`, specifica di replica in
`ui-spec.md` e galleria apribile in `gallery.html`.

## Limiti noti della 0.1

- Etichette multicolonna, crosstab e wizard guidati del report non sono ancora inclusi.
- Debugger dello script: log e interruzione, senza breakpoint/passo-passo.
- Import `.DBF` legacy, grafici e campi calcolati persistenti sono previsti dopo la 1.0.
- Bundle PyInstaller: helper incluso (`designers/project_builder.package_with_pyinstaller`),
  richiede `pip install pyinstaller`.
