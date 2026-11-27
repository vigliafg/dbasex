# Release readiness — dBX 0.10.0

Checklist go/no-go per la release 0.10.0. Aggiornata il 2026-11-27.

## Criteri bloccanti

| # | Criterio | Comando / verifica | Esito |
|---:|---|---|---|
| 1 | Versione coerente tra `pyproject.toml`, pacchetto, changelog, note e tag | `python tools/release_check.py --tag v0.10.0` | verde (tag `v0.10.0`) |
| 2 | Suite completa verde | `python -m pytest` | verde |
| 3 | Smoke headless verde | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | verde |
| 4 | Harness E2E completo con gate di copertura fase 3 | `python tools/e2e_harness.py --require-coverage --coverage-phase 3` | verde |
| 5 | Rendering canonici rigenerati | `python tools/capture_ui.py` | verde |
| 6 | CI pytest + smoke su Linux, Windows e macOS | workflow `CI` | Linux/macOS verdi; Windows intermittente (vedi sotto) |
| 7 | Pacchetto Python `sdist` + wheel | workflow `Release`, job `sdist` | verde in dry run |
| 8 | Bundle autonomi Linux, Windows e macOS | workflow `Release`, job `standalone` | verde in dry run |
| 9 | Release GitHub con note, artefatti e `SHA256SUMS` | workflow `Release`, job `publish` | verde: release `v0.10.0` pubblicata con 6 asset |

## Esito dry run multipiattaforma (2026-11-27)

Run GitHub Actions `45962616155` (`workflow_dispatch`, `dry_run=true`), concluso con successo:

| Job | Esito |
|---|---|
| Gate di release (pytest, smoke, harness E2E) | success |
| Pacchetto Python (`sdist` + wheel) | success |
| Eseguibile Linux x86_64 | success |
| Eseguibile Windows x86_64 | success |
| Eseguibile macOS arm64 | success |
| Pubblica la release | skipped (dry run) |

**Nota Windows:** la matrice `CI` su `windows-latest` fallisce in modo intermittente con un
`KeyboardInterrupt` durante `sqlite3.Connection.close()`, a circa 20 secondi dall'avvio e in test
diversi. Il difetto è pre-esistente (presente dal 2026-11-25, anche su commit precedenti) e non
dipende dalle modifiche 0.10.0: lo stesso bundle Windows viene costruito con successo. L'indagine è
registrata nel diario; la release non è bloccata dai bundle, ma la CI Windows va stabilizzata in una
sessione dedicata.

## Pubblicazione (2026-11-27)

Run `45968324760`, avviato dal tag `v0.10.0`: gate, pacchetto Python, tre bundle e pubblicazione
tutti verdi. Release:

<https://github.com/vigliafg/dbasex/releases/tag/v0.10.0>

Asset pubblicati:

- `dbx-0.10.0-py3-none-any.whl`
- `dbx-0.10.0.tar.gz`
- `dbx-0.10.0-linux-x86_64.tar.gz`
- `dbx-0.10.0-windows-x86_64.zip`
- `dbx-0.10.0-macos-arm64.tar.gz`
- `SHA256SUMS`

Il primo `SHA256SUMS` conteneva per errore anche il proprio hash vuoto; il workflow è stato corretto
(`! -name SHA256SUMS`) e l'asset della release è stato rigenerato senza la riga spuria. Verificati
con `sha256sum -c` wheel e sdist scaricati dalla release.

## Verifiche manuali sulla macchina di destinazione

Queste voci non sono automatizzabili nel repository e vanno spuntate prima di considerare la
release “distribuita”:

- [ ] Aprire un progetto reale, modificare e salvare un record, chiudere e riaprire il progetto.
- [ ] Provare query, form, report, etichette, script e Project Runner.
- [ ] Esportare PDF di un report e di un foglio di etichette.
- [ ] Stampare su almeno una stampante fisica.
- [ ] Creare una build distribuibile e riaprire la copia prodotta.
- [ ] Verificare tema Aurora, Silver e Dark.
- [ ] Verificare file chooser, stampante e cartelle native su Windows e macOS.
- [ ] Verificare HiDPI a 125% e 150% e le risoluzioni 1280×720 e 1920×1080.
- [ ] Backup dei progetti reali prima della prima apertura con la 0.10.0.

## Decisioni

| Decisione | Scelta |
|---|---|
| Piattaforme di release | Linux x86_64, Windows x86_64, macOS arm64; wheel/sdist universali |
| Packaging | `sdist` + wheel come percorso primario; bundle PyInstaller come artefatto di release |
| PyInstaller | Richiesto solo nel workflow di release (`.[release]`), non a runtime |
| Firma codice | Fuori scope 0.10.0: i bundle Windows/macOS non sono firmati né notarizzati |
| Fase 2 del collaudo (usi errati, dati corrotti, concorrenza) | Piano separato, non bloccante per la 0.10.0 |
| Pubblicazione | GitHub Release creata dal workflow sul tag `v*`, con artefatti e checksum |

## Procedura di taglio

```bash
# 1. Gate locale
python tools/release_check.py --tag v0.10.0
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
QT_QPA_PLATFORM=offscreen DBX_CONFIG_DIR=/tmp/opencode/dbx-e2e-config \
  python tools/e2e_harness.py --require-coverage --coverage-phase 3

# 2. Dry run dei bundle (già verde il 2026-11-27, run 45962616155)
gh workflow run release.yml --ref main -f tag=v0.10.0 -f dry_run=true
gh run watch

# 3. Commit e push
git add -A && git commit -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin main

# 4. Tag annotato e push: avvia il workflow Release
git tag -a v0.10.0 -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin v0.10.0
```

Il workflow `.github/workflows/release.yml` esegue il gate, costruisce wheel/sdist e i tre bundle,
calcola `SHA256SUMS` e pubblica la GitHub Release con le note in `docs/release-0.10.0.md`.
