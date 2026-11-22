# FileMaker — Passi script predefiniti

Documento di riferimento per il trapianto delle idee di **FileMaker Pro** nella
release dBX 0.5.0. dBX non diventa un clone di FileMaker: adotta il modello
“script = sequenza ordinata di passi predefiniti con opzioni”, già coerente con
il MiniScript esistente.

## Fonti

- **FileMaker Pro 13 Script Steps Reference — category list**:
  <https://help.claris.com/archive/help/13/fmp/en/html/help_script_cat.34.2.html>
- **Claris FileMaker Pro Help — Script steps reference** (versione corrente):
  <https://help.claris.com/en/pro-help/content/script-steps-reference.html>
- **FileMaker Script Steps Reference** (PDF):
  <https://help.claris.com/archive/docs/14/en/fmp14_scripts_reference.pdf>

## L’idea centrale

In FileMaker uno script è un elenco ordinato di **script step**. Ogni passo ha:

- un nome e una categoria;
- opzioni (parametri) specifiche;
- un comportamento definito dal runtime;
- una rappresentazione nell’editor, senza richiedere codice libero.

dBX ha già la stessa base: `ACTIONS` in `dbx/runtime/script_engine.py` e la forma
testuale bidirezionale. La 0.5.0 completa il catalogo, lo organizza per
categorie e aggiunge i passi che mancano.

## Categorie FileMaker rilevanti

Elenco delle categorie della guida (non tutti i passi sono adottati):

| Categoria | Esempi | Adozione dBX |
|---|---|---|
| Control | If/Else/End If, Loop/Exit Loop If/End Loop, Exit Script, Halt Script, Set Variable, Comment | Sì, sottoinsieme |
| Navigation | Go to Layout, Go to Record/Request/Page, Go to Field, Enter Find Mode | Parziale: form/report/query, record, tabella |
| Editing | Undo, Cut, Copy, Paste, Select All | No: sono azioni UI, non passi di script dati |
| Fields | Set Field, Insert Calculated Result, Replace Field Contents | Solo `Set Field` |
| Records | New Record, Duplicate Record, Delete Record, Commit, Revert | Sì |
| Found Sets | Perform Find, Show All Records, Sort Records | Tramite `select_table` con filtro/ordine |
| Windows | New Window, Close Window, Adjust Window, Set Window Title | No nella 0.5.0 |
| Files | Print, Print Setup, Export Records, Import Records | Stampa report, export CSV; import CSV come estensione |
| Accounts | Add Account, Change Password, Re-Login | No |
| Scripts | Perform Script, Exit Script, Halt Script | Sì |
| Miscellaneous | Show Custom Dialog, Beep, Comment, Execute SQL | Sì, sottoinsieme |

## Passi adottati nel core dBX (~16)

| Azione dBX | Categoria | Parametri | Equivalente FileMaker |
|---|---|---|---|
| `comment` | Controllo | `text` | Comment |
| `if` / `else` | Controllo | `expr` | If / Else / End If |
| `loop` | Controllo | — | Loop / End Loop |
| `exit_loop_if` | Controllo | `expr` | Exit Loop If |
| `exit_script` | Controllo | — | Exit Script |
| `halt` | Controllo | `message` | Halt Script |
| `select_table` | Navigazione | `table`, `filter`, `order` | Go to Layout + Perform Find + Sort |
| `go_record` | Navigazione | `mode`, `number` | Go to Record/Request/Page |
| `open_form` | Navigazione | `form` | Go to Layout (form) |
| `open_report` | Navigazione | `report` | Go to Layout (report) + Preview |
| `open_query` | Navigazione | `query` | Go to Layout (query results) |
| `set_field` | Dati | `field`, `expr` | Set Field |
| `new_record` | Record | `table` (opzionale) | New Record/Request |
| `duplicate_record` | Record | — | Duplicate Record/Request |
| `delete_record` | Record | `confirm` | Delete Record/Request |
| `commit_record` | Record | — | Commit Records/Requests |
| `revert_record` | Record | — | Revert Record/Request |
| `custom_dialog` | Interfaccia | `title`, `message`, `variable` | Show Custom Dialog |
| `beep` | Interfaccia | — | Beep |
| `print_report` | File | `report` | Print |
| `export_csv` | File | `table`, `filter`, `path` | Export Records |
| `call` | Script | `script` | Perform Script |
| `ask` | Variabili | `prompt`, `variable` | Show Custom Dialog / input |
| `set` | Variabili | `variable`, `expr` | Set Variable |
| `sql` | Avanzate | `statement` | Execute SQL |

`elseif` è trattato come zucchero sintattico: `ELSE IF` viene memorizzato come
un `if` annidato dentro `else`, senza aggiungere un’azione al motore.

## Semantica dBX

- Lo script opera su un **contesto attivo**: tabella corrente, cursore
  `Rowset`, record corrente, id interno.
- `select_table` apre il cursore con filtro e ordine e carica il primo record.
- `go_record` gestisce primo/precedente/successivo/ultimo/numero.
- `set_field` valuta l’espressione e scrive subito sul record corrente; le
  scritture sono registrate nel log.
- `new_record` inserisce i valori di default e posiziona il cursore;
  `duplicate_record` copia il record corrente; `delete_record` chiede conferma.
- `foreach` conserva l’id interno della riga, così `set_field` funziona anche
  dentro un ciclo.
- `loop` usa il limite `max_steps` già presente contro i cicli infiniti.
- `exit_script` e `halt` usano il flag di stop del motore.
- Gli errori finiscono nel log e in `ScriptResult.error`; la UI non va in crash.

Scelta esplicita: **scrittura immediata per passo**, non transazione implicita
tra passi. `revert_record` ricarica il record dal database. Una transazione
unica renderebbe ambigua l’interazione con finestre e dialoghi.

## Cosa non viene trapiantato

- layout, portali, temi e script trigger;
- account, privilegi, Re-Login;
- FileMaker Server, plugin, Perform Script on Server;
- AppleScript, DDE, Send Event, Open URL, Send Mail;
- motore di calcolo completo e funzioni `Get(...)`;
- import/export nei formati FileMaker.

## Compatibilità

1. Gli script JSON e testuali esistenti devono continuare a funzionare senza
   modifiche.
2. Ogni azione del catalogo deve avere categoria, descrizione e handler.
3. `to_text` e `from_text` devono coprire ogni azione con test di andata e
   ritorno.
4. `validate_project` deve controllare i riferimenti a tabelle, campi, form,
   report, query e script.
5. Il Form Runtime passa un adattatore UI allo `ScriptEngine` e ricarica il
   record dopo l’esecuzione, così `set_field`, `custom_dialog` e i messaggi
   funzionano anche dagli eventi form.
