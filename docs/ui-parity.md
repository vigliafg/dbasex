# Stato di parità UI — dBX 0.2 vs dBASE 5.5

Aggiornato: 2026-11-22 (release 0.2.0, Checkpoint C)

Legenda: `fatto` = struttura e chrome coerenti; `parziale` = struttura presente ma da rifinire;
`fuori scope` = escluso dalla 0.2 per decisione di piano; `mancante` = non implementato.

| Finestra originale | Riferimento | Modulo dBX | Stato 0.2 | Gap principale |
|---|---|---|---|---|
| Desktop + menu + SpeedBar | `01`, `43` | `dbx/ui/main_window.py` | fatto | — |
| Navigator | `01`, `42`, `43` | `dbx/ui/navigator.py` | fatto | Query/Etichette/Immagini/Suoni/Cataloghi/Personalizzati disabilitate |
| Command Window | `01`, `02`, `04` | `dbx/ui/command_window.py` | fatto | Comandi limitati a HELP/TABELLE/USE/RECORD/CLEAR/espressioni |
| Browse / Table | `07`, `11`, `18` | `dbx/ui/data_view.py` | fatto | — |
| Table Structure | `08`, `09`, `13`, `14` | `dbx/designers/table_builder.py` | fatto | Rinomina tabella rimandata al motore; stampa minimale |
| Query Designer | `15`, `19`, `20`, `21` | — | fuori scope 0.2 | Previsto per la 0.3 |
| Query Results | `16`, `17` | — | fuori scope 0.2 | Previsto per la 0.3 |
| Form Expert | `22`–`26` | `dbx/designers/form_expert.py` | fatto | Query non disponibili; miniatura layout strutturale |
| Form Designer | `27`–`31`, `40` | `dbx/designers/form_builder.py` | fatto | Palette in pannello ridimensionabile, non flottante |
| Properties Inspector | `30`, `31`, `40` | `dbx/ui/widgets.py` | fatto | Albero condiviso con il Report Designer |
| Form Runtime | `40` | `dbx/runtime/form_runtime.py` | fatto | Dispatcher di azioni, non linguaggio di scripting |
| Report Designer | `32`–`38`, `41` | `dbx/designers/report_builder.py` | fatto | Selezione singola; ordine delle bande di flusso fisso |
| Report Preview | `39` | `dbx/ui/report_preview.py` | fatto | Zoom persistente per sessione; pagina singola/continua |
| Program Editor | `31`, `32` | `dbx/designers/script_builder.py` | fatto | Nessuna esecuzione passo-passo |
| Menu Designer | — | `dbx/designers/menu_builder.py` | fatto | Anteprima come menu bar, non popup sempre aperto |
| Project Editor/Builder | — | `dbx/designers/project_builder.py` | fatto | Build sincrono, senza barra di avanzamento |
| Label Designer | — | — | fuori scope 0.2 | Previsto per la 0.3 |
| Interactive Tutor | `03` | — | fuori scope 0.2 | Non previsto nella 0.2 |
| About | `42`, `43` | `dbx/ui/main_window.py` | parziale | Testo e versione presenti; chrome Borland non replicato |

## Note

- Lo stato si riferisce alla struttura e al chrome, non al pixel-perfect.
- Rendering canonici: `docs/reference/dbx-ui/renders/01-desktop.png` … `13-project-editor.png`;
  indice in `docs/reference/dbx-ui/README.md`.
- `10-desktop-mdi.png` mostra Browse e Form Designer nell'area MDI.
- `11-script-editor.png`, `12-menu-designer.png` e `13-project-editor.png` coprono gli strumenti O6.
- La checklist di collaudo, i test e i difetti noti accettati sono in `docs/qa-0.2.md`.
- Query Designer e Label Designer restano fuori dalla 0.2 per decisione di piano: le categorie del
  Navigator sono visibili ma disabilitate, così l'assenza è esplicita e non un errore.
