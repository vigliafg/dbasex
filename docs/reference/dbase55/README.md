# Riferimenti visivi — dBASE 5.5 for Windows (Borland)

Raccolta di schermate originali usata come riferimento per replicare l'interfaccia di dBX.
Le immagini **non** sono asset dell'applicazione: servono solo come documentazione di progetto.

## Fonti

| Fonte | Cosa contiene | URL |
|---|---|---|
| Borland — *dBASE 5.0 for Windows Evaluator's Guide* (1995-96), figure 1–40 | Tutte le finestre del prodotto: desktop, Navigator, Command Window, Table Structure, Query Designer, FormExpert, Form Designer, Property Inspector, Program Editor, Crystal Reports | <https://web.archive.org/web/19961221164303/http://www.borland.com/VdBASE/vdbprev/db5win/db5win.html> |
| WinWorld — dBASE 5.x screenshots | Form Designer, Crystal Reports, Navigator + About Visual dBASE 5.5 | <https://winworldpc.com/product/dbase/v> |
| Gladir — Visual dBASE présentation | Desktop 5.5 con Navigator, Command Window e finestra About | <https://www.gladir.com/SOFTWARE/VISUALDBASE/presentation.htm> |

La guida Borland è relativa a dBASE 5.0 for Windows: l'interfaccia è la stessa di Visual dBASE 5.5,
cambiano solo il nome nella barra del titolo e la finestra About (confronta `42-…` con `43-…`).

## Indice delle immagini

Cartella `images/`.

### Desktop, Navigator, Command Window

| File | Schermata |
|---|---|
| `01-desktop-navigator-command.gif` | Desktop completo: menu `File Edit Program Table Properties Window Help`, SpeedBar, Navigator a sinistra, Command Window a destra |
| `02-command-window-pane.gif` | Dettaglio del riquadro comandi (pannello superiore di input) |
| `03-interactive-tutor.gif` | Finestra dell'Interactive Tutor (categorie a sinistra, lezioni a destra) |
| `04-command-results-dbase4-app.gif` | Applicazione dBASE IV eseguita dentro la finestra Command Results |
| `05-speedmenu-object.gif` | SpeedMenu contestuale su un oggetto del form |
| `42-navigator-about55-winworld.png` | Navigator 5.5: colonna icone (All, Tables, Queries, Forms, Reports, Labels, Programs, Images, Sounds, Catalogs, Custom), filtro `Table Files (*.DBF; *.DB)`, campo Current Directory, finestra About |
| `43-desktop-55-gladir.jpg` | Desktop Visual dBASE 5.5 con About, Navigator e Command Window affiancati |

### Tabelle e Browse

| File | Schermata |
|---|---|
| `06-table-records-properties.gif` | Dialogo a schede delle proprietà di tabella/browse (Editing Options, Scope, Index Range) |
| `07-browse-inspector-tabs.gif` | Browse Inspector con schede in basso |
| `08-table-structure-new.gif` | `Table Structure (Untitled)`: Name, Type (DBASE), Updated, Bytes Used, Records, Bytes Left; griglia Field/Name/Type/Width/Decimal/Index |
| `09-table-structure-fields.gif` | Table Structure mentre si aggiungono campi con Tab/Invio |
| `10-save-table-dialog.gif` | Dialogo Save Table |
| `11-table-add-records.gif` | Comando `Table | Add Records` su tabella aperta |
| `12-editing-options-panel.gif` | Pannello Editing Options (Append, Edit, …) |
| `13-table-structure-modify.gif` | Table Structure riaperta dopo `Open Exclusive` |
| `14-table-field-drag.gif` | Riordino di un campo trascinandone il bordo |

### Query Designer

| File | Schermata |
|---|---|
| `15-query-designer-contacts.gif` | Query Designer con tutte le colonne di CONTACTS.DBF e la SpeedBar |
| `16-query-results.gif` | Finestra Query Results |
| `17-query-results-filtered.gif` | Query Results filtrata sul campo COMPANY |
| `18-system-dbf-table.gif` | Tabella SYSTEM.DBF in browse |
| `19-query-designer-system.gif` | Query Designer su SYSTEM.DBF |
| `20-query-designer-system-contacts.gif` | Query Designer con SYSTEM.DBF collegata a CONTACTS.DBF |
| `21-query-designer-confinan.gif` | Query Designer con CONFINAN.DBF come tabella padre |

### Form Expert e Form Designer

| File | Schermata |
|---|---|
| `22-formexpert-step1.gif` | Form Expert, passo 1: Expert Assistance / Blank Form |
| `23-formexpert-step2.gif` | Passo 2: scelta tabella o query |
| `24-formexpert-step3.gif` | Passo 3: scelta campi |
| `25-formexpert-step4.gif` | Passo 4: schema di layout |
| `26-formexpert-step5.gif` | Passo 5: font, colori, stile dei campi |
| `27-form-designer-formexpert.gif` | Form Designer con il form generato dall'Expert (griglia di punti, righelli) |
| `28-form-reordered-fields.gif` | Form con campi riordinati |
| `29-form-designer-controls.gif` | Form con pulsanti di navigazione, palette Controls a destra, pulsanti Command e Navigator in basso a sinistra |
| `30-property-inspector.gif` | Properties Inspector con gruppo `Font Properties` espanso e schede Properties/Events/Methods |
| `31-program-editor-text1.gif` | Program Editor con le proprietà di TEXT1 |
| `40-form-designer-winworld.png` | Form Designer di Visual dBASE 5.5 con Control Palette e Field Palette flottanti e status bar `Order: 5  Page: 1  Top: 1.18  Left: 14.50  Height: 1.18  Width: 6.83` |

### Report (Crystal Reports for dBASE)

| File | Schermata |
|---|---|
| `32-crystal-reports-desktop.gif` | Desktop Crystal Reports + dialogo Insert Database Field |
| `33-report-field-dropped.gif` | Report con il campo COMPANY inserito |
| `34-report-resize-field.gif` | Ridimensionamento di un campo del report |
| `35-report-modified.gif` | Report modificato con i campi ridimensionati |
| `36-edit-text-field.gif` | Dialogo Edit Text Field |
| `37-report-title-added.gif` | Report con titolo |
| `38-record-sort-order.gif` | Dialogo Record Sort Order (Report Fields / Sort Fields / Sort Direction) |
| `39-report-preview.gif` | Preview Window con barra strumenti di anteprima (1 of 1, zoom, stampa, Close, 10 of 10, Total: 10, 100%) |
| `41-crystal-reports-winworld.png` | Crystal Reports 5.5 con bande Page header / Details / Page footer e status bar `Invoices  L:1.00  R:4.46` |

## Schermate non ancora reperite

Non esistono screenshot pubblici affidabili di: **Menu Designer**, **Label Designer**, **Application Builder**,
**Project Manager/Catalog Window**, **SpeedFilter**, **report wizard**. Per queste finestre il riferimento è la
documentazione testuale (manuali Borland, knowledge base dBASE) e l'analogia con le finestre qui archiviate;
vanno ricostruite per coerenza, non copiate.

## Uso

- `ui-spec.md` descrive nel dettaglio l'anatomia di ogni finestra (menu, barre, palette, status bar) e la
  corrispondenza con i moduli di dBX: è il documento da seguire per la replica.
- `gallery.html` mostra tutte le immagini in un'unica pagina autonoma: le schermate sono incorporate come data URI, quindi si vedono anche aprendo il solo file (o la preview) senza la cartella `images/` accanto.
