"""Formato progetto su disco e ciclo di vita del progetto (A3).

Struttura:

    MioProgetto/
      project.dbx.json
      data/MioProgetto.sqlite
      objects/tables/clienti.table.json
      objects/forms/clienti.form.json
      objects/reports/...      objects/scripts/...      objects/menus/...
      backups/
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field as dc_field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .. import FORMAT_VERSION
from . import ddl
from .db import Database
from .metadata import MetadataError, Table, slugify

MANIFEST_NAME = "project.dbx.json"
LOCK_NAME = ".dbx.lock"

CATEGORIES = ("tables", "diagrams", "queries", "forms", "reports", "scripts", "menus")
CATEGORY_LABELS = {
    "tables": "Tabelle",
    "diagrams": "Schema",
    "queries": "Query",
    "forms": "Form",
    "reports": "Report",
    "scripts": "Script",
    "menus": "Menu",
}
OBJECT_SUFFIX = {
    "tables": "table",
    "diagrams": "diagram",
    "queries": "query",
    "forms": "form",
    "reports": "report",
    "scripts": "script",
    "menus": "menu",
}


class ProjectError(RuntimeError):
    """Errore di progetto (percorso, formato, lock, migrazione)."""


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@dataclass
class Project:
    path: Path
    name: str
    caption: str = ""
    settings: dict[str, Any] = dc_field(default_factory=dict)
    objects: dict[str, dict[str, dict[str, Any]]] = dc_field(
        default_factory=lambda: {category: {} for category in CATEGORIES}
    )
    format_version: int = FORMAT_VERSION
    _db: Database | None = dc_field(default=None, repr=False)
    _locked: bool = dc_field(default=False, repr=False)

    # ------------------------------------------------------------- struttura
    @property
    def manifest_path(self) -> Path:
        return self.path / MANIFEST_NAME

    @property
    def objects_path(self) -> Path:
        return self.path / "objects"

    @property
    def data_path(self) -> Path:
        return self.path / "data"

    @property
    def backups_path(self) -> Path:
        return self.path / "backups"

    @property
    def database_file(self) -> Path:
        return self.data_path / f"{self.name}.sqlite"

    @property
    def db(self) -> Database:
        if self._db is None:
            self._db = Database(self.database_file)
            self._db.con  # apre subito per far emergere errori di I/O
        return self._db

    def ensure_dirs(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        self.objects_path.mkdir(parents=True, exist_ok=True)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.backups_path.mkdir(parents=True, exist_ok=True)
        for category in CATEGORIES:
            (self.objects_path / category).mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- creazione
    @classmethod
    def create(cls, path: str | Path, name: str, caption: str = "") -> "Project":
        target = Path(path)
        if target.exists() and any(target.iterdir()):
            raise ProjectError(f"La cartella {target} non è vuota")
        name = str(name).strip()
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_ ]*$", name):
            raise ProjectError("Nome progetto non valido: usa lettere, cifre, underscore e spazi")
        project = cls(path=target, name=name, caption=caption or name)
        project.ensure_dirs()
        project.settings.setdefault("main_form", "")
        project.settings.setdefault("title", caption or name)
        project._acquire_lock()
        project.save()
        project.db.con  # crea il file sqlite
        return project

    # ---------------------------------------------------------------- apertura
    @classmethod
    def open(cls, path: str | Path, force: bool = False) -> "Project":
        target = Path(path)
        if target.is_file() and target.name == MANIFEST_NAME:
            target = target.parent
        manifest = target / MANIFEST_NAME
        if not manifest.exists():
            raise ProjectError(f"Manifest di progetto non trovato: {manifest}")
        try:
            data = _read_json(manifest)
        except (OSError, ValueError) as exc:
            raise ProjectError(f"Manifest illeggibile: {exc}") from exc
        version = int(data.get("format_version", 1))
        if version > FORMAT_VERSION:
            raise ProjectError(
                f"Il progetto usa il formato {version}, questa versione di dBX supporta fino a {FORMAT_VERSION}"
            )
        project = cls(
            path=target,
            name=str(data.get("name", target.name)),
            caption=str(data.get("caption", "")),
            settings=dict(data.get("settings", {})),
            format_version=version,
        )
        project._acquire_lock(force=force)
        try:
            project._load_objects(data.get("objects", {}))
        except Exception:
            project._release_lock()
            raise
        return project

    def _load_objects(self, index: dict[str, Any]) -> None:
        for category in CATEGORIES:
            self.objects[category] = {}
        for category in CATEGORIES:
            folder = self.objects_path / category
            if not folder.exists():
                continue
            for file in sorted(folder.glob(f"*.{OBJECT_SUFFIX[category]}.json")):
                try:
                    artifact = _read_json(file)
                except (OSError, ValueError):
                    continue
                name = str(artifact.get("name") or file.stem)
                self.objects[category][name] = artifact
        # Il manifest è l'indice autorevole: aggiunge eventuali oggetti non presenti su disco.
        for category, mapping in (index or {}).items():
            if category not in self.objects or not isinstance(mapping, dict):
                continue
            for name in mapping:
                if name not in self.objects[category]:
                    self.objects[category].setdefault(name, {"name": name})

    # ------------------------------------------------------------------- salvataggio
    def save(self) -> None:
        self.ensure_dirs()
        index: dict[str, dict[str, str]] = {}
        for category in CATEGORIES:
            index[category] = {}
            for name, artifact in self.objects[category].items():
                slug = slugify(name)
                suffix = OBJECT_SUFFIX[category]
                relative = f"objects/{category}/{slug}.{suffix}.json"
                _write_json(self.path / relative, artifact)
                index[category][name] = slug
        self._remove_orphan_files(index)
        manifest = {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "caption": self.caption,
            "settings": self.settings,
            "objects": index,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "application": "dBX",
        }
        _write_json(self.manifest_path, manifest)

    def _remove_orphan_files(self, index: dict[str, dict[str, str]]) -> None:
        """Elimina gli artefatti rimasti sul disco dopo una rinomina o un'eliminazione."""
        for category in CATEGORIES:
            folder = self.objects_path / category
            if not folder.exists():
                continue
            suffix = OBJECT_SUFFIX[category]
            expected = {f"{slug}.{suffix}.json" for slug in index.get(category, {}).values()}
            for file in folder.glob(f"*.{suffix}.json"):
                if file.name not in expected:
                    try:
                        file.unlink()
                    except OSError:
                        pass

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
        self._release_lock()

    # --------------------------------------------------------------------- lock
    def _acquire_lock(self, force: bool = False) -> None:
        lock = self.path / LOCK_NAME
        if lock.exists() and not force:
            try:
                info = json.loads(lock.read_text(encoding="utf-8"))
                pid = int(info.get("pid", 0))
            except (OSError, ValueError):
                pid = 0
            detail = f" (processo {pid}{', attivo' if _pid_alive(pid) else ', non attivo'})" if pid else ""
            raise ProjectError(
                "Il progetto risulta già aperto%s. Usa l'apertura forzata se il programma è chiuso." % detail
            )
        lock.write_text(
            json.dumps({"pid": os.getpid(), "opened_at": datetime.now().isoformat(timespec="seconds")}),
            encoding="utf-8",
        )
        self._locked = True

    def _release_lock(self) -> None:
        lock = self.path / LOCK_NAME
        if self._locked and lock.exists():
            try:
                lock.unlink()
            except OSError:
                pass
        self._locked = False

    # ------------------------------------------------------------------ oggetti
    def artifact(self, category: str, name: str) -> dict[str, Any] | None:
        if category not in self.objects:
            raise ProjectError(f"Categoria sconosciuta: {category}")
        if name in self.objects[category]:
            return self.objects[category][name]
        lowered = str(name).lower()
        for key, value in self.objects[category].items():
            if key.lower() == lowered:
                return value
        return None

    def add_object(self, category: str, artifact: dict[str, Any]) -> str:
        if category not in self.objects:
            raise ProjectError(f"Categoria sconosciuta: {category}")
        name = str(artifact.get("name") or "").strip()
        if not name:
            raise ProjectError("L'oggetto non ha un nome")
        existing = self.artifact(category, name)
        if existing is not None and existing is not artifact:
            raise ProjectError(f"Esiste già un oggetto chiamato {name} in {CATEGORY_LABELS[category]}")
        self.objects[category][name] = artifact
        return name

    def put_object(self, category: str, artifact: dict[str, Any], previous_name: str | None = None) -> str:
        """Inserisce o sostituisce un oggetto, gestendo l'eventuale rinomina."""
        name = str(artifact.get("name") or "").strip()
        if not name:
            raise ProjectError("L'oggetto non ha un nome")
        collision = self.artifact(category, name)
        if collision is not None and (previous_name is None or collision is not artifact):
            if previous_name is None or str(previous_name).lower() != name.lower():
                raise ProjectError(f"Esiste già un oggetto chiamato {name}")
        if previous_name and previous_name in self.objects[category]:
            del self.objects[category][previous_name]
        self.objects[category][name] = artifact
        return name

    def remove_object(self, category: str, name: str) -> bool:
        if category not in self.objects:
            return False
        if name in self.objects[category]:
            del self.objects[category][name]
            stale = self.objects_path / category / f"{slugify(name)}.{OBJECT_SUFFIX[category]}.json"
            if stale.exists():
                try:
                    stale.unlink()
                except OSError:
                    pass
            return True
        return False

    def names(self, category: str) -> list[str]:
        return sorted(self.objects.get(category, {}), key=str.lower)

    # ------------------------------------------------------------------ tabelle
    def tables(self) -> dict[str, Table]:
        result: dict[str, Table] = {}
        for name, artifact in self.objects["tables"].items():
            try:
                result[name] = Table.from_dict(artifact)
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def table(self, name: str) -> Table | None:
        artifact = self.artifact("tables", name)
        if artifact is None:
            return None
        try:
            return Table.from_dict(artifact)
        except (KeyError, TypeError, ValueError):
            return None

    def require_table(self, name: str) -> Table:
        table = self.table(name)
        if table is None:
            raise ProjectError(f"Tabella sconosciuta: {name}")
        return table

    def backup(self, reason: str = "manuale") -> Path | None:
        if not self.database_file.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_reason = re.sub(r"[^a-z0-9]+", "-", reason.lower()).strip("-") or "backup"
        target = self.backups_path / f"{stamp}-{safe_reason}.sqlite"
        return self.db.backup_to(target)

    def apply_table(self, table: Table, backup: bool = True) -> ddl.MigrationPlan:
        """Valida, migra e salva una tabella; esegue un backup se distruttivo."""
        old = self.table(table.name)
        try:
            plan = ddl.plan_migration(old, table)
        except MetadataError as exc:
            raise ProjectError(str(exc)) from exc
        if not plan:
            self.put_object(
                "tables", table.to_dict(), previous_name=old.name if old else None
            )
            self.save()
            return plan
        if backup and (plan.destructive or plan.kind == "rebuild"):
            self.backup(reason=f"migrazione-{table.name}")
        try:
            ddl.apply_migration(self.db.con, table, old)
        except Exception as exc:
            raise ProjectError(f"Migrazione di {table.name} non riuscita: {exc}") from exc
        self.put_object("tables", table.to_dict(), previous_name=old.name if old else None)
        self.save()
        return plan

    def drop_table(self, name: str) -> None:
        table = self.require_table(name)
        plan_drop_sql = f'DROP TABLE IF EXISTS "{table.name}"'
        self.backup(reason=f"drop-{table.name}")
        self.db.execute(plan_drop_sql)
        self.remove_object("tables", name)
        self.save()

    # ------------------------------------------------------------------- menu
    def menu_actions(self, menu_name: str) -> list[dict[str, Any]]:
        artifact = self.artifact("menus", menu_name) or {}
        return list(artifact.get("items", []))


def iter_project_files(project: Project) -> Iterable[Path]:
    for category in CATEGORIES:
        for name in project.names(category):
            yield project.objects_path / category / f"{slugify(name)}.{OBJECT_SUFFIX[category]}.json"
