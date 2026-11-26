# Handoff — dBX, 26 novembre 2026

## Stato della sessione

- **Branch:** `main`
- **Ultimo commit:** `a831634` — E2E: chiude il Checkpoint B con diario e rendering
- **Push:** completato su `origin/main`
- **Working tree:** pulito
- **Checkpoint:** **B raggiunto**; campagna E2E 2.0 conclusa.

### Numeri finali

| Metrica | Risultato |
|---|---:|
| Workflow granulari | **133/133** |
| Scenari harness totali | **147/147** (14 storici + 133 nuovi) |
| Controlli nominati | **1.611/1.611** |
| Feature del catalogo | **505/505 (100%)** |
| pytest | **579 passed** |
| Smoke headless | **SMOKE OK** |
| Determinismo | **3 run consecutivi identici** |
| Screenshot E2E | **60** |
| Durata harness completo | **189,1 s** |

---

## Cosa abbiamo fatto oggi

### E1–E3 — Harness e fondamenta (Checkpoint A)

- Creato `tools/e2e/`: contesto esteso, fixture deterministiche, helper Qt, catalogo delle funzioni,
  gate di copertura, filtri `--area`/`--feature`, controllo `min_checks`.
- Coperti progetto, Table Builder, tutti i tipi campo, indici, relazioni, migrazioni, Browse,
  validazione, Find/Replace, ricerche salvate, import/export CSV, Database Designer e manutenzione.
- Aggiunti `PLAN-E2E.md`, `docs/e2e-coverage.md`, `tests/test_e2e_catalog.py`.

### E4 — Query e form (32 workflow)

- Query guidata, join INNER/LEFT suggeriti dalle FK, tutti i 14 operatori, gruppi AND/OR,
  ordinamento multiplo, `GROUP BY` con cinque aggregati, SQL parametrizzato, salvataggio/rinomina.
- QBE: query image, includi, tre righe criteri, example element, `between`, `like`, vuoti, righe OR.
- Query Results, export CSV, Crosstab con totali e casi limite, Query Expert.
- Form Expert a cinque passi e varianti, palette con 12 controlli, Palette Field, geometria,
  clipboard/undo/redo, allineamento, pagine, Inspector, eventi, runtime, otto pulsanti, Vista Lista,
  portale, form su query, round-trip e JSON legacy.

### E5 — Report, etichette e script (30 workflow)

- Report Designer: sette bande, Insert Field, Edit Text, espressioni, ordinamento, gruppi,
  cinque totali, grafici barre/linee/torta, formattazione, anteprima multi-pagina, stampa, PDF,
  report su query, round-trip e Report Expert.
- Etichette: quattro preset, formato personalizzato, modello `[campo]`/`{{espressione}}`, filtro,
  ordinamento, salto etichette, anteprima multi-foglio, PDF e persistenza.
- Program Editor: tutte le 34 azioni MiniScript, Step Picker, parametri, transazioni, variabili
  globali, SQL/call, integrazione con form/query/report e script da evento form.

### E6 — Shell, progetto, journey e qualità (26 workflow)

- Navigator, Command Window, schede, otto menu, SpeedBar/status bar, clipboard tra editor, zoom,
  scorciatoie, guida/tema/versione, Menu Designer e runtime, Project Editor, validazione, build e
  Project Runner.
- Journey: nuova applicazione, sportello, import/bonifica, chiusura mensile, 1:N, riavvio, legacy,
  10.000 righe, form 100 controlli/tabella 50 campi/report 200 controlli, distribuzione su copia.

### Difetti reali trovati e corretti (9)

| # | Difetto | Correzione |
|---:|---|---|
| 1 | Default dei campi persi in `Rowset.insert` | default applicato quando il campo è assente |
| 2 | Pulsanti di navigazione attivi su tabella vuota | stato aggiornato anche con zero record |
| 3 | `COUNT(*)` nel Query Designer perdeva la tabella | tabella dell'aggregato conservata |
| 4 | Form Expert non applicava font/stile ai campi | stile passato anche ai controlli |
| 5 | “Browse Field Data” sempre vuoto | accesso corretto a `sqlite3.Row` |
| 6 | Anteprima con “2 paginae” | pluralizzazione “pagina/pagine” |
| 7 | Scorciatoie standard shell non registrate | conversione a `QKeySequence`; `Ctrl+W` esplicito |
| 8 | Zoom/stampa/allinea non raggiungevano i dialoghi in scheda | unwrap `DialogEditor` |
| 9 | Build con WAL poteva produrre DB vuoto | backup SQLite invece di copia file |

### Documentazione aggiornata

- `PLAN-E2E.md`, `PLAN.md`, `DIARIO.md` (con `CHECKPOINT B` e `RIPRESA`).
- `docs/e2e.md`, `docs/e2e-coverage.md`, `README.md`, `CHANGELOG.md`.
- Rendering canonici `01`–`37` rigenerati.

---

## Cosa dobbiamo fare domani

### P0 — Gate di lancio (prima di distribuire)

- [ ] Eseguire su **macchina di destinazione**:
  - `python -m pytest`
  - `QT_QPA_PLATFORM=offscreen python -m dbx --smoke`
  - `python tools/e2e_harness.py --require-coverage --coverage-phase 3`
- [ ] Smoke manuale con un progetto reale:
  - aprire, modificare e salvare un record;
  - chiudere e riaprire il progetto;
  - query, form, report, etichette, script e runner;
  - esportare PDF di report ed etichette;
  - provare la stampa fisica su almeno una stampante;
  - creare una build e riaprire la copia distribuita.
- [ ] Backup dei progetti reali prima della prima apertura.
- [ ] Verificare tema `silver` e `dark` sulle schermate reali.

### P1 — Piattaforme e packaging

- [ ] Provare build/packaging su Windows e macOS, non solo Linux.
- [ ] Verificare dialoghi nativi: file chooser, stampante, cartelle.
- [ ] Verificare HiDPI e risoluzioni 1280×720 / 1920×1080.
- [ ] Decidere se PyInstaller è requisito di release o optional.

### P2 — Fase 2 del collaudo (errori e robustezza)

- [ ] Input errati dell'utente su ogni editor.
- [ ] Dialoghi annullati e operazioni interrotte.
- [ ] JSON/artefatti corrotti e riferimenti mancanti.
- [ ] Violazioni FK, duplicati, cancellazioni con dipendenze.
- [ ] Concorrenza e apertura doppia del progetto.
- [ ] Crash/recovery e integrità dopo interruzioni.

### P3 — Miglioramenti opzionali

- [ ] Instrumentazione runtime delle feature (oltre la dichiarazione negli scenari).
- [ ] `--workers` e `--repeat` per il harness.
- [ ] Soak test e memoria oltre 10.000 righe.
- [ ] Accessibilità e regressione visiva delle schermate.
- [ ] Documento `docs/release-readiness.md` con checklist e criteri go/no-go.

---

## Comandi utili

```bash
# Suite e smoke
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke

# Harness completo con gate di copertura
QT_QPA_PLATFORM=offscreen DBX_CONFIG_DIR=/tmp/opencode/dbx-e2e-config \
  python tools/e2e_harness.py --require-coverage --coverage-phase 3

# Solo un'area
python tools/e2e_harness.py --area queries --skip-pytest --skip-smoke

# Rigenerare la matrice di copertura
python tools/e2e_coverage.py

# Rigenerare i rendering canonici
QT_QPA_PLATFORM=offscreen python tools/capture_ui.py
```

---

## File chiave

- `PLAN-E2E.md` — piano dei 133 workflow e criteri di accettazione.
- `DIARIO.md` — cronologia E1–E6, `CHECKPOINT B`, `RIPRESA`.
- `docs/e2e-coverage.md` — matrice feature → scenario.
- `docs/e2e.md` — uso e architettura del harness.
- `tools/e2e/` — contesto, fixture, catalogo, registry e scenari `s00`–`s90`.
- `tools/e2e_harness.py` — runner.
- `tests/test_e2e_catalog.py` — gate di coerenza e copertura.
- `CHANGELOG.md` — difetti corretti e novità E2E 2.0.

---

## Ripresa della prossima sessione

1. Leggere questo handoff, `DIARIO.md` (ultima voce e `CHECKPOINT B`) e `PLAN-E2E.md`.
2. Controllare `git status` e `git log --oneline -5`.
3. **Non ripetere E1–E6**: la baseline è verde.
4. Partire dal **P0 — Gate di lancio** e chiedere all'utente:
   - quale piattaforma è il target di lancio;
   - se la stampa fisica è requisito;
   - se autorizza la fase 2 (errori/robustezza) prima del rilascio.

**Definition of done per domani:** gate P0 verde su macchina target, checklist manuale completata,
eventuali problemi P1 registrati nel diario e decisione esplicita su fase 2 e packaging.
