# Collaudo 0.5.0 — Catalogo azioni e passi core

Data: 2026-11-22

La release 0.5.0 porta nel Program Editor il **catalogo categorizzato** delle azioni script e un set
di **passi core** per controllo, tabelle, record, campi, query, report e dialoghi. Gli script restano
JSON con forma testuale bidirezionale; i progetti 0.4 si aprono senza migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 345 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `program editor` e `script core actions` |
| Versione | `python -m dbx --version` | `DBX 0.5.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_step_catalog.py`: categorie e descrizioni di ogni azione, copertura completa del
  catalogo, filtro e selezione dello Step Picker, Inspector con categoria e descrizione.
- `tests/test_script_actions.py`: passi core su tabelle e record, `SET FIELD`, `LOOP`,
  `EXIT LOOP IF`, `EXIT SCRIPT`, `HALT`, `CUSTOM DIALOG`, `BEEP`, forma testuale, `ELSE IF`,
  validazione del progetto e adattatore del Form Runtime.
- `tests/test_ui_script_editor.py`: editor, andata/ritorno sorgente ↔ azioni, dialogo parametri,
  inspector e prova dello script.
- `tests/test_script_engine.py`: motore, variabili, espressioni, blocchi e ciclo di esecuzione.
- `tests/test_ui_form_runtime.py`: eventi del form e dispatcher con `script:nome`.

## Collaudo manuale/headless

1. **Step Picker** — `Aggiungi azione` apre il catalogo per categoria; il filtro `csv` riduce
   l'elenco a **Esporta CSV**; la descrizione mostra parametri e categoria; **Aggiungi** è attivo
   solo con un'azione selezionata.
2. **Inspector del passo** — selezionando un passo l'Inspector mostra azione, categoria,
   descrizione, numero di blocchi e parametri modificabili.
3. **`SELECT TABLE` e `GO RECORD`** — apertura della tabella con filtro e ordinamento, poi primo,
   precedente, successivo, ultimo o numero di record; il log riporta la posizione.
4. **`SET FIELD`** — l'espressione è calcolata sul record corrente e scritta subito; il log mostra
   `tabella.campo = valore`; un campo o una tabella errati producono un errore chiaro.
5. **Record** — `NEW RECORD` inserisce i default, `DUPLICATE RECORD` copia il corrente,
   `DELETE RECORD` chiede conferma salvo `NOCONFIRM`, `COMMIT` e `REVERT` ricaricano dal database.
6. **Ciclo** — `LOOP` con `EXIT LOOP IF :i >= 2` esce dal solo ciclo; `EXIT SCRIPT` e `HALT`
   fermano lo script.
7. **Dialoghi e servizi** — `CUSTOM DIALOG` salva il valore in `:variabile`, `BEEP` suona,
   `OPEN QUERY` e `OPEN REPORT` aprono l'oggetto richiesto.
8. **`ELSE IF`** — la forma testuale produce un `if` annidato nell'`else`; l'andata/ritorno
   conserva la struttura.
9. **Validazione progetto** — tabella, campo, form, report, query, script e modalità `GO RECORD`
   mancanti sono segnalati da `validate_project`.
10. **Form Runtime** — un evento `script:nome` esegue lo script e ricarica il record corrente; query,
    report, messaggi e conferme passano dall'adattatore UI.

## Screenshot

- `11-script-editor.png`: Program Editor con albero, sorgente e Inspector del passo.
- `24-script-step-picker.png`: Step Picker con catalogo azioni categorizzato e descrizioni.

## Limiti accettati

- Le scritture degli script sono immediate per passo; non c'è una transazione implicita.
  `REVERT RECORD` ricarica il record ma non annulla una scrittura già eseguita.
- `NEW RECORD` usa i valori predefiniti della tabella: con campi obbligatori senza default l'azione
  fallisce e lo script riporta l'errore.
- Gli eventi form restano un dispatcher di azioni singole o `script:nome`, non un linguaggio.
- Il Program Editor non offre breakpoint, esecuzione passo-passo o debugger.
- Non ci sono script trigger, account, privilegi, server o plugin; l'import CSV resta fuori scope.
- `SET FIELD` lavora sulla tabella corrente del cursore; per cambiare tabella usare `SELECT TABLE`.
