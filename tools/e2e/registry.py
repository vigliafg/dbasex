"""Registro degli scenari E2E 2.0."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Callable

from e2e_scenarios import HarnessContext


@dataclass
class ScenarioDefinition:
    """Scenario granulare con metadati di copertura e prestazioni."""

    name: str
    title: str
    function: Callable[[HarnessContext], None]
    area: str
    features: tuple[str, ...] = ()
    min_checks: int = 3
    budget_s: float = 8.0
    screenshots: tuple[str, ...] = ()
    legacy: bool = False


SCENARIOS: list[ScenarioDefinition] = []


def scenario(
    name: str,
    title: str,
    area: str,
    *,
    features: tuple[str, ...] = (),
    min_checks: int = 3,
    budget_s: float = 8.0,
    screenshots: tuple[str, ...] = (),
):
    """Decoratore che registra uno scenario nel catalogo E2E."""

    def decorate(function: Callable[[HarnessContext], None]) -> Callable[[HarnessContext], None]:
        if any(item.name == name for item in SCENARIOS):
            raise RuntimeError(f"Scenario duplicato: {name}")
        SCENARIOS.append(
            ScenarioDefinition(
                name=name,
                title=title,
                function=function,
                area=area,
                features=tuple(features),
                min_checks=min_checks,
                budget_s=budget_s,
                screenshots=tuple(screenshots),
            )
        )
        return function

    return decorate


def load() -> list[ScenarioDefinition]:
    """Importa i moduli degli scenari e restituisce il registro ordinato."""

    from .scenarios import s00_foundation, s10_tables, s20_browse, s30_data_ops  # noqa: F401

    return sorted(SCENARIOS, key=lambda item: (item.area, item.name))
