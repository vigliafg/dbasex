"""Coerenza tra catalogo delle funzioni e scenari E2E 2.0."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from e2e.catalog import FEATURES, coverage, validate_scenarios  # noqa: E402
from e2e.registry import load  # noqa: E402


def test_catalog_is_coherent() -> None:
    scenarios = load()
    assert scenarios
    assert validate_scenarios(scenarios) == []


def test_phase_one_coverage_is_complete() -> None:
    scenarios = load()
    result = coverage(scenarios, phase=1)
    assert result.required > 0
    assert result.missing == ()
    assert result.percent == 100.0


def test_every_scenario_has_metadata() -> None:
    seen: set[str] = set()
    for scenario in load():
        assert scenario.name not in seen, f"nome duplicato: {scenario.name}"
        seen.add(scenario.name)
        assert scenario.title.startswith(("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"))
        assert scenario.area
        assert scenario.features, scenario.name
        assert scenario.min_checks >= 1, scenario.name
        assert scenario.budget_s > 0, scenario.name
        for feature_id in scenario.features:
            assert feature_id in FEATURES, f"{scenario.name}: {feature_id}"


def test_derived_engine_features_are_in_catalog() -> None:
    from dbx.core import types as T
    from dbx.core.form_model import BUTTON_ACTIONS, CONTROL_KINDS
    from dbx.core.label_model import LABEL_PRESETS
    from dbx.core.metadata import ON_DELETE_ACTIONS
    from dbx.core.query_model import ALL_OPERATORS
    from dbx.runtime.report_engine import BAND_NAMES, CHART_TYPES
    from dbx.runtime.script_engine import ACTIONS

    expected = {f"TB-TYPE-{item.upper()}" for item in T.ALL_TYPES}
    expected |= {f"TB-ONDELETE-{item.replace(' ', '-')}" for item in ON_DELETE_ACTIONS}
    expected |= {f"QRY-OP-{item.upper()}" for item in ALL_OPERATORS}
    expected |= {f"FRM-CONTROL-{item.upper()}" for item in CONTROL_KINDS}
    expected |= {f"FRM-BUTTON-{item.upper()}" for item in BUTTON_ACTIONS}
    expected |= {f"REP-BAND-{item.upper()}" for item in BAND_NAMES}
    expected |= {f"REP-CHART-{item.upper()}" for item in CHART_TYPES}
    expected |= {f"LBL-PRESET-{item.upper()}" for item in LABEL_PRESETS}
    expected |= {f"SCR-ACTION-{item.upper()}" for item in ACTIONS}
    missing = sorted(expected - set(FEATURES))
    assert missing == []


def test_phase_two_and_three_features_exist_for_future_waves() -> None:
    scenarios = load()
    phase_two = coverage(scenarios, phase=2)
    phase_three = coverage(scenarios, phase=3)
    assert phase_two.required > coverage(scenarios, phase=1).required
    assert phase_three.required >= phase_two.required


def test_query_and_form_features_are_covered() -> None:
    """E4 chiude il catalogo di query e form della fase 2."""

    scenarios = load()
    declared = {feature_id for scenario in scenarios for feature_id in scenario.features}
    required = {
        feature.id
        for feature in FEATURES.values()
        if feature.area in ("queries", "forms") and feature.phase <= 2
    }
    missing = sorted(required - declared)
    assert required
    assert missing == []


def test_phase_two_coverage_is_complete() -> None:
    """E5 chiude il catalogo della fase 2: report, etichette e script."""

    scenarios = load()
    result = coverage(scenarios, phase=2)
    assert result.required > 0
    assert result.missing == ()
    assert result.percent == 100.0
