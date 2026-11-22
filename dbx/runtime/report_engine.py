"""Motore report a bande: modello, layout e paginazione (E1, E3–E6).

Il layout è indipendente dal disegno: produce pagine con operazioni
posizionate in millimetri, così è testabile senza GUI e disegnabile su
schermo, stampante o PDF dallo stesso risultato.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable

from ..core.expressions import Expression, ExpressionError
from ..core.page_sizes import PAGE_SIZES, page_dimensions

_FIELD_TOKEN = re.compile(r"\[([^\[\]]+)\]")

MM_PER_PT = 0.3527778
LINE_FACTOR = 1.28
BAND_NAMES = (
    "title",
    "page_header",
    "group_header",
    "detail",
    "group_footer",
    "page_footer",
    "summary",
)
DEFAULT_BAND_ORDER = list(BAND_NAMES)
BAND_LABELS = {
    "title": "Title",
    "page_header": "Page header",
    "group_header": "Group header",
    "detail": "Details",
    "group_footer": "Group footer",
    "page_footer": "Page footer",
    "summary": "Summary",
}
CONTROL_KINDS = ("text", "field", "expr", "total", "line", "rect", "image")
DEFAULT_MARGINS = {"top": 15.0, "bottom": 15.0, "left": 15.0, "right": 15.0}


def field_display_name(table: str, field: str) -> str:
    """Nome visualizzato in stile Crystal: ``TABELLA->CAMPO``."""
    return f"{table}->{field}" if table else field


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "sì", "si", "on")



@dataclass
class Control:
    id: str
    kind: str = "text"
    x: float = 0.0
    y: float = 0.0
    w: float = 40.0
    h: float = 6.0
    text: str = ""
    expr: str = ""
    font_size: int = 10
    font_name: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "left"
    border: bool = False
    fill: str = ""
    color: str = ""
    func: str = "sum"
    label: str = ""
    fmt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "text": self.text,
            "expr": self.expr,
            "font_size": self.font_size,
            "font_name": self.font_name,
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "align": self.align,
            "border": self.border,
            "fill": self.fill,
            "color": self.color,
            "func": self.func,
            "label": self.label,
            "fmt": self.fmt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Control":
        return cls(
            id=str(data.get("id", "")),
            kind=str(data.get("kind", "text")),
            x=float(data.get("x", 0) or 0),
            y=float(data.get("y", 0) or 0),
            w=float(data.get("w", 40) or 0),
            h=float(data.get("h", 6) or 0),
            text=str(data.get("text", "")),
            expr=str(data.get("expr", "")),
            font_size=int(data.get("font_size", 10) or 10),
            font_name=str(data.get("font_name", "")),
            bold=bool(data.get("bold", False)),
            italic=bool(data.get("italic", False)),
            underline=bool(data.get("underline", False)),
            align=str(data.get("align", "left")),
            border=bool(data.get("border", False)),
            fill=str(data.get("fill", "")),
            color=str(data.get("color", "")),
            func=str(data.get("func", "sum")),
            label=str(data.get("label", "")),
            fmt=str(data.get("fmt", "")),
        )


@dataclass
class ReportSpec:
    name: str
    title: str = ""
    table: str = ""
    source_type: str = "table"
    query: str = ""
    filter: str = ""
    order: str = ""
    group_by: str = ""
    group_label: str = ""
    page_size: str = "A4"
    orientation: str = "portrait"
    margins: dict[str, float] = dc_field(default_factory=lambda: dict(DEFAULT_MARGINS))
    bands: dict[str, list[Control]] = dc_field(
        default_factory=lambda: {name: [] for name in BAND_NAMES}
    )
    band_order: list[str] = dc_field(default_factory=list)
    band_heights: dict[str, float] = dc_field(default_factory=dict)
    band_visible: dict[str, bool] = dc_field(default_factory=dict)
    sort_fields: list[dict[str, str]] = dc_field(default_factory=list)
    groups: list[dict[str, str]] = dc_field(default_factory=list)

    @classmethod
    def create(cls, name: str, table: str, title: str = "") -> "ReportSpec":
        spec = cls(name=name, table=table, title=title or name)
        spec._default_bands()
        return spec

    @classmethod
    def create_for_query(
        cls, name: str, query: str, fields: list[str], title: str = ""
    ) -> "ReportSpec":
        """Report sulle colonne di una query, con dettaglio sul primo campo."""
        spec = cls(
            name=name,
            title=title or name,
            source_type="query",
            query=query,
        )
        spec._default_bands(fields[0] if fields else "")
        return spec

    def _default_bands(self, first_field: str = "") -> None:
        self.bands["title"].append(
            Control(id="titolo", kind="text", x=0, y=0, w=170, h=12, text=self.title or self.name, font_size=16, bold=True)
        )
        self.bands["page_header"].append(
            Control(id="intestazione", kind="text", x=0, y=0, w=170, h=6, text="dBX — report", font_size=8, color="#666666")
        )
        self.bands["detail"].append(
            Control(id="dettaglio", kind="field", x=0, y=0, w=170, h=6, expr=first_field, font_size=10, border=False)
        )
        self.bands["page_footer"].append(
            Control(id="pagina", kind="text", x=0, y=0, w=170, h=6, text="Pagina {PAGINA} di {PAGINE}", font_size=8, align="right")
        )

    def band(self, name: str) -> list[Control]:
        return self.bands.get(name, [])

    def effective_band_order(self) -> list[str]:
        """Ordine delle bande sul foglio, completato con quelle mancanti."""
        order = [name for name in self.band_order if name in BAND_NAMES]
        for name in BAND_NAMES:
            if name not in order:
                order.append(name)
        return order

    def is_visible(self, name: str) -> bool:
        return bool(self.band_visible.get(name, True))

    def band_height(self, name: str, minimum: float = 0.0) -> float:
        return max(float(self.band_heights.get(name, 0.0) or 0.0), minimum)

    def effective_groups(self) -> list[dict[str, str]]:
        """Gruppi espliciti oppure il vecchio ``group_by`` per compatibilità."""
        if self.groups:
            return [group for group in self.groups if group.get("field")]
        if self.group_by:
            return [{"field": self.group_by, "label": self.group_label}]
        return []

    def page_dimensions(self) -> tuple[float, float]:
        return page_dimensions(self.page_size, self.orientation)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("Il report non ha un nome")
        if self.source_type not in ("table", "query"):
            errors.append(f"Tipo di sorgente sconosciuto: {self.source_type}")
        if self.source_type == "table" and not self.table:
            errors.append("Nessuna tabella sorgente selezionata")
        if self.source_type == "query" and not self.query:
            errors.append("Nessuna query sorgente selezionata")
        for band_name in self.bands:
            if band_name not in BAND_NAMES:
                errors.append(f"Banda sconosciuta: {band_name}")
        if len(set(self.band_order)) != len(self.band_order):
            errors.append("Ordine delle bande con duplicati")
        for band_name in self.band_order:
            if band_name not in BAND_NAMES:
                errors.append(f"Ordine bande: banda sconosciuta {band_name}")
        for entry in self.sort_fields:
            if not str(entry.get("field", "")).strip():
                errors.append("Ordinamento senza campo")
            if str(entry.get("direction", "asc")).lower() not in ("asc", "desc"):
                errors.append(f"Direzione di ordinamento non valida: {entry.get('direction')}")
        for entry in self.groups:
            if not str(entry.get("field", "")).strip():
                errors.append("Gruppo senza campo")
        for band_name, controls in self.bands.items():
            for control in controls:
                if control.kind not in CONTROL_KINDS:
                    errors.append(f"{band_name}: controllo di tipo sconosciuto {control.kind}")
                if control.kind in ("field", "expr", "total") and not control.expr:
                    errors.append(f"{band_name}: espressione mancante nel controllo {control.id}")
                if control.kind == "total" and control.func not in ("sum", "count", "avg", "min", "max"):
                    errors.append(f"{band_name}: funzione totale non valida {control.func}")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "table": self.table,
            "source_type": self.source_type,
            "query": self.query,
            "filter": self.filter,
            "order": self.order,
            "group_by": self.group_by,
            "group_label": self.group_label,
            "page_size": self.page_size,
            "orientation": self.orientation,
            "margins": dict(self.margins),
            "bands": {
                name: [control.to_dict() for control in controls]
                for name, controls in self.bands.items()
            },
            "band_order": list(self.band_order),
            "band_heights": {name: float(value) for name, value in self.band_heights.items()},
            "band_visible": {name: bool(value) for name, value in self.band_visible.items()},
            "sort_fields": [
                {"field": str(entry.get("field", "")), "direction": str(entry.get("direction", "asc"))}
                for entry in self.sort_fields
            ],
            "groups": [
                {"field": str(entry.get("field", "")), "label": str(entry.get("label", ""))}
                for entry in self.groups
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSpec":
        margins = dict(DEFAULT_MARGINS)
        margins.update({k: float(v) for k, v in (data.get("margins") or {}).items()})
        bands: dict[str, list[Control]] = {name: [] for name in BAND_NAMES}
        for name, controls in (data.get("bands") or {}).items():
            bands[str(name)] = [Control.from_dict(c) for c in controls]
        band_order = [
            str(name)
            for name in (data.get("band_order") or [])
            if str(name) in BAND_NAMES
        ]
        band_heights = {
            str(name): float(value)
            for name, value in (data.get("band_heights") or {}).items()
            if str(name) in BAND_NAMES
        }
        band_visible = {
            str(name): _as_bool(value)
            for name, value in (data.get("band_visible") or {}).items()
            if str(name) in BAND_NAMES
        }
        sort_fields = [
            {
                "field": str(entry.get("field", "")),
                "direction": str(entry.get("direction", "asc")).lower(),
            }
            for entry in (data.get("sort_fields") or [])
            if isinstance(entry, dict)
        ]
        groups = [
            {
                "field": str(entry.get("field", "")),
                "label": str(entry.get("label", "")),
            }
            for entry in (data.get("groups") or [])
            if isinstance(entry, dict)
        ]
        return cls(
            name=str(data.get("name", "")),
            title=str(data.get("title", "")),
            table=str(data.get("table", "")),
            source_type=str(data.get("source_type", "table") or "table"),
            query=str(data.get("query", "")),
            filter=str(data.get("filter", "")),
            order=str(data.get("order", "")),
            group_by=str(data.get("group_by", "")),
            group_label=str(data.get("group_label", "")),
            page_size=str(data.get("page_size", "A4")),
            orientation=str(data.get("orientation", "portrait")),
            margins=margins,
            bands=bands,
            band_order=band_order,
            band_heights=band_heights,
            band_visible=band_visible,
            sort_fields=sort_fields,
            groups=groups,
        )


@dataclass
class Op:
    kind: str
    x: float
    y: float
    w: float
    h: float
    text: str = ""
    lines: list[str] = dc_field(default_factory=list)
    font_size: int = 10
    font_name: str = ""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "left"
    border: bool = False
    fill: str = ""
    color: str = ""


@dataclass
class Page:
    index: int
    width: float
    height: float
    ops: list[Op] = dc_field(default_factory=list)


def wrap_text(text: str, width_mm: float, font_size: int, bold: bool = False) -> list[str]:
    """A capo per parole con larghezza stimata: deterministica e testabile."""
    if text is None:
        return []
    raw = str(text)
    if not raw:
        return []
    char_width = max(font_size * MM_PER_PT * (0.55 if bold else 0.50), 0.05)
    max_chars = max(1, int(width_mm / char_width))
    result: list[str] = []
    for paragraph in raw.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if len(candidate) <= max_chars or not line:
                line = candidate
            else:
                result.append(line)
                line = word
        result.append(line)
    return result


def text_height(lines: Iterable[str], font_size: int) -> float:
    return len(list(lines)) * font_size * MM_PER_PT * LINE_FACTOR


def format_number(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sì" if value else "No"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:,.2f}"
        text = text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        if text.endswith(",00"):
            text = text[:-3]
        return text
    return str(value)


def _format_value(value: Any, fmt: str = "") -> str:
    """Formatta un valore di record: date, numeri e booleani."""
    from datetime import date, datetime

    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sì" if value else "No"
    if isinstance(value, datetime):
        return value.strftime(_strftime(fmt) or "%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime(_strftime(fmt) or "%d/%m/%Y")
    if isinstance(value, float):
        if fmt and all(char in "#0.," for char in fmt):
            try:
                return format(value, fmt)
            except (ValueError, TypeError):
                pass
        return format_number(value)
    return str(value)


def _strftime(fmt: str) -> str:
    if not fmt:
        return ""
    if "%" in fmt:
        return fmt
    from ..core.types import python_format

    return python_format(fmt, "date")


class _Accumulator:
    def __init__(self, func: str) -> None:
        self.func = func
        self.total = 0.0
        self.count = 0
        self.minimum: float | None = None
        self.maximum: float | None = None

    def add(self, value: Any) -> None:
        if value is None or value == "":
            return
        if self.func == "count":
            self.count += 1
            return
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        self.count += 1
        self.total += number
        self.minimum = number if self.minimum is None else min(self.minimum, number)
        self.maximum = number if self.maximum is None else max(self.maximum, number)

    def value(self) -> Any:
        if self.func == "count":
            return self.count
        if self.func == "sum":
            return self.total
        if self.func == "avg":
            return self.total / self.count if self.count else 0
        if self.func == "min":
            return self.minimum
        if self.func == "max":
            return self.maximum
        return None


class ReportRenderer:
    """Costruisce le pagine del report a partire dai record."""

    def __init__(self, spec: ReportSpec, rows: Iterable[dict[str, Any]], variables: dict[str, Any] | None = None):
        errors = spec.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.spec = spec
        self.rows = list(rows)
        self.variables = variables or {}
        self.page_width, self.page_height = spec.page_dimensions()
        self.margin_top = float(spec.margins.get("top", 15))
        self.margin_bottom = float(spec.margins.get("bottom", 15))
        self.margin_left = float(spec.margins.get("left", 15))
        self.margin_right = float(spec.margins.get("right", 15))
        self.content_width = self.page_width - self.margin_left - self.margin_right
        self._pages: list[Page] = []
        self._page: Page | None = None
        self._y = self.margin_top
        self._report_acc: dict[str, _Accumulator] = {}
        self._group_acc: dict[tuple[str, ...], dict[str, _Accumulator]] = {}
        self._group_fields = spec.effective_groups()
        total_controls = [
            control
            for controls in spec.bands.values()
            for control in controls
            if control.kind == "total"
        ]
        self._total_controls = total_controls
        self._report_acc = {c.id: _Accumulator(c.func) for c in total_controls}

    # ------------------------------------------------------------------ layout
    def _footer_height(self) -> float:
        if not self.spec.is_visible("page_footer"):
            return 0.0
        controls = self.spec.band("page_footer")
        if not controls:
            return self.spec.band_height("page_footer")
        return self.spec.band_height(
            "page_footer", max(c.y + c.h for c in controls)
        )

    def _content_bottom(self) -> float:
        return self.page_height - self.margin_bottom - self._footer_height()

    def _band_height(self, name: str) -> float:
        if not self.spec.is_visible(name):
            return 0.0
        controls = self.spec.band(name)
        minimum = max((c.y + c.h for c in controls), default=0.0)
        return self.spec.band_height(name, minimum)

    def _new_page(self) -> Page:
        page = Page(index=len(self._pages), width=self.page_width, height=self.page_height)
        self._pages.append(page)
        return page

    def _start_page(self) -> None:
        self._page = self._new_page()
        self._y = self.margin_top
        first_page = len(self._pages) == 1
        for name in self.spec.effective_band_order():
            if name not in ("title", "page_header"):
                continue
            if name == "title" and not first_page:
                continue
            self._emit_band(name, None, allow_break=False)

    def _finish_page(self) -> None:
        if self._page is None:
            return
        if self.spec.is_visible("page_footer"):
            controls = self.spec.band("page_footer")
            if controls:
                footer_top = self.page_height - self.margin_bottom - self._footer_height()
                for control in controls:
                    self._place(control, footer_top, None, None, page=self._page)
        self._page = None

    def _ensure_space(self, height: float) -> None:
        if self._page is None:
            self._start_page()
            return
        if self._y + height > self._content_bottom() and height > 0:
            self._finish_page()
            self._start_page()

    def _place(self, control: Control, band_top: float, record: dict[str, Any] | None, group: tuple[str, ...] | None, page: Page | None = None) -> None:
        target = page or self._page
        if target is None:
            return
        text = self._control_text(control, record, group)
        lines = (
            wrap_text(text, control.w, control.font_size, control.bold)
            if control.kind in ("text", "field", "expr", "total")
            else []
        )
        target.ops.append(
            Op(
                kind=control.kind,
                x=self.margin_left + control.x,
                y=band_top + control.y,
                w=control.w,
                h=max(control.h, text_height(lines, control.font_size)),
                text=text,
                lines=lines,
                font_size=control.font_size,
                font_name=control.font_name,
                bold=control.bold,
                italic=control.italic,
                underline=control.underline,
                align=control.align,
                border=control.border,
                fill=control.fill,
                color=control.color,
            )
        )

    def _emit_band(self, name: str, record: dict[str, Any] | None, group: tuple[str, ...] | None = None, allow_break: bool = True) -> None:
        if not self.spec.is_visible(name):
            return
        controls = self.spec.band(name)
        height = self._band_height(name)
        if not controls and height <= 0:
            return
        if allow_break:
            self._ensure_space(height)
        if self._page is None:
            self._start_page()
        for control in controls:
            self._place(control, self._y, record, group)
        self._y += height

    def _group_key(self, record: dict[str, Any]) -> tuple[str, ...] | None:
        if not self._group_fields:
            return None
        values: list[str] = []
        for group in self._group_fields:
            field = str(group.get("field", ""))
            try:
                value = Expression(field).evaluate(record, self.variables, self.spec.table)
            except ExpressionError:
                value = record.get(field)
            values.append("" if value is None else str(value))
        return tuple(values)

    def _value_of(self, source: str, record: dict[str, Any]) -> Any:
        """Valore di un campo o di un'espressione, con nomi nudi tollerati."""
        source = str(source or "").strip()
        if not source:
            return None
        if "[" not in source and "(" not in source:
            return record.get(source)
        try:
            return Expression(source).evaluate(record, self.variables, self.spec.table)
        except ExpressionError:
            return record.get(source)

    def _accumulate(self, record: dict[str, Any], group: tuple[str, ...] | None) -> None:
        for control in self._total_controls:
            value = self._value_of(control.expr, record)
            self._report_acc[control.id].add(value)
            if not group:
                continue
            for level in range(len(group)):
                key = group[: level + 1]
                bucket = self._group_acc.setdefault(
                    key, {c.id: _Accumulator(c.func) for c in self._total_controls}
                )
                bucket[control.id].add(value)

    def _total_value(self, control: Control, group: tuple[str, ...] | None) -> Any:
        if control.kind != "total":
            return None
        if group and control.id in self._group_acc.get(group, {}):
            return self._group_acc[group][control.id].value()
        return self._report_acc[control.id].value()

    def _control_text(self, control: Control, record: dict[str, Any] | None, group: tuple[str, ...] | None) -> str:
        if control.kind in ("line", "rect", "image"):
            return ""
        if control.kind == "text":
            return self._interpolate(control.text, record)
        if control.kind == "total":
            value = self._total_value(control, group)
            text = format_number(value)
            return f"{control.label}{text}" if control.label else text
        if record is None:
            return ""
        value = self._value_of(control.expr, record)
        return _format_value(value, control.fmt)

    def _interpolate(self, text: str, record: dict[str, Any] | None) -> str:
        """Sostituisce i riferimenti ``[campo]`` nei testi fissi, se c'è un record."""
        if record is None or "[" not in text:
            return text

        def replace(match: re.Match[str]) -> str:
            value = self._value_of(match.group(1), record)
            return "" if value is None else str(value)

        return _FIELD_TOKEN.sub(replace, text)

    def _sort_key(self, record: dict[str, Any], field: str) -> tuple[int, Any]:
        value = self._value_of(field, record)
        if value is None or value == "":
            return (3, "")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return (0, float(value))
        return (1, str(value).casefold())

    def _sorted_rows(self) -> list[dict[str, Any]]:
        entries = [
            entry
            for entry in self.spec.sort_fields
            if str(entry.get("field", "")).strip()
        ]
        rows = list(self.rows)
        for entry in reversed(entries):
            field = str(entry.get("field", ""))
            reverse = str(entry.get("direction", "asc")).lower() == "desc"
            rows.sort(key=lambda row, f=field: self._sort_key(row, f), reverse=reverse)
        return rows

    def layout(self) -> list[Page]:
        self._pages = []
        self._page = None
        self._report_acc = {c.id: _Accumulator(c.func) for c in self._total_controls}
        self._group_acc = {}
        self._start_page()
        current: tuple[str, ...] | None = None
        for record in self._sorted_rows():
            key = self._group_key(record)
            if key != current:
                shared = 0
                if current is not None and key is not None:
                    while (
                        shared < len(current)
                        and shared < len(key)
                        and current[shared] == key[shared]
                    ):
                        shared += 1
                if current is not None:
                    for level in range(len(current) - 1, shared - 1, -1):
                        self._emit_band("group_footer", None, group=current[: level + 1])
                if key is not None:
                    for level in range(shared, len(key)):
                        self._emit_band("group_header", record, group=key[: level + 1])
                current = key
            self._accumulate(record, key)
            self._emit_band("detail", record)
        if current is not None:
            for level in range(len(current) - 1, -1, -1):
                self._emit_band("group_footer", None, group=current[: level + 1])
        if not self.rows:
            self._emit_band("detail", None)
        self._emit_band("summary", None)
        self._finish_page()

        total_pages = len(self._pages)
        for page in self._pages:
            for op in page.ops:
                if "{PAGINA}" in op.text or "{PAGINE}" in op.text:
                    op.text = op.text.replace("{PAGINA}", str(page.index + 1)).replace(
                        "{PAGINE}", str(total_pages)
                    )
                    op.lines = wrap_text(op.text, op.w, op.font_size, op.bold)
        return self._pages


def render_report(
    spec: ReportSpec,
    rows: Iterable[dict[str, Any]],
    variables: dict[str, Any] | None = None,
) -> list[Page]:
    return ReportRenderer(spec, rows, variables).layout()
