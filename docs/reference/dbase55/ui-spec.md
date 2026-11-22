# Specifica di replica dell'interfaccia — dBASE 5.5 for Windows

Documento operativo ricavato dalle schermate in `images/`. Descrive **com'è fatta** ogni finestra
originale e **come deve apparire in dBX**. Dove l'originale usa Win16/MDI, dBX usa Qt6 ma con la stessa
struttura visiva.

## 1. Cromo comune (tutte le finestre)

| Elemento | Originale | Replica in dBX |
|---|---|---|
| Barra del titolo | grigio Windows, testo centrato `dBASE 5.0 for Windows` / `Visual dBASE`; nel designer `Form Designer (Untitled)` | `dBX — <progetto>`; nei designer `<Oggetto> (nome)` |
| Barra dei menu | `File Edit View Layout Procedure Properties Window Help` (designer); `File Edit Program Table Properties Window Help` (desktop); `File Edit View Navigator Properties Window Help` (Navigator) | stessi gruppi, in italiano ma con la stessa sequenza: `Progetto Modifica Visualizza Oggetto Procedure Proprietà Finestra ?` |
| SpeedBar | una riga di pulsanti **con icona**, raggruppati da separatori: Nuovo/Apri/Salva/Stampa · Taglia/Copia/Incolla · Annulla · strumenti oggetto · allineamento · Esegui (fulmine) · Command Window · Guida (?) | `QToolBar` non flottante, `ToolButtonTextBesideIcon` disattivato ma **icona + tooltip**; gruppi separati |
| Barra di stato | riquadri: `Pos: 10, 64` · nome oggetto selezionato (`ENTRYFIELD1`) · indice record (`Order: 3`) | `QStatusBar` con campi permanenti: coordinate, oggetto, record |
| Bordi e pannelli | grigio argento `#c0c0c0`, bordi 1 px neri infossati, pulsanti in rilievo | QSS: pannelli `#c0c0c0`, `border: 1px solid #808080`, pulsanti con bordo chiaro in alto a sinistra e scuro in basso a destra |
| Aree documento | bianco puro; superficie di design grigio chiaro con **griglia di punti** ogni 8 px | idem, griglia disegnata in `paintEvent` |
| Tipografia | MS Sans Serif 8 pt per l'interfaccia, Times New Roman 10 pt nei report, Courier per il codice | `MS Sans Serif`/`Segoe UI` 9 px, Times New Roman nei report, monospace per codice |
| Finestre flottanti | palette e inspector sono finestre tool non modali, con barra del titolo propria e pulsante di chiusura | `QDockWidget` flottanti o `Qt.WindowType.Tool` |
| Finestre documento | MDI: più designer aperti dentro la finestra principale, ognuno con titolo, riduci/ingrandisci | `QMdiArea` (oggi dBX usa QDialog modali: da convertire) |

Colori di selezione: navy `#000080` con testo bianco; focus tratteggiato 1 px (marching ants) attorno al controllo selezionato.

## 2. Desktop / Navigator / Command Window

**Navigator** (`01`, `42`, `43`)
- colonna sinistra larga ~110 px: pulsanti verticali con icona sopra e testo sotto: `All`, `Tables`, `Queries`,
  `Forms`, `Reports`, `Labels`, `Programs`, `Images`, `Sounds`, `Catalogs`, `Custom`. Il pulsante attivo è infossato.
- in alto a destra: `Current Directory` con campo edit e pulsante `…`.
- elenco file: combo filtro (`Table Files (*.DBF; *.DB)`), lista con icona tipo file + nome, voce `[Untitled]` in cima
  per creare un nuovo oggetto della categoria, `Company.dbf` come intestazione di colonna.
- doppio clic = apri; trascinamento = associa.
- status bar: suggerimento contestuale (`Cliquez ici pour commencer`).

**Command Window** (`01`, `02`, `04`, `43`)
- finestra divisa in due riquadri sovrapposti: `Command` (input) e `Command Results` (output), ciascuno con la propria barra del titolo.
- i comandi si possono digitare uno per riga; i risultati restano scorrevoli.

**Interactive Tutor** (`03`): elenco categorie a sinistra, elenco lezioni a destra, pulsante di avvio.

**About** (`42`, `43`): logo Borland, `Visual dBASE Version 5.5`, copyright, memoria/GDI/User resources; pulsante OK.

## 3. Table Builder — `Table Structure` (`08`, `09`, `13`, `14`)

- finestra `Table Structure (Untitled)`, non ridimensionabile in larghezza.
- riga 1: `Name:` campo edit · `Type:` combo (`DBASE`, `Paradox`, …).
- blocco metadati: `Updated:` data, `Bytes Used:`, `Records:`, `Bytes Left:`.
- griglia: colonne `Field` (numero riga), `Name`, `Type`, `Width`, `Decimal`, `Index` (None / valore).
- la riga attiva è alta il doppio; `Tab`/`Invio` crea il campo successivo; trascinare il bordo sinistro riordina i campi.
- toolbar della finestra: `Open Exclusive`, `Add Records`, `Save As`, stampa.
- dialoghi collegati: `Save Table` (`10`), proprietà tabella a schede (`06`, `12`), Browse Inspector (`07`).

## 4. Query Designer (`15`, `19`, `20`, `21`) e Query Results (`16`, `17`)

- finestra `Query Designer [Untitled]`: in alto una riga per ogni tabella coinvolta, con il nome su un pulsante
  e accanto le colonne dei campi; ogni colonna ha icona (chiave se indicizzato), casella di inclusione e riga di condizione.
- unire due tabelle = trascinare il campo della prima sul campo della seconda (relazione indicata da una linea).
- toolbar: `New Query`, `Design Query`, `Add Relation`, `Run`, `Save`.
- `Query Results` è una griglia in sola lettura con la stessa intestazione del Browse.

## 5. Form Expert (`22`–`26`) e Form Designer (`27`–`31`, `40`)

**Form Expert** — finestra `Form Expert`, 5 passi, pulsanti `Cancel`, `Help`, `Next` in basso:
1. introduzione + scelta `Expert Assistance` / `Blank Form`;
2. scelta tabella o query;
3. scelta dei campi (liste sorgente/destinazione con frecce);
4. scelta del layout (radio button, miniatura di anteprima);
5. font, colori, stile dei campi.

**Form Designer** (finestra documento con righelli)
- barra del titolo `Form Designer (Untitled)`, pulsanti riduci/ingrandisci.
- **righello orizzontale in alto e verticale a sinistra**, tacche ogni 5 unità, etichette ogni 10, origine nell'angolo.
- superficie di lavoro grigia con griglia di punti, bordata 1 px; il form è un rettangolo bianco.
- controlli con maniglie di ridimensionamento, selezione con bordo tratteggiato.
- **palette Controls** flottante a destra: intestazione `Controls`, prima voce `Pointer`, poi pulsanti con icona e
  nome: `OKBUTTON CLOSEBUTTON CANCELBUTTON HELPBUTTON NOBUTTON NEXTBUTTON PREVBUTTON INFOBUTTON TOOLBUTTON
  REPORTBUTTON BROWSEBUTTON NEXTRECORD PREVRECORD ADDRECORD`; schede in basso `Standard` / `Custom`.
- **palette Field** flottante: elenco dei campi della tabella con icona e nome, schede per tipo; doppio clic o
  trascinamento crea il campo (con etichetta automatica).
- in basso a sinistra della finestra principale: due pulsanti icona+testo `Command` e `Navigator`.
- status bar: `Order: 5  Page: 1  Top: 1.18  Left: 14.50  Height: 1.18  Width: 6.83`.

**Properties Inspector** (`30`, `31`, `40`)
- finestra `Properties (Untitled)` con combo in alto contenente il nome completo dell'oggetto (`form.entryfield1`).
- elenco ad albero delle proprietà raggruppate (`• Font Properties` espandibile con `FontBold .T.`, `FontItalic .F.`,
  `FontName MS Sans Serif`, `FontSize 8.00`, `FontStrikeOut .F.`, `FontUnderline .F.`), valori modificabili in-place.
- schede in basso: `Properties` / `Events` / `Methods`.
- riga di filtro `Quick Filter`.

**Program Editor** (`31`, `32`): editor testuale con numeri di riga, parole chiave in grassetto, pannello proprietà laterale.

## 6. Report (Crystal Reports for dBASE) (`32`–`39`, `41`)

- barra del titolo `Crystal Reports for dBASE`.
- menu: `File Edit Insert Format Database Report Window Help`.
- due toolbar: standard (nuovo/apri/salva/stampa, taglia/copia/incolla, annulla, inserisci campo, ordinamento,
  totali, grafici) e formattazione (combo font, combo corpo, Grassetto/Corsivo/Sottolineato, allineamenti,
  bordi, colore, percentuali).
- area di lavoro con **bande** etichettate a sinistra: `Page header`, `Details`, `Page footer`; righello in alto;
  griglia tratteggiata; delimitatori di banda trascinabili.
- dialoghi: `Insert Database Field` (elenco `TABELLA->CAMPO`, pulsanti `Insert`, `Done`, `Browse Field Data…`),
  `Edit Text Field`, `Record Sort Order` (`Report Fields` / `Add` / `<- Remove` / `Sort Fields` / `Sort Direction`).
- anteprima `Preview Window: Untitled Report #1`: pagina bianca, toolbar inferiore con primo/precedente/successivo/ultimo,
  `1 of 1`, zoom, stampa, esporta, fax, `Close`, `10 of 10`, `Total: 10`, `100%`.
- status bar: `Invoices   L:1.00   R:4.46`.

## 7. Corrispondenza con dBX 0.2

La tabella di dettaglio, con stato e gap residui, è in `../../ui-parity.md`; la checklist di collaudo
è in `../../qa-0.2.md`. Sintesi:

| Finestra originale | Modulo dBX | Stato 0.2 | Nota |
|---|---|---|---|
| Desktop + menu + SpeedBar + status | `dbx/ui/main_window.py` | fatto | Sequenza menu dBASE, toolbar a icone, status a campi, MDI |
| Navigator | `dbx/ui/navigator.py` | fatto | Categorie, filtro, directory, `[Untitled]`; categorie 0.3 disabilitate |
| Command Window | `dbx/ui/command_window.py` | fatto | Due riquadri non modali nell'MDI |
| Browse / Table | `dbx/ui/data_view.py` | fatto | Selettore, navigazione, filtro, ordinamento, editing |
| Table Structure | `dbx/designers/table_builder.py` | fatto | Griglia unica e metadati; rinomina tabella rimandata al motore |
| Query Designer / Query Results | — | fuori scope 0.2 | Previsti per la 0.3 |
| Form Expert | `dbx/designers/form_expert.py` | fatto | Wizard a cinque passi |
| Form Designer | `dbx/designers/form_builder.py` | fatto | Tre zone, righelli, maniglie, Inspector ad albero |
| Properties Inspector | `dbx/ui/widgets.py` | fatto | Albero condiviso con il Report Designer |
| Form Runtime | `dbx/runtime/form_runtime.py` | fatto | CRUD, sottomaschere, eventi come azioni singole |
| Report Designer | `dbx/designers/report_builder.py` | fatto | Bande impilate, due toolbar, dialoghi |
| Report Preview | `dbx/ui/report_preview.py` | fatto | Pagina singola/continua, zoom, stampa, PDF |
| Program Editor | `dbx/designers/script_builder.py` | fatto | Numeri di riga, sintassi, vista bidirezionale |
| Menu Designer | `dbx/designers/menu_builder.py` | fatto | Albero, azioni tipizzate, anteprima |
| Project Editor / Builder | `dbx/designers/project_builder.py` | fatto | Validazione e build |
| Label Designer | — | fuori scope 0.2 | Previsto per la 0.3 |
| Interactive Tutor / About | `dbx/ui/main_window.py` | parziale | About presente; Tutor non previsto nella 0.2 |

Le palette dei designer sono pannelli ridimensionabili, non finestre tool flottanti; il target resta
clone strutturale e chrome, non pixel-perfect Win16.

## 8. Ordine di lavoro seguito nella 0.2

1. QSS "Win95" (grigio argento, bordi infossati, pulsanti 3D) e tipografia: cambia l'aspetto di **tutte** le finestre in un colpo.
2. Desktop: menu originali, toolbar a gruppi, status bar a campi, pulsanti `Command`/`Navigator`.
3. Navigator a colonna icone + Command Window a due riquadri.
4. Form Designer a tre zone con anteprima live (palette Controls/Field, Inspector a schede, righelli).
5. Table Structure unificata.
6. Report Designer + Preview con toolbar originale.
7. Wizard (Form Expert) e Query Designer.

I punti 1–6 sono stati completati nella 0.2; il Form Expert è incluso. Query Designer, Query Results
e Label Designer sono rinviati alla 0.3.
