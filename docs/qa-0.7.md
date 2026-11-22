# Collaudo 0.7.0 — Calcolo, aggregati e crosstab

Data: 2026-11-22

La release 0.7.0 porta il calcolo nei dati: campi calcolati virtuali, auto-enter con serie e date,
aggregati `GROUP BY` nelle query e tabella incrociata read-only. I progetti 0.6 si aprono senza
migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 407 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `calcolati`, `aggregati query`, `crosstab read-only` |
| Versione | `python -m dbx --version` | `DBX 0.7.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_calculated_fields.py`: DDL virtuale, calcolo a catena, serie, date, auto-enter,
  regole, migrazioni additive, query/search rifiutate, rinomina dei riferimenti.
- `tests/test_ui_calculated.py`: Table Builder, Browse in sola lettura, RecordDialog.
- `tests/test_query_aggregates.py`: aggregati globali, GROUP BY, join, ordinamento per alias,
  validazione, JSON, esclusione dei calcolati.
- `tests/test_ui_query_aggregates.py`: scheda Raggruppa, aggiunta/rimozione, Query Results.
- `tests/test_crosstab.py` e `tests/test_ui_crosstab.py`: pivot, totali, CSV, cambio dimensioni.

## Collaudo manuale/headless

1. **Campo calcolato** — Table Structure → Proprietà → Calcolato, inserire `[prezzo] * [quantita]`;
   applicare. La colonna non compare in `PRAGMA table_info`, ma il valore è visibile in Browse.
2. **Auto-enter** — creare un campo Testo con Auto-enter `CONCAT([nome], ' —')`; inserire un record
   senza compilare il campo e verificare il valore.
3. **Serie automatica** — campo Intero con Serie automatica; inserire tre record e verificare 1, 2, 3.
4. **Data automatica** — campo Data con “Data di creazione” e un secondo con “Data di modifica”;
   creare e aggiornare un record. La prima resta stabile, la seconda cambia.
5. **Modifica parziale** — aggiornare solo un campo: serie, data, auto-enter e gli altri valori non
   vengono azzerati.
6. **Calcolato in regola** — regola `[totale] >= 0` su un campo; un valore negativo viene rifiutato
   con il messaggio del campo.
7. **Aggregati globali** — Query Designer su `fatture`, scheda Raggruppa → aggiungere COUNT senza
   campo e SUM di `importo`; l'anteprima mostra una riga con 5 e 5900.5.
8. **GROUP BY** — aggiungere `clienti.nome` ai raggruppamenti e `fatture.pagata` ai campi, con SUM
   di importo; l'anteprima mostra quattro combinazioni e i totali per cliente.
9. **Ordinamento per alias** — in Ordinamento scegliere l'alias dell'aggregato (`totale`) e
   verificare l'ordine; lo SQL usa l'alias tra virgolette.
10. **Crosstab** — da Query Results premere Crosstab, scegliere Nome / Pagata / Somma di importo;
    la matrice mostra Alfa, Beta e Gamma con i totali. Esportare il CSV e riaprirlo.
11. **Crosstab da designer** — premere Crosstab nel Query Designer dopo l'anteprima; la finestra usa
    il risultato corrente, non una query salvata.
12. **Compatibilità** — aprire un progetto 0.6 e verificare che query, form, report, script e
    Browse funzionino senza migrazione.

## Screenshot

- `27-table-calculated.png`: proprietà Calcolato/Auto-enter nel Table Structure.
- `28-browse-calculated.png`: totale e serie calcolati nella Browse.
- `29-query-aggregates.png`: scheda Raggruppa con GROUP BY e aggregati.
- `30-crosstab.png`: matrice incrociata con totali.

## Limiti accettati

- I campi calcolati sono virtuali: niente indici, foreign key, ricerca SQL, ordinamento SQL o
  aggregazione nelle query.
- Auto-enter, serie e date automatiche sono gestiti dal `Rowset`; scritture SQL dirette possono
  aggirarli.
- Le query non hanno HAVING, sottoquery, parametri interattivi o RIGHT/FULL JOIN.
- Gli aggregati lavorano su campi fisici, non su espressioni arbitrarie.
- Il Crosstab legge un risultato già aggregato e non è un oggetto salvato; niente grafici.
- La crosstab somma i valori (o li conta se la query usa COUNT); non applica altre funzioni.
- Le finestre già aperte non seguono automaticamente una modifica di struttura: vanno riaperte.
