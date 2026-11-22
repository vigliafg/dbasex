# Collaudo 0.8.0 — Etichette, grafici, vista Lista e portali

Data: 2026-11-22

La release 0.8.0 chiude il ciclo **stampa e viste**: etichette con mail merge, grafici nei report,
vista Lista dei form e portali ordinati/filtrati. I progetti 0.7 si aprono senza migrazione.

## Automazione

| Verifica | Comando | Esito |
|---|---|---|
| Suite completa | `python -m pytest` | 455 passed |
| Smoke headless | `QT_QPA_PLATFORM=offscreen python -m dbx --smoke` | OK, include `etichette`, `grafici report`, `form vista lista`, `portale` |
| Versione | `python -m dbx --version` | `DBX 0.8.0` |
| Rendering Aurora | `python tools/capture_ui.py` | OK |
| Rendering Dark | `python tools/capture_ui.py --theme dark` | OK |

Test dedicati:

- `tests/test_label_model.py`, `tests/test_label_engine.py`, `tests/test_ui_label_designer.py`:
  preset, geometria, filtri, query, griglia, paginazione, salto etichette, formattazione, calcolati,
  rinomina, designer, anteprima e MDI.
- `tests/test_report_charts.py`, `tests/test_ui_report_chart.py`: barre, linee, torta, COUNT,
  group footer, query, validazione, dialogo, Inspector e rendering pagina.
- `tests/test_form_list_portal.py`, `tests/test_ui_form_list_portal.py`: vista Lista, navigazione,
  salvataggio, query read-only, ordine/filtro del portale, proprietà del designer e persistenza.

## Collaudo manuale/headless

1. **Nuova etichetta** — Oggetto → Nuova etichetta, scegliere tabella e preset A4 70×37; il designer
   mostra campi e modello `[codice]`, `[nome]`, `[citta]`.
2. **Modello e campo** — Cancellare il modello, selezionare un campo e premere Inserisci campo;
   il cursore riceve `[campo]`. Aggiungere un'espressione `{{[importo] * 2}}` e verificarla in
   anteprima.
3. **Mail merge** — Impostare filtro `attivo = 1`, ordine `nome`, saltare 2 etichette; l'anteprima
   mostra due etichette a partire dalla terza posizione del foglio.
4. **Stampa/PDF** — Dalla Preview usare Stampa o Esporta PDF; il numero di fogli corrisponde ai
   record divisi per etichette del foglio, con il salto iniziale.
5. **Grafico a barre** — Report Designer, pulsante Grafico: Summary, categoria `[cliente]`,
   valore importo, Somma. L'anteprima mostra tre barre e i totali per cliente.
6. **Torta e linee** — Ripetere con tipo Torta e categoria `[pagata]`, poi Linee su `[cliente]`;
   verificare colori, etichette e legenda.
7. **Grafico di gruppo** — Inserire il grafico nella banda Group footer: ogni gruppo mostra una
   serie limitata ai propri record.
8. **Vista Lista** — Aprire `form_clienti`, premere Lista; selezionare una riga: la scheda e lo
   stato passano al record scelto. Premere Scheda per tornare al form.
9. **Lista su query** — Aprire `form_clienti_attivi`: la lista è in sola lettura e i pulsanti
   Nuovo/Salva/Elimina sono disabilitati.
10. **Portale** — Aprire `form_fatture`, selezionare un cliente e verificare le fatture collegate;
    impostare nel Form Designer Portal order `importo desc` e Portal filter `[importo] >= 200`.
11. **Portale non valido** — Impostare un filtro incompleto: il portale resta vuoto e lo stato
    segnala l'errore senza bloccare il form.
12. **Compatibilità** — Aprire un progetto 0.7 e verificare form, report, query, etichette e script;
    le nuove proprietà hanno default innocui.

## Screenshot

- `31-label-designer.png`, `32-label-preview.png`: etichette e mail merge.
- `33-report-chart.png`, `34-report-chart-designer.png`: grafico a barre in Preview e nel designer.
- `35-form-list.png`, `36-form-portal.png`: vista Lista e portale ordinato/filtrato.

## Limiti accettati

- Etichette senza barcode/QR, immagini, più blocchi di testo o selezione manuale dei record oltre a
  filtro/ordine.
- Grafici non interattivi, senza tooltip, assi configurabili o legenda oltre 8 voci.
- La vista Lista è di consultazione: non consente modifica inline.
- I portali mostrano tutte le colonne del figlio e supportano ordine/filtro, non layout o azioni per
  riga.
- Form su query, Crosstab e viste Read-only non modificano i dati.
