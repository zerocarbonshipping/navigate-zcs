# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Directional behaviour: the sign of the model's response to one perturbed input.

Each test runs a base deck and a perturbed deck that differs from it by one
Include, and asserts the direction in which a horizon total moves, never its
size. Conventions: README.md next to this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from helpers.simulation import check_invariants, run_simulation

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.simulation import SimulationManager

SIMULATIONS_DIR = Path(__file__).resolve().parent / "simulations"

# Relative margin a horizon total must move by before its direction counts.
# The bunker LPs have non-unique optima (helpers/baseline.py), so equal-cost
# alternatives can trade volume between steps and ports without any input
# changing: a per-step value can flip sign on such a tie, while a horizon total
# barely moves. 1% sits far above that and the runner-noise floor, and each
# perturbation is sized so the response the domain demands is several times
# larger.
MARGIN_REL = 0.01

AMMONIA = "ammonia_electro"

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def run() -> Callable[[str], SimulationManager]:
    """Run a deck by directory name once per module, checking the invariants."""
    managers: dict[str, SimulationManager] = {}

    def _run(name: str) -> SimulationManager:
        if name not in managers:
            manager = run_simulation(SIMULATIONS_DIR / name)
            check_invariants(manager)
            managers[name] = manager
        return managers[name]

    return _run


def assert_rises(what: str, base: float, perturbed: float) -> None:
    assert perturbed > base + MARGIN_REL * abs(base), (
        f"{what} did not rise: base {base:.6g}, perturbed {perturbed:.6g}"
    )


def assert_falls(what: str, base: float, perturbed: float) -> None:
    assert perturbed < base - MARGIN_REL * abs(base), (
        f"{what} did not fall: base {base:.6g}, perturbed {perturbed:.6g}"
    )


def consumed(manager: SimulationManager, fuel: str) -> float:
    return float(manager.profile.get_consumed_energy()[fuel].sum())


def ammonia_share(manager: SimulationManager) -> float:
    total = float(manager.profile.get_total_consumed_energy().sum())
    return consumed(manager, AMMONIA) / total


def test_development_headroom_relieves_supply_shortage(run):
    """
    Raising MaximumDevelopment under unmet demand raises supply and compliance.

    A regulation demands more e-ammonia than the Producer may build plants for,
    so the development limit is what holds supply back: lifting it must let the
    Producer build more, and the fleet then buys fewer remedial units for the
    emissions it cannot abate.
    """
    base = run("supply_constrained")
    raised = run("supply_raised")

    def development(manager):
        producer = manager.nodes.producers["epc_europe"]
        return float(producer.profile.get_development().sum())

    def remedial(manager):
        regulation = manager.nodes.regulations["intensity_regulation"]
        return float(regulation.profile.get_remedial_units().sum())

    # deck validity: the base must leave demand unmet, or the limit is not binding
    assert remedial(base) > 0.0, "The base deck is not supply-constrained"

    assert_rises("Cumulative development", development(base), development(raised))
    assert_falls("Remedial units", remedial(base), remedial(raised))


def test_tighter_regulation_raises_alternative_fuel_share(run):
    """
    Lowering the GHG-intensity threshold raises the e-ammonia share of energy.

    With supply free to follow demand, a stricter intensity limit can only be met
    by burning more zero-carbon fuel relative to oil.
    """
    base = run("supply_raised")
    tightened = run("regulation_tightened")

    # deck validity: the base threshold must bind, or tightening it is inert
    regulation = base.nodes.regulations["intensity_regulation"]
    assert regulation.profile.get_remedial_units().sum() > 0.0, (
        "The base regulation does not bind"
    )

    assert_rises(
        "E-ammonia energy share", ammonia_share(base), ammonia_share(tightened)
    )


def test_removing_carbon_levy_raises_emissions(run):
    """
    Removing a carbon levy raises WTW emissions and lowers e-ammonia use.

    The levy is the only reason to pay for zero-carbon fuel in this deck: without
    it, the fleet falls back to cheaper, emitting oil.
    """
    base = run("carbon_levy")
    removed = run("carbon_levy_removed")

    # deck validity: the base levy must collect and must buy ammonia uptake
    collected = base.nodes.levies["carbon_levy"].profile.get_collected()
    # the first step only initializes expectations
    assert np.all(collected[1:] > 0.0), "The base levy does not collect"
    assert consumed(base, AMMONIA) > 0.0, "The base levy buys no e-ammonia"

    def wtw(manager):
        return float(manager.profile.get_total_equivalent_wtw().sum())

    assert_rises("Total WTW emissions", wtw(base), wtw(removed))
    assert_falls(
        "E-ammonia energy", consumed(base, AMMONIA), consumed(removed, AMMONIA)
    )


def test_dearer_destination_fuel_slows_conversion(run):
    """
    Raising the price of LNG lowers the number of oil -> methane conversions.

    A conversion pays for itself through the fuel-cost saving over the vessel's
    remaining life; a smaller oil-vs-LNG spread shrinks that saving, so fewer
    owners convert.
    """
    base = run("fuel_conversion")
    dearer = run("fuel_conversion_dearer_lng")

    def conversions(manager):
        fleet = manager.nodes.fleets["container_15000_teu"]
        lane = ("container_15000_teu_ice_oil", "container_15000_teu_ice_methane")
        return float(fleet.profile.get_fuel_conversions()[lane].sum())

    # deck validity: more than one vessel must convert in the base
    assert conversions(base) > 1.0, "The base deck converts no vessels"

    assert_falls("Oil -> methane conversions", conversions(base), conversions(dearer))
