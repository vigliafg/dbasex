# Paradox for Windows — Esperti e QBE

Documento di riferimento per il trapianto delle idee di **Paradox for Windows**
nella release dBX 0.4.0. Non è una specifica di compatibilità: dBX resta un
personal database SQLite con un modello proprio.

## Fonti

- **Paradox 9 User Guide** (Corel), capitoli su query, QBE, Answer table,
  esperti e template:
  <https://ftpmirror.your.org/pub/misc/ftp.corel.com/pub/documentation/pdfdocs/support_docs/english/px9en.PDF>
- **Paradox Queries: A Developer’s Reference**, Dan Ehrmann (M&T Books, 1993):
  query image, checkmark, operatori, example elements, Answer table e file
  `.qbe`:
  <https://dokumen.pub/paradox-queries-a-developers-reference-1558513116.html>
- **Paradox Feature Guide / WordPerfect Office User Guide**: elenco degli
  Experts (Table, Form, Report, Query, Label, Chart, Launcher, Startup,
  Database, Merge, Text Import, Field, Button).

## Cosa sono gli Experts

In Paradox gli **Experts** sono procedure guidate invocate dal menu degli
strumenti. Guidano l’utente nella creazione di un oggetto, ma non introducono
un formato parallelo: l’oggetto prodotto è un normale oggetto Paradox,
modificabile in seguito con i designer.

Elenco rilevante:

| Expert | Scopo | Cosa produce |
|---|---|---|
| Table Expert | Crea una tabella partendo da template | Struttura tabella con campi, tipi e indici |
| Form Expert | Crea un form da una o due tabelle | Form con campi, layout, colori e pulsanti |
| Report Expert | Crea un report da una o due tabelle | Report con layout tabellare/colonnare, gruppi e stili |
| Query Expert | Crea una query guidata | Query con tabelle, campi, criteri e ordinamento |
| Label Expert | Etichette | Fuori scope dBX |
| Chart Expert | Grafici | Fuori scope dBX |
| Launcher/Startup Expert | Cruscotto di avvio | Candidato futuro |

## QBE: i concetti da trapiantare

### Query image

Per ogni tabella coinvolta Paradox mostra una **query image**: una griglia con
i nomi dei campi. L’utente compila la griglia con un esempio dei dati cercati.
L’insieme delle immagini è la query.

### Checkmark e Answer table

- Il segno di spunta sul nome di un campo include il campo nella **Answer
  table**, cioè nel risultato.
- L’Answer table è il risultato materializzato della query.
- L’ordinamento si imposta con marcatori di colonna (crescente/decrescente).

In dBX l’Answer table corrisponde a **Query Results**; il checkmark corrisponde
alla presenza del campo in `QuerySpec.fields`.

### Criteri AND e OR

- Criteri su campi diversi nella **stessa riga** sono combinati in **AND**.
- Criteri in **righe diverse** sono combinati in **OR**.

dBX oggi combina tutti i filtri in AND. Per il QBE serve un’estensione
additiva: `QueryFilter.group`, dove lo stesso gruppo è AND e gruppi diversi
sono OR.

### Operatori

Paradox usa operatori digitati nella cella, tra cui:

| Operatore | Significato |
|---|---|
| `=`, `<>`, `>`, `>=`, `<`, `<=` | Confronti |
| `..` | Intervallo (es. `10..20`) |
| `blank`, `not blank` | Campo vuoto / non vuoto |
| `like`, `not like` | Pattern |
| wildcard `*` e `?` | Testo |
| `today` | Data corrente (dipendente dal contesto) |

dBX adotta un sottoinsieme esplicito e documentato:

- `=`, `<>`, `>`, `>=`, `<`, `<=`, valore nudo = uguaglianza;
- `a..b` = intervallo inclusivo per campi numerici e date;
- `blank`, `not blank`;
- `*testo*`, `te?t` per il testo;
- nessun `today` implicito: le date si scrivono in ISO `AAAA-MM-GG`.

### Example elements

Paradox crea un **example element** (tipicamente con F5) e lo riusa in più
campi. Due campi con lo stesso example element sono messi in relazione.

Esempio: `_cliente` in `clienti.id` e in `fatture.cliente_id` significa
`clienti.id = fatture.cliente_id`.

In dBX:

- l’example element si scrive `_nome`;
- due celle con lo stesso `_nome` producono un filtro di tipo `ref`;
- il filtro `ref` confronta due campi già presenti nella query;
- la tabella coinvolta deve essere già inclusa tramite un join; il designer
  segnala il caso e propone di aggiungerla.

### Tipi di query Paradox

Paradox distingue query di ricerca, inserimento, cancellazione, modifica
(`Set`/`ChangeTo`) e crosstab. **dBX adotta solo la ricerca in sola lettura**,
coerentemente con la decisione della 0.3: niente query che modificano dati o
struttura.

## Mappatura su dBX

| Paradox | dBX 0.4.0 | Modulo |
|---|---|---|
| Table Expert | `TableExpert` con template, campi e indici | `dbx/designers/table_expert.py` |
| Form Expert | Già presente, allineato allo shell comune | `dbx/designers/form_expert.py` |
| Report Expert | `ReportExpert` con layout, campi, gruppi e stile | `dbx/designers/report_expert.py` |
| Query Expert | `QueryExpert` con tabelle, join, campi, criteri e ordine | `dbx/designers/query_expert.py` |
| Query image | Griglia QBE per tabella | `dbx/designers/query_builder.py` |
| Checkmark | Checkbox “Includi” | `QuerySpec.fields` |
| Criteri AND/OR | `QueryFilter.group` | `dbx/core/query_model.py` |
| Example elements | Operatore `ref` con valore `tabella.campo` | `dbx/core/query_model.py` |
| Answer table | Query Results | `dbx/ui/query_results.py` |
| Query `.qbe` | `*.query.json` | `Project.objects["queries"]` |

## Cosa non viene trapiantato

- query Insert/Delete/Set/ChangeTo e crosstab;
- campi calcolati e funzioni CALC nelle celle QBE;
- variabili tilde e prompt interattivi;
- formato `.qbe`, tasti funzione Paradox, chrome e scorciatoie Win16;
- template Paradox originali e relativi asset.

## Conseguenze architetturali

1. Il QBE è una **vista** sullo stesso `QuerySpec`, non un secondo modello.
2. Le modifiche al modello sono additive e retrocompatibili:
   `value2` e `group` hanno default; i JSON 0.3 si caricano senza migrazione.
3. Il QBE non genera SQL a mano: passa sempre da `query_engine`, che continua a
   usare parametri `?`.
4. La validazione distingue errori bloccanti (campo inesistente, gruppo
   invalido) da avvisi (OR su una tabella in `LEFT JOIN`).
