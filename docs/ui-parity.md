# Stato di parità UI — dBX vs dBASE 5.5

Aggiornato: 2026-11-22 (Ondata 0)

Legenda: `fatto` = struttura e chrome coerenti; `parziale` = struttura presente ma da rifinire; `mancante` = non implementato.

| Finestra originale | Riferimento | Modulo dBX | Stato 0.1 | Target | Gap principale |
|---|---|---|---|---|---|
| Desktop + menu + SpeedBar | `01`, `43` | `dbx/ui/main_window.py` | parziale | O1 | MDI assente, menu incompleti, toolbar con testo |
| Navigator | `01`, `42`, `43` | `dbx/ui/navigator.py` | parziale | O2 | categorie ridotte, filtro legacy, `[Untitled]` per categoria |
| Command Window | `01`, `02`, `04` | `dbx/ui/command_window.py` | parziale | O2 | dialog non MDI, cronologia assente |
| Browse / Table | `07`, `11`, `18` | `dbx/ui/data_view.py` | parziale | O2 | intestazione, selettore record, navigazione |
| Table Structure | `08`, `09`, `13`, `14` | `dbx/designers/table_builder.py` | parziale | O3 | schede invece di griglia unica, metadati |
| Query Designer | `15`, `19`, `20`, `21` | — | mancante | 0.3 | non implementato |
| Query Results | `16`, `17` | — | mancante | 0.3 | non implementato |
| Form Expert | `22`–`26` | — | mancante | O4 | wizard assente |
| Form Designer | `27`–`31`, `40` | `dbx/designers/form_builder.py` | parziale | O4 | maniglie non funzionanti, palette verticale, eventi readonly |
| Properties Inspector | `30`, `31`, `40` | `dbx/ui/widgets.py` | parziale | O4 | form piatto, niente albero/gruppi |
| Program Editor | `31`, `32` | `dbx/designers/script_builder.py` | parziale | O6 | niente numeri di riga/syntax |
| Menu Designer | — | `dbx/designers/menu_builder.py` | parziale | O6 | chrome e anteprima |
| Project Editor/Builder | — | `dbx/designers/project_builder.py` | parziale | O6 | chrome e validazione visiva |
| Report Designer | `32`–`38`, `41` | `dbx/designers/report_builder.py` | parziale | O5 | una banda per volta, no toolbar doppia, no dialoghi |
| Report Preview | `39` | `dbx/ui/report_preview.py` | parziale | O5 | toolbar inferiore incompleta |
| Label Designer | — | — | mancante | 0.3 | non implementato |

## Note

- Lo stato si riferisce alla struttura e al chrome, non al pixel-perfect.
- Baseline O0 (tema Silver): `docs/reference/dbx-ui/renders/01-desktop.png` … `09-command-window.png`.
- Ogni ondata aggiorna questa tabella.
