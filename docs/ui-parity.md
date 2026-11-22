# Stato di parità UI — dBX 0.4 vs dBASE 5.5

Aggiornato: 2026-11-22 (release 0.4.0)

Legenda: `fatto` = struttura e chrome coerenti; `parziale` = struttura presente ma da rifinire;
`fuori scope` = escluso dalla 0.3 per decisione di piano; `mancante` = non implementato.

| Finestra originale | Riferimento | Modulo dBX | Stato 0.3 | Gap principale |
|---|---|---|---|---|
| Desktop + menu + SpeedBar | `01`, `43` | `dbx/ui/main_window.py` | fatto | — |
| Navigator | `01`, `42`, `43` | `dbx/ui/navigator.py` | fatto | Immagini/Suoni/Cataloghi/Personalizzati disabilitate |
| Command Window | `01`, `02`, `04` | `dbx/ui/command_window.py` | fatto | Comandi limitati a HELP/TABELLE/USE/RECORD/CLEAR/espressioni |
| Browse / Table | `07`, `11`, `18` | `dbx/ui/data_view.py` | fatto | — |
| Table Structure | `08`, `09`, `13`, `14` | `dbx/designers/table_builder.py` | fatto | Rinomina tabella rimandata al motore; stampa minimale |
| Table Expert | — | `dbx/designers/table_expert.py` | fatto (0.4/O1) | Template, campi e indici; crea e apre la tabella in Browse |
| Query Expert | — | `dbx/designers/query_expert.py` | fatto (0.4/O2) | Join suggeriti dalle FK, campi, criteri AND e ordinamento |
| Report Expert | — | `dbx/designers/report_expert.py` | fatto (0.4/O2) | Layout tabellare/colonnare/riepilogo, gruppi, stile |
| Database Designer ER | — | `dbx/designers/database_designer.py` | fatto (0.3/O3) | Diagramma, relazioni e modifiche schema; export PNG/SVG |
| Query Designer | `15`, `19`, `20`, `21`, `23` | `dbx/designers/query_builder.py` | fatto (0.3/O5, QBE 0.4/O4) | Query statiche, INNER/LEFT JOIN, filtri, gruppi OR e QBE read-only |
| Query Results | `16`, `17` | `dbx/ui/query_results.py` | fatto (0.3/O6) | Griglia read-only, aggiornamento ed export CSV |
| Form Expert | `22`–`26` | `dbx/designers/form_expert.py` | fatto | Sorgente tabella o query (read-only); miniatura layout strutturale |
| Form Designer | `27`–`31`, `40` | `dbx/designers/form_builder.py` | fatto | Palette in pannello ridimensionabile, non flottante; form query in sola lettura |
| Properties Inspector | `30`, `31`, `40` | `dbx/ui/widgets.py` | fatto | Albero condiviso con il Report Designer |
| Form Runtime | `40` | `dbx/runtime/form_runtime.py` | fatto | Dispatcher di azioni, non linguaggio di scripting; query read-only |
| Report Designer | `32`–`38`, `41` | `dbx/designers/report_builder.py` | fatto | Selezione singola; ordine delle bande di flusso fisso; sorgente query |
| Report Preview | `39` | `dbx/ui/report_preview.py` | fatto | Zoom persistente per sessione; pagina singola/continua; report su query |
| Program Editor | `31`, `32` | `dbx/designers/script_builder.py`, `dbx/designers/step_picker.py` | fatto (catalogo 0.5/O5) | Nessuna esecuzione passo-passo |
| Menu Designer | — | `dbx/designers/menu_builder.py` | fatto | Anteprima come menu bar, non popup sempre aperto |
| Project Editor/Builder | — | `dbx/designers/project_builder.py` | fatto | Build sincrono, senza barra di avanzamento |
| Label Designer | — | — | rimosso | Sostituito dal Database Designer ER |
| Interactive Tutor | `03` | — | fuori scope 0.3 | Non previsto nella 0.3 |
| About | `42`, `43` | `dbx/ui/main_window.py` | parziale | Testo e versione presenti; chrome Borland non replicato |

## Note

- Lo stato si riferisce alla struttura e al chrome, non al pixel-perfect. Il tema predefinito è Aurora; Silver resta selezionabile con `--theme silver`.
- Rendering canonici: `docs/reference/dbx-ui/renders/01-desktop.png` … `14-menu-progetto.png`;
  indice in `docs/reference/dbx-ui/README.md`.
- `10-desktop-mdi.png` mostra Browse e Form Designer nell'area MDI.
- `11-script-editor.png`, `12-menu-designer.png` e `13-project-editor.png` coprono gli strumenti O6.
- `15-database-designer.png`, `16-query-designer.png`, `17-query-results.png` coprono Database
  Designer, Query Designer e Query Results.
- `18-form-query.png` e `19-report-query.png` mostrano form e report alimentati da query.
- `20-table-expert.png` mostra il Table Expert introdotto nella 0.4.
- `21-query-expert.png` e `22-report-expert.png` mostrano i nuovi esperti guidati.
- `23-qbe-mode.png` mostra il Query Designer in modalità QBE, con example elements e righe OR.
- `24-script-step-picker.png` mostra il catalogo azioni categorizzato del Program Editor.
- Le checklist di collaudo, i test e i difetti noti accettati sono in `docs/qa-0.2.md` e
  `docs/qa-0.3.md`.
- Il Label Designer è stato rimosso: la categoria Etichette è stata sostituita da **Schema**.
- Query Designer, Query Results e le query come sorgente di form/report sono parte della release 0.3.0.
