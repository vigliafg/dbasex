# Collaudo 0.4.0 — Esperti e QBE

Data: 2026-11-22

La release 0.4.0 aggiunge gli esperti per tabella, query, report e form e la modalità QBE del
Query Designer. Le query restano statiche e in sola lettura; i progetti 0.3 si aprono senza
migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 326 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `table expert`, `query expert`, `report expert`, `qbe mode` |
| Versione | `python -m dbx --version` | `DBX 0.4.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_table_expert.py`: template, campi, indici, riepilogo DDL.
- `tests/test_query_expert.py`: join dalle foreign key, campi, criteri, ordinamento, SQL.
- `tests/test_report_expert.py`: tabellare, colonnare, riepilogo, sorgente query, orientamento.
- `tests/test_qbe_core.py`: grammatica delle celle, operatori, intervalli, jolly, example elements.
- `tests/test_qbe_model.py`: modello e motore QBE, gruppi OR, `between`, `like`, `ref`.
- `tests/test_ui_qbe.py`: toggle QBE/Guidato, query image, sincronizzazione, celle non valide,
  example elements, avviso LEFT JOIN, salvataggio con gruppi e intervalli.

## Collaudo manuale/headless

1. **Table Expert** — `Oggetto → Nuovo con esperto → Tabella…`, template Contatti, nome libero,
   indici suggeriti, DDL nel riepilogo, creazione e apertura in Browse.
2. **Query Expert** — tabella base Clienti, join Fatture proposto dalla FK, campi, criterio e
   ordinamento, SQL nel riepilogo; la query creata si apre nel Query Designer.
3. **Report Expert** — sorgente tabella e query, layout tabellare/colonnare/riepilogo, gruppo e
   ordinamento; il report creato si apre nel Report Designer.
4. **QBE** — toggle QBE/Guidato, caselle Includi, tre righe Criteri, riga Ordinamento, priorità
   nell'etichetta, same-row AND e righe diverse OR.
5. **Example elements** — `_cli` in `fatture.cliente` e `clienti.codice`, anteprima a 5 righe,
   riapertura della vista con `_rif1`.
6. **Celle non valide** — `>` senza valore: bordo d'errore, messaggio nella vista, filtro non
   applicato; correggendo in `>1000` il filtro viene applicato.
7. **LEFT JOIN** — OR su `clienti.citta` con join LEFT: avviso non bloccante.
8. **Compatibilità** — apertura dei progetti demo 0.3 e salvataggio senza migrazione.

## Screenshot

- `23-qbe-mode.png`: Query Designer in modalità QBE con query image, example elements e OR.

## Limiti accettati

- QBE solo ricerca: niente Insert/Delete/Set/ChangeTo, crosstab, CALC o parametri interattivi.
- Un OR su campi di tabelle in LEFT JOIN è permesso ma segnalato.
- Gli example elements richiedono la tabella collegata già presente; il designer non la aggiunge
  automaticamente.
- Il layout Riepilogo del Report Expert richiede un gruppo; senza gruppo il report resta tabellare.
