"""Modello delle etichette e del mail merge (0.8 O7).

Un'etichetta è un oggetto di progetto indipendente dai report: descrive un
foglio a griglia (formato, colonne, righe, distanze) e un modello di testo con
riferimenti ``[campo]``. Il runtime legge i record dalla tabella o dalla query
indicata e genera una pagina per ogni foglio di etichette. Il formato è
additivo: i progetti 0.7 restano validi perché i nuovi campi hanno default.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .page_sizes import PAGE_SIZES, page_dimensions

ALIGNMENTS = ("left", "center", "right")

_MARGINS = ("top", "bottom", "left", "right")


def _margin_map(value: float = 0.0) -> dict[str, float]:
    return {side: float(value) for side in _MARGINS}


# Formati pronti: geometria del foglio, non stili grafici. Le misure sono in mm.
LABEL_PRESETS: dict[str, dict[str, Any]] = {
    "a4_70x37": {
        "label": "A4 · 70 × 37 mm (3 × 8)",
        "page_size": "A4",
        "orientation": "portrait",
        "label_width": 70.0,
        "label_height": 37.0,
        "columns": 3,
        "rows": 8,
        "gutter_x": 0.0,
        "gutter_y": 0.0,
        "margins": _margin_map(0.0),
    },
    "avery5160": {
        "label": "Avery 5160 · 66,7 × 25,4 mm (3 × 10)",
        "page_size": "Letter",
        "orientation": "portrait",
        "label_width": 66.7,
        "label_height": 25.4,
        "columns": 3,
        "rows": 10,
        "gutter_x": 2.54,
        "gutter_y": 0.0,
        "margins": {"top": 12.7, "bottom": 12.7, "left": 4.8, "right": 4.8},
    },
    "avery5163": {
        "label": "Avery 5163 · 101,6 × 50,8 mm (2 × 5)",
        "page_size": "Letter",
        "orientation": "portrait",
        "label_width": 101.6,
        "label_height": 50.8,
        "columns": 2,
        "rows": 5,
        "gutter_x": 0.0,
        "gutter_y": 0.0,
        "margins": {"top": 12.7, "bottom": 12.7, "left": 4.8, "right": 4.8},
    },
    "a4_52x30": {
        "label": "A4 · 52 × 30 mm (4 × 9)",
        "page_size": "A4",
        "orientation": "portrait",
        "label_width": 52.0,
        "label_height": 30.0,
        "columns": 4,
        "rows": 9,
        "gutter_x": 0.0,
        "gutter_y": 0.0,
        "margins": {"top": 2.0, "bottom": 2.0, "left": 1.0, "right": 1.0},
    },
}

DEFAULT_PRESET = "a4_70x37"


def preset_labels() -> list[tuple[str, str]]:
    return [(key, str(data["label"])) for key, data in LABEL_PRESETS.items()]


def preset_data(key: str) -> dict[str, Any] | None:
    data = LABEL_PRESETS.get(str(key))
    if data is None:
        return None
    result = dict(data)
    result["margins"] = dict(data["margins"])
    return result


def default_template(fields: list[str]) -> str:
    """Testo iniziale: i primi campi, uno per riga."""
    return "\n".join(f"[{name}]" for name in fields[:3] if name)


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class LabelSpec:
    """Foglio di etichette con sorgente, griglia e modello di testo."""

    name: str
    title: str = ""
    source_type: str = "table"
    table: str = ""
    query: str = ""
    filter: str = ""
    order: str = ""
    page_size: str = "A4"
    orientation: str = "portrait"
    margins: dict[str, float] = dc_field(default_factory=_margin_map)
    label_width: float = 70.0
    label_height: float = 37.0
    columns: int = 3
    rows: int = 8
    gutter_x: float = 0.0
    gutter_y: float = 0.0
    padding: float = 2.0
    font_size: int = 10
    bold: bool = False
    align: str = "left"
    border: bool = False
    color: str = ""
    start_offset: int = 0
    template: str = ""

    # ------------------------------------------------------------------ crea
    @classmethod
    def create(
        cls,
        name: str,
        table: str,
        fields: list[str],
        title: str = "",
        preset: str = DEFAULT_PRESET,
    ) -> "LabelSpec":
        spec = cls(name=name, table=table, title=title or name)
        spec.apply_preset(preset)
        spec.template = default_template(fields)
        return spec

    @classmethod
    def create_for_query(
        cls,
        name: str,
        query: str,
        fields: list[str],
        title: str = "",
        preset: str = DEFAULT_PRESET,
    ) -> "LabelSpec":
        spec = cls(
            name=name,
            title=title or name,
            source_type="query",
            query=query,
        )
        spec.apply_preset(preset)
        spec.template = default_template(fields)
        return spec

    @classmethod
    def from_project(cls, project, name: str) -> "LabelSpec | None":
        artifact = project.artifact("labels", name)
        return cls.from_dict(artifact) if artifact else None

    def apply_preset(self, key: str) -> bool:
        data = preset_data(key)
        if data is None:
            return False
        self.page_size = str(data.get("page_size", "A4"))
        self.orientation = str(data.get("orientation", "portrait"))
        self.label_width = float(data.get("label_width", 70.0))
        self.label_height = float(data.get("label_height", 37.0))
        self.columns = int(data.get("columns", 3))
        self.rows = int(data.get("rows", 8))
        self.gutter_x = float(data.get("gutter_x", 0.0))
        self.gutter_y = float(data.get("gutter_y", 0.0))
        self.margins = dict(data.get("margins") or _margin_map(0.0))
        return True

    def preset_key(self) -> str:
        """Chiave del preset con la stessa geometria, se esiste."""
        for key, data in LABEL_PRESETS.items():
            if (
                str(data["page_size"]) == self.page_size
                and str(data["orientation"]) == self.orientation
                and abs(float(data["label_width"]) - self.label_width) < 0.05
                and abs(float(data["label_height"]) - self.label_height) < 0.05
                and int(data["columns"]) == self.columns
                and int(data["rows"]) == self.rows
                and abs(float(data["gutter_x"]) - self.gutter_x) < 0.05
                and abs(float(data["gutter_y"]) - self.gutter_y) < 0.05
            ):
                return key
        return ""

    # --------------------------------------------------------------- geometria
    def page_dimensions(self) -> tuple[float, float]:
        return page_dimensions(self.page_size, self.orientation)

    @property
    def labels_per_page(self) -> int:
        return max(1, int(self.columns) * int(self.rows))

    def margin(self, side: str) -> float:
        return float(self.margins.get(side, 0.0) or 0.0)

    # --------------------------------------------------------------- validità
    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("L'etichetta non ha un nome")
        if self.source_type not in ("table", "query"):
            errors.append(f"Tipo di sorgente sconosciuto: {self.source_type}")
        if self.source_type == "table" and not self.table:
            errors.append("Nessuna tabella sorgente selezionata")
        if self.source_type == "query" and not self.query:
            errors.append("Nessuna query sorgente selezionata")
        if self.page_size not in PAGE_SIZES:
            errors.append(f"Formato pagina sconosciuto: {self.page_size}")
        if self.orientation not in ("portrait", "landscape"):
            errors.append(f"Orientamento sconosciuto: {self.orientation}")
        if self.label_width <= 0 or self.label_height <= 0:
            errors.append("Larghezza e altezza dell'etichetta devono essere positive")
        if self.columns < 1 or self.rows < 1:
            errors.append("Colonne e righe devono essere almeno 1")
        if self.gutter_x < 0 or self.gutter_y < 0:
            errors.append("Le distanze tra etichette non possono essere negative")
        if self.padding < 0:
            errors.append("Il margine interno dell'etichetta non può essere negativo")
        if self.font_size < 4:
            errors.append("Il corpo del testo è troppo piccolo")
        if self.align not in ALIGNMENTS:
            errors.append(f"Allineamento sconosciuto: {self.align}")
        if self.start_offset < 0:
            errors.append("Le etichette da saltare non possono essere negative")
        for side in _MARGINS:
            if self.margin(side) < 0:
                errors.append(f"Margine pagina negativo: {side}")
        if errors:
            return errors

        page_width, page_height = self.page_dimensions()
        content_width = page_width - self.margin("left") - self.margin("right")
        content_height = page_height - self.margin("top") - self.margin("bottom")
        needed_width = self.columns * self.label_width + max(0, self.columns - 1) * self.gutter_x
        needed_height = self.rows * self.label_height + max(0, self.rows - 1) * self.gutter_y
        if needed_width > content_width + 0.5:
            errors.append(
                f"Le etichette non entrano in larghezza: servono {needed_width:.1f} mm, "
                f"disponibili {content_width:.1f} mm"
            )
        if needed_height > content_height + 0.5:
            errors.append(
                f"Le etichette non entrano in altezza: servono {needed_height:.1f} mm, "
                f"disponibili {content_height:.1f} mm"
            )
        return errors

    # ---------------------------------------------------------------- persistenza
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "source_type": self.source_type,
            "table": self.table,
            "query": self.query,
            "filter": self.filter,
            "order": self.order,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "margins": {side: float(self.margin(side)) for side in _MARGINS},
            "label_width": float(self.label_width),
            "label_height": float(self.label_height),
            "columns": int(self.columns),
            "rows": int(self.rows),
            "gutter_x": float(self.gutter_x),
            "gutter_y": float(self.gutter_y),
            "padding": float(self.padding),
            "font_size": int(self.font_size),
            "bold": bool(self.bold),
            "align": self.align,
            "border": bool(self.border),
            "color": self.color,
            "start_offset": int(self.start_offset),
            "template": self.template,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LabelSpec":
        margins = _margin_map()
        for side in _MARGINS:
            margins[side] = _as_float((data.get("margins") or {}).get(side), 0.0)
        return cls(
            name=str(data.get("name", "")),
            title=str(data.get("title", "")),
            source_type=str(data.get("source_type", "table") or "table"),
            table=str(data.get("table", "")),
            query=str(data.get("query", "")),
            filter=str(data.get("filter", "")),
            order=str(data.get("order", "")),
            page_size=str(data.get("page_size", "A4")),
            orientation=str(data.get("orientation", "portrait")),
            margins=margins,
            label_width=_as_float(data.get("label_width"), 70.0),
            label_height=_as_float(data.get("label_height"), 37.0),
            columns=_as_int(data.get("columns"), 3),
            rows=_as_int(data.get("rows"), 8),
            gutter_x=_as_float(data.get("gutter_x"), 0.0),
            gutter_y=_as_float(data.get("gutter_y"), 0.0),
            padding=_as_float(data.get("padding"), 2.0),
            font_size=_as_int(data.get("font_size"), 10),
            bold=bool(data.get("bold", False)),
            align=str(data.get("align", "left")),
            border=bool(data.get("border", False)),
            color=str(data.get("color", "")),
            start_offset=_as_int(data.get("start_offset"), 0),
            template=str(data.get("template", "")),
        )


__all__ = [
    "ALIGNMENTS",
    "DEFAULT_PRESET",
    "LABEL_PRESETS",
    "LabelSpec",
    "default_template",
    "preset_data",
    "preset_labels",
]
