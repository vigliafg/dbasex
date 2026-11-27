# Handoff — dBX, 27 novembre 2026

## Stato della sessione

- **Branch:** `main`
- **Versione:** `0.10.0` (`pyproject.toml` e `dbx/__init__.py` allineati)
- **Working tree:** pulito; tag `v0.10.0` su `e9b1a55`, release pubblicata
- **Release:** <https://github.com/vigliafg/dbasex/releases/tag/v0.10.0>
- **Checkpoint:** **B E2E raggiunto**, campagna conclusa e release 0.10.0 distribuita su Linux,
  Windows e macOS.
- **Gate automatico:** verde su Linux e dry run verde su tre piattaforme; run di release
  `45968324760` verde. La CI Windows resta intermittente (difetto pre-esistente); le verifiche
  manuali di `docs/release-readiness.md` restano da spuntare sulla macchina di destinazione.

### Numeri finali

| Metrica | Risultato |
|---|---:|
| pytest | **584 passed** |
| Smoke headless | **SMOKE OK** |
| Scenari E2E | **147/147** |
| Controlli E2E | **1.611/1.611** |
| Feature coperte | **505/505 (100%)** |
| Screenshot E2E | **60** |
| Rendering canonici | **01–37**, Aurora + Dark |
| Dry run di release | **verde** su Linux, Windows e macOS (run `45962616155`) |
| `release_check.py --tag v0.10.0` | verde |

---

## Cosa abbiamo completato oggi

### P0 — Gate di lancio

- [x] `python -m pytest` → 584 passed.
- [x] `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` → SMOKE OK.
- [x] `python tools/e2e_harness.py --require-coverage --coverage-phase 3` → PASS 147/147,
  1.611 controlli, 505/505 feature.
- [x] `python tools/capture_ui.py` e `--theme dark` → rendering `01`–`37` rigenerati, Aurora
  ripristinata.
- [x] `python -m dbx --version` → `DBX 0.10.0`.
- [x] Dry run del workflow `Release`: gate, `sdist`/wheel e tre bundle verdi.
- [ ] Stampa fisica e dialoghi nativi Windows/macOS: richiedono la macchina di destinazione.

### P1 — Piattaforme e packaging

- [x] Deciso il modello di distribuzione: wheel/sdist come percorso primario, bundle PyInstaller
  per Linux x86_64, Windows x86_64 e macOS arm64.
- [x] Aggiunto `.github/workflows/release.yml`: gate, `sdist` + wheel, tre bundle, `SHA256SUMS`,
  GitHub Release sul tag `v*`; input `dry_run` per provare le build senza pubblicare.
- [x] Dry run verde: pacchetto Python e bundle Linux, Windows e macOS costruiti e caricati.
- [x] PyInstaller reso requisito solo della CI tramite l'extra `.[release]`.
- [x] Documentati gli avvisi dei bundle non firmati (SmartScreen e Gatekeeper).
- [ ] Verificare file chooser, stampante e cartelle native su Windows e macOS reali.
- [ ] CI Windows: `KeyboardInterrupt` intermittente durante `sqlite3.Connection.close()`,
  pre-esistente dal 2026-11-25; il bundle Windows si costruisce. Da stabilizzare in una sessione
  dedicata, senza mascherare l'eccezione nel motore.

### P2 — Fase 2 del collaudo

- Decisione registrata: resta un piano separato, **non bloccante** per la 0.10.0.

### P3 — Documentazione

- [x] `docs/release-readiness.md` con criteri go/no-go, decisioni e procedura di taglio.
- [x] `docs/qa-0.10.md` con gate, copertura e verifiche manuali residue.
- [x] `docs/release-0.10.0.md` come note pubbliche della release.
- [x] `CHANGELOG.md`, `README.md`, `PLAN.md`, `PLAN-E2E.md`, `docs/ui-parity.md` aggiornati.

---

## Procedura di taglio

```bash
# Gate locale (già verde)
python tools/release_check.py --tag v0.10.0
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke

# Prova delle build su tutti i runner senza pubblicare (già verde il 2026-11-27)
gh workflow run release.yml --ref main -f tag=v0.10.0 -f dry_run=true
gh run watch

# Commit e push
git add -A
git commit -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin main

# Tag annotato: avvia la pubblicazione
git tag -a v0.10.0 -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin v0.10.0

# Verifica
gh release view v0.10.0
gh run list --workflow release.yml --limit 3
```

La procedura qui sopra è quella usata per la 0.10.0 ed è già stata eseguita: il tag `v0.10.0`
esiste e la release è pubblicata. Usarla come riferimento per il prossimo taglio.

La release pubblica:

- `dbx-0.10.0-py3-none-any.whl` e `dbx-0.10.0.tar.gz`;
- `dbx-0.10.0-linux-x86_64.tar.gz`;
- `dbx-0.10.0-windows-x86_64.zip`;
- `dbx-0.10.0-macos-arm64.tar.gz`;
- `SHA256SUMS`.

---

## Verifiche manuali residue

Elencate in `docs/release-readiness.md`:

1. Progetto reale: aprire, modificare, salvare, chiudere e riaprire.
2. Query, form, report, etichette, script e Project Runner.
3. PDF di report ed etichette e stampa fisica.
4. Build distribuibile e riapertura della copia.
5. File chooser, stampante e cartelle native su Windows/macOS.
6. HiDPI 125%/150%, 1280×720 e 1920×1080.
7. Apertura dei bundle non firmati su Windows e macOS.
8. Backup dei progetti reali prima della prima apertura con la 0.10.0.

---

## File chiave

- `docs/release-readiness.md` — criteri go/no-go e procedura.
- `docs/qa-0.10.md` — collaudo della release.
- `docs/release-0.10.0.md` — note pubbliche.
- `.github/workflows/release.yml` — build e pubblicazione multipiattaforma.
- `tools/release_check.py` — coerenza versione/tag/changelog/note.
- `CHANGELOG.md` — sezione `[0.10.0] — 2026-11-27`.
- `DIARIO.md` — voce del 2026-11-27.
- `PLAN-E2E.md` e `docs/e2e-coverage.md` — baseline E2E verde.

---

## Ripresa

1. Leggere questo handoff, la voce `2026-11-27` del diario e `docs/release-readiness.md`.
2. Controllare `git status`, `git log --oneline -5` e il tag `v0.10.0`.
3. La release 0.10.0 è già pubblicata: non ripetere taglio e pubblicazione.
4. Prossime attività possibili: stabilizzare la CI Windows intermittente, spuntare le verifiche
   manuali di `docs/release-readiness.md`, oppure aprire un nuovo piano.
5. Non riaprire E1–E6 né le fasi 0–7 della validazione: sono baseline verde.
6. La fase 2 (usi errati, dati corrotti, concorrenza) richiede un piano separato.
