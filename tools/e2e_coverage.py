#!/usr/bin/env python3
"""Genera la matrice feature → scenario del catalogo E2E.

Uso: python3 tools/e2e_coverage.py [docs/e2e-coverage.md]
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from e2e.catalog import FEATURES, coverage  # noqa: E402
from e2e.registry import load  # noqa: E402


def render() -> str:
    scenarios = load()
    mapping: dict[str, list[str]] = defaultdict(list)
    for scenario in scenarios:
        for feature_id in scenario.features:
            mapping[feature_id].append(scenario.name)
    lines = [
        "# Copertura funzionale E2E",
        "",
        "Generato da `tools/e2e_coverage.py`. Non modificare a mano.",
        "",
        f"- Scenari registrati: **{len(scenarios)}**",
        f"- Feature di fase 1: **{coverage(scenarios, 1).covered}/{coverage(scenarios, 1).required}**",
        f"- Feature di fase 2: **{coverage(scenarios, 2).covered}/{coverage(scenarios, 2).required}**",
        f"- Feature di fase 3: **{coverage(scenarios, 3).covered}/{coverage(scenarios, 3).required}**",
        "",
        "## Fase 1 — coperta",
        "",
        "| Feature | Area | Descrizione | Scenari |",
        "|---|---|---|---|",
    ]
    for feature in sorted(FEATURES.values(), key=lambda item: (item.area, item.id)):
        if feature.phase != 1:
            continue
        lines.append(
            f"| `{feature.id}` | {feature.area} | {feature.label} | "
            f"{', '.join(f'`{name}`' for name in mapping.get(feature.id, [])) or '—'} |"
        )
    lines += ["", "## Fasi 2–3 — da completare", "", "| Feature | Area | Fase |", "|---|---|---:|"]
    for feature in sorted(FEATURES.values(), key=lambda item: (item.phase, item.area, item.id)):
        if feature.phase == 1:
            continue
        lines.append(f"| `{feature.id}` | {feature.area} | {feature.phase} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else ROOT / "docs" / "e2e-coverage.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    print(f"Scritto {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
