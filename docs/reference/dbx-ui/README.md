# Rendering dell'interfaccia dBX

Questa cartella contiene gli screenshot canonici dell'interfaccia **Aurora** (0.3.0), generati con:

```bash
python tools/capture_ui.py
python tools/capture_ui.py --theme dark
```

La cattura usa il progetto demo, gira headless e scrive in `renders/`. I file in `renders/` sono
l'unica fonte di verità per README, `docs/ui-parity.md`, `docs/qa-0.2.md` e `docs/qa-0.3.md`.

| File | Finestra |
|---|---|
| `01-desktop.png` | Desktop vuoto con menu, SpeedBar, Navigator e barra di stato |
| `02-navigator.png` | Navigator isolato |
| `03-browse-clienti.png` | Browse della tabella clienti |
| `04-table-structure.png` | Table Structure |
| `05-form-designer.png` | Form Designer a tre zone |
| `06-form-runtime.png` | Runtime del form con dati reali |
| `07-report-designer.png` | Report Designer a bande impilate |
| `08-report-preview.png` | Preview del report |
| `09-command-window.png` | Command Window |
| `10-desktop-mdi.png` | Desktop MDI con Browse e Form Designer |
| `11-script-editor.png` | Program Editor MiniScript |
| `12-menu-designer.png` | Menu Designer |
| `13-project-editor.png` | Project Editor |
| `14-menu-progetto.png` | Menu Progetto con icona + descrizione |
| `15-database-designer.png` | Database Designer ER con tabelle e relazioni |
| `16-query-designer.png` | Query Designer con campi, join e risultato |
| `17-query-results.png` | Query Results in sola lettura con export CSV |
| `18-form-query.png` | Form runtime alimentato da una query, sola lettura |
| `19-report-query.png` | Report a bande su query con gruppi e totali |
| `20-table-expert.png` | Table Expert con template, campi e riepilogo |
| `21-query-expert.png` | Query Expert con join suggeriti dalle foreign key |
| `22-report-expert.png` | Report Expert con scelta del layout |

Per il tema storico usare `--theme silver`; per il tema scuro `--theme dark`. Le immagini della 0.1
nella cartella superiore sono state rimosse: restano nella storia git e sono superate da questa serie.
