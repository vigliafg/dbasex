# Collaudo della release 0.2.1

Data: 2026-11-22. Riferimento visivo: 43 schermate in `docs/reference/dbase55/images/`.
Rendering dBX: `docs/reference/dbx-ui/renders/`.

## Comandi eseguiti

```bash
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
python tools/capture_ui.py
python tools/capture_ui.py --theme dark
```

Esito: suite `207 passed`, smoke OK, cattura Aurora e Dark OK.

## Checklist finestra per finestra

| Finestra | Riferimento | Esito | Note |
|---|---|---|---|
| Desktop + menu + SpeedBar + status | `01`, `43` | OK | Sequenza menu dBASE, toolbar a icone raggruppate, quattro campi di stato; versione 0.2.1 visibile |
| Navigator | `01`, `42`, `43` | OK | Categorie con icona, `[Untitled]`, filtro, directory; categorie fuori scope disabilitate con tooltip |
| Command Window | `01`, `02`, `04`, `43` | OK | Due riquadri non modali nell'MDI, cronologia, stato |
| Browse / Table | `07`, `11`, `18` | OK | Intestazione scura, selettore, navigazione, filtro, ordinamento, editing |
| Table Structure | `08`, `09`, `13`, `14` | OK | Griglia unica, metadati, toolbar, schede; rinomina tabella rimandata al motore |
| Form Expert | `22`–`26` | OK | Cinque passi, assistito/vuoto, campi, layout, stile; miniatura strutturale |
| Form Designer | `27`–`31`, `40` | OK | Tre zone, righelli, griglia 8 px, maniglie reali, pagine, Inspector ad albero |
| Properties Inspector | `30`, `31`, `40` | OK | Albero con gruppi, combo in-cell, `.T./.F.`, schede Proprietà/Eventi/Metodi |
| Form Runtime | `40` | OK | Navigazione, CRUD, stato, sottomaschere, eventi come azioni singole |
| Report Designer | `32`–`38`, `41` | OK | Bande impilate etichettate, divider trascinabili, due toolbar, dialoghi |
| Report Preview | `39` | OK | Pagina singola/continua, fit-width, zoom persistente, totale, stampa, PDF |
| Program Editor | `31`, `32` | OK | Numeri di riga, sintassi, vista bidirezionale, inspector, log |
| Menu Designer | — | OK | Albero voci/separatori, azioni tipizzate, anteprima |
| Project Editor / Builder | — | OK | Albero oggetti, impostazioni, validazione, build |
| Query Designer / Query Results | `15`–`21` | Fuori scope 0.2 | Previsti per la 0.3; categorie Navigator disabilitate |
| Label Designer | — | Fuori scope 0.2 | Previsto per la 0.3 |
| Interactive Tutor / About | `03`, `42`, `43` | Parziale | About presente; Tutor non previsto nella 0.2 |

## Verifiche trasversali

- **JSON 0.1**: apertura senza migrazione; i campi `events`, `methods`, `band_order`, `band_heights`,
  `band_visible`, `sort_fields`, `groups`, `underline`, `font_name`, colori hanno default vuoti.
- **Eventi**: un `onClick` valorizzato sostituisce l'azione del pulsante; un'azione errata finisce in
  `event_log` e nella status line senza crash.
- **Tema Aurora**: menu bar, toolbar, Navigator, area MDI, schede, tabelle, status bar e pannelli sono
  colorati con gradienti; nessuno sfondo grigio residuo nelle zone principali.
- **Menu icona + descrizione**: tutte le voci dei menu principali mostrano icona, titolo, descrizione
  e scorciatoia; frecce, Invio e Invio a capo funzionano.
- **Tema Dark**: tutti i canvas leggono `dbx_theme`; bande report e superfici form restano leggibili;
  lo sfondo MDI segue il tema attivo anche dopo il cambio a runtime.
- **Accessibilità**: nomi accessibili sui controlli principali, focus visibile, ordine di tabulazione
  nei pannelli chiave, scorciatoie documentate in README e nella guida `F1`.
- **HiDPI**: icone 16–48 px, politica di scala `PassThrough`, righelli coerenti a 125% e 150%.
- **Prestazioni**: apertura progetto demo < 2 s; form con 100 controlli costruito e caricato < 2 s
  (`tests/test_performance.py`).
- **CI**: test headless su Linux/Windows/macOS, smoke, cattura screenshot e artifact su Linux;
  `PyQt6==6.10.2`.
- **Tema storico**: `--theme silver` conserva il chrome dBASE 5.5; `--theme dark` resta opzionale.

## Screenshot rigenerati

`01-desktop`, `02-navigator`, `03-browse-clienti`, `04-table-structure`, `05-form-designer`,
`06-form-runtime`, `07-report-designer`, `08-report-preview`, `09-command-window`,
`10-desktop-mdi`, `11-script-editor`, `12-menu-designer`, `13-project-editor`,
`14-menu-progetto`.

## Difetti corretti durante il collaudo

- Intestazione di gruppo del report: `[cliente]` non veniva interpolato nei testi fissi.
- Totale di conteggio: accettava solo espressioni con parentesi e ignorava i valori non numerici.
- Palette del Form Designer: nomi dBASE lunghi troncati e lista campi troppo corta.
- Pulsanti con solo icona: nome accessibile mancante e focus non visibile.
- Versione applicativa e metadati ancora a 0.1.0.
- Menu bar e pulsanti delle toolbar senza tema colorato; sostituiti dal tema Aurora.
- Voci di menu senza icona o descrizione; ricostruite con il sistema icona + descrizione.

## Difetti noti accettati per la 0.2

- Palette non flottante; Report Designer a selezione singola.
- Ordine personalizzato delle bande di flusso non invertibile.
- Build sincrona; nessun debugger passo-passo.
- Anteprima menu come barra, non popup sempre aperto.
