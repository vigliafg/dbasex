# Copertura funzionale E2E

Generato da `tools/e2e_coverage.py`. Non modificare a mano.

- Scenari registrati: **133**
- Feature di fase 1: **111/111**
- Feature di fase 2: **369/369**
- Feature di fase 3: **505/505**

## Fase 1 — coperta

| Feature | Area | Descrizione | Scenari |
|---|---|---|---|
| `DV-CALCULATED` | browse | Calcolati in sola lettura | `brw-04-calculated-readonly`, `tbl-06-calculated` |
| `DV-CHOICE` | browse | Editor Scelta | `brw-03-editors` |
| `DV-COLUMNS` | browse | Larghezza colonne persistente | `brw-10-columns-options` |
| `DV-CRUD` | browse | CRUD nella griglia | `brw-01-crud-navigation`, `brw-11-record-dialogs`, `jrn-02-sportello` |
| `DV-DELETE` | browse | Eliminazione record | `brw-11-record-dialogs` |
| `DV-EDIT-CELL` | browse | Editing in-place | `brw-01-crud-navigation`, `brw-02-validation-cell`, `brw-03-editors` |
| `DV-EMPTY` | browse | Tabella vuota | `brw-12-empty-boundary-refresh` |
| `DV-FILTER` | browse | Filtro rapido | `brw-09-sort-filter-status` |
| `DV-FIND` | browse | Find mode | `brw-05-find-operators`, `brw-06-find-dialog`, `brw-08-saved-finds`, `jrn-02-sportello` |
| `DV-FIND-AND` | browse | Criteri AND | `brw-05-find-operators`, `brw-06-find-dialog` |
| `DV-FIND-OMIT` | browse | Criterio Ometti | `brw-05-find-operators` |
| `DV-FIND-OR` | browse | Criteri OR | `brw-05-find-operators` |
| `DV-NAV` | browse | Navigazione record | `brw-01-crud-navigation`, `brw-12-empty-boundary-refresh` |
| `DV-NEW-DIALOG` | browse | Dialogo nuovo record | `brw-11-record-dialogs` |
| `DV-OPTIONS` | browse | Editing Options | `brw-10-columns-options` |
| `DV-REFRESH` | browse | Aggiornamento griglia | `brw-12-empty-boundary-refresh` |
| `DV-REPLACE` | browse | Sostituzione | `brw-07-replace` |
| `DV-REPLACE-CASE` | browse | Sostituzione con maiuscole | `brw-07-replace` |
| `DV-SAVED-FINDS` | browse | Ricerche salvate | `brw-08-saved-finds` |
| `DV-SORT` | browse | Ordinamento | `brw-09-sort-filter-status` |
| `DV-STATUS` | browse | Stato record | `brw-01-crud-navigation`, `brw-06-find-dialog`, `brw-09-sort-filter-status` |
| `DV-VALIDATION` | browse | Validazione per cella | `brw-02-validation-cell` |
| `CSV-CALCULATED` | data | Calcolati in import | `dat-02-csv-mapping` |
| `CSV-CLEAR-BACKUP` | data | Svuotamento con backup | `dat-04-csv-clear-backup` |
| `CSV-DETECT-DELIM` | data | Rilevamento delimitatore | `dat-01-csv-detect`, `jrn-03-import` |
| `CSV-DETECT-ENCODING` | data | Rilevamento codifica | `dat-01-csv-detect` |
| `CSV-EXPORT` | data | Export CSV | `dat-05-csv-export`, `jrn-03-import` |
| `CSV-EXPORT-CALC` | data | Export dei calcolati | `dat-05-csv-export` |
| `CSV-HEADER` | data | Gestione intestazione | `dat-01-csv-detect`, `dat-02-csv-mapping` |
| `CSV-MAPPING` | data | Mappatura colonne | `dat-02-csv-mapping`, `dat-03-csv-rejects`, `jrn-03-import` |
| `CSV-REJECTS` | data | Scarti di import | `dat-03-csv-rejects`, `dat-04-csv-clear-backup` |
| `CSV-TYPES` | data | Conversione tipi | `dat-02-csv-mapping` |
| `ER-CARD` | data | Card tabella compatta | `dat-06-er-diagram`, `dat-08-er-schema-edit` |
| `ER-EXPORT-PNG` | data | Export PNG | `dat-06-er-diagram` |
| `ER-EXPORT-SVG` | data | Export SVG | `dat-06-er-diagram` |
| `ER-INSPECTOR` | data | Ispettore tabella/relazione | `dat-06-er-diagram`, `dat-07-er-relation` |
| `ER-LAYOUT` | data | Auto-layout | `dat-06-er-diagram` |
| `ER-RELATION` | data | Creazione relazione | `dat-07-er-relation` |
| `ER-SCHEMA-EDIT` | data | Modifica schema dal diagramma | `dat-08-er-schema-edit` |
| `ER-VIEW` | data | Vista schema ER | `dat-06-er-diagram`, `dat-08-er-schema-edit` |
| `ER-ZOOM` | data | Zoom diagramma | `dat-06-er-diagram` |
| `MNT-BACKUP` | data | Backup | `dat-04-csv-clear-backup`, `dat-09-rename-refs`, `dat-11-maintenance`, `jrn-04-closing` |
| `MNT-COMPACT` | data | Compattazione | `dat-11-maintenance`, `jrn-04-closing` |
| `MNT-DUPLICATE` | data | Duplicazione oggetti | `dat-10-duplicate` |
| `MNT-DUPLICATE-DATA` | data | Duplicazione tabella con dati | `dat-10-duplicate` |
| `MNT-INTEGRITY` | data | Verifica integrità | `dat-11-maintenance` |
| `MNT-REEVALUATE` | data | Riapplica regole | `dat-12-reevaluate`, `jrn-03-import` |
| `MNT-RENAME-REFS` | data | Rinomina con riferimenti | `dat-09-rename-refs` |
| `PROJ-CLI` | project | Avvio da riga di comando | `proj-06-cli` |
| `PROJ-COMPAT` | project | Compatibilità artefatti legacy | `jrn-07-legacy`, `proj-04-legacy` |
| `PROJ-DEMO` | project | Progetto demo | `proj-02-demo` |
| `PROJ-NEW` | project | Nuovo progetto vuoto | `proj-01-new-empty` |
| `PROJ-RECENT` | project | Progetti recenti | `proj-08-recent` |
| `PROJ-SAVE` | project | Salvataggio e riapertura | `jrn-06-restart`, `proj-01-new-empty`, `proj-02-demo`, `proj-03-settings`, `proj-05-save-reopen` |
| `PROJ-SETTINGS` | project | Impostazioni progetto | `proj-03-settings` |
| `PROJ-THEME` | project | Temi Aurora/Silver/Dark | `proj-07-themes` |
| `TB-ADD-RECORDS` | tables | Aggiunta record dalla struttura | `tbl-12-migration-saveas` |
| `TB-BACKUP` | tables | Backup prima della migrazione | `dat-07-er-relation`, `tbl-12-migration-saveas` |
| `TB-CAPTION` | tables | Didascalia tabella | `tbl-01-new-minimal`, `tbl-03-field-attributes` |
| `TB-DDL` | tables | Anteprima DDL | `tbl-01-new-minimal` |
| `TB-EXPERT` | tables | Table Expert | `tbl-13-expert` |
| `TB-EXPERT-FIELDS` | tables | Campi Table Expert | `tbl-13-expert` |
| `TB-EXPERT-INDEXES` | tables | Indici Table Expert | `tbl-13-expert` |
| `TB-EXPERT-TEMPLATE` | tables | Template Table Expert | `tbl-13-expert` |
| `TB-FIELD-AUTODATE` | tables | Data automatica | `tbl-07-auto-enter` |
| `TB-FIELD-AUTOENTER` | tables | Auto-enter | `tbl-07-auto-enter` |
| `TB-FIELD-CALCULATED` | tables | Campo calcolato | `brw-04-calculated-readonly`, `tbl-06-calculated` |
| `TB-FIELD-CAPTION` | tables | Didascalia campo | `tbl-03-field-attributes` |
| `TB-FIELD-CASE` | tables | Normalizzazione maiuscole | `dat-12-reevaluate`, `tbl-10-domain-mask-case` |
| `TB-FIELD-CHOICE-BLANK` | tables | Scelta con vuoto | `tbl-08-choice-static` |
| `TB-FIELD-CHOICE-CASE` | tables | Scelta con maiuscole | `tbl-08-choice-static` |
| `TB-FIELD-CHOICE-COMBINE` | tables | Combinazione valori Scelta | `tbl-09-choice-dynamic` |
| `TB-FIELD-CHOICE-DYNAMIC` | tables | Scelta dinamica | `proj-04-legacy`, `tbl-09-choice-dynamic` |
| `TB-FIELD-CHOICE-LABELS` | tables | Etichette Scelta | `tbl-08-choice-static`, `tbl-09-choice-dynamic` |
| `TB-FIELD-CHOICE-OTHER` | tables | Scelta con testo libero | `tbl-08-choice-static` |
| `TB-FIELD-CHOICE-STATIC` | tables | Scelta statica | `tbl-08-choice-static` |
| `TB-FIELD-DEFAULT` | tables | Valore predefinito | `tbl-03-field-attributes` |
| `TB-FIELD-DOMAIN` | tables | Dominio numerico | `dat-12-reevaluate`, `tbl-10-domain-mask-case` |
| `TB-FIELD-DOMAIN-RANGES` | tables | Intervalli di dominio | `tbl-10-domain-mask-case` |
| `TB-FIELD-FORMAT` | tables | Formato campo | `tbl-03-field-attributes` |
| `TB-FIELD-INCREMENT` | tables | Incremento | `proj-04-legacy`, `tbl-07-auto-enter` |
| `TB-FIELD-MASK` | tables | Maschera input | `tbl-10-domain-mask-case` |
| `TB-FIELD-REQUIRED` | tables | Campo obbligatorio | `tbl-03-field-attributes`, `tbl-04-required-conditional` |
| `TB-FIELD-REQUIRED-IF` | tables | Obbligatorietà condizionale | `tbl-04-required-conditional` |
| `TB-FIELD-RULE` | tables | Regola di validazione | `tbl-05-rule` |
| `TB-FIELD-RULE-MSG` | tables | Messaggio regola | `tbl-05-rule` |
| `TB-FIELD-SKIP-IF` | tables | Salto condizionale | `tbl-04-required-conditional` |
| `TB-FK` | tables | Chiave esterna | `dat-07-er-relation`, `tbl-11-indexes-relations` |
| `TB-INDEX` | tables | Indice semplice | `tbl-11-indexes-relations` |
| `TB-INDEX-COMPOSITE` | tables | Indice composto | `tbl-11-indexes-relations` |
| `TB-INDEX-UNIQUE` | tables | Indice univoco | `tbl-11-indexes-relations` |
| `TB-MIGRATE` | tables | Migrazione struttura | `tbl-12-migration-saveas` |
| `TB-NEW` | tables | Nuova tabella | `proj-05-save-reopen`, `tbl-01-new-minimal`, `tbl-02-all-types` |
| `TB-ONDELETE-CASCADE` | tables | ON DELETE CASCADE | `tbl-11-indexes-relations` |
| `TB-ONDELETE-NO-ACTION` | tables | ON DELETE NO ACTION | `tbl-11-indexes-relations` |
| `TB-ONDELETE-RESTRICT` | tables | ON DELETE RESTRICT | `tbl-11-indexes-relations` |
| `TB-ONDELETE-SET-NULL` | tables | ON DELETE SET NULL | `tbl-11-indexes-relations` |
| `TB-PRINT` | tables | Stampa struttura | `tbl-12-migration-saveas` |
| `TB-REMOVE` | tables | Rimozione campo | `tbl-01-new-minimal` |
| `TB-REORDER` | tables | Riordino campi | `tbl-12-migration-saveas` |
| `TB-SAVE-AS` | tables | Save As | `tbl-12-migration-saveas` |
| `TB-STATS` | tables | Metadati Updated/Bytes/Records | `tbl-12-migration-saveas` |
| `TB-TYPE-BLOB` | tables | Tipo campo blob | `tbl-02-all-types` |
| `TB-TYPE-BOOLEAN` | tables | Tipo campo boolean | `brw-03-editors`, `tbl-02-all-types` |
| `TB-TYPE-CHOICE` | tables | Tipo campo choice | `tbl-02-all-types` |
| `TB-TYPE-DATE` | tables | Tipo campo date | `brw-03-editors`, `tbl-02-all-types` |
| `TB-TYPE-DATETIME` | tables | Tipo campo datetime | `tbl-02-all-types` |
| `TB-TYPE-DECIMAL` | tables | Tipo campo decimal | `tbl-02-all-types` |
| `TB-TYPE-INTEGER` | tables | Tipo campo integer | `tbl-02-all-types` |
| `TB-TYPE-MEMO` | tables | Tipo campo memo | `tbl-02-all-types` |
| `TB-TYPE-TEXT` | tables | Tipo campo text | `tbl-02-all-types` |

## Fasi 2–3 — da completare

| Feature | Area | Fase |
|---|---|---:|
| `FRM-ALIGN` | forms | 2 |
| `FRM-AUTOLABEL` | forms | 2 |
| `FRM-BUTTON-CLOSE` | forms | 2 |
| `FRM-BUTTON-DELETE` | forms | 2 |
| `FRM-BUTTON-FIRST` | forms | 2 |
| `FRM-BUTTON-LAST` | forms | 2 |
| `FRM-BUTTON-NEW` | forms | 2 |
| `FRM-BUTTON-NEXT` | forms | 2 |
| `FRM-BUTTON-PREVIOUS` | forms | 2 |
| `FRM-BUTTON-SAVE` | forms | 2 |
| `FRM-CLIPBOARD` | forms | 2 |
| `FRM-CONTROL-BUTTON` | forms | 2 |
| `FRM-CONTROL-CHECKBOX` | forms | 2 |
| `FRM-CONTROL-COMBO` | forms | 2 |
| `FRM-CONTROL-DATE` | forms | 2 |
| `FRM-CONTROL-FIELD` | forms | 2 |
| `FRM-CONTROL-GRID` | forms | 2 |
| `FRM-CONTROL-IMAGE` | forms | 2 |
| `FRM-CONTROL-LABEL` | forms | 2 |
| `FRM-CONTROL-LINE` | forms | 2 |
| `FRM-CONTROL-MEMO` | forms | 2 |
| `FRM-CONTROL-NUMBER` | forms | 2 |
| `FRM-CONTROL-RECT` | forms | 2 |
| `FRM-DESIGNER-PALETTE` | forms | 2 |
| `FRM-DISTRIBUTE` | forms | 2 |
| `FRM-EVENT-ONCLICK` | forms | 2 |
| `FRM-EVENT-ONCLOSE` | forms | 2 |
| `FRM-EVENT-ONENTER` | forms | 2 |
| `FRM-EVENT-ONEXIT` | forms | 2 |
| `FRM-EVENT-ONOPEN` | forms | 2 |
| `FRM-EXPERT-5STEPS` | forms | 2 |
| `FRM-EXPERT-BLANK` | forms | 2 |
| `FRM-EXPERT-COLORS` | forms | 2 |
| `FRM-EXPERT-FIELDS` | forms | 2 |
| `FRM-EXPERT-LAYOUTS` | forms | 2 |
| `FRM-EXPERT-STYLE` | forms | 2 |
| `FRM-FIELD-KINDS` | forms | 2 |
| `FRM-GRID-SNAP` | forms | 2 |
| `FRM-HANDLES` | forms | 2 |
| `FRM-INSPECTOR` | forms | 2 |
| `FRM-INSPECTOR-DATA` | forms | 2 |
| `FRM-INSPECTOR-FORM` | forms | 2 |
| `FRM-KEYBOARD` | forms | 2 |
| `FRM-LEGACY-JSON` | forms | 2 |
| `FRM-LIST-FIELDS` | forms | 2 |
| `FRM-LIST-SELECT` | forms | 2 |
| `FRM-LIST-VIEW` | forms | 2 |
| `FRM-METHOD-CLOSE` | forms | 2 |
| `FRM-METHOD-SAVE` | forms | 2 |
| `FRM-METHODS` | forms | 2 |
| `FRM-MULTISELECT` | forms | 2 |
| `FRM-PAGES` | forms | 2 |
| `FRM-PALETTE-FIELD` | forms | 2 |
| `FRM-PORTAL-FILTER` | forms | 2 |
| `FRM-PORTAL-LINK` | forms | 2 |
| `FRM-PORTAL-ORDER` | forms | 2 |
| `FRM-QUERY-CALC` | forms | 2 |
| `FRM-QUERY-NAV` | forms | 2 |
| `FRM-QUERY-READONLY` | forms | 2 |
| `FRM-ROUNDTRIP` | forms | 2 |
| `FRM-RUNTIME-CRUD` | forms | 2 |
| `FRM-RUNTIME-MESSAGES` | forms | 2 |
| `FRM-RUNTIME-NAV` | forms | 2 |
| `FRM-RUNTIME-STATUS` | forms | 2 |
| `FRM-RUNTIME-VALIDATION` | forms | 2 |
| `FRM-UNDO-REDO` | forms | 2 |
| `FRM-ZORDER` | forms | 2 |
| `LBL-ALIGN-CENTER` | labels | 2 |
| `LBL-ALIGN-LEFT` | labels | 2 |
| `LBL-ALIGN-RIGHT` | labels | 2 |
| `LBL-CUSTOM` | labels | 2 |
| `LBL-FIELD-INSERT` | labels | 2 |
| `LBL-FILTER` | labels | 2 |
| `LBL-GRID` | labels | 2 |
| `LBL-MARGINS` | labels | 2 |
| `LBL-NEW` | labels | 2 |
| `LBL-OFFSET` | labels | 2 |
| `LBL-ORDER` | labels | 2 |
| `LBL-PAGES` | labels | 2 |
| `LBL-PDF` | labels | 2 |
| `LBL-PRESET` | labels | 2 |
| `LBL-PRESET-A4_52X30` | labels | 2 |
| `LBL-PRESET-A4_70X37` | labels | 2 |
| `LBL-PRESET-AVERY5160` | labels | 2 |
| `LBL-PRESET-AVERY5163` | labels | 2 |
| `LBL-PREVIEW` | labels | 2 |
| `LBL-SAVE-REOPEN` | labels | 2 |
| `LBL-SELECTION` | labels | 2 |
| `LBL-STYLE` | labels | 2 |
| `LBL-TEMPLATE-EXPR` | labels | 2 |
| `LBL-TEMPLATE-FIELD` | labels | 2 |
| `QRY-AGG-AVG` | queries | 2 |
| `QRY-AGG-COUNT` | queries | 2 |
| `QRY-AGG-MAX` | queries | 2 |
| `QRY-AGG-MIN` | queries | 2 |
| `QRY-AGG-SUM` | queries | 2 |
| `QRY-CROSSTAB` | queries | 2 |
| `QRY-CROSSTAB-CSV` | queries | 2 |
| `QRY-CROSSTAB-EMPTY` | queries | 2 |
| `QRY-CROSSTAB-ERROR` | queries | 2 |
| `QRY-CROSSTAB-TOTALS` | queries | 2 |
| `QRY-EXPERT` | queries | 2 |
| `QRY-EXPERT-CRITERIA` | queries | 2 |
| `QRY-EXPERT-RELATIONS` | queries | 2 |
| `QRY-EXPERT-SORT` | queries | 2 |
| `QRY-FIELD-ALIAS` | queries | 2 |
| `QRY-FIELD-INCLUDE` | queries | 2 |
| `QRY-FILTER-AND` | queries | 2 |
| `QRY-FILTER-GROUPS` | queries | 2 |
| `QRY-FILTER-OR` | queries | 2 |
| `QRY-GROUP-BY` | queries | 2 |
| `QRY-JOIN-INNER` | queries | 2 |
| `QRY-JOIN-LEFT` | queries | 2 |
| `QRY-JOIN-SUGGEST` | queries | 2 |
| `QRY-NEW` | queries | 2 |
| `QRY-OP-BETWEEN` | queries | 2 |
| `QRY-OP-CONTAINS` | queries | 2 |
| `QRY-OP-ENDS` | queries | 2 |
| `QRY-OP-EQ` | queries | 2 |
| `QRY-OP-GE` | queries | 2 |
| `QRY-OP-GT` | queries | 2 |
| `QRY-OP-LE` | queries | 2 |
| `QRY-OP-LIKE` | queries | 2 |
| `QRY-OP-LT` | queries | 2 |
| `QRY-OP-NE` | queries | 2 |
| `QRY-OP-NOTNULL` | queries | 2 |
| `QRY-OP-NULL` | queries | 2 |
| `QRY-OP-REF` | queries | 2 |
| `QRY-OP-STARTS` | queries | 2 |
| `QRY-QBE-BETWEEN` | queries | 2 |
| `QRY-QBE-EXAMPLE` | queries | 2 |
| `QRY-QBE-EXAMPLE-WARN` | queries | 2 |
| `QRY-QBE-IMAGE` | queries | 2 |
| `QRY-QBE-INCLUDE` | queries | 2 |
| `QRY-QBE-LIKE` | queries | 2 |
| `QRY-QBE-NULL` | queries | 2 |
| `QRY-QBE-OR` | queries | 2 |
| `QRY-QBE-ROWS` | queries | 2 |
| `QRY-RESULTS-EXPORT` | queries | 2 |
| `QRY-RESULTS-FORMAT` | queries | 2 |
| `QRY-RESULTS-GRID` | queries | 2 |
| `QRY-RESULTS-REFRESH` | queries | 2 |
| `QRY-SAVE-REJECT` | queries | 2 |
| `QRY-SAVE-REOPEN` | queries | 2 |
| `QRY-SORT-ASC` | queries | 2 |
| `QRY-SORT-DESC` | queries | 2 |
| `QRY-SORT-MULTI` | queries | 2 |
| `QRY-SQL-PARAMS` | queries | 2 |
| `QRY-SQL-PREVIEW` | queries | 2 |
| `QRY-VALIDATE` | queries | 2 |
| `REP-ALIGN-CONTROL` | reports | 2 |
| `REP-BAND-DETAIL` | reports | 2 |
| `REP-BAND-GROUP_FOOTER` | reports | 2 |
| `REP-BAND-GROUP_HEADER` | reports | 2 |
| `REP-BAND-PAGE_FOOTER` | reports | 2 |
| `REP-BAND-PAGE_HEADER` | reports | 2 |
| `REP-BAND-SUMMARY` | reports | 2 |
| `REP-BAND-TITLE` | reports | 2 |
| `REP-BANDS-DRAG` | reports | 2 |
| `REP-BANDS-HEIGHT` | reports | 2 |
| `REP-BANDS-ORDER` | reports | 2 |
| `REP-BANDS-VISIBLE` | reports | 2 |
| `REP-CHART-BAND` | reports | 2 |
| `REP-CHART-BAR` | reports | 2 |
| `REP-CHART-CATEGORY` | reports | 2 |
| `REP-CHART-LINE` | reports | 2 |
| `REP-CHART-PIE` | reports | 2 |
| `REP-CHART-VALUE` | reports | 2 |
| `REP-CONTROL-CHART` | reports | 2 |
| `REP-CONTROL-EXPR` | reports | 2 |
| `REP-CONTROL-FIELD` | reports | 2 |
| `REP-CONTROL-IMAGE` | reports | 2 |
| `REP-CONTROL-LINE` | reports | 2 |
| `REP-CONTROL-RECT` | reports | 2 |
| `REP-CONTROL-TEXT` | reports | 2 |
| `REP-CONTROL-TOTAL` | reports | 2 |
| `REP-EDIT-TEXT` | reports | 2 |
| `REP-EXPERT` | reports | 2 |
| `REP-EXPERT-GROUP` | reports | 2 |
| `REP-EXPERT-LAYOUTS` | reports | 2 |
| `REP-EXPERT-SORT` | reports | 2 |
| `REP-EXPRESSION` | reports | 2 |
| `REP-FIELD-PREVIEW` | reports | 2 |
| `REP-FILTER` | reports | 2 |
| `REP-FORMAT-ALIGN` | reports | 2 |
| `REP-FORMAT-BORDER` | reports | 2 |
| `REP-FORMAT-COLOR` | reports | 2 |
| `REP-FORMAT-FONT` | reports | 2 |
| `REP-FORMAT-STYLE` | reports | 2 |
| `REP-GROUP` | reports | 2 |
| `REP-INSERT-FIELD` | reports | 2 |
| `REP-LEGACY` | reports | 2 |
| `REP-NEW` | reports | 2 |
| `REP-PDF` | reports | 2 |
| `REP-PREVIEW-FIT` | reports | 2 |
| `REP-PREVIEW-PAGES` | reports | 2 |
| `REP-PREVIEW-SINGLE` | reports | 2 |
| `REP-PREVIEW-ZOOM` | reports | 2 |
| `REP-PRINT` | reports | 2 |
| `REP-QUERY` | reports | 2 |
| `REP-ROUNDTRIP` | reports | 2 |
| `REP-SORT` | reports | 2 |
| `REP-SOURCE-QUERY` | reports | 2 |
| `REP-SOURCE-TABLE` | reports | 2 |
| `REP-TOTAL-AVG` | reports | 2 |
| `REP-TOTAL-COUNT` | reports | 2 |
| `REP-TOTAL-MAX` | reports | 2 |
| `REP-TOTAL-MIN` | reports | 2 |
| `REP-TOTAL-SUM` | reports | 2 |
| `REP-ZOOM` | reports | 2 |
| `SCR-ACTION-ASK` | scripts | 2 |
| `SCR-ACTION-BEEP` | scripts | 2 |
| `SCR-ACTION-BEGIN_TRANSACTION` | scripts | 2 |
| `SCR-ACTION-CALL` | scripts | 2 |
| `SCR-ACTION-COMMENT` | scripts | 2 |
| `SCR-ACTION-COMMIT_RECORD` | scripts | 2 |
| `SCR-ACTION-COMMIT_TRANSACTION` | scripts | 2 |
| `SCR-ACTION-CONFIRM` | scripts | 2 |
| `SCR-ACTION-CUSTOM_DIALOG` | scripts | 2 |
| `SCR-ACTION-DELETE_RECORD` | scripts | 2 |
| `SCR-ACTION-DUPLICATE_RECORD` | scripts | 2 |
| `SCR-ACTION-EXIT_LOOP_IF` | scripts | 2 |
| `SCR-ACTION-EXIT_SCRIPT` | scripts | 2 |
| `SCR-ACTION-EXPORT_CSV` | scripts | 2 |
| `SCR-ACTION-FOREACH` | scripts | 2 |
| `SCR-ACTION-GO_RECORD` | scripts | 2 |
| `SCR-ACTION-HALT` | scripts | 2 |
| `SCR-ACTION-IF` | scripts | 2 |
| `SCR-ACTION-LOOP` | scripts | 2 |
| `SCR-ACTION-MESSAGE` | scripts | 2 |
| `SCR-ACTION-NEW_RECORD` | scripts | 2 |
| `SCR-ACTION-OPEN_FORM` | scripts | 2 |
| `SCR-ACTION-OPEN_QUERY` | scripts | 2 |
| `SCR-ACTION-OPEN_REPORT` | scripts | 2 |
| `SCR-ACTION-PRINT_REPORT` | scripts | 2 |
| `SCR-ACTION-REVERT_RECORD` | scripts | 2 |
| `SCR-ACTION-ROLLBACK_TRANSACTION` | scripts | 2 |
| `SCR-ACTION-SELECT_TABLE` | scripts | 2 |
| `SCR-ACTION-SET` | scripts | 2 |
| `SCR-ACTION-SET_FIELD` | scripts | 2 |
| `SCR-ACTION-SET_GLOBAL` | scripts | 2 |
| `SCR-ACTION-SQL` | scripts | 2 |
| `SCR-ACTION-STATUS` | scripts | 2 |
| `SCR-ACTION-UNSET_GLOBAL` | scripts | 2 |
| `SCR-ARGS-DIALOG` | scripts | 2 |
| `SCR-FORM-EVENT` | scripts | 2 |
| `SCR-LEGACY` | scripts | 2 |
| `SCR-LINE-NUMBERS` | scripts | 2 |
| `SCR-LOG` | scripts | 2 |
| `SCR-PARAMS` | scripts | 2 |
| `SCR-PICKER` | scripts | 2 |
| `SCR-PICKER-CATEGORIES` | scripts | 2 |
| `SCR-PICKER-DESCRIPTION` | scripts | 2 |
| `SCR-PICKER-SEARCH` | scripts | 2 |
| `SCR-RUN` | scripts | 2 |
| `SCR-SAVE-REOPEN` | scripts | 2 |
| `SCR-SOURCE-TEXT` | scripts | 2 |
| `SCR-SYNTAX` | scripts | 2 |
| `JOURNEY-1N` | journey | 3 |
| `JOURNEY-CLOSING` | journey | 3 |
| `JOURNEY-IMPORT` | journey | 3 |
| `JOURNEY-LEGACY` | journey | 3 |
| `JOURNEY-NEWAPP` | journey | 3 |
| `JOURNEY-RESTART` | journey | 3 |
| `JOURNEY-SPORTELLO` | journey | 3 |
| `MENU-ACTION-OPEN_FORM` | menus | 3 |
| `MENU-ACTION-OPEN_REPORT` | menus | 3 |
| `MENU-ACTION-QUIT` | menus | 3 |
| `MENU-ACTION-RUN_SCRIPT` | menus | 3 |
| `MENU-ACTION-SEPARATOR` | menus | 3 |
| `MENU-ACTION5` | menus | 3 |
| `MENU-BUILDER` | menus | 3 |
| `MENU-FILTER-TARGET` | menus | 3 |
| `MENU-PREVIEW` | menus | 3 |
| `MENU-RUNTIME` | menus | 3 |
| `MENU-SEPARATORS` | menus | 3 |
| `BUILD-CONTENT` | project | 3 |
| `BUILD-FOLDER` | project | 3 |
| `BUILD-REOPEN` | project | 3 |
| `BUILD-ZIP` | project | 3 |
| `PROJECT-EDITOR` | project | 3 |
| `PROJECT-EDITOR-SAVE` | project | 3 |
| `PROJECT-SETTINGS` | project | 3 |
| `PROJECT-VALIDATE` | project | 3 |
| `PROJECT-VALIDATE-MISSING` | project | 3 |
| `RUNNER-CLOSE` | project | 3 |
| `RUNNER-F5` | project | 3 |
| `RUNNER-FORM` | project | 3 |
| `RUNNER-MENU` | project | 3 |
| `DETERMINISM` | quality | 3 |
| `DOCS-COVERAGE` | quality | 3 |
| `PERF-BROWSE` | quality | 3 |
| `PERF-FORM100` | quality | 3 |
| `PERF-PDF` | quality | 3 |
| `PERF-QUERY` | quality | 3 |
| `PERF-REPORT` | quality | 3 |
| `PERF-REPORT200` | quality | 3 |
| `PERF-TABLE50` | quality | 3 |
| `ABOUT` | shell | 3 |
| `CMD-CLEAR` | shell | 3 |
| `CMD-EXPR` | shell | 3 |
| `CMD-HELP` | shell | 3 |
| `CMD-HISTORY` | shell | 3 |
| `CMD-RECORD` | shell | 3 |
| `CMD-TABLES` | shell | 3 |
| `CMD-USE` | shell | 3 |
| `EDIT-CROSS` | shell | 3 |
| `EDIT-DELETE` | shell | 3 |
| `EDIT-UNDO-REDO` | shell | 3 |
| `HELP-QUICK` | shell | 3 |
| `NAV-CATEGORY-ALL` | shell | 3 |
| `NAV-CATEGORY-CATALOGS` | shell | 3 |
| `NAV-CATEGORY-CUSTOM` | shell | 3 |
| `NAV-CATEGORY-DIAGRAMS` | shell | 3 |
| `NAV-CATEGORY-FORMS` | shell | 3 |
| `NAV-CATEGORY-IMAGES` | shell | 3 |
| `NAV-CATEGORY-LABELS` | shell | 3 |
| `NAV-CATEGORY-MENUS` | shell | 3 |
| `NAV-CATEGORY-QUERIES` | shell | 3 |
| `NAV-CATEGORY-REPORTS` | shell | 3 |
| `NAV-CATEGORY-SCRIPTS` | shell | 3 |
| `NAV-CATEGORY-SOUNDS` | shell | 3 |
| `NAV-CATEGORY-TABLES` | shell | 3 |
| `NAV-CONTEXT` | shell | 3 |
| `NAV-COUNT` | shell | 3 |
| `NAV-DISABLED` | shell | 3 |
| `NAV-FILTER` | shell | 3 |
| `NAV-REFRESH` | shell | 3 |
| `NAV-UNTITLED` | shell | 3 |
| `SHELL-ACTION-AGGIORNA-NAVIGATOR` | shell | 3 |
| `SHELL-ACTION-ALLINEA` | shell | 3 |
| `SHELL-ACTION-ANNULLA` | shell | 3 |
| `SHELL-ACTION-APRI-PROGETTO` | shell | 3 |
| `SHELL-ACTION-AUMENTA-ZOOM` | shell | 3 |
| `SHELL-ACTION-BARRA-DI-STATO` | shell | 3 |
| `SHELL-ACTION-BUILD-DISTRIBUIBILE` | shell | 3 |
| `SHELL-ACTION-CHIUDI-PROGETTO` | shell | 3 |
| `SHELL-ACTION-CHIUDI-SCHEDA` | shell | 3 |
| `SHELL-ACTION-CHIUDI-TUTTE-LE-SCHEDE` | shell | 3 |
| `SHELL-ACTION-COMMAND-WINDOW` | shell | 3 |
| `SHELL-ACTION-COMPATTA-DATABASE` | shell | 3 |
| `SHELL-ACTION-COPIA` | shell | 3 |
| `SHELL-ACTION-CREA-PROGETTO-DEMO` | shell | 3 |
| `SHELL-ACTION-DATABASE` | shell | 3 |
| `SHELL-ACTION-DISTRIBUISCI` | shell | 3 |
| `SHELL-ACTION-ELIMINA` | shell | 3 |
| `SHELL-ACTION-ESCI` | shell | 3 |
| `SHELL-ACTION-ESEGUI-PROGETTO` | shell | 3 |
| `SHELL-ACTION-FORM-CON-ESPERTO` | shell | 3 |
| `SHELL-ACTION-GUIDA-RAPIDA` | shell | 3 |
| `SHELL-ACTION-IMPOSTAZIONI` | shell | 3 |
| `SHELL-ACTION-INCOLLA` | shell | 3 |
| `SHELL-ACTION-INFORMAZIONI-SU-DBX` | shell | 3 |
| `SHELL-ACTION-MODIFICA-PROGETTO` | shell | 3 |
| `SHELL-ACTION-NESSUNA-SCHEDA-APERTA` | shell | 3 |
| `SHELL-ACTION-NUOVA-ETICHETTA` | shell | 3 |
| `SHELL-ACTION-NUOVA-QUERY` | shell | 3 |
| `SHELL-ACTION-NUOVO-FORM` | shell | 3 |
| `SHELL-ACTION-NUOVO-MENU` | shell | 3 |
| `SHELL-ACTION-NUOVO-PROGETTO` | shell | 3 |
| `SHELL-ACTION-NUOVO-REPORT` | shell | 3 |
| `SHELL-ACTION-NUOVO-SCRIPT` | shell | 3 |
| `SHELL-ACTION-QUERY-CON-ESPERTO` | shell | 3 |
| `SHELL-ACTION-REPORT-CON-ESPERTO` | shell | 3 |
| `SHELL-ACTION-RIAPPLICA-REGOLE-DI-CAMPO` | shell | 3 |
| `SHELL-ACTION-RIDUCI-ZOOM` | shell | 3 |
| `SHELL-ACTION-RIPETI` | shell | 3 |
| `SHELL-ACTION-SALVA-PROGETTO` | shell | 3 |
| `SHELL-ACTION-SPEEDBAR` | shell | 3 |
| `SHELL-ACTION-STAMPA` | shell | 3 |
| `SHELL-ACTION-TABELLA-CON-ESPERTO` | shell | 3 |
| `SHELL-ACTION-TAGLIA` | shell | 3 |
| `SHELL-ACTION-VALIDA-PROGETTO` | shell | 3 |
| `SHELL-ACTION-VERIFICA-INTEGRITÀ` | shell | 3 |
| `SHELL-ACTION-ZOOM-100` | shell | 3 |
| `SHELL-ACTIONS` | shell | 3 |
| `SHELL-ACTIVATE` | shell | 3 |
| `SHELL-CLOSE` | shell | 3 |
| `SHELL-CLOSE-ALL` | shell | 3 |
| `SHELL-DIRTY` | shell | 3 |
| `SHELL-MENUS` | shell | 3 |
| `SHELL-SAFE` | shell | 3 |
| `SHELL-TABS` | shell | 3 |
| `SHORTCUTS` | shell | 3 |
| `SPEEDBAR` | shell | 3 |
| `STATUS-BAR` | shell | 3 |
| `THEME` | shell | 3 |
| `TOGGLE` | shell | 3 |
| `TOOLTIPS` | shell | 3 |
| `VERSION` | shell | 3 |
| `ZOOM-IN` | shell | 3 |
| `ZOOM-OUT` | shell | 3 |
| `ZOOM-PERSIST` | shell | 3 |
| `ZOOM-RESET` | shell | 3 |
