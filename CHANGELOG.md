# Changelog

Tutte le modifiche rilevanti di dBX. Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto usa [Semantic Versioning](https://semver.org/lang/it/).

## [0.2.0] — 2026-11-22

Release della parità strutturale con dBASE 5.5 for Windows: desktop MDI, designer a tre zone,
report a bande impilate, program editor e project editor.

### Aggiunto

- **Desktop MDI**: `QMdiArea` con finestre documento, menu `Progetto · Modifica · Visualizza ·
  Oggetto · Procedure · Proprietà · Finestra · ?`, SpeedBar a icone raggruppate e barra di stato
  con coordinate, oggetto, record e modalità.
- **Navigator**: categorie con icona, `[Untitled]` in cima, filtro file, directory corrente,
  azioni contestuali e nuove categorie Menu; Query, Etichette, Immagini, Suoni, Cataloghi e
  Personalizzati restano visibili ma disabilitate.
- **Command Window** nell'MDI con cronologia, stato e comandi `HELP`, `TABELLE`, `USE`, `RECORD`,
  `CLEAR` ed espressioni.
- **Browse**: selettore di record, barra di navigazione, filtro, ordinamento, modifica inline con
  rollback, opzioni di editing e persistenza delle larghezze colonna.
- **Table Structure** a griglia unica (`Field · Name · Type · Width · Decimal · Index`), metadati,
  toolbar, pannello proprietà, riordino a trascinamento, `Save As`, stampa e migrazioni con backup.
- **Form Designer** a tre zone: palette `Controls` / `Field`, canvas con righelli, griglia 8 px,
  otto maniglie reali, selezione multipla, clipboard, undo/redo, allineamento, distribuzione,
  z-order, pagine a schede, Object Inspector ad albero e Form Expert a cinque passi.
- **Eventi form**: `onClick`, `onEnter`, `onExit`, `onOpen`, `onClose` come azione singola dello
  stesso dispatcher dei pulsanti; errori registrati senza crash. Nessun linguaggio di scripting.
- **Runtime form** nell'MDI con navigazione, CRUD, stato del record, sottomaschere uno-a-molti,
  script, report e messaggi.
- **Report Designer** a foglio unico con bande impilate ed etichettate, delimitatori trascinabili,
  due toolbar (standard e formattazione), zoom 50–200%, dialoghi Insert Field, Edit Text,
  Record Sort Order, Insert Group e Total.
- **Modello report** esteso con `band_order`, `band_heights`, `band_visible`, `sort_fields` e
  `groups`; renderer con più livelli di raggruppamento, ordinamenti multipli e totali per livello.
- **Report Preview** con pagina singola/continua, fit-width, zoom persistente, totale pagine,
  aggiornamento, stampa ed export PDF.
- **Program Editor** MiniScript con numeri di riga, evidenziazione di parole chiave, stringhe,
  commenti e numeri, vista azioni ↔ sorgente bidirezionale, inspector dei parametri e log.
- **Menu Designer** ad albero con separatori, azioni tipizzate, filtro delle destinazioni e
  anteprima del menu.
- **Project Editor** con albero oggetti, impostazioni (`title`, `main_form`, `main_menu`),
  validazione visiva e build distribuibile.
- **Accessibilità**: nomi accessibili sui controlli principali, focus visibile su pulsanti e
  schede, ordine di tabulazione nei pannelli chiave e scorciatoie documentate.
- **HiDPI**: icona multi-risoluzione, `PassThrough` per il fattore di scala e righelli coerenti a
  125% e 150%.
- **CI**: test UI offscreen su Linux, Windows e macOS, smoke headless e artifact degli screenshot
  su Linux; `PyQt6==6.10.2` fissato.

### Cambiato

- `FormBuilderDialog`, `ReportBuilderDialog`, `ScriptBuilderDialog` e `MenuBuilderDialog` sono ora
  widget ospitati nell'MDI; restano come alias per compatibilità con test, smoke e script esterni.
- Il progetto demo e i report usano nomi visualizzati `TABELLA->CAMPO` e riferimenti `[campo]`
  interpolati anche nei testi fissi.
- `apply_theme` registra il tema attivo sull'applicazione, così i canvas leggono i token corretti.

### Corretto

- Il tema Dark non è più forzato sui token Silver nei canvas.
- I pulsanti delle toolbar non assumono più lo stile navy dei pulsanti predefiniti quando sono
  disabilitati.
- L'intestazione di gruppo dei report mostra il valore del campo invece del segnaposto `[campo]`.
- I totali di conteggio accettano nomi di campo nudi e contano anche valori non numerici.

### Note di aggiornamento

- I JSON di progetto 0.1 si aprono senza migrazione: i nuovi campi del modello hanno default vuoti.
- Query Designer e Label Designer non fanno parte della 0.2 e restano previsti per la 0.3.
- Gli screenshot di riferimento sono in `docs/reference/dbx-ui/renders/`.

[0.2.0]: https://github.com/vigliafg/dbasex/releases/tag/v0.2.0
