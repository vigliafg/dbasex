# Collaudo 0.10.0 — Validazione dei campi e collaudo E2E 2.0

Data: 2026-11-27

La release 0.10.0 porta nel prodotto l'estensione **validazione dei campi** e chiude la campagna
**E2E 2.0**. Non introduce finestre nuove: consolida regole e strumenti già presenti e li copre con
un gate end-to-end. I progetti 0.9 si aprono senza migrazione.

## Gate di release

| Verifica | Comando | Esito |
|---|---|---|
| Versione, changelog, note e tag | `python tools/release_check.py --tag v0.10.0` | ok |
| CLI | `python -m dbx --version` | `DBX 0.10.0` |
| Suite completa | `python -m pytest` | 584 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK |
| Harness E2E con copertura fase 3 | `python tools/e2e_harness.py --require-coverage --coverage-phase 3` | PASS · 147/147 scenari · 1.611/1.611 controlli · 505/505 feature |
| Rendering Aurora | `python tools/capture_ui.py` | OK, serie `01`–`37` |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK, Aurora ripristinata dopo la cattura |
| Dry run di release su tre piattaforme | `gh workflow run release.yml --ref main -f tag=v0.10.0 -f dry_run=true` | success: gate, sdist/wheel, bundle Linux/Windows/macOS |

Il dry run (run `45962616155`) ha costruito e caricato come artifact il pacchetto Python e i tre
bundle, senza pubblicare la release. La matrice `CI` resta invece rossa su `windows-latest` per un
`KeyboardInterrupt` intermittente durante `sqlite3.Connection.close()`, pre-esistente e indipendente
dalle modifiche 0.10.0: il bundle Windows si costruisce correttamente. Dettagli e rimando in
[`docs/release-readiness.md`](release-readiness.md).

## Pubblicazione

Il tag annotato `v0.10.0` ha avviato il run `45968324760`: gate, `sdist` + wheel, bundle Linux,
Windows e macOS e pubblicazione tutti verdi. La GitHub Release è disponibile su
<https://github.com/vigliafg/dbasex/releases/tag/v0.10.0> con cinque artefatti più `SHA256SUMS`.
Il checksum iniziale includeva per errore il proprio hash vuoto; il workflow è stato corretto e
l'asset rigenerato. Wheel e sdist sono stati verificati con `sha256sum -c` dopo il download.

Test dedicati alla release:

- `tests/test_release.py`: versione allineata tra `pyproject.toml` e pacchetto, sezione del changelog,
  note di rilascio presenti, accettazione del tag corretto e rifiuto di un tag sbagliato.
- `tests/test_validation.py` e `tests/test_ui_validation.py`: modello, `Rowset`, migrazioni e
  comportamento della UI di validazione.
- `tests/test_e2e_catalog.py`: coerenza catalogo → scenari e gate di copertura.

## Validazione dei campi

| Area | Copertura |
|---|---|
| Issue strutturate | `ValidationIssue`, `ValidationError`, severità e codice per la UI |
| Validazione per cella | `validate_field`, `Rowset.update(only=)` con rollback della sola cella |
| Obbligatorietà | semplice, condizionale (`required_expr`), `skip_expr`, `rule_message` |
| Campo Scelta | statica, dinamica `tabella.colonna`, etichette, cache, testo libero, migrazione `lookup` |
| Dominio numerico | minimo/massimo e intervalli, estremi aperti, messaggio dedicato |
| Maschere | `9`/`A`/`a`/spazio, normalizzazione maiuscole/minuscole/titolo/frase, auto-advance |
| Incremento | `records` e `updates`, migrazione da `auto_serial` |
| Manutenzione | `Riapplica regole di campo`, avvisi `choice_stale`/`domain_stale` |
| Import | CSV a scarti con riga e motivo del rifiuto |

## Collaudo E2E 2.0

- **147 scenari** (14 storici + 133 granulari) e **1.611 controlli** nominati.
- **505/505 feature** del catalogo coperte, con gate `--require-coverage --coverage-phase 3`.
- **60 screenshot** E2E e rendering canonici `01`–`37`.
- Journey realistici: nuova applicazione, sportello, import e bonifica, chiusura mensile, relazione
  1:N, riavvio, progetto legacy, 10.000 righe, form 100 controlli / tabella 50 campi / report 200
  controlli, distribuzione su copia.
- Difetti reali corretti durante il collaudo: default in inserimento, navigazione su tabella vuota,
  `COUNT(*)` nel Query Designer, stile dei campi nel Form Expert, Browse Field Data, pluralizzazione
  delle pagine, scorciatoie standard, zoom nei dialoghi, build con WAL.

## Rendering aggiornati

I rendering che mostrano la versione nella barra di stato o nel titolo sono stati rigenerati:
`01-desktop.png`, `02-navigator.png`, `04-table-structure.png`, `10-desktop-tabs.png`,
`13-project-editor.png`, `26-import-csv.png`, `27-table-calculated.png` e
`28-browse-calculated.png`. La serie resta `01`–`37`.

## Verifiche manuali ancora richieste

Non automatizzabili nel repository; vanno eseguite sulla macchina di destinazione prima di
considerare la release distribuita:

- [ ] Aprire, modificare, salvare e riaprire un progetto reale.
- [ ] Stampare su una stampante fisica un report e un foglio di etichette.
- [ ] Creare una build distribuibile e riaprire la copia.
- [ ] Verificare file chooser, stampante e cartelle native su Windows e macOS.
- [ ] Verificare HiDPI 125% e 150% e le risoluzioni 1280×720 e 1920×1080.
- [ ] Provare i bundle non firmati su Windows (SmartScreen) e macOS (Gatekeeper).

Checklist completa e criteri go/no-go in [`docs/release-readiness.md`](release-readiness.md).

## Limiti accettati

- La fase 2 del collaudo (usi errati, dati corrotti, concorrenza) resta un piano separato.
- I bundle Windows e macOS non sono firmati né notarizzati.
- Restano i limiti delle release precedenti: query statiche, portali senza azioni per riga, grafici
  non interattivi, etichette senza barcode/QR o immagini, script senza breakpoint.
