#!/usr/bin/env python3
"""Harness end-to-end di dBX: pytest, smoke e scenari funzionali completi.

Uso tipico:

    python tools/e2e_harness.py
    ./tools/run_e2e.sh
    python tools/e2e_harness.py --only ui_designers --no-screenshots
    python tools/e2e_harness.py --skip-pytest --skip-smoke

Il runner usa un ambiente Qt offscreen, progetti temporanei isolati e non
modifica il progetto reale. Produce in ``build/e2e/<timestamp>/``:

- ``report.json`` e ``report.md`` con esiti, controlli, tempi e traceback;
- ``run.log`` con tutto l'output del harness;
- ``pytest.log``, ``pytest-junit.xml`` e ``smoke.log``;
- ``screenshots/`` con le schermate delle superfici principali.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import signal
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field as dc_field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
for _path in (ROOT, TOOLS):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
DEFAULT_OUTPUT = ROOT / "build" / "e2e"
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2


# --------------------------------------------------------------------------- #
# Log e utilita'
# --------------------------------------------------------------------------- #
class RunLog:
    """Log su console e file, con UTF-8 e flush immediato."""

    def __init__(self, path: Path, quiet: bool = False) -> None:
        self.path = path
        self.quiet = quiet
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("w", encoding="utf-8")

    def write(self, message: str = "", *, console: bool = True) -> None:
        self._handle.write(message + "\n")
        self._handle.flush()
        if console and not self.quiet:
            print(message, flush=True)

    def close(self) -> None:
        self._handle.close()


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _duration(start: float) -> float:
    return round(time.perf_counter() - start, 3)


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _git_info() -> dict[str, Any]:
    commit = _git("rev-parse", "HEAD")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    status = _git("status", "--short")
    return {
        "commit": commit or "n/d",
        "commit_short": commit[:8] if commit else "n/d",
        "branch": branch or "n/d",
        "dirty_files": len(status.splitlines()) if status else 0,
        "dirty": bool(status),
    }


def _python_env(base: dict[str, str], config: Path, platform_name: str) -> dict[str, str]:
    env = dict(base)
    env["QT_QPA_PLATFORM"] = platform_name
    env["DBX_CONFIG_DIR"] = str(config)
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("PYTHONUTF8", "1")
    return env


@contextmanager
def _time_limit(seconds: float) -> Iterator[None]:
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        yield
        return

    def handler(_signum, _frame):
        raise TimeoutError(f"scenario oltre il limite di {seconds:.0f} s")

    previous = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@dataclass
class StageResult:
    name: str
    title: str
    status: str
    duration_s: float
    summary: str = ""
    log: str = ""
    command: str = ""


@dataclass
class ScenarioResult:
    name: str
    title: str
    status: str
    duration_s: float
    checks: list[dict[str, str]] = dc_field(default_factory=list)
    error: str | None = None
    traceback: str = ""
    screenshots: list[str] = dc_field(default_factory=list)
    info: dict[str, Any] = dc_field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Stage esterni: pytest e smoke
# --------------------------------------------------------------------------- #
def _run_stage(
    name: str,
    title: str,
    command: list[str],
    log_path: Path,
    env: dict[str, str],
    timeout: float,
    summary_hint: str = "",
) -> StageResult:
    started = time.perf_counter()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (result.stdout or "") + (result.stderr or "")
        log_path.write_text(output, encoding="utf-8")
        summary = ""
        for line in reversed(output.splitlines()):
            stripped = line.strip()
            if stripped and not stripped.startswith("="):
                summary = stripped
                break
        status = "pass" if result.returncode == 0 else "fail"
        if "SMOKE OK" in output:
            summary = "SMOKE OK"
        if not summary:
            summary = summary_hint or f"exit {result.returncode}"
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        log_path.write_text(output, encoding="utf-8")
        status = "fail"
        summary = f"timeout dopo {timeout:.0f} s"
    except FileNotFoundError as exc:
        log_path.write_text(str(exc), encoding="utf-8")
        status = "fail"
        summary = str(exc)
    return StageResult(
        name=name,
        title=title,
        status=status,
        duration_s=_duration(started),
        summary=summary,
        log=str(log_path),
        command=" ".join(shlex.quote(part) for part in command),
    )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def _write_reports(
    output: Path,
    started: datetime,
    finished: datetime,
    environment: dict[str, Any],
    git: dict[str, Any],
    options: dict[str, Any],
    stages: list[StageResult],
    scenarios: list[ScenarioResult],
    log_path: Path,
) -> tuple[Path, Path, dict[str, Any]]:
    checks_total = sum(len(item.checks) for item in scenarios)
    checks_failed = sum(
        1 for item in scenarios for check in item.checks if check["status"] != "pass"
    )
    scenarios_passed = sum(1 for item in scenarios if item.status == "pass")
    stages_failed = sum(1 for item in stages if item.status == "fail")
    overall = (
        "pass"
        if scenarios_passed == len(scenarios) and stages_failed == 0
        else "fail"
    )
    report = {
        "schema": 1,
        "tool": "dbx-e2e",
        "started_at": _iso(started),
        "finished_at": _iso(finished),
        "duration_s": round((finished - started).total_seconds(), 3),
        "overall": overall,
        "exit_code": EXIT_OK if overall == "pass" else EXIT_FAIL,
        "environment": environment,
        "git": git,
        "options": options,
        "summary": {
            "stages": len(stages),
            "stages_failed": stages_failed,
            "scenarios": len(scenarios),
            "scenarios_passed": scenarios_passed,
            "checks": checks_total,
            "checks_failed": checks_failed,
            "screenshots": sum(len(item.screenshots) for item in scenarios),
        },
        "stages": [asdict(item) for item in stages],
        "scenarios": [asdict(item) for item in scenarios],
        "artifacts": {
            "report_json": str(output / "report.json"),
            "report_md": str(output / "report.md"),
            "run_log": str(log_path),
        },
    }
    report_path = output / "report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    markdown = _render_markdown(report)
    md_path = output / "report.md"
    md_path.write_text(markdown, encoding="utf-8")
    return report_path, md_path, report


def _render_markdown(report: dict[str, Any]) -> str:
    env = report["environment"]
    git = report["git"]
    summary = report["summary"]
    lines = [
        f"# dBX E2E — {report['started_at']}",
        "",
        f"**Esito:** {'PASS' if report['overall'] == 'pass' else 'FAIL'} · "
        f"durata {report['duration_s']:.1f} s",
        "",
        f"- Versione dBX: `{env.get('dbx_version', 'n/d')}`",
        f"- Python: `{env.get('python', 'n/d')}` · Qt: `{env.get('qt', 'n/d')}` · "
        f"PyQt: `{env.get('pyqt', 'n/d')}`",
        f"- Piattaforma: `{env.get('platform', 'n/d')}`",
        f"- Commit: `{git.get('commit_short', 'n/d')}` su `{git.get('branch', 'n/d')}`"
        + (f" · {git.get('dirty_files')} file modificati" if git.get("dirty") else ""),
        f"- Scenari: {summary['scenarios_passed']}/{summary['scenarios']} · "
        f"controlli: {summary['checks'] - summary['checks_failed']}/{summary['checks']} · "
        f"screenshot: {summary['screenshots']}",
        "",
        "## Stage",
        "",
        "| Stage | Esito | Durata | Riepilogo |",
        "|---|---|---:|---|",
    ]
    for stage in report["stages"]:
        lines.append(
            f"| {stage['title']} | {_badge(stage['status'])} | {stage['duration_s']:.2f} s | "
            f"{_md_cell(stage['summary'])} |"
        )
    lines += [
        "",
        "## Scenari",
        "",
        "| Scenario | Esito | Controlli | Durata |",
        "|---|---|---:|---:|",
    ]
    for scenario in report["scenarios"]:
        passed = sum(1 for check in scenario["checks"] if check["status"] == "pass")
        lines.append(
            f"| `{scenario['name']}` — {_md_cell(scenario['title'])} | "
            f"{_badge(scenario['status'])} | {passed}/{len(scenario['checks'])} | "
            f"{scenario['duration_s']:.2f} s |"
        )
    lines.append("")
    for scenario in report["scenarios"]:
        lines += [
            f"### {scenario['name']} — {scenario['status'].upper()}",
            "",
            f"_{scenario['title']}_ · {scenario['duration_s']:.2f} s",
            "",
        ]
        for check in scenario["checks"]:
            mark = "x" if check["status"] == "pass" else " "
            detail = f" — {_md_cell(check['detail'])}" if check.get("detail") else ""
            lines.append(f"- [{mark}] {check['name']}{detail}")
        if scenario.get("error"):
            lines += [
                "",
                f"**Errore:** `{scenario['error']}`",
            ]
        if scenario.get("traceback"):
            lines += ["", "```", scenario["traceback"].rstrip(), "```"]
        workdir = (scenario.get("info") or {}).get("workdir")
        if workdir:
            lines += ["", f"Progetto temporaneo: `{workdir}`"]
        if scenario.get("screenshots"):
            lines += ["", "Screenshot: " + ", ".join(f"`{p}`" for p in scenario["screenshots"])]
        lines.append("")
    lines += [
        "## Artefatti",
        "",
        f"- Report JSON: `{report['artifacts']['report_json']}`",
        f"- Report Markdown: `{report['artifacts']['report_md']}`",
        f"- Log completo: `{report['artifacts']['run_log']}`",
        "",
    ]
    return "\n".join(lines)


def _badge(status: str) -> str:
    return {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP"}.get(status, status.upper())


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- #
# Argomenti
# --------------------------------------------------------------------------- #
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="e2e_harness.py",
        description="Harness end-to-end di dBX: pytest, smoke e scenari completi.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Cartella dei risultati (default: build/e2e/<timestamp>)",
    )
    parser.add_argument("--list", action="store_true", help="Elenca gli scenari ed esce")
    parser.add_argument(
        "--only",
        default="",
        help="Esegue solo gli scenari indicati, separati da virgola",
    )
    parser.add_argument(
        "--area",
        default="",
        help="Esegue solo le aree indicate (project,tables,browse,data,...)",
    )
    parser.add_argument(
        "--feature",
        default="",
        help="Esegue gli scenari che dichiarano una feature (glob ammessi, virgola)",
    )
    parser.add_argument(
        "--require-coverage",
        action="store_true",
        help="Fallisce se il catalogo della fase non è coperto al 100%%",
    )
    parser.add_argument(
        "--coverage-phase",
        type=int,
        default=1,
        help="Fase del catalogo da verificare (default 1)",
    )
    parser.add_argument("--skip-pytest", action="store_true", help="Non esegue pytest")
    parser.add_argument("--skip-smoke", action="store_true", help="Non esegue lo smoke")
    parser.add_argument(
        "--no-screenshots", action="store_true", help="Non salva gli screenshot"
    )
    parser.add_argument(
        "--keep", action="store_true", help="Conserva i progetti temporanei"
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Ferma al primo scenario fallito"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Console ridotta; il report resta completo"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Stampa ogni controllo eseguito"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=240.0,
        help="Timeout per scenario in secondi (default 240; 0 = nessuno)",
    )
    parser.add_argument(
        "--pytest-args",
        default="",
        help="Argomenti extra per pytest, tra virgolette",
    )
    parser.add_argument(
        "--platform",
        default="offscreen",
        help="Plugin Qt (default offscreen)",
    )
    return parser.parse_args(argv)


def _default_output() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return DEFAULT_OUTPUT / stamp


def _select_scenarios(definitions, only: str):
    if not only.strip():
        return list(definitions)
    wanted = {name.strip() for name in only.split(",") if name.strip()}
    known = {item.name for item in definitions}
    unknown = sorted(wanted - known)
    if unknown:
        raise ValueError(f"Scenari sconosciuti: {', '.join(unknown)}")
    return [item for item in definitions if item.name in wanted]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    started = _now()

    os.environ["QT_QPA_PLATFORM"] = args.platform

    try:
        from e2e_scenarios import SCENARIOS as LEGACY_SCENARIOS, HarnessContext, ScenarioFailure
        from e2e.registry import load as load_new_scenarios
        from e2e.context import E2EContext
        from e2e.catalog import coverage as coverage_of, validate_scenarios

        NEW_SCENARIOS = load_new_scenarios()
        SCENARIOS = list(LEGACY_SCENARIOS) + list(NEW_SCENARIOS)
    except Exception:
        traceback.print_exc()
        print("ERRORE: impossibile importare gli scenari E2E", file=sys.stderr)
        return EXIT_USAGE

    try:
        selected = _select_scenarios(SCENARIOS, args.only)
    except ValueError as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.area:
        wanted_areas = {item.strip() for item in args.area.split(",") if item.strip()}
        selected = [item for item in selected if getattr(item, "area", "") in wanted_areas]
    if args.feature:
        import fnmatch

        patterns = [item.strip().upper() for item in args.feature.split(",") if item.strip()]
        selected = [
            item
            for item in selected
            if any(
                fnmatch.fnmatch(feature.upper(), pattern)
                for feature in getattr(item, "features", ())
                for pattern in patterns
            )
        ]
    if args.list:
        print("Scenari E2E disponibili:")
        for item in SCENARIOS:
            area = getattr(item, "area", "legacy")
            features = len(getattr(item, "features", ()))
            print(f"  {item.name:<26} [{area:<8}] {features:>2} feature  {item.title}")
        return EXIT_OK
    if not selected:
        print("ERRORE: nessuno scenario selezionato", file=sys.stderr)
        return EXIT_USAGE

    output = (args.output or _default_output()).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = output / "config"
    config.mkdir(parents=True, exist_ok=True)
    screenshots = not args.no_screenshots
    log = RunLog(output / "run.log", quiet=args.quiet)


    environment = {
        "python": platform.python_version(),
        "executable": sys.executable,
        "platform": platform.platform(),
        "qt_plugin": args.platform,
        "dbx_version": "",
        "qt": "",
        "pyqt": "",
    }
    try:
        from dbx import __version__

        environment["dbx_version"] = __version__
        from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR

        environment["qt"] = QT_VERSION_STR
        environment["pyqt"] = PYQT_VERSION_STR
    except Exception:
        pass
    git = _git_info()

    log.write("=" * 72)
    log.write("dBX E2E harness")
    log.write(f"Avvio: {_iso(started)}")
    log.write(f"Commit: {git['commit_short']} · branch {git['branch']}")
    log.write(f"Versione: {environment['dbx_version']} · Python {environment['python']}")
    log.write(f"Output: {output}")
    log.write(f"Scenari: {', '.join(item.name for item in selected)}")
    log.write("=" * 72)
    log.write("")

    stage_env = _python_env(os.environ, config / "stages", args.platform)
    stages: list[StageResult] = []
    if not args.skip_pytest:
        command = [
            sys.executable,
            "-m",
            "pytest",
            f"--junitxml={output / 'pytest-junit.xml'}",
        ]
        if args.pytest_args:
            command.extend(shlex.split(args.pytest_args))
        log.write("[stage] pytest — suite completa")
        stages.append(
            _run_stage(
                "pytest",
                "Suite pytest",
                command,
                output / "pytest.log",
                stage_env,
                timeout=max(300.0, args.timeout * 2),
            )
        )
        log.write(f"        {stages[-1].status.upper()} · {stages[-1].summary}")
    else:
        stages.append(StageResult("pytest", "Suite pytest", "skipped", 0.0, "saltato"))
        log.write("[stage] pytest — saltato")

    if not args.skip_smoke:
        log.write("[stage] smoke headless")
        stages.append(
            _run_stage(
                "smoke",
                "Smoke headless",
                [sys.executable, "-m", "dbx", "--smoke"],
                output / "smoke.log",
                stage_env,
                timeout=max(180.0, args.timeout),
            )
        )
        log.write(f"        {stages[-1].status.upper()} · {stages[-1].summary}")
    else:
        stages.append(StageResult("smoke", "Smoke headless", "skipped", 0.0, "saltato"))
        log.write("[stage] smoke — saltato")
    log.write("")

    try:
        from dbx.ui.app import create_application
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or create_application(["dbx-e2e"])
    except Exception:
        log.write("ERRORE: impossibile avviare Qt/QApplication")
        log.write(traceback.format_exc())
        log.close()
        return EXIT_USAGE

    ctx = E2EContext(output=output, qapp=app, screenshots_enabled=screenshots)
    ctx.keep = args.keep
    scenario_results: list[ScenarioResult] = []
    overall_started = time.perf_counter()
    for index, definition in enumerate(selected, start=1):
        log.write(f"[{index}/{len(selected)}] {definition.name} — {definition.title}")
        ctx.begin(definition.name)
        started_scenario = time.perf_counter()
        status = "fail"
        error: str | None = None
        tb = ""
        try:
            with ctx.auto_dialogs():
                with _time_limit(args.timeout):
                    definition.function(ctx)
            minimum = int(getattr(definition, "min_checks", 0) or 0)
            passed_checks = sum(1 for check in ctx.checks if check["status"] == "pass")
            if minimum and passed_checks < minimum:
                ctx.check(
                    False,
                    "numero minimo di controlli",
                    f"attesi almeno {minimum}, ottenuti {passed_checks}",
                )
            status = "pass"
        except ScenarioFailure as exc:
            status = "fail"
            error = str(exc)
            tb = traceback.format_exc()
        except Exception as exc:
            status = "fail"
            error = f"{type(exc).__name__}: {exc}"
            tb = traceback.format_exc()
            ctx.checks.append(
                {"name": "eccezione imprevista", "status": "fail", "detail": error}
            )
        finally:
            ctx.keep = args.keep or status == "fail"
            if ctx.keep:
                ctx.note("workdir", str(ctx.work))
            ctx.finish()
        duration = _duration(started_scenario)
        passed = sum(1 for check in ctx.checks if check["status"] == "pass")
        result = ScenarioResult(
            name=definition.name,
            title=definition.title,
            status=status,
            duration_s=duration,
            checks=list(ctx.checks),
            error=error,
            traceback=tb,
            screenshots=list(ctx.screenshots),
            info=dict(ctx.info),
        )
        scenario_results.append(result)
        log.write(
            f"        {status.upper()} · {passed}/{len(ctx.checks)} controlli · "
            f"{duration:.2f} s"
        )
        if args.verbose:
            for check in ctx.checks:
                log.write(f"          [{'ok' if check['status'] == 'pass' else '!!'}] {check['name']}")
        if error:
            log.write(f"        {error}")
            if ctx.keep and ctx.info.get("workdir"):
                log.write(f"        Progetto temporaneo: {ctx.info['workdir']}")
        if args.fail_fast and status == "fail":
            log.write("        --fail-fast: esecuzione interrotta")
            break

    elapsed = time.perf_counter() - overall_started
    log.write("")
    log.write(f"Scenari completati in {elapsed:.2f} s")

    catalog_coverage = coverage_of(NEW_SCENARIOS, args.coverage_phase)
    catalog_errors = validate_scenarios(NEW_SCENARIOS)
    coverage_status = "pass"
    if catalog_errors or (args.require_coverage and catalog_coverage.missing):
        coverage_status = "fail"
    coverage_summary = (
        f"{catalog_coverage.covered}/{catalog_coverage.required} feature "
        f"({catalog_coverage.percent:.0f}%)"
    )
    if catalog_errors:
        coverage_summary += f" · {len(catalog_errors)} errori di catalogo"
    stages.append(
        StageResult(
            "coverage",
            "Copertura funzioni E2E",
            coverage_status,
            0.0,
            coverage_summary,
        )
    )
    log.write(f"[coverage] {coverage_summary}")
    for error in catalog_errors[:20]:
        log.write(f"        {error}")

    finished = _now()
    report_path, md_path, report = _write_reports(
        output,
        started,
        finished,
        environment,
        git,
        {
            "output": str(output),
            "platform": args.platform,
            "skip_pytest": args.skip_pytest,
            "skip_smoke": args.skip_smoke,
            "screenshots": screenshots,
            "keep": args.keep,
            "fail_fast": args.fail_fast,
            "only": args.only,
            "area": args.area,
            "feature": args.feature,
            "coverage_phase": args.coverage_phase,
            "require_coverage": args.require_coverage,
            "coverage": {
                "phase": catalog_coverage.phase,
                "required": catalog_coverage.required,
                "covered": catalog_coverage.covered,
                "percent": round(catalog_coverage.percent, 1),
                "missing": list(catalog_coverage.missing[:50]),
                "errors": catalog_errors[:50],
            },
            "timeout_s": args.timeout,
        },
        stages,
        scenario_results,
        output / "run.log",
    )
    if output.parent == DEFAULT_OUTPUT:
        try:
            (output.parent / "latest.txt").write_text(str(output), encoding="utf-8")
        except OSError:
            pass
    summary = report["summary"]
    log.write("")
    log.write("=" * 72)
    log.write(
        f"ESITO: {report['overall'].upper()} · scenari "
        f"{summary['scenarios_passed']}/{summary['scenarios']} · controlli "
        f"{summary['checks'] - summary['checks_failed']}/{summary['checks']} · "
        f"screenshot {summary['screenshots']}"
    )
    log.write(f"Report: {report_path}")
    log.write(f"Markdown: {md_path}")
    log.write("=" * 72)
    log.close()
    if args.quiet:
        print(
            f"ESITO: {report['overall'].upper()} · report: {report_path}",
            flush=True,
        )
    return report["exit_code"]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as exc:
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(EXIT_USAGE)
