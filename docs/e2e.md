# Harness end-to-end dBX

`tools/e2e_harness.py` è il collaudo automatico completo di dBX. Esegue in sequenza:

1. la **suite pytest** completa;
2. lo **smoke headless** (`python -m dbx --smoke`);
3. dieci **scenari E2E** funzionali e quattro **workflow realistici** su progetti temporanei
   isolati, con interfaccia Qt offscreen.

Non usa pytest per gli scenari: ogni controllo ha un nome, un esito e un tempo, e il risultato
finale è disponibile in JSON e Markdown. I dialoghi modali sono neutralizzati, quindi il harness non
può bloccarsi in attesa di un clic.

## Avvio rapido

```bash
./tools/run_e2e.sh
# equivalente a
python tools/e2e_harness.py
```

Al termine stampa una riga come:

```text
ESITO: PASS · scenari 14/14 · controlli 298/298 · screenshot 32
Report: build/e2e/20261123-090000/report.json
```

Il percorso esatto è sempre scritto anche in `build/e2e/latest.txt`.

Per una singola area:

```bash
python tools/e2e_harness.py --only ui_designers
python tools/e2e_harness.py --only project_tables,queries_crosstab --no-screenshots
```

## Scenari

| Nome | Copertura |
|---|---|
| `environment` | Versioni, import dei moduli, CLI, progetto demo e validazione |
| `project_tables` | Tipi, indici, chiavi esterne, calcolati, auto-enter, CRUD, Browse |
| `search_csv` | Find mode AND/OR/Ometti, sostituzione, ricerche salvate, import/export CSV |
| `queries_crosstab` | Join, filtri, `GROUP BY`, aggregati, QBE, Query Results, Crosstab |
| `forms_runtime` | Navigazione, CRUD, eventi, vista Lista, portale, form su query |
| `reports_labels` | Report a bande, totali, grafici, PDF, anteprima, etichette e mail merge |
| `scripts_automation` | Azioni core, parametri, variabili globali, transazioni, Program Editor |
| `maintenance` | Backup, rinomina con riferimenti, duplicazione, integrità, compattazione |
| `ui_designers` | Shell a schede, Navigator, tutti i designer, esperti, temi Aurora/Silver/Dark |
| `runner_build` | Menu runtime, Project Runner, validazione, build ZIP e riapertura |

### Workflow realistici

I quattro scenari `workflow_*` non collaudano una singola area: percorrono una giornata di lavoro
completa, con stato che passa dall'interfaccia alla persistenza e sopravvive a un riavvio del
progetto. Ogni workflow usa le stesse superfici dell'utente (Browse, form runtime, designer,
import wizard, Project Runner, report preview) e verifica il risultato nel database e nei file
prodotti.

| Nome | Racconto e copertura |
|---|---|
| `workflow_nuova_applicazione` | Un consulente parte da un progetto vuoto, inserisce clienti e fatture dal Browse, crea query, form, report, etichette, menu e script, collauda la shell e il runtime, esporta la build ZIP e riapre la copia distribuita |
| `workflow_sportello` | Una giornata allo sportello: ricerca per città, riattivazione di un cliente, registrazione e incasso di una fattura direttamente dalla griglia, riepilogo di fine giornata, etichette e report, con verifica dopo il riavvio |
| `workflow_import_bonifica` | Import di un CSV sporco con mappatura automatica, normalizzazione delle città, eliminazione di inattivi e duplicati, ricerca salvata «senza email», export del file pulito, mailing e report |
| `workflow_chiusura_mensile` | Chiusura mensile lanciata dal menu runtime con parametro data, registrazione delle chiusure, solleciti su query con join, PDF, etichette, backup, compattazione e riapertura |

Per eseguirli da soli:

```bash
python tools/e2e_harness.py --only workflow_sportello
python tools/e2e_harness.py --only workflow_nuova_applicazione,workflow_chiusura_mensile --no-screenshots
```

## Opzioni

| Opzione | Significato |
|---|---|
| `--output DIR` | Cartella risultati (default `build/e2e/<timestamp>`) |
| `--only a,b` | Esegue solo gli scenari indicati |
| `--skip-pytest` | Salta la suite pytest |
| `--skip-smoke` | Salta lo smoke headless |
| `--no-screenshots` | Non salva le schermate |
| `--keep` | Conserva i progetti temporanei anche se lo scenario passa |
| `--fail-fast` | Ferma al primo scenario fallito |
| `--timeout N` | Timeout per scenario in secondi (default 240; `0` disabilita) |
| `--pytest-args "..."` | Argomenti extra per pytest |
| `--platform offscreen` | Plugin Qt; cambiarlo solo per debug grafico |
| `--quiet` / `--verbose` | Console ridotta / ogni controllo stampato |
| `--list` | Elenca gli scenari ed esce |

I progetti temporanei sono creati in una cartella `dbx-e2e-*` e cancellati alla fine. In caso di
fallimento vengono conservati per il debug, salvo `--keep` esplicito per conservarli sempre.

## Artefatti

```text
build/e2e/<timestamp>/
├── report.json          # esito macchina-leggibile, controlli e traceback
├── report.md            # rapporto leggibile
├── run.log              # log completo del harness
├── pytest.log           # stdout/stderr della suite pytest
├── pytest-junit.xml     # JUnit per CI o strumenti esterni
├── smoke.log            # output dello smoke
├── config/              # DBX_CONFIG_DIR isolata
└── screenshots/         # e2e-main-window.png, e2e-report-preview.png, ...
```

`report.json` contiene anche commit Git, branch, file modificati, versioni di Python/Qt/dBX e i
tempi di ogni stage. Un fallimento riporta il controllo preciso e il traceback.

## Codici di uscita

| Codice | Significato |
|---|---|
| `0` | Tutti gli stage e tutti gli scenari sono passati |
| `1` | Almeno uno stage o scenario è fallito |
| `2` | Errore d'uso, argomenti non validi o avvio Qt impossibile |

## Esecuzione programmata

Per lanciarlo domani in modo non interattivo:

```bash
mkdir -p build/e2e
nohup ./tools/run_e2e.sh --output build/e2e/$(date +%Y%m%d-%H%M%S) \
  > build/e2e/console.log 2>&1 &
```

Il log console non è indispensabile: `run.log` e `report.md` nella cartella di output contengono
tutto. Su Linux il harness applica anche un timeout per scenario.

## Integrazione continua

La CI GitHub Actions esegue il harness su Linux/Python 3.12 dopo pytest, smoke e screenshot:

```bash
python tools/e2e_harness.py --skip-pytest --skip-smoke --output build/e2e-ci
```

La cartella `build/e2e-ci` viene pubblicata come artifact. La suite pytest include
`tests/test_e2e_harness.py`, che verifica `--list` e uno scenario minimo isolato.

## Aggiungere uno scenario

In `tools/e2e_scenarios.py`:

1. scrivere `def scenario_nome(ctx: HarnessContext) -> None:`;
2. usare `ctx.new_project()` o `ctx.demo_project()`;
3. verificare con `ctx.check(condizione, "descrizione", "dettaglio opzionale")`;
4. salvare schermate con `ctx.capture(widget, "nome-file", (larghezza, altezza))`;
5. aggiungere `ScenarioDefinition("nome", "Titolo", scenario_nome)` a `SCENARIOS`.

Il contesto chiude i progetti e cancella i file temporanei anche in caso di eccezione. Un
controllo fallito solleva `ScenarioFailure`; il runner registra il punto esatto e prosegue con gli
altri scenari, salvo `--fail-fast`.

## Note e limiti

- Il harness è pensato per l'ambiente **offscreen**: non apre finestre visibili e non richiede uno
  schermo.
- Non modifica il progetto dell'utente: usa solo copie temporanee del progetto demo o progetti nuovi.
- Salva screenshot in `build/e2e/...`, non in `docs/reference/`; la galleria canonica resta gestita
  da `tools/capture_ui.py`.
- I dialoghi di conferma, avviso e input sono neutralizzati. Se un test ha bisogno di una risposta
  diversa, usa `unittest.mock.patch` all'interno dello scenario.
- I tempi dipendono dalla macchina; il report riporta la durata reale di ogni stage e scenario.
- Su Windows il timeout per scenario non usa `SIGALRM`: il limite vale per i sottoprocessi pytest e
  smoke, non per i singoli scenari.
