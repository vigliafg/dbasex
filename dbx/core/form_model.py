"""Modello dei form (D1): controlli, pagine e generazione assistita."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from .metadata import Table, new_id, slugify

CONTROL_KINDS = {
    "label": "Etichetta",
    "field": "Campo di testo",
    "memo": "Testo lungo",
    "checkbox": "Casella di controllo",
    "combo": "Casella combinata",
    "number": "Numero",
    "date": "Data",
    "button": "Pulsante",
    "grid": "Sottomaschera",
    "line": "Linea",
    "rect": "Riquadro",
    "image": "Immagine",
}

BUTTON_ACTIONS = {
    "new": "Nuovo record",
    "save": "Salva",
    "delete": "Elimina",
    "first": "Primo",
    "previous": "Precedente",
    "next": "Successivo",
    "last": "Ultimo",
    "close": "Chiudi",
}

FIELD_KINDS = ("field", "memo", "checkbox", "combo", "number", "date")

# Nomi dBASE degli oggetti, usati dall'Inspector e dai log degli eventi.
OBJECT_BASENAMES = {
    "label": "text",
    "field": "entryfield",
    "memo": "memoeditor",
    "checkbox": "checkbox",
    "combo": "combobox",
    "number": "spinbox",
    "date": "datefield",
    "button": "commandbutton",
    "grid": "grid",
    "line": "line",
    "rect": "rectangle",
    "image": "image",
}

# Eventi riconosciuti dal dispatcher del runtime.
CONTROL_EVENTS = ("onClick", "onEnter", "onExit")
FORM_EVENTS = ("onOpen", "onClose")


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def object_name(control: "FormControl", controls: list["FormControl"]) -> str:
    """Nome in stile dBASE: ``form.entryfield1``, ``form.commandbutton2``."""
    base = OBJECT_BASENAMES.get(control.kind, control.kind or "control")
    number = 0
    for candidate in controls:
        if candidate.kind == control.kind:
            number += 1
        if candidate is control:
            break
    return f"form.{base}{max(1, number)}"


@dataclass
class FormControl:
    id: str
    kind: str = "field"
    field: str = ""
    text: str = ""
    x: int = 8
    y: int = 8
    w: int = 180
    h: int = 24
    font_size: int = 10
    font_name: str = ""
    bold: bool = False
    align: str = "left"
    action: str = "save"
    lookup: str = ""
    table: str = ""
    link_parent: str = ""
    link_child: str = ""
    backcolor: str = ""
    forecolor: str = ""
    events: dict[str, str] = dc_field(default_factory=dict)
    methods: dict[str, str] = dc_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "field": self.field,
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "font_size": self.font_size,
            "font_name": self.font_name,
            "bold": self.bold,
            "align": self.align,
            "action": self.action,
            "lookup": self.lookup,
            "table": self.table,
            "link_parent": self.link_parent,
            "link_child": self.link_child,
            "backcolor": self.backcolor,
            "forecolor": self.forecolor,
            "events": dict(self.events),
            "methods": dict(self.methods),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormControl":
        return cls(
            id=str(data.get("id") or new_id()),
            kind=str(data.get("kind", "field")),
            field=str(data.get("field", "")),
            text=str(data.get("text", "")),
            x=int(data.get("x", 8) or 0),
            y=int(data.get("y", 8) or 0),
            w=int(data.get("w", 180) or 0),
            h=int(data.get("h", 24) or 0),
            font_size=int(data.get("font_size", 10) or 10),
            font_name=str(data.get("font_name", "")),
            bold=bool(data.get("bold", False)),
            align=str(data.get("align", "left")),
            action=str(data.get("action", "save")),
            lookup=str(data.get("lookup", "")),
            table=str(data.get("table", "")),
            link_parent=str(data.get("link_parent", "")),
            link_child=str(data.get("link_child", "")),
            backcolor=str(data.get("backcolor", "")),
            forecolor=str(data.get("forecolor", "")),
            events=_string_map(data.get("events")),
            methods=_string_map(data.get("methods")),
        )


@dataclass
class FormPage:
    caption: str = "Dati"
    controls: list[FormControl] = dc_field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"caption": self.caption, "controls": [c.to_dict() for c in self.controls]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormPage":
        return cls(
            caption=str(data.get("caption", "Dati")),
            controls=[FormControl.from_dict(c) for c in data.get("controls", [])],
        )


@dataclass
class FormSpec:
    name: str
    caption: str = ""
    table: str = ""
    source_type: str = "table"
    query: str = ""
    width: int = 620
    height: int = 440
    order: str = ""
    pages: list[FormPage] = dc_field(default_factory=lambda: [FormPage()])
    backcolor: str = ""
    forecolor: str = ""
    events: dict[str, str] = dc_field(default_factory=dict)
    methods: dict[str, str] = dc_field(default_factory=dict)

    # ------------------------------------------------------------------ API
    def all_controls(self) -> list[FormControl]:
        return [control for page in self.pages for control in page.controls]

    def control_object_name(self, control: FormControl) -> str:
        for page in self.pages:
            if control in page.controls:
                return object_name(control, page.controls)
        return object_name(control, self.all_controls())

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name:
            errors.append("Il form non ha un nome")
        if self.source_type not in ("table", "query"):
            errors.append(f"Tipo di sorgente sconosciuto: {self.source_type}")
        if self.source_type == "table" and not self.table:
            errors.append("Nessuna tabella collegata al form")
        if self.source_type == "query" and not self.query:
            errors.append("Nessuna query collegata al form")
        if not self.pages:
            errors.append("Il form non ha pagine")
        for page in self.pages:
            for control in page.controls:
                if control.kind not in CONTROL_KINDS:
                    errors.append(f"Controllo {control.id}: tipo sconosciuto {control.kind}")
                if control.kind in FIELD_KINDS and not control.field:
                    errors.append(f"Controllo {control.id}: campo non impostato")
                if control.kind == "grid" and not control.table:
                    errors.append(f"Controllo {control.id}: sottomaschera senza tabella")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "caption": self.caption,
            "table": self.table,
            "source_type": self.source_type,
            "query": self.query,
            "width": self.width,
            "height": self.height,
            "order": self.order,
            "pages": [page.to_dict() for page in self.pages],
            "backcolor": self.backcolor,
            "forecolor": self.forecolor,
            "events": dict(self.events),
            "methods": dict(self.methods),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FormSpec":
        pages = [FormPage.from_dict(p) for p in data.get("pages", [])]
        if not pages:
            pages = [FormPage()]
        return cls(
            name=str(data.get("name", "")),
            caption=str(data.get("caption", "")),
            table=str(data.get("table", "")),
            source_type=str(data.get("source_type", "table") or "table"),
            query=str(data.get("query", "")),
            width=int(data.get("width", 620) or 620),
            height=int(data.get("height", 440) or 440),
            order=str(data.get("order", "")),
            pages=pages,
            backcolor=str(data.get("backcolor", "")),
            forecolor=str(data.get("forecolor", "")),
            events=_string_map(data.get("events")),
            methods=_string_map(data.get("methods")),
        )

    # ------------------------------------------------------- generazione form
    @classmethod
    def create_from_query(
        cls, columns_table: Table, query: str, name: str | None = None
    ) -> "FormSpec":
        """Form generato dalle colonne di una query, in sola lettura."""
        spec = cls.create(columns_table, name=name or f"form_{slugify(query)}")
        spec.source_type = "query"
        spec.query = query
        spec.table = ""
        spec.caption = columns_table.display_name()
        for page in spec.pages:
            page.controls = [
                control
                for control in page.controls
                if not (
                    control.kind == "button"
                    and control.action in ("new", "save", "delete")
                )
            ]
        return spec

    @classmethod
    def create(cls, table: Table, name: str | None = None) -> "FormSpec":
        spec = cls(
            name=name or f"form_{slugify(table.name)}",
            caption=table.display_name(),
            table=table.name,
            source_type="table",
            width=620,
            height=120 + 32 * max(1, len(table.fields)),
        )
        page = FormPage(caption="Dati")
        page.controls.append(
            FormControl(
                id=new_id(),
                kind="label",
                text=table.display_name(),
                x=12,
                y=8,
                w=400,
                h=26,
                font_size=14,
                bold=True,
            )
        )
        y = 44
        for field in table.fields:
            page.controls.append(
                FormControl(
                    id=new_id(),
                    kind="label",
                    text=field.display_name(),
                    x=12,
                    y=y + 3,
                    w=150,
                    h=20,
                )
            )
            kind = "field"
            if field.type in ("integer", "decimal"):
                kind = "number"
            elif field.type == "boolean":
                kind = "checkbox"
            elif field.type == "memo":
                kind = "memo"
            elif field.type == "date":
                kind = "date"
            elif field.lookup:
                kind = "combo"
            page.controls.append(
                FormControl(
                    id=new_id(),
                    kind=kind,
                    field=field.name,
                    x=170,
                    y=y,
                    w=300,
                    h=52 if kind == "memo" else 24,
                    lookup=field.lookup,
                )
            )
            y += 30 if kind != "memo" else 58
        button_x = 12
        for action, caption in (
            ("first", "Primo"),
            ("previous", "Prec."),
            ("next", "Succ."),
            ("last", "Ultimo"),
            ("new", "Nuovo"),
            ("save", "Salva"),
            ("delete", "Elimina"),
            ("close", "Chiudi"),
        ):
            page.controls.append(
                FormControl(
                    id=new_id(),
                    kind="button",
                    text=caption,
                    x=button_x,
                    y=y + 12,
                    w=84,
                    h=28,
                    action=action,
                )
            )
            button_x += 90
        spec.height = max(spec.height, y + 60)
        spec.width = max(spec.width, button_x + 12)
        spec.pages = [page]
        return spec

    @classmethod
    def create_master_detail(
        cls,
        parent: Table,
        child: Table,
        link_parent: str,
        link_child: str,
        name: str | None = None,
    ) -> "FormSpec":
        spec = cls.create(parent, name=name)
        page = spec.pages[0]
        grid_y = spec.height - 40
        page.controls.append(
            FormControl(
                id=new_id(),
                kind="label",
                text=f"{child.display_name()} collegati",
                x=12,
                y=grid_y,
                w=300,
                h=20,
                bold=True,
            )
        )
        page.controls.append(
            FormControl(
                id=new_id(),
                kind="grid",
                table=child.name,
                link_parent=link_parent,
                link_child=link_child,
                x=12,
                y=grid_y + 22,
                w=spec.width - 40,
                h=160,
            )
        )
        spec.height += 190
        return spec


def form_references(spec: FormSpec) -> set[str]:
    """Tabelle citate dal form (per la validazione di progetto)."""
    tables = {spec.table} if spec.table else set()
    for control in spec.all_controls():
        if control.kind == "grid" and control.table:
            tables.add(control.table)
        if control.lookup and "." in control.lookup:
            tables.add(control.lookup.split(".", 1)[0])
    return tables
