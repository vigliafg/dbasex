"""Configurazione utente: cartella ~/.config/dbx, recenti, preferenze (A1, A3)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_DIR_NAME = "dbx"


def config_dir() -> Path:
    override = os.environ.get("DBX_CONFIG_DIR")
    if override:
        base = Path(override).expanduser()
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.sys.platform == "darwin":  # type: ignore[attr-defined]
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_DIR_NAME


def config_path() -> Path:
    return config_dir() / "config.json"


DEFAULT_CONFIG: dict[str, Any] = {
    "recent": [],
    "theme": "aurora",
    "last_dir": str(Path.home()),
    "window": None,
    "max_recent": 8,
}


def load_config() -> dict[str, Any]:
    path = config_path()
    config = dict(DEFAULT_CONFIG)
    config["recent"] = []
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update(data)
        except (OSError, ValueError):
            pass
    if not isinstance(config.get("recent"), list):
        config["recent"] = []
    return config


def save_config(config: dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)
    return path


def recent_projects() -> list[str]:
    return [str(p) for p in load_config().get("recent", []) if Path(str(p)).exists()]


def add_recent(path: str | Path) -> None:
    config = load_config()
    resolved = str(Path(path).resolve())
    recent = [p for p in config.get("recent", []) if str(p) != resolved]
    recent.insert(0, resolved)
    config["recent"] = recent[: int(config.get("max_recent", 8))]
    config["last_dir"] = str(Path(resolved).parent)
    save_config(config)


def forget_recent(path: str | Path) -> None:
    config = load_config()
    resolved = str(Path(path).resolve())
    config["recent"] = [p for p in config.get("recent", []) if str(p) != resolved]
    save_config(config)
