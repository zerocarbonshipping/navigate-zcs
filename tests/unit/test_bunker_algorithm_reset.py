# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the per-time-step reset of BunkerAlgorithm's dynamic state."""
from navigate.bunker.bunker_algorithm import BunkerAlgorithm

# every container of per-time-step policy/regulation state; each is fully
# recalculated during build, so a stale entry surviving the reset can leak a
# previous time-step's value (e.g. for a vessel that left the fleet)
DYNAMIC_CONTAINERS = (
    "cost_levy",
    "regulation_vessel_threshold",
    "regulation_emission_factor",
    "regulation_spend_coefficient",
    "shore_power_regulation_emission_factor",
    "shore_power_regulation_coefficient",
    "regulation_measure",
    "regulation_rhs_individual",
    "regulation_rhs_flexibility",
    "regulation_total_rhs_flexibility",
    "regulation_emission_terms",
    "regulation_energy_terms",
    "flexible_unit_cost",
    "adjusted_vessel_thresholds",
    "adjusted_shared_thresholds",
    "emission_factor",
)


def test_reset_clears_every_dynamic_container():
    algo = BunkerAlgorithm()

    for name in DYNAMIC_CONTAINERS:
        getattr(algo, name)["stale_key"] = object()

    algo._reset_dynamic_properties()

    stale = [name for name in DYNAMIC_CONTAINERS if getattr(algo, name)]
    assert not stale, f"Containers not cleared by _reset_dynamic_properties: {stale}"


def test_reset_targets_only_declared_attributes():
    """A reset assigning to a name absent from __init__ silently orphans the
    real container (regression guard: regulation_emission_coefficient)."""

    algo = BunkerAlgorithm()
    declared = set(vars(algo))

    algo._reset_dynamic_properties()

    assert set(vars(algo)) == declared
