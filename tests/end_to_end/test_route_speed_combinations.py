# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every RouteType x SpeedAlignment x AllowSpeedManagement of a fleet runs.

The base fleet's oil and methane vessels face different fuel costs, so their
individually optimal speeds differ. An aligned fleet sails both at one speed,
taken from those individual optima. The first speed decision is read for the
comparison with the INDIVIDUAL run: up to that step, the alignment has not
acted yet, so both runs hold the same individual optima there.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from navigate.core.enum_ import RouteTypeID

ROUTE_TYPES = ("ROUND_TRIP", "REGIONAL_TRIP")
ALIGNMENTS = ("INDIVIDUAL", "MINIMUM", "MAXIMUM", "AVERAGE")
ALIGNED = ALIGNMENTS[1:]

FLEET = "container_15000_teu"
ROUTE = "combination_route"

# the same speed mapped through the same route distribution
SPEED_RTOL = 1e-9

pytestmark = pytest.mark.slow


def _run(run_combination, route_type, alignment, speed_management):
    return run_combination(
        (f"route_{route_type.lower()}.inc", {}),
        (
            "fleet_speed.inc",
            {
                "speed_alignment": alignment,
                "allow_speed_management": "TRUE" if speed_management else "FALSE",
            },
        ),
    )


def _vessels(manager):
    return manager.nodes.fleets[FLEET].vessels


@pytest.mark.parametrize(
    ("route_type", "alignment", "speed_management"),
    list(itertools.product(ROUTE_TYPES, ALIGNMENTS, (True, False))),
)
def test_fleet_sails_its_route_at_aligned_speeds(
    run_combination, route_type, alignment, speed_management
):
    vessels = _vessels(_run(run_combination, route_type, alignment, speed_management))

    for vessel in vessels:
        assert vessel.route.name == ROUTE
        assert vessel.route.route_type == RouteTypeID[route_type]

    if not speed_management:
        return

    for vessel in vessels:
        decided = vessel.profile.get_optimal_speed()[1:]
        assert np.all(np.isfinite(decided)), f"{vessel} took no speed decision"

    if alignment in ALIGNED:
        reference = vessels[0].profile
        for vessel in vessels[1:]:
            np.testing.assert_allclose(
                vessel.profile.get_optimal_speed(),
                reference.get_optimal_speed(),
                rtol=SPEED_RTOL,
            )
            np.testing.assert_allclose(
                vessel.profile.get_actual_speed(),
                reference.get_actual_speed(),
                rtol=SPEED_RTOL,
            )


@pytest.mark.parametrize(
    ("route_type", "alignment"), list(itertools.product(ROUTE_TYPES, ALIGNED))
)
def test_alignment_picks_from_the_individual_optima(
    run_combination, route_type, alignment
):
    individual = _vessels(_run(run_combination, route_type, "INDIVIDUAL", True))
    aligned = _vessels(_run(run_combination, route_type, alignment, True))

    speeds = individual[0].profile.get_optimal_speed()
    first = np.flatnonzero(np.isfinite(speeds))[0]

    optima = [vessel.profile.get_optimal_speed()[first] for vessel in individual]
    assert min(optima) < max(optima), "the vessels' optima must differ"

    speed = aligned[0].profile.get_optimal_speed()[first]

    if alignment == "MINIMUM":
        assert speed == pytest.approx(min(optima), rel=SPEED_RTOL)
    elif alignment == "MAXIMUM":
        assert speed == pytest.approx(max(optima), rel=SPEED_RTOL)
    else:
        assert min(optima) < speed < max(optima)


@pytest.mark.parametrize(
    ("route_type", "alignment"), list(itertools.product(ROUTE_TYPES, ALIGNED))
)
def test_alignment_is_ignored_without_speed_management(
    run_combination, route_type, alignment
):
    individual = _run(run_combination, route_type, "INDIVIDUAL", False)
    aligned = _run(run_combination, route_type, alignment, False)

    expected = individual.profile.get_consumed_energy()
    consumed = aligned.profile.get_consumed_energy()

    assert consumed.keys() == expected.keys()
    for fuel, energy in consumed.items():
        np.testing.assert_array_equal(energy, expected[fuel], err_msg=fuel)
