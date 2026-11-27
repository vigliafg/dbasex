# Stato di parità UI — dBX 0.10 vs dBASE 5.5

Aggiornato: 2026-11-27 (release 0.10.0)

Legenda: `fatto` = struttura e chrome coerenti; `parziale` = struttura presente ma da rifinire;
`fuori scope` = escluso dalla 0.3 per decisione di piano; `mancante` = non implementato.

| Finestra originale | Riferimento | Modulo dBX | Stato 0.3 | Gap principale |
|---|---|---|---|---|
| Desktop + menu + SpeedBar | `01`, `43` | `dbx/ui/main_window.py` | fatto | — |
| Navigator | `01`, `42`, `43` | `dbx/ui/navigator.py` | fatto | **Database** apre lo schema ER, **Tabelle** apre la struttura; Immagini/Suoni/Cataloghi/Personalizzati disabilitate |
| Command Window | `01`, `02`, `04` | `dbx/ui/command_window.py` | fatto | Comandi limitati a HELP/TABELLE/USE/RECORD/CLEAR/espressioni |
| Browse / Table | `07`, `11`, `18` | `dbx/ui/data_view.py` | fatto | Find mode, sostituzione e import CSV (0.6) |
| Table Structure | `08`, `09`, `13`, `14`, `27` | `dbx/designers/table_builder.py` | fatto | Campi calcolati, auto-enter, incremento, Scelta, dominio numerico e maschere nella scheda Proprietà (con scorrimento interno); nuova tabella e modifica nella scheda del workspace; stampa minimale |
| Table Expert | — | `dbx/designers/table_expert.py` | fatto (0.4/O1) | Template, campi e indici; crea e apre la tabella in Browse |
| Query Expert | — | `dbx/designers/query_expert.py` | fatto (0.4/O2) | Join suggeriti dalle FK, campi, criteri AND e ordinamento |
| Report Expert | — | `dbx/designers/report_expert.py` | fatto (0.4/O2) | Layout tabellare/colonnare/riepilogo, gruppi, stile |
| Database Designer ER | — | `dbx/designers/database_designer.py` | fatto (0.3/O3) | Diagramma dominante, card compatte a 168 px, pannelli laterali stretti, toolbar a due righe; relazioni e modifiche schema; export PNG/SVG |
| Query Designer | `15`, `19`, `20`, `21`, `23`, `29` | `dbx/designers/query_builder.py` | fatto (0.3/O5, QBE 0.4/O4, aggregati 0.7/O5) | Query statiche, INNER/LEFT JOIN, filtri, gruppi OR, QBE read-only e GROUP BY con aggregati |
| Query Results | `16`, `17`, `30` | `dbx/ui/query_results.py` | fatto (0.3/O6, crosstab 0.7/O6) | Griglia read-only, aggiornamento, export CSV e Crosstab con totali |
| Form Expert | `22`–`26` | `dbx/designers/form_expert.py` | fatto | Sorgente tabella o query (read-only); miniatura layout strutturale |
| Form Designer | `27`–`31`, `40` | `dbx/designers/form_builder.py` | fatto (viste 0.8/O9) | Palette in pannello ridimensionabile; View/List fields e Portal order/filter nell'Inspector |
| Properties Inspector | `30`, `31`, `40` | `dbx/ui/widgets.py` | fatto | Albero condiviso con il Report Designer |
| Form Runtime | `40`, `35`, `36` | `dbx/runtime/form_runtime.py` | fatto (viste 0.8/O9) | Scheda/Lista, portali ordinati e filtrati; dispatcher di azioni, query read-only |
| Report Designer | `32`–`38`, `41`, `34` | `dbx/designers/report_builder.py` | fatto (grafici 0.8/O8) | Selezione singola; ordine delle bande di flusso fisso; grafici barre/linee/torta |
| Report Preview | `39`, `33` | `dbx/ui/report_preview.py` | fatto (grafici 0.8/O8) | Zoom persistente per sessione; pagina singola/continua; report su query e grafici |
| Program Editor | `31`, `32`, `37` | `dbx/designers/script_builder.py`, `dbx/designers/step_picker.py`, `dbx/ui/script_params.py` | fatto (automazione 0.9/O10) | Parametri, variabili globali e transazioni; nessuna esecuzione passo-passo |
| Menu Designer | — | `dbx/designers/menu_builder.py` | fatto | Anteprima come menu bar, non popup sempre aperto |
| Project Editor/Builder | — | `dbx/designers/project_builder.py` | fatto | Build sincrono, senza barra di avanzamento |
| Label Designer | `31` | `dbx/designers/label_builder.py` | fatto (0.8/O7) | Etichette e mail merge con preset, griglia e modello `[campo]` |
| Label Preview | `32` | `dbx/ui/label_preview.py` | fatto (0.8/O7) | Riusa la Preview dei report per stampa e PDF |
| Interactive Tutor | `03` | — | fuori scope 0.3 | Non previsto nella 0.3 |
| About | `42`, `43` | `dbx/ui/main_window.py` | parziale | Testo e versione presenti; chrome Borland non replicato |

## Note

- Lo stato si riferisce alla struttura e al chrome, non al pixel-perfect. Il tema predefinito è Aurora; Silver resta selezionabile con `--theme silver`.
- Rendering canonici: `docs/reference/dbx-ui/renders/01-desktop.png` … `14-menu-progetto.png`;
  indice in `docs/reference/dbx-ui/README.md`.
- `10-desktop-tabs.png` mostra Browse e Form Designer in due schede affiancate.
- `11-script-editor.png`, `12-menu-designer.png` e `13-project-editor.png` coprono gli strumenti O6.
- `15-database-designer.png`, `16-query-designer.png`, `17-query-results.png` coprono Database
  Designer, Query Designer e Query Results.
- `18-form-query.png` e `19-report-query.png` mostrano form e report alimentati da query.
- `20-table-expert.png` mostra il Table Expert introdotto nella 0.4.
- `21-query-expert.png` e `22-report-expert.png` mostrano i nuovi esperti guidati.
- `23-qbe-mode.png` mostra il Query Designer in modalità QBE, con example elements e righe OR.
- `24-script-step-picker.png` mostra il catalogo azioni categorizzato del Program Editor.
- `25-find-dialog.png` mostra il Find mode con criteri AND/OR, “Ometti” e ricerche salvate.
- `26-import-csv.png` mostra l'importazione CSV con anteprima e mappatura delle colonne.
- `27-table-calculated.png` mostra la proprietà Calcolato del Table Structure, con
  i campi Maiuscole/Maschera, il combo Incremento e il gruppo Dominio numerico;
  `28-browse-calculated.png` mostra totale e serie calcolati nella Browse.
- La 0.10.0 rilascia la validazione dei campi (Scelta, dominio numerico, maschere, incremento) e il
  collaudo E2E 2.0; nessuna finestra nuova, rifiniture a Table Structure e Navigator.
- La 0.9.0 introduce parametri script, variabili globali e transazioni esplicite.
- La 0.8.0 introduce etichette/mail merge, grafici nei report, vista Lista e portali.
- La 0.7.0 introduce campi calcolati virtuali, auto-enter, aggregati `GROUP BY` e Crosstab
  read-only.
- `29-query-aggregates.png` mostra la scheda Raggruppa con aggregati e anteprima.
- `30-crosstab.png` mostra la matrice incrociata con totali di riga, colonna e generale.
- `31-label-designer.png` mostra il Label Designer con preset, griglia e modello; `32-label-preview.png`
  mostra il mail merge su foglio A4.
- `33-report-chart.png` mostra un grafico a barre nella Preview; `34-report-chart-designer.png`
  mostra il controllo grafico selezionato nel Report Designer.
- `35-form-list.png` mostra la vista Lista di un form; `36-form-portal.png` mostra il portale delle
  fatture ordinate e filtrate nel form principale.
- `37-script-parameters.png` mostra l'editor dei parametri di uno script.
- La 0.6.0 aggiunge ricerca guidata, sostituzione, import CSV, rinomina/duplicazione oggetti e
  manutenzione del database.
- La 0.5.0 completa il Program Editor con 17 passi core, cursore dati e Step Picker; rende visibili
  categoria e descrizione nell'Inspector e nel dialogo dei parametri.
- Le checklist di collaudo, i test e i difetti noti accettati sono in `docs/qa-0.2.md`,
  `docs/qa-0.3.md`, `docs/qa-0.4.md`, `docs/qa-0.5.md`, `docs/qa-0.6.md`, `docs/qa-0.7.md`, `docs/qa-0.8.md` e `docs/qa-0.9.md`.
- Il Label Designer leggero è tornato nella 0.8: la categoria **Etichette** convive con **Database** e
  **Tabelle** e produce etichette/mail merge; non è il designer a controlli liberi di dBASE.
- Query Designer, Query Results e le query come sorgente di form/report sono parte della release 0.3.0.
