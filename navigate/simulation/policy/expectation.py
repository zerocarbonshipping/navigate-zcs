# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Per-step expectations of regulations and levies over the remaining timeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationMeasureID
from navigate.simulation.policy.jurisdiction import calculate_jurisdiction_fractions

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


def calculate_policy_expectations(
    regulations: dict[str, Regulation],
    levies: dict[str, Levy],
    emissions: dict[str, Emission],
    routes: dict[str, Route],
    vessels: dict[str, Vessel],
    emissions_lifetime: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the expectations of every active regulation and levy.

    Levy levels, regulation remedial costs, transport-measure vessel capacities and the
    jurisdiction fractions of every route port and leg are set over the remaining
    timeline. Global warming potentials are set at each policy's emissions lifetime.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    levies
        All levies in the simulation.
    emissions
        All emissions in the simulation.
    routes
        All routes in the simulation.
    vessels
        All vessels in the simulation.
    emissions_lifetime
        Model-wide emissions lifetime, in years; a policy's own lifetime replaces it.
    timeline
        Simulation timeline, in days.
    idx
        Current time-step index.
    """
    times = timeline[idx:]

    for regulation in regulations.values():
        if not regulation.active:
            continue

        _calculate_regulation_forecasts(regulation, vessels, times, idx)
        calculate_jurisdiction_fractions(regulation, routes, times, idx)
        _calculate_global_warming_potentials(regulation, emissions, emissions_lifetime)

    for levy in levies.values():
        if not levy.active:
            continue

        _calculate_levy_forecasts(levy, times, idx)
        _calculate_global_warming_potentials(levy, emissions, emissions_lifetime)


def _calculate_regulation_forecasts(
    regulation: Regulation, vessels: dict[str, Vessel], times: FloatArray, idx: int
) -> None:
    """Set the regulation's remedial cost and transport-measure vessel capacities."""
    expectation = regulation.expectation

    expectation.set_remedial_cost(idx, regulation.remedial_cost.get(times))

    if regulation.measure in (
        RegulationMeasureID.TRANSPORT,
        RegulationMeasureID.TRANSPORT_NOMINAL,
    ):
        for vessel_name, own_capacity in regulation.vessel_capacities.items():
            if own_capacity is None:
                capacity = vessels[vessel_name].nominal_capacity.get(times)
            else:
                capacity = own_capacity.get(times)

            expectation.set_vessel_capacity(idx, vessel_name, capacity)


def _calculate_levy_forecasts(levy: Levy, times: FloatArray, idx: int) -> None:
    """Set the levy's level."""
    levy.expectation.set_level(idx, levy.level.get(times))


def _calculate_global_warming_potentials(
    policy: Levy | Regulation,
    emissions: dict[str, Emission],
    emissions_lifetime: float,
) -> None:
    """Set the policy's global warming potentials at its emissions lifetime."""
    if policy.emissions_lifetime is None:
        lifetime = emissions_lifetime
    else:
        lifetime = policy.emissions_lifetime.get()

    for emission_name, own_potential in policy.global_warming_potentials.items():
        if own_potential is None:
            potential = emissions[emission_name].global_warming_potential
        else:
            potential = own_potential

        gwp = potential.get(lifetime)
        policy.expectation.set_global_warming_potential(emission_name, gwp)
