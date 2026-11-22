# Collaudo dBX 0.3.0 — stato Checkpoint B

Data: 2026-11-22. Scope: Database Designer ER, motore Query, Query Designer, Query Results e query
come sorgente di form e report. Checkpoint A e B superati; O7 (release) da iniziare.

## Comandi eseguiti

```bash
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
python tools/capture_ui.py
python tools/capture_ui.py --theme dark
```

Esito Checkpoint B: `269 passed`, smoke OK, cattura Aurora/Dark OK.

## Database Designer ER — O1–O3

| Verifica | Esito | Note |
|---|---|---|
| Grafo da metadati reali | OK | Tabelle come nodi, `ForeignKey` come archi |
| Cardinalità 1:1 / 1:N | OK | 1:1 con PK o indice unico sulle colonne figlio |
| Layout persistente | OK | `diagrams/schema.diagram.json` con posizioni, zoom e note |
| Card tabella | OK | Nome, campi, tipi, PK/FK, caption |
| Archi ER | OK | Linee ortogonali, crow’s foot, cardinalità e `ON DELETE` |
| Pan/zoom | OK | Zoom 25–200%, pan con tasto centrale |
| Auto-layout | OK | Griglia deterministica |
| Export | OK | PNG e SVG |
| Nuova tabella | OK | Riusa Table Builder, applica con backup |
| Modifica tabella | OK | Riusa Table Builder |
| Nuova relazione | OK | Dialog figlio/padre, campi PK/unique, `ON DELETE` |
| Eliminazione relazione | OK | Conferma e backup |
| Eliminazione tabella | OK | Bloccata se esistono relazioni in ingresso |
| Navigator Schema | OK | Categoria abilitata, oggetto `schema` nel demo |
| Apertura MDI | OK | `Oggetto → Database Designer…` |

## Motore Query — O4

| Verifica | Esito | Note |
|---|---|---|
| Modello serializzabile | OK | Tabella base, campi, alias, join, filtri e ordinamento |
| SELECT parametrizzata | OK | Valori sempre con `?`, mai interpolati |
| Join | OK | INNER e LEFT con campi qualificati |
| Filtri | OK | `eq/ne/gt/ge/lt/le/contains/starts/ends/null/notnull`, AND |
| Tipi del risultato | OK | Conversioni dBX per testo, numeri, date, logici |
| DISTINCT e nomi duplicati | OK | Alias espliciti o qualificazione `tabella_campo` |
| Validazione | OK | Tabelle, campi, join, filtri e ordinamenti |
| Persistenza | OK | `objects/queries/*.query.json` |

## Query Designer — O5

| Verifica | Esito | Note |
|---|---|---|
| Campi con spunta dall'albero | OK | Aggiunta/rimozione e alias |
| Tabelle e join | OK | INNER/LEFT, campi proposti dalle foreign key |
| Aggiunta/rimozione tabella | OK | La tabella base non è rimovibile; i campi collegati vengono puliti |
| Filtri | OK | Operatori completi, combinati in AND |
| Ordinamento multiplo | OK | Crescente/decrescente e riordino con Sposta su/giù |
| Anteprima SQL | OK | SQL parametrizzato con `?` e parametri elencati |
| Risultato | OK | Griglia read-only, colonne tipizzate, limite 500 righe mostrate |
| Salvataggio/rinomina | OK | Artefatto `objects/queries/*.query.json` |
| Nuova query | OK | Dialog nome, didascalia, tabella base; apertura MDI |
| Navigator | OK | Categoria Query abilitata e filtro `*.query.json` |
| Demo | OK | `fatture_clienti` (join) e `clienti_attivi` (filtro) |

## Query Results e sorgenti dati — O6

| Verifica | Esito | Note |
|---|---|---|
| Griglia Query Results | OK | Read-only, intestazioni dBX, tipi e formati |
| Aggiornamento | OK | Riesegue la query salvata |
| Export CSV | OK | Intestazioni dei campi e valori formattati |
| Apertura MDI | OK | Dal contesto Navigator o dal pulsante del Query Designer |
| Form su query | OK | Campi calcolati, navigazione, nessun CRUD |
| Form Expert | OK | Scelta tabella/query; query genera form read-only |
| Form Designer | OK | Apre form su query con tabella sintetica delle colonne |
| Nuovo report su query | OK | Scelta tabella/query nel dialog di creazione |
| Report Designer su query | OK | Campi, gruppi, totali e ordinamento sulle colonne della query |
| Report Preview su query | OK | Filtro e ordine applicati alle righe, gruppi contigui |
| Validazione progetto | OK | Query non valide e riferimenti `query` mancanti |
| Build | OK | Gli artefatti `queries` sono inclusi nel pacchetto |
| Demo | OK | `form_clienti_attivi` e `fatture_clienti_report` |

## Screenshot

- Serie canonica `01`–`19` in Aurora.
- Nuovi: `15-database-designer.png`, `16-query-designer.png`, `17-query-results.png`,
  `18-form-query.png`, `19-report-query.png`.
- `tools/capture_ui.py --theme dark` verificato senza regressioni.

## Difetti noti accettati

- Il canvas del Database Designer gestisce una relazione per volta nel dialog; chiavi composite si
  creano dal Table Builder.
- La rinomina tabella resta limitata dal motore.
- Il diagramma è unico (`schema`); più diagrammi sono previsti dopo la 0.3.
- Le query non supportano aggregazioni, parametri interattivi, RIGHT/FULL JOIN o query annidate.
- I form su query sono in sola lettura nella 0.3.
- Query Results non offre modifica inline: è una vista di controllo, non un Browse.
- I report su query usano le colonne della query; sottoreport e query annidate non sono previsti.

## Prossimo passo

Checkpoint B superato. O0–O6 completate; prossimo passo O7 — QA finale, versione 0.3.0, CHANGELOG,
tag `v0.3.0` e note di rilascio. Fermarsi e attendere `continua`.
