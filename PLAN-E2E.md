# Piano E2E intensivo dBX — copertura funzionale completa

**Data:** 2026-11-26
**Esecuzione:** ondate E1–E6 con checkpoint A (fine E3) e B (fine E6)
**Stato:** approvato il 2026-11-26; E1–E5 completate, E6 da eseguire
**Ambito:** collaudo end-to-end di dBX 0.9.0 + estensione validazione
**Obiettivo:** 100+ workflow distinti che simulano l'uso reale di ogni ambiente, builder e opzione, con verifica di funzionalità, persistenza ed efficienza.

---

## 0. Sintesi esecutiva

Il harness attuale è già una buona base: **14 scenari, 298 controlli, 32 screenshot, 58 s** totali
(pytest + smoke inclusi). Non basta per la richiesta: gli scenari sono larghi e verificano una
funzionalità per volta, non ogni opzione di ogni builder.

La proposta è costruire **E2E 2.0**: un harness a scenari granulari, con catalogo delle funzioni
derivato dal codice e un **gate di copertura** che fallisce se una nuova opzione (tipo campo,
operatore, azione script, controllo form, banda report, preset etichetta, azione di menu) non ha
almeno uno scenario che la esercita.

**Numeri target fase 1**

| Metrica | Oggi | Target |
|---|---:|---:|
| Workflow distinti | 14 | **133** |
| Controlli nominati | 298 | **≥ 1.200** |
| Feature tracciate nel catalogo | 0 | **≥ 350** |
| Superfici con screenshot | ~20 | **≥ 21, una per ambiente** |
| Copertura opzioni derivate dal codice | non misurata | **100%** |
| Durata scenari (4 worker) | ~22 s (1 processo) | **< 8 min** |
| Determinismo | non verificato | **3 run consecutivi identici** |

---

## 1. Interpretazione della richiesta e assunzioni

1. **“100+ workflow”** = 100+ scenari E2E distinti, non 100+ controlli. Ogni scenario è un flusso
   utente autonomo con progetto temporaneo isolato.
2. **“Ogni builder, ogni opzione”** = per ogni superficie (Table Builder, Database Designer, Query
   Designer/QBE, Form Expert/Designer/Runtime, Report Designer/Preview, Label Designer, Program
   Editor, Menu Designer, Project Editor, Import Wizard, Find, Crosstab, Command Window,
   Navigator, shell) vanno esercitate tutte le opzioni dichiarate nei modelli e nei widget.
3. **Fase 1 = comportamento corretto su uso legittimo.** I rifiuti di validazione previsti (campo
   obbligatorio vuoto, FK inesistente, scelta fuori elenco, tipi errati) fanno parte della
   funzionalità e vengono testati come esito atteso. La **fase 2** (comportamenti errati dell'utente,
   dialoghi annullati, dati corrotti, crash, concorrenza) resta fuori da questo piano.
4. **UI-first.** Per ogni funzione che l'utente raggiunge da una finestra, lo scenario usa il vero
   widget/dialogo della UI (via `objectName`, segnali e slot pubblici). Le API di `core` si usano
   solo per fixture e verifiche, non per sostituire il percorso utente.
5. **Nessun test distruttivo sul progetto reale.** Solo progetti temporanei, `DBX_CONFIG_DIR`
   isolata, nessuna scrittura in `docs/` o nel repository durante i run.

---

## 2. Baseline misurata

Da `build/e2e/20261125-133608/report.md`:

- 14/14 scenari, 298/298 controlli, 32 screenshot.
- pytest: 571 test in 35,31 s; smoke: 2,51 s; harness totale 58,1 s.
- Scenario più lento: `ui_designers` 14,56 s (show/grab delle finestre); gli altri < 1,5 s.
- Punto debole: un solo scenario copre “tutti i designer” (`ui_designers`, 30 controlli). Un errore
  su un'opzione viene mascherato dal controllo aggregato; non c'è tracciamento feature→scenario.

---

## 3. Criteri di successo (gate di accettazione)

Il piano è concluso solo se, su un checkout pulito:

1. `python -m pytest` verde.
2. `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` → `SMOKE OK`.
3. `python tools/e2e_harness.py --skip-pytest --skip-smoke` → **PASS**, 133/133 scenari.
4. Report con **0 controlli falliti**, **0 feature scoperte**, **0 dialoghi imprevisti**.
5. Copertura catalogo **100%** (esclusioni esplicite e motivate ammesse, mai silenziose).
6. Almeno uno screenshot non vuoto per ogni ambiente elencato in §5.
7. Budget di durata rispettati (§12) su 3 run consecutivi.
8. Nessuna modifica non committata generata dal run (`git status` invariato a fine harness).
9. `docs/e2e-coverage.md` rigenerato e coerente con il catalogo.
10. `DIARIO.md` aggiornato con ondate, checkpoint e blocco `RIPRESA`.

---

## 4. Fuori scope della fase 1

- Test di comportamenti errati dell'utente (fase 2).
- Pixel-diff delle schermate; il criterio resta strutturale + smoke dei PNG.
- Stampa fisica su carta: si verifica il percorso “stampa” con mock e l'output PDF.
- Dialoghi nativi del sistema operativo (file chooser, stampante) oltre i mock già usati.
- Build PyInstaller su Windows/macOS reali: si testa lo script e l'output su Linux.
- Prestazioni estreme (> 100k righe): la soglia fase 1 è 10k righe e 100 controlli.

---

## 5. Strategia

### 5.1 UI-first, verifica su tre livelli

Ogni scenario verifica lo stesso esito su tre livelli:

1. **UI**: il widget/dialogo reale accetta l'azione e aggiorna lo stato visibile.
2. **Modello**: l'artefatto in memoria (`Table`, `QuerySpec`, `FormSpec`, `ReportSpec`,
   `LabelSpec`, `ScriptSpec`, `MenuSpec`) contiene il valore atteso.
3. **Persistenza**: dopo `save()` + chiusura + riapertura, il JSON su disco, il manifest e il
   database SQLite contengono ancora il valore; il progetto passa `validate_project`.

Regola: nessuno scenario può chiudersi senza almeno un **round-trip di riapertura** quando produce
un artefatto persistente.

### 5.2 Isolamento e determinismo

- Un progetto temporaneo per scenario, creato con fixture deterministiche (date fisse, nessun
  `random`).
- Un processo worker per area (default) e modalità `--isolate scenario` per il gate finale: un crash
  non compromette gli altri scenari.
- `DBX_CONFIG_DIR` temporanea per worker, nessun accesso alla configurazione utente.
- Dialoghi modali neutralizzati con risposte esplicite e **registro dei dialoghi attesi**: una
  domanda non prevista fa fallire lo scenario (invece di rispondere “sì” alla cieca).
- Nessun `sleep`; solo `processEvents()` e `QTest` per input.

### 5.3 Copertura derivata dal codice

Il catalogo non è un elenco scritto a mano destinato a marcire. Una parte consistente è **derivata
per introspezione/AST**:

| Fonte | Opzioni derivate |
|---|---|
| `dbx/core/types.py` | 9 tipi campo |
| `dbx/core/metadata.py` | 4 azioni `ON DELETE`, indici, PK, FK |
| `dbx/core/query_model.py` | 14 operatori, 5 aggregati, 2 join, 2 direzioni |
| `dbx/core/form_model.py` | 12 tipi controllo, 8 azioni pulsante, 5 eventi, 2 metodi |
| `dbx/runtime/report_engine.py` | 7 bande, 8 tipi controllo report, 3 grafici |
| `dbx/core/label_model.py` | 4 preset, 3 allineamenti |
| `dbx/runtime/script_engine.py` | 34 azioni script |
| `dbx/designers/menu_builder.py` | 5 azioni menu |
| `dbx/ui/navigator.py` | 12 categorie Navigator |
| `dbx/ui/main_window.py` | 8 menu, 48 `QAction` |
| AST su `dbx/ui` + `dbx/designers` | classi dialogo/designer e schede (`addTab`) |
| Catalogo manuale | opzioni di campo dei builder (~120), proprietà Inspector, toolbar report |

`tests/test_e2e_catalog.py` verifica che:

- ogni costante derivata abbia un ID nel catalogo;
- ogni ID punti a uno scenario esistente;
- ogni scenario dichiari solo feature esistenti;
- nessuna feature `auto` resti senza scenario.

Aggiungere un nuovo operatore o una nuova azione script senza uno scenario E2E diventa un test
pytest rosso. È il meccanismo che garantisce “ogni opzione” nel tempo.

### 5.4 Efficienza verificata, non dichiarata

- **Budget per scenario** dichiarato nel decoratore (`budget_s`): soft warning oltre 1×, fail oltre
  3× o timeout hard.
- **Test prestazionali dedicati** (§12) su 10k righe, 100 controlli form, report da 1.000 righe,
  query con join e aggregati.
- **Censimento SQL**: un helper `ctx.sql_count()` usa `sqlite3.Connection.set_trace_callback` per
  contare le query. Soglie esplicite per prevenire N+1 su DataView, report e navigazione form
  (es. caricamento 100 righe Browse ≤ 5 statement; rendering report ≤ 10 statement).
- **Memoria**: 20 ripetizioni di uno scenario leggero con `tracemalloc`; crescita < 20 MB.
- Tempi registrati nel report con mediana, p95 e massimo per area.

### 5.5 Dialoghi deterministici e verificati

`ctx.dialogs` registra ogni `QMessageBox`, `QInputDialog`, `QFileDialog` e dialogo custom.
L'helper `ctx.expect_dialog(kind, contains=...)` dichiara l'attesa; a fine scenario
`ctx.assert_dialogs_consumed()` fallisce se:

- un dialogo atteso non è comparso;
- è comparso un dialogo non atteso;
- il testo non contiene la stringa chiave (es. “backup”, “sovrascrivere”).

Questo trasforma i dialoghi da “ostacolo da neutralizzare” a parte verificata del flusso.

---

## 6. Architettura E2E 2.0

```
tools/e2e/
  __init__.py
  context.py          # E2EContext: progetto, dialoghi, check, screenshot, reopen, sql_count
  ui.py               # helper Qt: click, choose, type, press, drag, edit_cell, menu_trigger
  checks.py           # check nominati, expect_error, artifact/db/file assertions
  fixtures.py         # schemi: vuoto, 1:N, tutti i tipi, legacy, sporco, 10k righe
  catalog.py          # FEATURES + derivazione da costanti/AST + esclusioni motivate
  coverage.py         # calcolo copertura, report MD/JSON, gate
  registry.py         # decoratore @scenario, raccolta, alias dei 14 scenari legacy
  reporting.py        # report.json v2, report.md, JUnit-like, artefatti
  workers.py          # shard per area, subprocessi, aggregazione, repeat
  scenarios/
    s00_foundation.py
    s10_tables.py
    s20_browse.py
    s30_data_ops.py
    s40_queries.py
    s50_forms.py
    s60_reports.py
    s70_labels.py
    s80_scripts.py
    s90_shell.py
    s95_journeys.py
    s99_quality.py
tools/e2e_harness.py  # entrypoint sottile, CLI retrocompatibile
tools/e2e_scenarios.py# shim: riesporta registry e contesto (test esistenti invariati)
```

Vincoli:

- `tools/e2e_harness.py` mantiene tutte le opzioni attuali e i nomi dei 14 scenari come alias.
- `tests/test_e2e_harness.py` continua a passare senza modifiche, salvo l'aggiunta di nuovi assert.
- `build/e2e/<timestamp>/` resta la destinazione; `latest.txt` invariato.
- Nessuna dipendenza nuova: solo PyQt6, stdlib, pytest già presente.

### Nuove opzioni CLI

| Opzione | Funzione |
|---|---|
| `--area tables,forms` | Filtra per area funzionale |
| `--feature TB-FIELD-*` | Esegue gli scenari che coprono una feature |
| `--workers N` | Shard in processi separati (default 1, CI 4) |
| `--isolate area\|scenario` | Granularità dell'isolamento |
| `--repeat N` | Ripete per il controllo di determinismo |
| `--require-coverage 100` | Gate copertura (default attivo) |
| `--coverage-md PATH` | Rigenera la matrice documentale |
| `--baseline PATH` | Confronta scenari/controlli/tempi con la baseline versionata |
| `--list --verbose` | Mostra ID, area, feature e budget di ogni scenario |

---

## 7. Contratto di scenario

```python
@scenario(
    id="tbl-04-required",
    area=Area.TABLES,
    title="Obbligatorietà semplice e condizionale",
    features={"TB-FIELD-REQUIRED", "TB-FIELD-REQUIRED-IF", "TB-FIELD-REQUIRED-MSG"},
    min_checks=8,
    budget_s=6.0,
    screenshots=("table-required",),
)
def run(ctx: E2EContext) -> None:
    project = ctx.new_project("required")

    builder = ctx.open_table_builder(project, "clienti", create=True)
    ctx.table_row(builder, 0, name="codice", type=T.TEXT, required=True)
    ctx.table_row(builder, 1, name="email", type=T.TEXT, required_if="[attivo] = .T.")
    ctx.save(builder)

    project = ctx.reopen(project)               # round-trip obbligatorio
    table = project.require_table("clienti")
    ctx.check(table.field("codice").required, "obbligatorietà persistita")
    ctx.check(table.field("email").required_if, "condizione persistita")

    with ctx.expect_error(RowsetError, "Obbligatorio"):
        Rowset(project.db, table).insert({"codice": ""})

    ctx.capture(ctx.main_window(), "table-required")
```

Regole vincolanti:

- `min_checks`: il runner fallisce se lo scenario produce meno controlli del dichiarato.
- Ogni controllo ha un nome univoco e un dettaglio utile (valore atteso vs ottenuto).
- Vietato `assert` nudo negli scenari: solo `ctx.check` / `ctx.expect_*`.
- Ogni scenario ≤ ~120 righe; la logica comune sta nelle fixture/helper.
- Ogni scenario chiude i widget in `finally` o via `ctx.track()`.
- Nessuna modifica a `dbx/` dentro lo scenario: i test collaudano, non preparano il terreno.

---

## 8. Inventario dei 133 workflow

Legenda: ID stabili usati anche in `--area`, `--feature`, report e `docs/e2e-coverage.md`.

### A. Fondamenta e progetto (8)

| ID | Workflow |
|---|---|
| A01 | Nuovo progetto vuoto: cartelle, manifest, riapertura |
| A02 | Progetto demo: artefatti, dati, `validate_project` |
| A03 | Impostazioni progetto: titolo, form principale, menu principale, persistenza |
| A04 | Compatibilità progetti 0.1–0.9: caricamento senza migrazione manuale |
| A05 | Salvataggio completo, chiusura, riapertura, dirty flag |
| A06 | Avvio CLI: `--version`, `--demo`, `--theme`, progetto da percorso |
| A07 | Temi Aurora/Silver/Dark: token, canvas, cambio a runtime, persistenza |
| A08 | Progetti recenti e progetto mancante: elenco, apertura, messaggio |

### B. Table Structure e Table Expert (13)

| ID | Workflow |
|---|---|
| B01 | Nuova tabella minima: nome, didascalia, primo campo, salva |
| B02 | Tutti i 9 tipi campo con larghezza/decimali/formato |
| B03 | Attributi campo: didascalia, default, formato, obbligatorietà |
| B04 | Obbligatorietà condizionale con espressione |
| B05 | Regola di validazione con espressione e messaggio |
| B06 | Campi calcolati e funzioni espressione |
| B07 | Auto-enter: default, data inserimento/modifica, incremento record/modifiche |
| B08 | Scelta statica: valori, etichette, vuoto, testo libero, maiuscole |
| B09 | Scelta dinamica da tabella: sorgente, cache, valori storici |
| B10 | Dominio numerico min/max/intervalli, maschere, maiuscole, auto-advance |
| B11 | Indici singoli/composti/univoci e riordino campi |
| B12 | Relazione 1:N e 4 azioni `ON DELETE`; DDL, Save As, migrazione con backup |
| B13 | Table Expert: template, scelta campi, indici, anteprima DDL → tabella normale |

### C. Browse / DataView / validazione (12)

| ID | Workflow |
|---|---|
| C01 | CRUD completo e navigazione primo/precedente/successivo/ultimo |
| C02 | Validazione per cella: evidenziazione, messaggio, rollback |
| C03 | Editor per tipo: testo, numero, data, booleano, memo, scelta |
| C04 | Campi calcolati in sola lettura nella griglia |
| C05 | Find mode: tutti gli operatori su testo, numeri, date |
| C06 | Find mode: AND, OR, “Ometti”, nessun risultato |
| C07 | Sostituisci: ambito record visibili, distinzione maiuscole |
| C08 | Ricerche salvate: salva, applica, elimina, persistenza |
| C09 | Ordinamento, filtro, stato record e conteggio |
| C10 | Larghezza colonne persistente e Editing Options |
| C11 | Nuovo/duplica/elimina record dai comandi e dalla toolbar |
| C12 | Tabella vuota, confini, refresh dopo modifica esterna |

### D. Import/export, Database Designer, manutenzione (12)

| ID | Workflow |
|---|---|
| D01 | Import CSV: rilevamento codifica, delimitatore, intestazione |
| D02 | Mappatura colonne→campi, conversione tipi, campi calcolati |
| D03 | Import con scarti: motivazioni, conteggi, nessuna scrittura parziale |
| D04 | Svuotamento tabella con backup e import |
| D05 | Export CSV: selezione, ordine, formati, calcolati |
| D06 | Database Designer: auto-layout, pan, zoom, export PNG/SVG |
| D07 | Creazione relazione dal canvas, cardinalità, backup |
| D08 | Modifica schema dal diagramma → Table Builder → aggiornamento card |
| D09 | Rinomina tabella con aggiornamento di query/form/report/script/menu |
| D10 | Duplicazione oggetti e tabella con dati |
| D11 | Compattazione con backup e verifica integrità |
| D12 | Riapplica regole di campo: aggiornati, errori, avvisi storici |

### E. Query, QBE, risultati, esperti (15)

| ID | Workflow |
|---|---|
| E01 | Nuova query guidata: tabelle, campi, alias, includi |
| E02 | Join INNER/LEFT suggeriti dalle FK, campi proposti |
| E03 | Tutti i 14 operatori di filtro |
| E04 | Filtri AND/OR con gruppi |
| E05 | Ordinamento multiplo asc/desc |
| E06 | `GROUP BY` e 5 aggregati (COUNT/SUM/AVG/MIN/MAX) |
| E07 | Anteprima SQL parametrizzata e validazione |
| E08 | Salvataggio, riapertura, query invalida rifiutata con messaggio |
| E09 | QBE: query image, includi, tre righe criteri |
| E10 | QBE: example elements `_nome` e `ref` |
| E11 | QBE: `between`, `like`, `null`, `notnull` |
| E12 | QBE: righe OR, gruppo preservato nella scheda Filtri |
| E13 | Query Results: griglia, formati, refresh, conteggio, export CSV |
| E14 | Crosstab: righe, colonne, valore, totali, caso vuoto |
| E15 | Query Expert: join, campi, criteri, ordinamento → query normale |

### F. Form Expert, Designer, Inspector, Runtime (17)

| ID | Workflow |
|---|---|
| F01 | Form Expert assistito: 5 passi, tabella/query, campi, layout, font |
| F02 | Form Expert “vuoto” e varianti layout/font/colori/stile |
| F03 | Form Designer: palette con tutti i 12 tipi controllo |
| F04 | Palette Field: doppio clic/drag, etichetta automatica, binding |
| F05 | Geometria: righelli, griglia 8 px, snap, 8 maniglie, frecce, passo fine |
| F06 | Selezione multipla, clipboard, duplica, elimina, undo/redo |
| F07 | Allinea, distribuisci, porta avanti/indietro |
| F08 | Pagine: aggiungi, rinomina, rimuovi, cambia, persistenza |
| F09 | Inspector: gruppi Font/Geometry/Data/Behavior/Layout, editing immediato |
| F10 | Eventi controllo `onClick`/`onEnter`/`onExit` |
| F11 | Eventi form `onOpen`/`onClose` e metodi `save`/`close` |
| F12 | Runtime: CRUD, navigazione, stato record, messaggi |
| F13 | Runtime: tutti gli 8 pulsanti azione |
| F14 | Vista Lista: ordinamento, filtro, selezione, apertura record |
| F15 | Portale uno-a-molti: collegamento padre/figlio, ordine, filtro |
| F16 | Form su query: colonne calcolate, sola lettura, navigazione |
| F17 | Round-trip form, compatibilità JSON legacy, riapertura in designer |

### G. Report Designer, Preview, Report Expert (13)

| ID | Workflow |
|---|---|
| G01 | Nuovo report da tabella o query, nome, sorgente, filtro |
| G02 | 7 bande: visibilità, ordine, altezze, trascinamento delimitatori |
| G03 | Insert Field: `TABELLA->CAMPO`, anteprima dati, inserimento |
| G04 | Edit Text: testo, font, bordo, allineamento, espressioni |
| G05 | Record Sort Order: aggiunta/rimozione, asc/desc, ordine multiplo |
| G06 | Gruppi header/footer e 5 funzioni totale sulle bande |
| G07 | Grafici barre/linee/torta: categoria, valore, funzione, banda |
| G08 | Toolbar formattazione: font, stile, allineamento, bordi, colore, zoom |
| G09 | Preview: pagina singola/continua, fit-width, pagine, zoom persistente |
| G10 | Stampa mock e PDF multi-pagina |
| G11 | Report su query: colonne, gruppi, totali, filtro, ordinamento |
| G12 | Round-trip report, JSON legacy, riapertura nel designer |
| G13 | Report Expert: layout tabellare/colonnare/riepilogo, gruppi, risultato |

### H. Label Designer e mail merge (5)

| ID | Workflow |
|---|---|
| H01 | 4 preset + personalizzato: griglia, margini, etichette |
| H02 | Modello `[campo]` e `{{espressione}}`, allineamento |
| H03 | Filtro, ordinamento, selezione record |
| H04 | Salto etichette, anteprima multi-foglio, pagine |
| H05 | Stampa/PDF, salvataggio e riapertura |

### I. Program Editor, script e automazione (12)

| ID | Workflow |
|---|---|
| I01 | Sorgente ↔ azioni, numeri riga, sintassi, log |
| I02 | Step Picker: 10 categorie, descrizioni, ricerca, inserimento |
| I03 | Controllo: `if`, `foreach`, `loop`, `exit_loop_if`, `exit_script`, `halt`, `comment` |
| I04 | Tabelle e navigazione: `select_table`, `go_record` |
| I05 | Record: `set_field`, `new`, `duplicate`, `delete`, `commit`, `revert` |
| I06 | Transazioni: `begin`, `commit`, `rollback` |
| I07 | Variabili: `set`, `set_global`, `unset_global`, persistenza |
| I08 | Parametri dichiarati, dialogo esecuzione, validazione |
| I09 | UI: `message`, `status`, `ask`, `confirm`, `custom_dialog`, `beep` |
| I10 | Integrazione: `open_form`, `open_query`, `open_report`, `print_report`, `export_csv` |
| I11 | `sql`, `call`, propagazione errori e log |
| I12 | Round-trip script, compatibilità legacy, eventi form → script |

### J. Shell, Navigator, Command, Menu, Project (16)

| ID | Workflow |
|---|---|
| J01 | Navigator: 12 categorie, conteggi, categorie disabilitate |
| J02 | Navigator: filtro, directory, `[Untitled]`, doppio clic, contesto, refresh |
| J03 | Command Window: HELP/TABELLE/USE/RECORD/CLEAR, espressioni, cronologia |
| J04 | Shell a schede: apri, attiva, chiudi, dirty, chiudi tutte |
| J05 | 8 menu e 48 azioni: presenza, abilitazione, esecuzione sicura |
| J06 | SpeedBar, tooltip, toggle, status bar con Pos/Oggetto/Record/Modalità |
| J07 | Annulla/ripeti/taglia/copia/incolla/elimina tra editor |
| J08 | Zoom avanti/indietro/100% e persistenza |
| J09 | Scorciatoie documentate (`Ctrl+N/O/S/F/H/K/R/W`, `F1`, `F5`, frecce) |
| J10 | Guida rapida, Informazioni, tema e versione |
| J11 | Menu Designer: albero, separatori, 5 azioni, filtro destinazioni |
| J12 | Anteprima menu e runtime: apri form/report, esegui script, esci |
| J13 | Project Editor: albero oggetti, impostazioni, salvataggio |
| J14 | Validazione progetto: riferimenti validi e riferimenti mancanti attesi |
| J15 | Build distribuibile: cartella, zip, contenuto, riapertura |
| J16 | Project Runner: `F5`, form principale, menu principale, chiusura |

### K. Journey realistici, compatibilità, prestazioni (10)

| ID | Workflow |
|---|---|
| K01 | *Nuova applicazione*: tabella → relazione → query → form → report → script → menu → build |
| K02 | *Sportello*: ricerca, modifica, incasso, riepilogo, etichette, report, riavvio |
| K03 | *Import e bonifica*: CSV sporco, normalizzazione, dedup, export, mailing |
| K04 | *Chiusura mensile*: parametri, solleciti su query, PDF, backup, compattazione |
| K05 | Due tabelle 1:N da zero: form con portale, query join, report raggruppato |
| K06 | Sessione lunga + riavvio: tutto persistito, nessuna perdita, dirty coerente |
| K07 | Progetto legacy: apri, modifica, salva, riapri senza migrazione manuale |
| K08 | Prestazioni 10k righe: Browse, filtro, query join/aggregata, report, PDF |
| K09 | Prestazioni UI: form 100 controlli, tabella 50 campi, report 200 controlli |
| K10 | Distribuzione: build in cartella pulita, apertura e uso della copia |

**Totale: 133 workflow.** I 4 `workflow_*` attuali diventano K01–K04 e mantengono l'alias storico.

---

## 9. Ondate e checkpoint

Rispetta il protocollo di `AGENTS.md` (ondate, diario append-only, checkpoint ogni 3 ondate).

| Ondata | Contenuto | Scenari nuovi | Checkpoint |
|---|---|---:|---|
| E1 — Harness 2.0 e fondamenta | package `tools/e2e/`, contesto, helper Qt, catalogo, coverage gate, report v2, migrazione 14 scenari, alias | 0 (14 migrati) | — |
| E2 — Dati e struttura | A01–A08, B01–B13 | 21 | — |
| E3 — Browse, import, ER, manutenzione | C01–C12, D01–D12 | 24 | **A** |
| E4 — Query e form | E01–E15, F01–F17 | 32 | — |
| E5 — Report, etichette, script | G01–G13, H01–H05, I01–I12 | 30 | — |
| E6 — Shell, menu, progetto, journey, qualità | J01–J16, K01–K10, prestazioni, determinismo, documentazione | 26 | **B** |

Alla fine di E3 e E6: fermarsi, eseguire pytest + smoke + harness completo, aggiornare
`DIARIO.md` con `CHECKPOINT A/B` e blocco `RIPRESA`, chiedere all'utente di compattare il contesto.

**Stima onesta:** 133 scenari con ~1.200 controlli sono 8–12 ore di lavoro dell'agente, più review.
Con il protocollo checkpoint coprono 3 sessioni. Se l'utente vuole “tutto oggi”, l'alternativa è
un'unica ondata con checkpoint finale, accettando run più lunghi e nessuna pausa di verifica
intermedia.

---

## 10. Esecuzione

```bash
# Sviluppo di un'area
python tools/e2e_harness.py --area tables --skip-pytest --skip-smoke --no-screenshots

# Feature singola
python tools/e2e_harness.py --feature TB-FIELD-CHOICE-DYNAMIC --skip-pytest --skip-smoke

# Gate completo locale
python tools/e2e_harness.py --skip-pytest --skip-smoke --workers 4 --isolate scenario --require-coverage 100

# Gate completo con pytest e smoke
./tools/run_e2e.sh --workers 4 --isolate scenario

# Determinismo
python tools/e2e_harness.py --skip-pytest --skip-smoke --repeat 3 --workers 4
```

La CI `.github/workflows/ci.yml` passa da `--skip-pytest --skip-smoke` a:
`--workers 4 --isolate scenario --require-coverage 100 --coverage-md docs/e2e-coverage.md`,
pubblica `report.json`, `report.md`, `coverage.md` e gli screenshot come artifact. Job notturno
opzionale con `--repeat 3`.

---

## 11. Report e artefatti

`report.json` v2 aggiunge:

```json
{
  "schema": 2,
  "overall": "pass",
  "summary": {
    "scenarios": 133, "scenarios_passed": 133,
    "checks": 1280, "checks_failed": 0,
    "features_total": 372, "features_covered": 372,
    "screenshots": 61, "duration_s": 240.5
  },
  "areas": [{"id": "tables", "scenarios": 13, "checks": 142, "coverage": 1.0, "p95_s": 4.1}],
  "features": [{"id": "TB-FIELD-TYPE-DATE", "scenario": "tbl-02-types", "status": "pass"}],
  "budgets": [{"scenario": "frm-05-geometry", "budget_s": 15, "actual_s": 8.2, "status": "pass"}],
  "performance": [{"name": "query_join_10k", "value_ms": 180, "budget_ms": 500}],
  "dialogs": [{"scenario": "tbl-12-migrations", "kind": "question", "expected": true}]
}
```

Artefatti in `build/e2e/<timestamp>/`:

- `report.json`, `report.md`, `run.log`, `pytest.log`, `smoke.log`;
- `screenshots/` con almeno uno scatto per ambiente;
- `coverage.md` / `docs/e2e-coverage.md` con matrice feature → scenario → controllo;
- `projects/` solo per gli scenari falliti (debug);
- `baseline-diff.md` con scenari mancanti, controlli calati, tempi oltre budget.

---

## 12. Budget di prestazione

| Misura | Budget | Note |
|---|---:|---|
| Scenario UI pesante (Form/Report Designer) | 20 s | show/grab offscreen |
| Scenario normale | 6 s | CRUD, query, script, import |
| Gate completo, 4 worker | 8 min | esclusi pytest e smoke |
| Gate completo, 1 worker | 20 min | |
| p95 scenari | 10 s | riportato per area |
| Apertura progetto demo | 2 s | |
| Browse 10k righe, primo paint | 1 s | |
| Filtro/ricerca su 10k righe | 500 ms | |
| Query join + GROUP BY 10k righe | 500 ms | |
| Report 1.000 righe, render + PDF | 3 s | |
| Form 100 controlli, paint | 500 ms | |
| Salva + riapri progetto con 10k righe | 2 s | |
| Statement SQL caricamento 100 righe Browse | ≤ 5 | anti N+1 |
| Statement SQL rendering report | ≤ 10 | anti N+1 |
| Crescita memoria, 20 ripetizioni | < 20 MB | tracemalloc |

I budget sono verificati come **fail** solo oltre 3× o timeout; tra 1× e 3× sono warning nel report,
per non rendere la suite ostaggio della macchina. I test prestazionali dedicati (K08/K09) falliscono
oltre il budget dichiarato.

---

## 13. Definition of Done per scenario

Uno scenario è “done” quando:

1. Ha ID, area, titolo e feature dichiarate.
2. Produce almeno `min_checks` controlli nominati.
3. Esercita il percorso UI reale, non solo le API.
4. Fa round-trip di persistenza se produce un artefatto.
5. Verifica gli esiti attesi di validazione senza lasciare stato sporco.
6. Ha screenshot se è una superficie visiva.
7. Chiude tutti i widget e non lascia dialoghi aperti.
8. Rispetta il budget (o il warning è motivato).
9. Le sue feature risultano coperte nel catalogo.
10. Passa in 3 run consecutivi.

---

## 14. Rischi e mitigazioni

| Rischio | Impatto | Mitigazione |
|---|---|---|
| 133 scenari diventano fragili e duplicati | Alto | fixture/helper condivisi, scenario ≤ 120 righe, ID feature stabili, niente pixel-diff |
| Test UI dipendono da coordinate/geometry | Medio | usare `objectName`, segnali e API canvas; pochi drag mirati con QTest |
| Offscreen diverso da desktop reale | Medio | smoke screenshot, non pixel-diff; un job manuale Silver/Dark a checkpoint |
| Run paralleli interferiscono | Medio | processi separati, config/temp per worker, nessuna risorsa globale |
| Tempi variabili | Medio | budget soft, hard 3×, perf test dedicati con warm-up e mediana |
| Un bug reale blocca un'ondata | Medio | fix + controllo di regressione nello stesso commit; se è una decisione di prodotto, aggiornare attesa e diario |
| Catalogo marcisce | Alto | derivazione da costanti/AST + test pytest che rompe su opzioni non mappate |
| Sessione unica troppo lunga | Medio | checkpoint A/B; oppure modalità intensiva concordata |
| Test “verdi ma vuoti” | Alto | `min_checks`, feature + scenario obbligatori, coverage gate, dialoghi attesi |
| Stampa/PDF dipendono dall'ambiente | Basso | mock stampante, verifica PDF > 1 KB e numero pagine |
| PyInstaller assente in CI | Basso | test dello script e del contenuto build, non dell'eseguibile |

---

## 15. Cosa NON fare

- Non gonfiare i controlli con assert duplicati solo per raggiungere il numero.
- Non testare due volte la stessa opzione in scenari diversi senza un motivo (integrazione vs unità).
- Non usare `eval`, sleep o attese arbitraria per far passare i test.
- Non modificare il comportamento dell'app per rendere un test più facile.
- Non dichiarare coperto ciò che è solo istanziato: una finestra aperta non è una feature testata.
- Non inserire screenshot o dati reali dell'utente nel repository.

---

## 16. Decisioni aperte (con raccomandazione)

1. **Numero di scenari:** 133 (raccomandato) oppure taglio a 100 escludendo K05–K10 e alcuni
   doppioni di opzioni. Il taglio riduce la copertura delle prestazioni e dei journey.
2. **Checkpoint:** protocollo standard con Checkpoint A dopo E3 e B dopo E6 (raccomandato), oppure
   un'unica ondata con checkpoint finale.
3. **Fase 2 errori:** confermata fuori scope; dentro solo i rifiuti di validazione previsti.
4. **CI:** gate completo su Linux/Python 3.12 a ogni push (raccomandato) e job notturno con
   `--repeat 3`; gli altri OS restano su pytest + smoke.

---

## 17. Primo passo esatto (E1)

1. Creare `PLAN-E2E.md` nel repository con questo piano e un rimando in `PLAN.md`.
2. Scrivere la voce di diario `2026-11-26 — E2E 2.0 — E1 Harness e catalogo` con stato `in corso`.
3. Estrarre `tools/e2e/context.py`, `ui.py`, `checks.py`, `registry.py`, `reporting.py` dal codice
   attuale, senza cambiare il comportamento dei 14 scenari.
4. Aggiungere `catalog.py` + `coverage.py` + `tests/test_e2e_catalog.py` con la derivazione da
   costanti e AST e le esclusioni motivate.
5. Aggiungere gli alias dei 14 nomi storici e verificare che `tests/test_e2e_harness.py` passi
   invariato.
6. Eseguire il gate completo: pytest, smoke, harness, `--require-coverage`.
7. Solo se tutto è verde, chiudere E1 e aprire E2 (A/B).
