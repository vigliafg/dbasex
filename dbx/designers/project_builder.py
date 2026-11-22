"""Validazione del progetto e build distribuibile (G5, G6)."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from ..core.form_model import FormSpec, form_references
from ..core.metadata import validate_project_tables
from ..core.project import Project
from ..runtime.report_engine import ReportSpec
from ..runtime.script_engine import ACTIONS


class BuildError(RuntimeError):
    """Errore di build o di validazione bloccante."""


def validate_project(project: Project) -> list[str]:
    """Controlla struttura, riferimenti incrociati e oggetti mancanti."""
    errors: list[str] = []
    tables = project.tables()
    errors.extend(validate_project_tables(tables.values()))
    table_names = {name.lower() for name in tables}
    form_names = {name.lower() for name in project.names("forms")}
    report_names = {name.lower() for name in project.names("reports")}
    script_names = {name.lower() for name in project.names("scripts")}

    for name, artifact in project.objects["forms"].items():
        spec = FormSpec.from_dict(artifact)
        for error in spec.validate():
            errors.append(f"Form {name}: {error}")
        for table in form_references(spec):
            if table and table.lower() not in table_names:
                errors.append(f"Form {name}: tabella inesistente {table}")

    for name, artifact in project.objects["reports"].items():
        spec = ReportSpec.from_dict(artifact)
        for error in spec.validate():
            errors.append(f"Report {name}: {error}")
        if spec.table and spec.table.lower() not in table_names:
            errors.append(f"Report {name}: tabella inesistente {spec.table}")

    for name, artifact in project.objects["scripts"].items():
        for error in _validate_steps(artifact.get("steps", []), table_names, form_names, report_names, script_names):
            errors.append(f"Script {name}: {error}")

    for name, artifact in project.objects["menus"].items():
        for item in artifact.get("items", []):
            action = item.get("action")
            target = str(item.get("target", "")).lower()
            if action == "open_form" and target and target not in form_names:
                errors.append(f"Menu {name}: form inesistente {item.get('target')}")
            if action == "open_report" and target and target not in report_names:
                errors.append(f"Menu {name}: report inesistente {item.get('target')}")
            if action == "run_script" and target and target not in script_names:
                errors.append(f"Menu {name}: script inesistente {item.get('target')}")

    main_form = str(project.settings.get("main_form", "")).lower()
    if main_form and main_form not in form_names:
        errors.append(f"Form principale inesistente: {project.settings.get('main_form')}")
    return errors


def _validate_steps(
    steps: list[dict[str, Any]],
    table_names: set[str],
    form_names: set[str],
    report_names: set[str],
    script_names: set[str],
) -> list[str]:
    errors: list[str] = []
    for step in steps:
        action = step.get("action")
        params = step.get("params") or {}
        if action not in ACTIONS:
            errors.append(f"azione sconosciuta {action}")
            continue
        if action in ("open_form",) and str(params.get("form", "")).lower() not in form_names:
            errors.append(f"form inesistente {params.get('form')}")
        if action == "print_report" and str(params.get("report", "")).lower() not in report_names:
            errors.append(f"report inesistente {params.get('report')}")
        if action in ("foreach", "export_csv"):
            table_name = str(params.get("table", "")).lower()
            if table_name and table_name not in table_names:
                errors.append(f"tabella inesistente {params.get('table')}")
        if action == "call" and str(params.get("script", "")).lower() not in script_names:
            errors.append(f"script inesistente {params.get('script')}")
        for key in ("then", "else", "steps"):
            child = step.get(key)
            if isinstance(child, list):
                errors.extend(_validate_steps(child, table_names, form_names, report_names, script_names))
    return errors


def build_project(project: Project, target: Path, make_zip: bool = True) -> Path:
    """Copia artefatti e dati in una cartella distribuibile (+ zip)."""
    errors = validate_project(project)
    if errors:
        raise BuildError("Validazione non superata:\n" + "\n".join(errors))
    project.save()
    base = Path(target) / project.name
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    shutil.copytree(project.objects_path, base / "objects")
    base.joinpath("data").mkdir()
    project.db.con.commit()
    if project.database_file.exists():
        shutil.copy2(project.database_file, base / "data" / project.database_file.name)
    shutil.copy2(project.manifest_path, base / "project.dbx.json")
    (base / "LEGGIMI.txt").write_text(
        "Applicazione dBX\n\n"
        f"Progetto: {project.name}\n"
        "Avvio: apri il progetto con dBX (File > Apri progetto) oppure esegui\n"
        f"  dbx \"{base / 'project.dbx.json'}\"\n",
        encoding="utf-8",
    )
    if not make_zip:
        return base
    archive = Path(target) / f"{project.name}.dbx.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(base.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(base))
    return archive


def package_with_pyinstaller(project: Project, target: Path) -> Path:
    """Crea un eseguibile con PyInstaller, se installato (G7)."""
    import shutil as _shutil
    import subprocess
    import sys

    if _shutil.which("pyinstaller") is None:
        raise BuildError(
            "PyInstaller non è installato. Installa con 'pip install pyinstaller' oppure distribuisci il progetto con il build zip."
        )
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    project_path = project.manifest_path
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",
        "--name",
        f"dbx_{project.name}",
        "--distpath",
        str(target),
        "--workpath",
        str(target / ".build"),
        "--specpath",
        str(target / ".build"),
        str(Path(__file__).resolve().parents[2] / "run_dbx.py"),
        "--",
        str(project_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise BuildError(result.stderr[-2000:] or "PyInstaller non riuscito")
    return target / f"dbx_{project.name}"
