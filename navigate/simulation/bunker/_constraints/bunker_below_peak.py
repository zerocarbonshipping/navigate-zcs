# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints that hold a fuel's bunkering at each stop below its peak."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_bunker_below_peak_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that hold a fuel's bunkering at each stop below its peak.

    For each stop p and fuel f bunkerable there (vessel index omitted):

        b_{p,f} <= \hat{b}_f

    where b is the fuel mass bunkered at stop p and \hat{b} the peak of the fuel, a
    variable without a cost. The constraints therefore leave the cheapest bunkering
    and its prices as they are. The least value a peak can take is the largest mass
    of the fuel the vessel bunkers at one stop, and that is what the bunker-peaks
    rule (_rules.py) minimizes.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name
    route = vessel.route

    rows = alg.bunker_below_peak
    bunker = alg.bunker
    bunker_peak = alg.bunker_peak
    model = alg.model

    for p, fuels in enumerate(vessel.bunkerable_fuels):
        for f in fuels:
            key = (v, p, f)
            constraint = get_constraint(
                alg, rows, key, "<=", "bunker_below_peak", route
            )

            model.set_coefficient(constraint, bunker[key], 1.0)
            model.set_coefficient(constraint, bunker_peak[v, f], -1.0)
