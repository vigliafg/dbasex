# Piano — Validazione dei campi in dBX

**Stato:** implementato il 2026-11-25; fasi 0–7 completate e verificate.
**Data:** 2026-11-25.
**Riferimento:** confronto con `adbx-legacy` (regole di campo Alpha Four) e
studio del tipo `choice` con dominio numerico.
**Obiettivo:** estendere la validazione di dBX con le regole che descrivono il
**dato** — inclusi il nuovo campo **Scelta** (`choice`) e il **dominio
numerico** — senza importare gli artefatti del character mode.

Questo documento è un sotto-piano di [`PLAN.md`](PLAN.md): non sostituisce le
ondate 0.2–0.9 e non ne riscrive la storia. Quando approvato, va linkato dalla
sezione 16 di `PLAN.md`.

---

## 1. Obiettivo e criteri

dBX oggi valida **tipo + obbligatorietà booleana + regola espressione +
unicità**, in un unico punto (`Rowset.validate`), su tutte le scritture.
Import e script non possono aggirare le regole: è un vantaggio da conservare.

Il piano aggiunge:

- obbligatorietà **condizionale** e **messaggio** per campo;
- **validazione per campo** con feedback immediato;
- **campo Scelta**: valori discreti, statici e/o da tabella, con etichette;
- **dominio numerico**: minimo/massimo o intervalli multipli;
- **maschera** e **normalizzazione maiuscole** in input;
- **skip** condizionale nella navigazione;
- **incremento a ogni modifica**;
- **re-evaluate** dei record esistenti.

Criterio guida: *portare le regole che descrivono il dato, non quelle che
descrivono il terminale 80×25.*

### Fuori perimetro (deciso)

| Feature di adbx | Perché no |
|---|---|
| Template di campo (`\|`, posizioni fisse, cursore a slot) | artefatto del character mode; nessun valore in Qt |
| Post data (`Add`/`Subtract`/`Replace`) | doppione di FK, trigger SQLite e transazioni |
| Trigger di campo `FIELD_ENTER/VALID/EXIT` | dBX ha già gli eventi dei controlli del form |
| Risoluzione regole set→database | dBX non ha i set |
| Geometria finestra lookup (posizione 1–9, hidden) | artefatto del character mode |
| Cascading / conditional lookup | solo su richiesta concreta, dopo la v1 |
| Doppia immissione | rinviata: solo se emergono casi concreti (importi, password) |
| Scelta multi-valore | un campo, un valore; rivalutare in v2 |
| Sorgente dinamica da query | v1 solo tabella.colonna; query in v2 |
| Riempimento di altri campi dalla scelta | la Scelta valida, non compila; il lookup-fill resta separato e rinviato |

---

## 2. Decisioni architetturali

| # | Decisione | Motivazione |
|---|---|---|
| D1 | `Rowset` resta l'**unico punto di enforcement** | import, script, form e griglia validano allo stesso modo |
| D2 | Le regole di **forma dell'input** vivono in un `InputRules` condiviso | maschere e maiuscole sono comportamento dell'editor, non del dato |
| D3 | I metadati nuovi sono **additivi** e con default | i `.table.json` esistenti restano validi |
| D4 | La validazione restituisce **issue strutturate** | la UI deve evidenziare il campo giusto |
| D5 | **Per campo all'uscita**, **intero record al salvataggio** | feedback immediato senza bloccare una cella per un altro campo vuoto |
| D6 | Un campo **saltato non è obbligatorio** | evita l'incoerenza presente in adbx |
| D7 | Import e script **validano** | coerenza con D1 |
| D8 | `choice` è un **tipo logico** mappato su `TEXT` | la UI mostra “Scelta”, lo storage resta testo e i file restano compatibili |
| D9 | Il **dominio numerico** è separato da `choice` | una tendina non può rappresentare un intervallo continuo |
| D10 | I valori storici non vengono riscritti | la lista/dominio vale alla scrittura; `re-evaluate` segnala soltanto |

### Confine tra input e dati

```text
InputRules  →  forma il valore (maschera, maiuscole, combo, auto-advance)
Rowset      →  verifica il valore (tipo, required, choice/domain, rule, unicità)
```

---

## 3. Modello dati

### 3.1 Campi di validazione (additivi)

In `dbx/core/metadata.py`, tutti con default retrocompatibili:

| Campo | Tipo | Default | Semantica |
|---|---|---|---|
| `required_expr` | `str` | `""` | se non vuota, obbligatorietà condizionale; vince su `required` |
| `rule_message` | `str` | `""` | messaggio quando `rule` è falsa |
| `skip_expr` | `str` | `""` | se vera, campo saltato e non obbligatorio |
| `case_mode` | `str` | `""` | `""`, `"upper"`, `"lower"`, `"title"`, `"sentence"` |
| `mask` | `str` | `""` | `9`, `A`, `a`; solo `TEXT`, non su `choice` |
| `increment` | `str` | `""` | `""`, `"records"`, `"updates"`; **sostituisce** `auto_serial` (migrazione in lettura) |

### 3.2 Tipo `choice`

Nuovo tipo logico in `dbx/core/types.py`:

- `CHOICE = "choice"`, etichetta **“Scelta”**;
- `sql_type(CHOICE)` → `TEXT`, `affinity(CHOICE)` → `TEXT`;
- `to_storage`/`from_storage`/`parse_input`/`format_value` si comportano come
  `TEXT`;
- nuovo helper `is_text_like(type_name)` → `TEXT`, `MEMO`, `CHOICE`.

Tutti i punti che oggi confrontano `(T.TEXT, T.MEMO)` vanno portati a
`T.is_text_like(...)`: ricerca, query, migrazioni DDL, import, esperti,
Table Builder. Sono circa dodici punti.

Campi di `Field`:

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `choices` | `list[dict]` | `[]` | lista statica: `{"value": "...", "label": "..."}` |
| `choice_source` | `str` | `""` | `""` o `"table"` |
| `choice_table` | `str` | `""` | tabella sorgente |
| `choice_value` | `str` | `""` | colonna del valore salvato |
| `choice_label` | `str` | `""` | colonna dell'etichetta (opzionale) |
| `choice_combine` | `str` | `"append"` | `"append"` o `"replace"` |
| `choice_case_sensitive` | `bool` | `True` | confronto esatto o casefold |
| `choice_allow_blank` | `bool` | `True` | voce vuota ammessa |
| `choice_allow_other` | `bool` | `False` | testo libero ammesso con avviso |

Semantica:

- **valore vs etichetta**: si salva `value`; la tendina mostra `label` (se
  vuota, `value`). Report, export e ricerca usano il valore.
- **statica + dinamica**: con `append` si mostrano prima gli statici, poi i
  dinamici non già presenti (dedupe per valore). Con `replace` la dinamica
  sostituisce gli statici; se la sorgente restituisce zero righe, si usano gli
  statici come fallback.
- **confronto**: esatto se `choice_case_sensitive`, altrimenti casefold; in
  caso di corrispondenza si salva il valore canonico della lista.
- **vuoto**: ammesso se `choice_allow_blank` e il campo non è obbligatorio.
- **testo libero**: con `choice_allow_other` il valore fuori lista è accettato
  con un avviso `Valore fuori elenco`; senza, è un errore bloccante.
- **sorgente irraggiungibile**: errore bloccante (`choice_source`), non
  fallback silenzioso.
- **limite**: 1000 valori; oltre, errore `La lista supera 1000 valori`.
- **storico**: i record esistenti non vengono toccati; `re_evaluate` segnala
  `choice_stale` come avviso.

### 3.3 Dominio numerico

Solo per `INTEGER` e `DECIMAL`:

| Campo | Tipo | Default | Note |
|---|---|---|---|
| `domain_min` | `str` | `""` | estremo inferiore incluso; vuoto = aperto |
| `domain_max` | `str` | `""` | estremo superiore incluso; vuoto = aperto |
| `domain_ranges` | `list[list[str]]` | `[]` | intervalli `[min, max]`; se non vuoto, sostituisce min/max |
| `domain_message` | `str` | `""` | messaggio personalizzato |

Semantica:

- **inclusivo** su entrambi gli estremi;
- se `domain_ranges` è valorizzato, il dominio è l'**unione** degli intervalli
  e `domain_min`/`domain_max` sono ignorati (warning di schema);
- un estremo vuoto in un intervallo significa “aperto”;
- confronto con `Decimal(str(value))` per evitare artefatti binari;
- vuoto ammesso: il dominio non si applica ai valori vuoti (ci pensa
  `required`);
- **storico**: `re_evaluate` segnala `domain_stale` come avviso, senza
  riscrivere.

### 3.4 Regole di schema (`Field.validate`)

- `choice` ⇒ tipo `CHOICE`; non calcolato, non `pk` con sorgente dinamica
  sulla stessa tabella (warning), niente maschera, niente `increment`;
- `domain_*` ⇒ solo `INTEGER`/`DECIMAL`; non calcolato; niente `choice`;
- `domain_min <= domain_max`; ogni intervallo con `min <= max`;
- `choice_source` valorizzato ⇒ `choice_table` e `choice_value` presenti;
- `choice_combine` ∈ `{"append", "replace"}`;
- `choice_case_sensitive` è un bool, default `True`;
- `choice_allow_other` è un bool, default `False`;
- `required_expr` e `skip_expr` devono essere espressioni valide;
- `mask` solo `TEXT` e solo caratteri `9`/`A`/`a`/spazio;
- `increment` ∈ `{"", "records", "updates"}`;
- restano i vincoli attuali: calcolato non può essere `pk`, `required`,
  `lookup`, `rule`.

### 3.5 JSON

```json
{
  "name": "stato",
  "type": "choice",
  "size": 20,
  "choices": [
    {"value": "A", "label": "Attivo"},
    {"value": "S", "label": "Sospeso"}
  ],
  "choice_source": "table",
  "choice_table": "stati",
  "choice_value": "codice",
  "choice_label": "descrizione",
  "choice_combine": "append",
  "choice_case_sensitive": true,
  "choice_allow_blank": true,
  "choice_allow_other": false
}
```

```json
{
  "name": "sconto",
  "type": "decimal",
  "domain_min": "0",
  "domain_max": "50",
  "domain_message": "Lo sconto deve essere tra 0 e 50"
}
```

```json
{
  "name": "quantita",
  "type": "integer",
  "domain_ranges": [["1", "10"], ["20", "30"]],
  "domain_message": "Quantità non ammessa"
}
```

Nessuna chiave è obbligatoria: i file esistenti si caricano con i default.

### 3.6 Migrazione dei metadati

- **`auto_serial` → `increment`**: in lettura, `auto_serial=True` diventa
  `increment="records"`; in scrittura si emette solo `increment` e
  `auto_serial` non viene più salvato. La migrazione è trasparente: il file
  viene riscritto alla prima modifica della tabella, senza intervento
  dell'utente.
- **`lookup` → `choice`**: un campo `TEXT` con `lookup="tabella.campo"` e
  nessuna configurazione `choice` viene interpretato in lettura come
  `choice_source="table"`, `choice_table`/`choice_value` ricavati da
  `lookup`, `choice_combine="replace"` (la tabella vince) e
  `choice_allow_other=True` per non rifiutare valori già presenti. Alla prima
  modifica il campo viene riscritto come `type="choice"`; i valori esistenti
  non vengono toccati.
- **Nessuna migrazione distruttiva**: i campi `TEXT` senza `lookup` restano
  `TEXT`; nessun dato viene convertito.

---

## 4. API di validazione

### 4.1 Tipi

In `dbx/runtime/rowset.py` (o nuovo `dbx/runtime/validation.py`):

```python
@dataclass(frozen=True)
class ValidationIssue:
    field: str
    message: str
    code: str   # type | required | choice | choice_source | choice_other
                # | domain | rule | unique | record
    severity: str = "error"   # "error" | "warning"

class ValidationError(RowsetError):
    @property
    def issues(self) -> list[ValidationIssue]: ...
```

`ValidationError` estende `RowsetError`: chi già cattura `RowsetError`
continua a funzionare.

### 4.2 `Rowset.validate`

```python
def validate(
    self,
    values: dict[str, Any],
    *,
    only: set[str] | None = None,
) -> dict[str, Any]:
```

- `only=None` → tutto il record;
- `only={"quantita"}` → converte tutti i campi (servono alle espressioni), ma
  applica `required`/`choice`/`domain`/`rule` solo ai campi indicati;
- i calcolati sono comunque valutati; l'unicità la gestisce il chiamante;
- ordine: tipo → required → choice/domain → calcolati → regole;
- gli errori si accumulano; gli avvisi (`choice_other`, `choice_stale`,
  `domain_stale`) non bloccano.

### 4.3 Scritture

```python
def insert(self, values, *, validate: bool = True) -> int
def update(self, record_id, values, *, only: set[str] | None = None,
           validate: bool = True) -> int
def validate_field(self, record_id, field_name, value) -> dict[str, Any]
```

`validate_field` è la primitiva della griglia: carica il record, applica il
nuovo valore, chiama `validate(..., only={field_name})` e restituisce i valori
pronti senza scrivere.

### 4.4 Risoluzione delle scelte

```python
@dataclass(frozen=True)
class ChoiceOption:
    value: str
    label: str

def resolve_choices(field: Field, db: Database) -> list[ChoiceOption]: ...
```

- statici: ordine di definizione, dedupe per valore;
- dinamici: `SELECT value, label FROM table ORDER BY label` (o valore se la
  label manca), `LIMIT 1001`;
- con `append` (decisione approvata): statici in testa, poi i dinamici non già
  presenti; con `replace`: dinamici, e statici solo se la sorgente restituisce
  zero righe;
- confronto esatto di default (decisione approvata); `choice_case_sensitive`
  può disattivarlo per singolo campo;
- un campo `TEXT` con vecchio `lookup` viene risolto come sorgente tabella
  (vedi §3.6), senza doppio meccanismo;
- cache per `Rowset` (e per form aperto), invalidata al salvataggio dello
  schema o della tabella sorgente;
- sorgente mancante → `ValidationIssue(code="choice_source")`.

### 4.5 Controllo del dominio

```python
def domain_error(field: Field, value: Any) -> ValidationIssue | None: ...
```

- vuoto → `None`;
- intervalli inclusivi, unione se `domain_ranges`;
- `Decimal(str(value))`;
- messaggio: `domain_message` o default
  `Il valore deve essere compreso tra {min} e {max}` /
  `Il valore non è in un intervallo ammesso`.

### 4.6 Re-evaluate

```python
def re_evaluate(table: Table, db: Database) -> tuple[int, list[ValidationIssue]]
```

Ricalcola i calcolati, applica `case_mode`, ricontrolla `required`, `choice`,
`domain` e `rule`. Non scrive se ci sono errori bloccanti; gli avvisi storici
(`choice_stale`, `domain_stale`) vengono riportati. Comando in
`File → Manutenzione database → Riapplica regole di campo`.

---

## 5. Input layer

Nuovo modulo `dbx/ui/input_rules.py` (parte pura testabile senza Qt):

```python
class InputRules:
    @staticmethod
    def apply_case(text: str, mode: str) -> str: ...
    @staticmethod
    def mask_slots(mask: str) -> dict[int, str]: ...
    @staticmethod
    def accepts(mask_char: str, char: str) -> bool: ...
    @staticmethod
    def check(mask: str, text: str) -> str: ...
```

Uso:

- **Scelta**: `RecordDialog`, griglia e Form Runtime usano una `QComboBox`
  popolata da `resolve_choices`; label visibile, valore salvato; voce vuota se
  ammessa; editable se `choice_allow_other`.
- **Dominio**: nessun widget speciale; il campo resta numerico, il messaggio
  arriva dalla validazione.
- **Maschera / maiuscole**: delegate della griglia e binder del form.
- **Auto-advance**: quando il campo è pieno o la maschera è completa, il focus
  passa al controllo successivo.

---

## 6. UI

### 6.1 Table Builder

- Il combo dei tipi include **Scelta**.
- Gruppo richiudibile **Valori** (solo per `CHOICE`):
  - sorgente: Lista fissa / Tabella / Lista + tabella;
  - editor della lista statica (finestra con Valore/Etichetta, aggiungi,
    elimina, riordina);
  - tabella, colonna valore, colonna etichetta;
  - combinazione: Aggiungi / Sostituisci;
  - opzioni: distinzione maiuscole, vuoto ammesso, testo libero.
- Gruppo **Dominio numerico** (solo `INTEGER`/`DECIMAL`):
  - modo: Nessuno / Min–max / Intervalli;
  - campi min/max oppure tabella degli intervalli;
  - messaggio personalizzato.
- I gruppi si escludono a vicenda e si disabilitano in base al tipo.
- Un campo calcolato nasconde entrambi i gruppi.

### 6.2 Griglia, form e nuovo record

- Cella `CHOICE`: combo con label; su selezione si salva il valore; invio/ESC
  come oggi.
- Form Runtime: combo al posto della line edit; `choice_allow_other` la rende
  modificabile.
- Errori: status bar con `Campo: messaggio`; cella/controllo evidenziato; il
  dialog modale resta solo per il salvataggio fallito.

---

## 7. Fasi

### Fase 0 — Fondamenta (mezza giornata)

- `ValidationIssue`, `ValidationError`, `ValidationReport`.
- `Rowset.validate` con `only=`, `validate_field`, `update(..., only=)`.
- `is_text_like` e refactor dei confronti di tipo.
- Test di non-regressione.

**DoD:** suite attuale verde, `RowsetError` compatibile, nessun cambio di
comportamento per i chiamanti.

### Fase 1 — Obbligatorietà e messaggi (1 giornata)

- `required_expr`, `rule_message`, `skip_expr`.
- Validazione per campo nella griglia.
- Evidenziazione in `RecordDialog` e `FormRuntime`.

**DoD:** una cella valida si salva anche con un altro campo obbligatorio
vuoto; skip esclude l'obbligatorietà.

### Fase 2 — Scelta statica (1 giornata)

- `T.CHOICE`, campi `choice_*`, regole di schema.
- Validazione statica in `Rowset`, combo in griglia/form/nuovo record.
- Editor “Valori” nel Table Builder.

**DoD:** un valore fuori lista è rifiutato; label e valore restano distinti;
JSON retrocompatibile.

### Fase 3 — Scelta dinamica (1 giornata)

- Sorgente `table.colonna`, label opzionale, `append`/`replace`.
- Cache e invalidazione; errori `choice_source`.
- Limite 1000 valori.

**DoD:** aggiornando la tabella sorgente la tendina cambia; una sorgente
mancante blocca con messaggio chiaro.

### Fase 4 — Dominio numerico (mezza giornata)

- `domain_min`, `domain_max`, `domain_ranges`, `domain_message`.
- Controllo in `Rowset` e validazione per campo.
- Gruppo “Dominio numerico” nel Table Builder.

**DoD:** min/max e intervalli multipli funzionano; i vuoti passano; il
messaggio è chiaro.

### Fase 5 — Input guidato (1–2 giornate)

- `InputRules`: maschera, maiuscole.
- `case_mode` e `mask` nel modello e nel Table Builder.
- Delegate della griglia, binder del form, auto-advance.

**DoD:** un carattere non ammesso non entra; i valori letti dal database non
cambiano.

### Fase 6 — Incrementi e re-evaluate (1 giornata)

- `increment` `records`/`updates`; **unificazione immediata** di
  `auto_serial`: migrazione in lettura, scrittura del solo `increment`,
  rimozione del vecchio attributo dal JSON.
- `re_evaluate` e comando nel menu.
- Avvisi storici per `choice` e dominio.

**DoD:** incremento su insert e update; un file con `auto_serial` continua a
funzionare e viene riscritto con `increment`; re-evaluate non scrive record
con errori bloccanti.

### Fase 7 — Rifinitura (mezza giornata)

- `CHANGELOG.md`, `README.md`, `PLAN.md` §16 (link a questo piano).
- `DIARIO.md`: voce unica a fine ondata.
- Screenshot del Table Builder, se previsti.

---

## 8. Test

### Unitari

- `tests/test_validation.py` (nuovo): issue, required expr, skip, messaggio,
  choice statica/dinamica, label, combine, case, blank, allow_other, dominio
  min/max e intervalli, maschera, maiuscole, incrementi.
- `tests/test_rowset.py`: `only=`, `validate_field`, compatibilità errori,
  import/script che validano.
- `tests/test_metadata.py`: nuove regole di schema, JSON additivo,
  migrazione `auto_serial` → `increment`, migrazione `lookup` → `choice`.
- `tests/test_types.py`: `CHOICE` come testo, `is_text_like`, conversioni.

### Integrazione

- Import CSV: riga non valida → issue con riga e campo; le righe valide
  entrano, gli scarti sono elencati con il motivo (decisione approvata).
- Script: `INSERT`/`UPDATE` passano da `validate`.
- Form Runtime: salvataggio con issue → nessuna scrittura, controllo
  evidenziato.

### UI (offscreen)

- Table Builder: gruppi Valori/Dominio si abilitano e disabilitano; i metadati
  sopravvivono a salva/ricarica.
- Griglia: cella valida con altro campo obbligatorio vuoto → salva; cella non
  valida → ripristino e messaggio.
- Combo: label visibile, valore salvato, vuoto e testo libero secondo le
  opzioni.

### Regressione

- `python -m pytest` completa.
- `python -m dbx --smoke` verde.
- `ruff check dbx tests` pulito.

---

## 9. Criteri di accettazione

1. I `.table.json` esistenti si aprono senza migrazione e senza perdita di
   metadati.
2. `RowsetError` resta il tipo catturato dai chiamanti; `ValidationError.issues`
   è disponibile per la UI.
3. Import e script non possono aggirare `required`, `rule`, `choice`,
   `domain`.
4. Una modifica di cella valida non fallisce per un campo obbligatorio diverso.
5. Un campo con `skip_expr` vera non blocca il salvataggio per obbligatorietà.
6. `choice` salva il valore, mostra la label; report ed export mostrano il
   valore.
7. Il dominio numerico è inclusivo, gestisce aperti e intervalli multipli.
8. I valori storici fuori lista/dominio non vengono riscritti; `re-evaluate`
   li segnala.
9. Un campo con vecchio `lookup` viene letto come `choice` con sorgente
   tabella, senza perdita di valori.
10. Un file con `auto_serial` viene letto e riscritto come `increment`, senza
    cambiare il comportamento.
11. L'import importa le righe valide e riporta gli scarti con riga e motivo.
12. Documentazione e changelog aggiornati.

---

## 10. Rischi

| Rischio | Impatto | Mitigazione |
|---|---|---|
| `CHOICE` trattato come non-testo nei punti esistenti | ricerca, query, migrazioni errate | helper `is_text_like` + test dedicati |
| Doppia semantica `required` bool / `required_expr` | confusione nell'editor | combo a tre stati; l'espressione vince |
| `only=` usato male e record invalidi salvati | dati incoerenti | il salvataggio usa sempre `only=None`; test |
| Lista dinamica grande o lenta | UI bloccata | limite 1000, `LIMIT 1001`, cache |
| Sorgente dinamica mancante | dati non validati | fail closed con messaggio |
| Confronto float nel dominio | falsi negativi | `Decimal(str(value))` |
| Due gruppi UI nel Table Builder | pannello illeggibile | gruppi richiudibili, mutuamente esclusivi |
| `auto_serial` → `increment` | migrazione incompleta o doppia verità | migrazione in lettura, scrittura del solo `increment`, test su file legacy |

---

## 11. File toccati (stima)

- `dbx/core/types.py` — `CHOICE`, `is_text_like`, conversioni.
- `dbx/core/metadata.py` — campi nuovi, schema, JSON.
- `dbx/runtime/rowset.py` — issue, `only=`, `validate_field`, choice/domain,
  `re_evaluate`.
- `dbx/runtime/validation.py` (nuovo, opzionale) — tipi e helper.
- `dbx/ui/input_rules.py` (nuovo) — maschera, maiuscole.
- `dbx/ui/data_view.py` — delegate combo, validazione per cella.
- `dbx/runtime/form_runtime.py` — combo, binder, evidenziazione.
- `dbx/designers/table_builder.py` — tipo Scelta, gruppi Valori/Dominio.
- `dbx/ui/import_wizard.py` — errori con riga/campo.
- `dbx/core/search.py`, `dbx/core/query_model.py`, `dbx/core/ddl.py`,
  `dbx/core/query_engine.py`, `dbx/designers/expert_common.py` — refactor
  `is_text_like`.
- `tests/test_validation.py` (nuovo), `tests/test_rowset.py`,
  `tests/test_metadata.py`, `tests/test_types.py`, `tests/test_e2e_harness.py`.
- `README.md`, `CHANGELOG.md`, `PLAN.md`, `DIARIO.md`.

---

## 12. Decisioni approvate (2026-11-25)

1. **Statica + dinamica**: `append` — i valori fissi restano in testa e i
   dinamici non già presenti seguono. `replace` resta disponibile come opzione
   per singolo campo.
2. **Vecchio `lookup`**: assorbito in `choice` in lettura, senza riscrivere i
   file; un solo meccanismo da imparare.
3. **Confronto dei valori**: esatto di default; l'opzione case-insensitive
   resta sul singolo campo.
4. **Testo libero**: `allow_other` disponibile ma spento di default; quando è
   attivo, il valore fuori lista è accettato con avviso.
5. **Dominio numerico**: due modalità nello stesso gruppo — min/max oppure
   intervalli multipli.
6. **Import**: le righe valide entrano, gli scarti sono elencati con numero di
   riga e motivo.
7. **`auto_serial`**: unificazione immediata in `increment`, con migrazione in
   lettura e riscrittura del solo campo nuovo.

### Conseguenze già recepite nel piano

- §3.1: `increment` sostituisce `auto_serial`.
- §3.6: migrazione trasparente di `auto_serial` e `lookup`.
- §4.4: `append` come comportamento predefinito, confronto esatto.
- §7 Fase 6: unificazione immediata, non alias.
- §9: criteri 9–11 aggiunti per migrazioni e import.
