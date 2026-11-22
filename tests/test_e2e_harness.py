"""Test del harness E2E: elenco scenari ed esecuzione minima isolata."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools" / "e2e_harness.py"


def _env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["DBX_CONFIG_DIR"] = str(tmp_path / "config")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def test_harness_lists_scenarios(tmp_path) -> None:
    result = subprocess.run(
        [sys.executable, str(HARNESS), "--list"],
        cwd=ROOT,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-1000:]
    assert "environment" in result.stdout
    assert "ui_designers" in result.stdout
    assert "runner_build" in result.stdout


def test_harness_runs_environment_scenario(tmp_path) -> None:
    output = tmp_path / "e2e"
    result = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--only",
            "environment",
            "--skip-pytest",
            "--skip-smoke",
            "--no-screenshots",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert report["overall"] == "pass"
    assert report["summary"]["scenarios"] == 1
    assert report["summary"]["checks"] > 0
    assert report["scenarios"][0]["name"] == "environment"
    assert (output / "report.md").exists()
    assert (output / "run.log").exists()


def test_harness_rejects_unknown_scenario(tmp_path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--only",
            "inesistente",
            "--skip-pytest",
            "--skip-smoke",
            "--output",
            str(tmp_path / "e2e"),
        ],
        cwd=ROOT,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 2
    assert "sconosciuti" in (result.stdout + result.stderr).lower()
