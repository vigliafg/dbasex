# Collaudo 0.6.0 — Ricerca, import e manutenzione

Data: 2026-11-22

La release 0.6.0 aggiunge le operazioni quotidiane sulla Browse e sul progetto: Find mode con più
criteri, sostituzione, importazione CSV guidata e manutenzione degli oggetti. I progetti 0.5 si
aprono senza migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 374 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `find mode`, `import csv` e `duplicazione oggetti + integrità` |
| Versione | `python -m dbx --version` | `DBX 0.6.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_search.py`: operatori, AND/OR, “Ometti”, campi vuoti, date, escape dei jolly,
  validazione, sostituzione e ricerche salvate.
- `tests/test_ui_search.py`: dialogo di ricerca, aggiunta/rimozione criteri, applicazione alla
  Browse, dialogo di sostituzione.
- `tests/test_csv_import.py`: rilevamento delimitatore e codifica, mappatura suggerita, conversione
  tipi, importazione e riga in errore.
- `tests/test_refactor.py`: rinomina con aggiornamento di FK, query, form e diagrammi; duplicazione
  di tabelle con dati e di oggetti; compattazione e integrità.
- `tests/test_ui_maintenance.py`: rinomina dal Table Structure, segnale di duplicazione del
  Navigator, azioni di manutenzione nella finestra principale.

## Collaudo manuale/headless

1. **Find mode** — nella Browse premere `Ctrl+F`, aggiungere un criterio su Città `contiene Milano`
   e uno su Attivo `uguale a 1`; la combinazione AND restituisce i record corrispondenti. Con
   combinazione OR l’insieme si allarga; con **Ometti** il criterio esclude i record.
2. **Campi vuoti e date** — usare `è vuoto` / `non è vuoto` senza valore e `maggiore o uguale a`
   con una data ISO; i record sono filtrati e il conteggio è mostrato nella status bar.
3. **Ricerche salvate** — salvare la ricerca con un nome, azzerarla con **Trova tutto**, ricaricarla
   dal combo e verificare che i criteri siano ripristinati; eliminarla con **Elimina**.
4. **Sostituisci** — premere `Ctrl+H`, scegliere tutti i campi o un campo, attivare
   “Distingui maiuscole” e “Solo parole intere”; la conferma riporta il numero di record visibili e
   la status bar il numero di celle sostituite.
5. **Importa CSV** — aprire una tabella, scegliere **Importa CSV…**, selezionare un file con
   intestazione, verificare anteprima, delimitatore e codifica, controllare la mappatura suggerita,
   importare. Una riga non valida produce un errore con il numero di riga e non scrive nulla.
6. **Svuota prima di importare** — l’opzione richiede conferma, crea un backup e sostituisce i dati
   solo se l’intera importazione riesce.
7. **Rinomina tabella** — in Table Structure cambiare `Name` e applicare; la tabella è rinominata nel
   database e i riferimenti in FK, query, form, report, script e diagrammi sono aggiornati.
8. **Duplica oggetto** — dal menu contestuale del Navigator scegliere **Duplica…**; una tabella copia
   struttura e dati, gli altri oggetti ricevono una copia JSON con nome univoco.
9. **Manutenzione** — `Progetto → Manutenzione database → Compatta database…` crea un backup e
   compatta; `Verifica integrità…` riporta `ok` o il messaggio di SQLite.
10. **Compatibilità** — aprire un progetto 0.5 e verificare che oggetti, query, form, report e
    script funzionino senza migrazione.

## Screenshot

- `25-find-dialog.png`: Find mode con criteri, combinazione, “Ometti” e ricerche salvate.
- `26-import-csv.png`: wizard CSV con opzioni, anteprima e mappatura colonne.

## Limiti accettati

- La ricerca guidata e la sostituzione lavorano sulla tabella aperta nella Browse; non c’è ancora
  una ricerca globale tra tutti gli oggetti del progetto.
- La sostituzione agisce sui record visibili, non su quelli esclusi dal filtro.
- L’import CSV richiede una tabella di destinazione esistente e non crea una tabella dalla struttura
  del file.
- La mappatura non può associare due colonne allo stesso campo.
- La rinomina non aggiorna le finestre già aperte: vanno riaperte dopo l’operazione.
- La duplicazione di una tabella copia i dati in una sola transazione; tabelle molto grandi possono
  richiedere qualche secondo.
- Compattazione e verifica sono sincrone e non mostrano una barra di avanzamento.
