# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the constraints that the fuel spent on a leg is on board when it starts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_mass_sufficient_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Update the constraints that fuel spent on a leg is on board when the leg starts.

    For each usable fuel f and tank stop i (vessel index omitted):

        n m_{i,f} >= \sum_{e} \sum_{c} x_{c,f,i,e}

    where m is the fuel mass in tank when departing stop i on one voyage, n the
    number of voyages per year, and x the annual fuel mass spent by converter c
    at sea on leg (i, e), summed over the legs departing i. Tank levels are per
    voyage while spend is annual, hence the scaling by n.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose constraints are updated.
    """
    v = vessel.name
    route = vessel.route
    voyages = float(vessel.expectation.get_voyages(alg.idx))

    rows = alg.mass_sufficient
    mass_tank = alg.mass_tank
    spend_sea = alg.spend_sea
    model = alg.model

    tank_stops = route.get_tank_stops()
    tank_departures = [(i, e) for i, e in route.get_legs() if i in tank_stops]

    for f, converters in vessel.converters_per_fuel.items():
        for i, e in tank_departures:
            key = (v, i, f)
            constraint = get_constraint(alg, rows, key, ">=", "mass_sufficient")

            model.set_coefficient(constraint, mass_tank[v, i, f], voyages)

            for c in converters:
                model.set_coefficient(constraint, spend_sea[v, c, f, i, e], -1.0)
