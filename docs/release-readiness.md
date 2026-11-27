# Release readiness — dBX 0.10.0

Checklist go/no-go per la release 0.10.0. Aggiornata il 2026-11-27.

## Criteri bloccanti

| # | Criterio | Comando / verifica | Esito |
|---:|---|---|---|
| 1 | Versione coerente tra `pyproject.toml`, pacchetto, changelog, note e tag | `python tools/release_check.py --tag v0.10.0` | da eseguire sul tag |
| 2 | Suite completa verde | `python -m pytest` | verde |
| 3 | Smoke headless verde | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | verde |
| 4 | Harness E2E completo con gate di copertura fase 3 | `python tools/e2e_harness.py --require-coverage --coverage-phase 3` | verde |
| 5 | Rendering canonici rigenerati | `python tools/capture_ui.py` | verde |
| 6 | CI pytest + smoke su Linux, Windows e macOS | workflow `CI` | da verificare sul commit di release |
| 7 | Pacchetto Python `sdist` + wheel | workflow `Release`, job `sdist` | da verificare sul tag |
| 8 | Bundle autonomi Linux, Windows e macOS | workflow `Release`, job `standalone` | da verificare sul tag |
| 9 | Release GitHub con note, artefatti e `SHA256SUMS` | workflow `Release`, job `publish` | da verificare sul tag |

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

# 2. Commit e push
git add -A && git commit -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin main

# 3. Tag annotato e push: avvia il workflow Release
git tag -a v0.10.0 -m "Rilascio 0.10.0: validazione dei campi e collaudo E2E"
git push origin v0.10.0
```

Il workflow `.github/workflows/release.yml` esegue il gate, costruisce wheel/sdist e i tre bundle,
calcola `SHA256SUMS` e pubblica la GitHub Release con le note in `docs/release-0.10.0.md`.
