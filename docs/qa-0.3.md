# Collaudo dBX 0.3.0 — stato Checkpoint A

Data: 2026-11-22. Scope: Database Designer ER e baseline per Query Designer/Results.

## Comandi eseguiti

```bash
python -m pytest
QT_QPA_PLATFORM=offscreen python -m dbx --smoke
python tools/capture_ui.py
python tools/capture_ui.py --theme dark
```

Esito Checkpoint A: `224 passed`, smoke OK, cattura Aurora/Dark OK.

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

## Screenshot

- `15-database-designer.png`
- `01`–`14` rigenerati in Aurora con categoria Schema nel Navigator.

## Difetti noti accettati

- Il canvas gestisce una relazione per volta nel dialog; chiavi composite si creano dal Table Builder.
- La rinomina tabella resta limitata dal motore.
- Il diagramma è unico (`schema`); più diagrammi sono previsti dopo la 0.3.
- Query Designer, Query Results e query come sorgente dati non sono ancora implementati: O4–O6.

## Prossimo passo

Checkpoint A raggiunto. Dopo `continua`: O4 — motore Query.
