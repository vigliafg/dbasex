# Stato di parità UI — dBX vs dBASE 5.5

Aggiornato: 2026-11-22 (Ondata 5)

Legenda: `fatto` = struttura e chrome coerenti; `parziale` = struttura presente ma da rifinire; `mancante` = non implementato.

| Finestra originale | Riferimento | Modulo dBX | Stato 0.1 | Target | Gap principale |
|---|---|---|---|---|---|
| Desktop + menu + SpeedBar | `01`, `43` | `dbx/ui/main_window.py` | fatto (O1, O4) | O1 | allinea/distribuisci attivi sul Form Designer |
| Navigator | `01`, `42`, `43` | `dbx/ui/navigator.py` | fatto (O2) | O2 | Query/Etichette/Immagini/Suoni/Cataloghi/Personalizzati disabilitate |
| Command Window | `01`, `02`, `04` | `dbx/ui/command_window.py` | fatto (O2) | O2 | comandi limitati a HELP/TABELLE/USE/RECORD/CLEAR/espressioni |
| Browse / Table | `07`, `11`, `18` | `dbx/ui/data_view.py` | fatto (O2) | O2 | `Struttura…` si apre in MDI (O3) |
| Table Structure | `08`, `09`, `13`, `14` | `dbx/designers/table_builder.py` | fatto (O3) | O3 | rinomina tabella rimandata; stampa minimale |
| Query Designer | `15`, `19`, `20`, `21` | — | mancante | 0.3 | non implementato |
| Query Results | `16`, `17` | — | mancante | 0.3 | non implementato |
| Form Expert | `22`–`26` | `dbx/designers/form_expert.py` | fatto (O4) | O4 | query non disponibili; miniatura layout strutturale |
| Form Designer | `27`–`31`, `40` | `dbx/designers/form_builder.py` | fatto (O4) | O4 | palette in pannello ridimensionabile, non flottante |
| Properties Inspector | `30`, `31`, `40` | `dbx/ui/widgets.py` | fatto (O4) | O4 | inspector condiviso anche col Report Designer in O5 |
| Program Editor | `31`, `32` | `dbx/designers/script_builder.py` | parziale | O6 | niente numeri di riga/syntax |
| Menu Designer | — | `dbx/designers/menu_builder.py` | parziale | O6 | chrome e anteprima |
| Project Editor/Builder | — | `dbx/designers/project_builder.py` | parziale | O6 | chrome e validazione visiva |
| Report Designer | `32`–`38`, `41` | `dbx/designers/report_builder.py` | fatto (O5) | O5 | selezione singola; ordine bande di flusso fisso |
| Report Preview | `39` | `dbx/ui/report_preview.py` | fatto (O5) | O5 | zoom persistente per sessione; pagina singola/continua |
| Label Designer | — | — | mancante | 0.3 | non implementato |
| Form Runtime | `40` | `dbx/runtime/form_runtime.py` | fatto (O4) | O4 | dispatcher di azioni, non linguaggio di scripting |

## Note

- Lo stato si riferisce alla struttura e al chrome, non al pixel-perfect.
- Baseline O0 (tema Silver): `docs/reference/dbx-ui/renders/01-desktop.png` … `09-command-window.png`.
- O1 aggiunge `10-desktop-mdi.png` con Browse e Form Designer aperti nell'area MDI.
- O4 aggiorna `05-form-designer.png` (tre zone, righelli, Inspector ad albero) e `06-form-runtime.png` (runtime con barra di navigazione).
- O5 aggiorna `07-report-designer.png` (foglio a bande impilate, due toolbar) e `08-report-preview.png` (toolbar inferiore completa).
- Ogni ondata aggiorna questa tabella.
