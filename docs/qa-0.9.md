# Collaudo 0.9.0 — Automazione: parametri, variabili globali e transazioni

Data: 2026-11-22

La release 0.9.0 chiude il ciclo **automazione**: gli script possono dichiarare parametri, condividere
variabili globali persistite nel progetto e raggruppare le scritture in transazioni esplicite. I
progetti 0.8 si aprono senza migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 481 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `parametri e variabili globali` e `transazioni script` |
| Versione | `python -m dbx --version` | `DBX 0.9.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_script_automation.py`: dichiarazione e validazione dei parametri, valori predefiniti e
  sostituzioni, filtri parametrizzati, globali condivise/persistite/cancellate, shadowing, date,
  commit, rollback, rollback automatico, errori di stato, cursore e forma testuale.
- `tests/test_ui_script_params.py`: dialoghi dei parametri e dei valori, Program Editor (modifica,
  salvataggio, esecuzione con predefiniti), Navigator e Project Runner con richiesta dei valori.

## Collaudo manuale/headless

1. **Dichiarare un parametro** — Program Editor → Parametri: nome `soglia`, etichetta
   `Importo minimo`, predefinito `1000`; salvare e riaprire lo script.
2. **Eseguire con valori** — Dal Navigator o dal menu del progetto scegliere lo script: il dialogo
   mostra i predefiniti; modificare `soglia` in `500` e confermare.
3. **Parametro nei messaggi** — Verificare che lo stato riporti il valore scelto e che i messaggi
   contengano il numero di fatture sopra soglia.
4. **Parametro nei filtri** — Lo script demo usa `importo >= :soglia`; cambiando soglia cambiano i
   record elencati, senza che il filtro venga valutato come espressione booleana.
5. **Annullare il dialogo** — Premere Cancel nel dialogo dei valori: lo script non parte e non
   modifica globali né dati.
6. **Variabili globali** — Eseguire `SET GLOBAL :ultima_soglia = :soglia`, poi riaprire il progetto:
   la variabile è ancora disponibile e leggibile con `:ultima_soglia`.
7. **Cancellare una globale** — `CLEAR GLOBAL :ultima_soglia` la rimuove dal manifest e dalle
   successive esecuzioni.
8. **Transazione confermata** — `BEGIN TRANSACTION`, alcune `SET FIELD`/`SQL`, `COMMIT TRANSACTION`:
   le modifiche restano in Browse dopo il ricaricamento.
9. **Transazione annullata** — Stessa sequenza con `ROLLBACK TRANSACTION`: i valori tornano quelli
   precedenti e la scheda corrente viene riletta.
10. **Errore dentro la transazione** — `BEGIN`, scritture, poi `HALT`: lo script termina e la
    transazione viene annullata automaticamente, senza lasciare il database bloccato.
11. **Testo e azioni** — Passare dal testo alle azioni e viceversa con `SET GLOBAL`, `CLEAR GLOBAL`,
    `BEGIN/COMMIT/ROLLBACK TRANSACTION`; il round-trip deve restare stabile.
12. **Validazione** — Un nome di parametro non valido o duplicato compare negli errori del Project
    Editor e blocca la build.
13. **Compatibilità** — Aprire un progetto 0.8: gli script senza `params` funzionano come prima e
    nessuna globale viene creata finché non si usa `SET GLOBAL`.

## Screenshot

- `37-script-parameters.png`: editor dei parametri con nome, etichetta e predefinito.
- La serie `01`–`36` resta quella delle release precedenti; `11-script-editor.png` mostra il nuovo
  pulsante Parametri.

## Limiti accettati

- Parametri solo testuali; per i calcoli numerici usare `VAL(:parametro)`.
- Nessuna transazione annidata, nessun salvataggio automatico parziale e nessun timeout esplicito.
- Variabili globali senza tipi, senza scoping per utente e con nomi condivisi con le variabili locali
  (il locale ha la precedenza).
- Il Program Editor non offre breakpoint né esecuzione passo-passo.
- Restano i limiti delle release precedenti: query statiche, portali senza azioni per riga, grafici
  non interattivi, etichette senza barcode/QR o immagini.
