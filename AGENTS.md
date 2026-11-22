# Istruzioni per l'agente — dBX / dbasex

Queste istruzioni valgono per qualsiasi agente che lavori sul repository `dbasex`.
Sono più specifiche di eventuali `AGENTS.md` nelle directory superiori.

## Contesto

- dBX è un personal database desktop in Python + PyQt6, motore SQLite, ispirato a dBASE 5.5 for Windows.
- Il piano di ristrutturazione UI è in `PLAN.md`.
- Il diario di implementazione è in `DIARIO.md`.
- La specifica delle finestre originali è in `docs/reference/dbase55/ui-spec.md`.
- Gli screenshot di riferimento sono in `docs/reference/dbase55/images/`.
- I rendering dello stato attuale sono in `docs/reference/dbx-ui/`.

## Prima di ogni sessione

1. Leggi `PLAN.md`.
2. Leggi `DIARIO.md`, in particolare l'ultima voce e l'eventuale blocco `RIPRESA`.
3. Controlla `git status` e `git log --oneline -5`.
4. Identifica l'ondata corrente e non iniziarne una successiva.

Non fidarti della memoria della conversazione: dopo una compattazione del contesto, la verità è in `PLAN.md` + `DIARIO.md` + repository.

## Lavoro a ondate

Le ondate sono O0–O7. Vanno eseguite in ordine, una alla volta.

Per ogni ondata:

1. Scrivi nel diario la voce di avvio con obiettivo e stato `in corso`.
2. Implementa solo lo scope dell'ondata.
3. Esegui i test dell'ondata.
4. Rigenera gli screenshot con `tools/capture_ui.py` quando esiste.
5. Aggiorna `docs/ui-parity.md` quando esiste.
6. Chiudi la voce di diario con stato, commit, test, problemi e prossimo passo.
7. Fai commit atomici e push.

Non iniziare l'ondata successiva se quella corrente non è verde.

## Diario

File: `DIARIO.md`.

Regole:

- **Append-only**: non riscrivere né cancellare voci precedenti.
- Una voce per ondata; più voci solo per sotto-attività rilevanti.
- Formato:

```markdown
### AAAA-MM-GG — Ondata N — Titolo
- Stato: in corso | completata | bloccata
- Branch/commit: ...
- Obiettivo: ...
- File toccati: ...
- Scelte/deviazioni: ...
- Test: ...
- Screenshot: ...
- Problemi aperti: ...
- Prossimo passo: ...
```

- A ogni checkpoint aggiungi una sezione `CHECKPOINT` con:
  - stato delle ondate;
  - test eseguiti;
  - blocco `RIPRESA` con il prossimo passo esatto;
  - eventuali decisioni rimandate all'utente.

## Checkpoint ogni 3 ondate

L'Ondata 0 è preparatoria e non conta nel ciclo.

| Checkpoint | Fine ondata |
|---|---|
| A | O3 |
| B | O6 |
| C | O7 (release) |

Alla fine di O3 e O6:

1. **Fermati.** Non iniziare l'ondata successiva.
2. Esegui `pytest`, smoke e cattura screenshot.
3. Aggiorna `DIARIO.md` con `CHECKPOINT A` o `CHECKPOINT B` e il blocco `RIPRESA`.
4. Comunica all'utente: “Checkpoint A/B raggiunto. Compatta il contesto e scrivi **continua**.”
5. Attendi.

Alla ricezione del comando **`continua`**:

1. Leggi `PLAN.md` e `DIARIO.md`.
2. Cerca il blocco `RIPRESA`.
3. Controlla `git status` e `git log`.
4. Riprendi dalla prima ondata non completata.
5. Non chiedere conferme se il piano è chiaro.

## Regole tecniche

- `dbx/ui/design.py` è l'unica fonte di colori, metriche e font.
- Non inserire colori hard-coded nei widget; i canvas leggono i token.
- Il tema predefinito è `silver`; `dark` è opzionale e non bloccante.
- Non modificare `core/` o `runtime/` per motivi estetici.
- Le modifiche ai modelli devono essere additive e retrocompatibili, con default.
- I designer non contengono logica dati: producono/consumano JSON.
- Non introdurre dipendenze nuove senza necessità dimostrata.
- Non eliminare o modificare le immagini in `docs/reference/dbase55/images/`.
- Non fare pixel-perfect Win16: il target è clone strutturale + chrome dBASE.
- Query Designer e Label Designer sono fuori dalla 0.2.

## Test

Esegui almeno:

```bash
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
python tools/capture_ui.py   # quando esiste
```

Se un test esistente fallisce per una modifica voluta, aggiorna il test nello stesso commit e spiega il motivo nel diario.

## Commit e push

- Commit atomici, messaggi in italiano, imperativo.
- Esempio: `UI O1: introduce area MDI e menu dBASE`.
- Non fare `git push --force`.
- Non riscrivere la storia.
- Includi nel commit il diario e i documenti aggiornati.
- Se lavori su branch, fai merge su `main` a fine ondata solo dopo test verdi.

## Cosa non fare

- Non implementare più ondate insieme.
- Non saltare il diario.
- Non superare un checkpoint senza fermarti.
- Non introdurre un linguaggio di scripting per gli eventi form.
- Non trasformare il Report Designer in un framework generico.
- Non rimuovere funzionalità esistenti (tema Dark, export, build) senza decisione esplicita.
- Non modificare il motore per adattarlo alla UI: adatta la UI al motore.

## Risposta all'utente

- In italiano, concisa.
- Alla fine di ogni ondata riporta: ondata completata, test, screenshot, prossimo passo.
- Al checkpoint fermati e chiedi la compattazione del contesto.
- Alla ripresa con `continua`, non ripetere l'analisi: riparti dal diario.
