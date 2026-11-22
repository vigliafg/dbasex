"""Rinomina, duplicazione e manutenzione degli oggetti (0.6).

Le trasformazioni restano nei metadati JSON e nel database SQLite: nessun
designer viene riscritto a mano. La rinomina aggiorna i riferimenti noti
(tabelle, query, form, report, script e diagrammi) e lascia intatti i testi
liberi che potrebbero contenere lo stesso nome per altri motivi.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from .metadata import Table, check_identifier
from .project import CATEGORY_LABELS, Project, ProjectError


# --------------------------------------------------------------- riferimenti
def _exact(value: Any, old: str, new: str) -> Any:
    return new if isinstance(value, str) and value == old else value


def _dotted(value: Any, old: str, new: str) -> Any:
    if not isinstance(value, str):
        return value
    if value == old:
        return new
    prefix = old + "."
    if value.startswith(prefix):
        return new + value[len(old):]
    return value


def _brackets(value: Any, old: str, new: str) -> Any:
    """Riscrive i riferimenti ``[tabella.campo]`` nelle espressioni."""
    if not isinstance(value, str) or old not in value:
        return value
    return re.sub(r"\[\s*" + re.escape(old) + r"\s*\.", f"[{new}.", value)


def _rewrite_table(table_artifact: dict[str, Any], old: str, new: str) -> None:
    for field in table_artifact.get("fields", []):
        if not isinstance(field, dict):
            continue
        if field.get("lookup"):
            field["lookup"] = _dotted(field["lookup"], old, new)
        if field.get("calculated"):
            field["calculated"] = _brackets(field["calculated"], old, new)
        if field.get("auto_enter"):
            field["auto_enter"] = _brackets(field["auto_enter"], old, new)
    for fk in table_artifact.get("foreign_keys", []):
        if isinstance(fk, dict) and fk.get("ref_table") == old:
            fk["ref_table"] = new


def _rewrite_query(artifact: dict[str, Any], old: str, new: str) -> None:
    artifact["base"] = _exact(artifact.get("base", ""), old, new)
    for field in artifact.get("fields", []):
        if isinstance(field, dict):
            field["table"] = _exact(field.get("table", ""), old, new)
    for join in artifact.get("joins", []):
        if not isinstance(join, dict):
            continue
        join["table"] = _exact(join.get("table", ""), old, new)
        join["left"] = _dotted(join.get("left", ""), old, new)
        join["right"] = _dotted(join.get("right", ""), old, new)
    for condition in artifact.get("filters", []):
        if not isinstance(condition, dict):
            continue
        condition["field"] = _dotted(condition.get("field", ""), old, new)
        if condition.get("op") == "ref":
            condition["value"] = _dotted(condition.get("value", ""), old, new)
    for sort in artifact.get("sorts", []):
        if isinstance(sort, dict):
            sort["field"] = _dotted(sort.get("field", ""), old, new)


def _rewrite_control(control: dict[str, Any], old: str, new: str) -> None:
    control["table"] = _exact(control.get("table", ""), old, new)
    if control.get("lookup"):
        control["lookup"] = _dotted(control["lookup"], old, new)
    if control.get("expr"):
        control["expr"] = _brackets(control["expr"], old, new)


def _rewrite_form(artifact: dict[str, Any], old: str, new: str) -> None:
    artifact["table"] = _exact(artifact.get("table", ""), old, new)
    for page in artifact.get("pages", []):
        if not isinstance(page, dict):
            continue
        for control in page.get("controls", []):
            if isinstance(control, dict):
                _rewrite_control(control, old, new)
    for control in artifact.get("controls", []):
        if isinstance(control, dict):
            _rewrite_control(control, old, new)


def _rewrite_report(artifact: dict[str, Any], old: str, new: str) -> None:
    artifact["table"] = _exact(artifact.get("table", ""), old, new)
    artifact["group_by"] = _exact(artifact.get("group_by", ""), old, new)
    for group in artifact.get("groups", []):
        if isinstance(group, dict):
            group["field"] = _exact(group.get("field", ""), old, new)
    for sort in artifact.get("sort_fields", []):
        if isinstance(sort, dict):
            sort["field"] = _dotted(sort.get("field", ""), old, new)
    for controls in artifact.get("bands", {}).values():
        for control in controls:
            if isinstance(control, dict):
                _rewrite_control(control, old, new)


def _rewrite_step(step: dict[str, Any], old: str, new: str) -> None:
    params = step.get("params")
    if isinstance(params, dict):
        if "table" in params:
            params["table"] = _exact(params.get("table", ""), old, new)
        if "field" in params:
            params["field"] = _dotted(params.get("field", ""), old, new)
        if "filter" in params:
            params["filter"] = _brackets(params.get("filter", ""), old, new)
    for key in ("steps", "then", "else"):
        for child in step.get(key, []) or []:
            if isinstance(child, dict):
                _rewrite_step(child, old, new)


def _rewrite_scripts(artifact: dict[str, Any], old: str, new: str) -> None:
    for step in artifact.get("steps", []):
        if isinstance(step, dict):
            _rewrite_step(step, old, new)


def _rewrite_diagram(artifact: dict[str, Any], old: str, new: str) -> None:
    for node in artifact.get("nodes", []):
        if isinstance(node, dict) and node.get("table") == old:
            node["table"] = new


def _rewrite_artifact(category: str, artifact: dict[str, Any], old: str, new: str) -> None:
    handlers = {
        "tables": _rewrite_table,
        "queries": _rewrite_query,
        "forms": _rewrite_form,
        "reports": _rewrite_report,
        "scripts": _rewrite_scripts,
        "diagrams": _rewrite_diagram,
    }
    handler = handlers.get(category)
    if handler is not None:
        handler(artifact, old, new)


# -------------------------------------------------------------------- rinomina
def rename_table(project: Project, old: str, new: str) -> None:
    """Rinomina tabella, schema SQLite e riferimenti nei metadati."""
    new = str(new).strip()
    check_identifier(new, "nome tabella")
    current = project.require_table(old)
    if new.lower() == current.name.lower():
        return
    if project.table(new) is not None:
        raise ProjectError(f"Esiste già una tabella chiamata {new}")
    if project.db.has_table(new):
        raise ProjectError(f"Il database contiene già una tabella chiamata {new}")
    project.backup(reason=f"rinomina-{current.name}")
    try:
        project.db.execute(f'ALTER TABLE "{current.name}" RENAME TO "{new}"')
    except Exception as exc:
        raise ProjectError(f"Rinomina di {current.name} non riuscita: {exc}") from exc

    tables = project.objects["tables"]
    actual_old = next((key for key in tables if key.lower() == current.name.lower()), current.name)
    artifact = tables.pop(actual_old)
    artifact["name"] = new
    tables[new] = artifact
    for category in ("tables", "queries", "forms", "reports", "scripts", "diagrams"):
        for name, item in project.objects.get(category, {}).items():
            if not isinstance(item, dict):
                continue
            _rewrite_artifact(category, item, actual_old, new)

    finds = project.settings.get("saved_finds")
    if isinstance(finds, dict) and actual_old in finds:
        finds[new] = finds.pop(actual_old)
    project.save()


# ---------------------------------------------------------------- duplicazione
def _slug(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", str(name)).strip("_")
    return cleaned or "copia"


def unique_name(project: Project, category: str, base: str) -> str:
    base = str(base).strip() or "Copia"
    existing = {name.lower() for name in project.names(category)}
    if base.lower() not in existing:
        return base
    separator = "_" if category == "tables" else " "
    index = 2
    while f"{base}{separator}{index}".lower() in existing:
        index += 1
    return f"{base}{separator}{index}"


def _duplicate_table(project: Project, name: str, new_name: str) -> str:
    check_identifier(new_name, "nome tabella")
    if project.table(new_name) is not None or project.db.has_table(new_name):
        raise ProjectError(f"Esiste già una tabella chiamata {new_name}")
    source = project.require_table(name)
    table = Table.from_dict(source.to_dict())
    table.name = new_name
    table.caption = f"{source.display_name()} (copia)"
    for index in table.indexes:
        index.name = ""
    for fk in table.foreign_keys:
        if fk.ref_table == source.name:
            fk.ref_table = new_name
    project.apply_table(table)
    fields = ", ".join(f'"{field.name}"' for field in source.fields)
    try:
        with project.db.transaction():
            project.db.execute(
                f'INSERT INTO "{new_name}" ({fields}) SELECT {fields} FROM "{source.name}"'
            )
    except Exception as exc:
        try:
            project.drop_table(new_name)
        except Exception:
            pass
        raise ProjectError(f"Copia dei dati di {source.name} non riuscita: {exc}") from exc
    project.save()
    return new_name


def duplicate_object(
    project: Project,
    category: str,
    name: str,
    new_name: str = "",
) -> str:
    """Duplica un oggetto; per le tabelle copia struttura e dati."""
    if category not in project.objects:
        raise ProjectError(f"Categoria sconosciuta: {category}")
    artifact = project.artifact(category, name)
    if artifact is None:
        raise ProjectError(f"Oggetto inesistente: {name}")
    base = new_name.strip() or f"{name}_copia"
    if category == "tables":
        base = _slug(base)
    target = unique_name(project, category, base)
    if category == "tables":
        return _duplicate_table(project, name, target)
    cloned = copy.deepcopy(artifact)
    cloned["name"] = target
    project.put_object(category, cloned)
    project.save()
    return target


# ----------------------------------------------------------------- manutenzione
def compact_database(project: Project) -> str | None:
    """Backup e VACUUM; restituisce il percorso del backup."""
    backup = project.backup(reason="compatta")
    project.db.vacuum()
    return str(backup) if backup else None


def check_database(project: Project) -> str:
    return project.db.integrity_check()


__all__ = [
    "CATEGORY_LABELS",
    "check_database",
    "compact_database",
    "duplicate_object",
    "rename_table",
    "unique_name",
]
