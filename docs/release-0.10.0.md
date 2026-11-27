# dBX 0.10.0 — Validazione dei campi e collaudo E2E 2.0

Data: 2026-11-27

La 0.10.0 porta nel prodotto l'estensione **validazione dei campi** e chiude la campagna di
collaudo **E2E 2.0**. I progetti 0.9 si aprono senza migrazione: i nuovi metadati sono additivi e
hanno default vuoti.

## In evidenza

### Validazione dei campi

- **Issue strutturate**: `Rowset` restituisce `ValidationIssue` con campo, codice e severità;
  `ValidationError` conserva l'elenco per la UI.
- **Validazione per cella**: `validate_field` e `Rowset.update(only=)` salvano una cella valida anche
  se un altro campo obbligatorio è ancora vuoto.
- **Obbligatorietà condizionale** con `required_expr`, `skip_expr` e `rule_message`.
- **Campo Scelta** statico o con sorgente dinamica `tabella.colonna`, valori ed etichette, cache e
  limite di 1000 valori.
- **Dominio numerico** con minimo/massimo o intervalli multipli e messaggio personalizzato.
- **Maschere, maiuscole e avanzamento automatico** del focus nella griglia, nel nuovo record e nel
  Form Runtime.
- **Incremento** all'inserimento (`records`) o contatore di revisione (`updates`), con migrazione
  trasparente di `auto_serial`.
- **Riapplica regole di campo** e **import CSV a scarti** con riga e motivo del rifiuto.

### Collaudo E2E 2.0

- **133 nuovi workflow granulari** (147 scenari totali) e **1.611 controlli** nominati.
- **Catalogo delle funzioni** derivato dal codice: **505/505 feature** coperte, con gate
  `--require-coverage`.
- **9 difetti reali corretti** durante il collaudo: default in inserimento, navigazione su tabella
  vuota, `COUNT(*)` nel Query Designer, stile dei campi nel Form Expert, Browse Field Data,
  pluralizzazione delle pagine, scorciatoie standard della shell, zoom nei dialoghi e build con WAL.

### Interfaccia

- Navigator: **Database** è lo schema ER, **Tabelle** apre la struttura della tabella scelta; la
  Browse resta come **Sfoglia dati** nel menu contestuale.
- Table Builder e Database Designer più compatti, con nuova tabella nella scheda del workspace e
  card ER a 168 px.
- Nomi di tabella con spazi interni singoli (`tabella 2`).

## Installazione

### Pacchetto Python

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install dbx-0.10.0-py3-none-any.whl
dbx --demo
```

Richiede Python 3.10+ e PyQt6 6.10.2.

### Eseguibili autonomi

La release allega un bundle per piattaforma:

| Piattaforma | File |
|---|---|
| Linux x86_64 | `dbx-0.10.0-linux-x86_64.tar.gz` |
| Windows x86_64 | `dbx-0.10.0-windows-x86_64.zip` |
| macOS arm64 | `dbx-0.10.0-macos-arm64.tar.gz` |

I bundle sono prodotti con PyInstaller e non includono un progetto: al primo avvio usare
`Progetto → Nuovo progetto` oppure `--demo` dalla riga di comando.

- **Windows**: l'eseguibile non è firmato; SmartScreen può chiedere una conferma.
- **macOS**: l'app non è firmata né notarizzata; aprirla con tasto destro → *Apri* oppure
  `xattr -dr com.apple.quarantine dbx.app`.
- **Linux**: servono le librerie di sistema `libegl1`, `libgl1` e `libxkbcommon0`.

Ogni file è elencato in `SHA256SUMS`.

## Note di aggiornamento

- I valori storici non vengono riscritti: Scelta e dominio valgono alla scrittura, mentre
  `File → Manutenzione database → Riapplica regole di campo…` li segnala come
  `choice_stale`/`domain_stale`.
- Maschera e maiuscole sono regole dell'editor: i valori già presenti cambiano solo quando vengono
  modificati o normalizzati dal comando di manutenzione.
- Il campo legacy `lookup` viene letto come Scelta con sorgente tabella; `auto_serial` viene letto
  come `increment="records"` e riscritto con il solo campo nuovo.
- `increment="updates"` è un contatore di revisione del singolo record, non una sequenza globale.

## Collaudo

- `pytest` completo, smoke headless e harness E2E con gate di copertura fase 3.
- Dettagli in [`docs/qa-0.10.md`](../docs/qa-0.10.md) e criteri go/no-go in
  [`docs/release-readiness.md`](../docs/release-readiness.md).
- Changelog completo: [`CHANGELOG.md`](../CHANGELOG.md).

## Limiti noti

Restano i limiti dichiarati delle release precedenti: query statiche in sola lettura, portali senza
azioni per riga, grafici non interattivi, etichette senza barcode/QR o immagini, script senza
breakpoint o esecuzione passo-passo. La stampa fisica va verificata sulla macchina di destinazione.
