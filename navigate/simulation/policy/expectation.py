# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Per-step expectations of regulations and levies over the remaining timeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationMeasureID

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.levy import Levy
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray

_TRANSPORT_MEASURES = (
    RegulationMeasureID.TRANSPORT,
    RegulationMeasureID.TRANSPORT_NOMINAL,
)


def calculate_policy_expectations(
    regulations: dict[str, Regulation],
    levies: dict[str, Levy],
    emissions: dict[str, Emission],
    vessels: dict[str, Vessel],
    emissions_lifetime: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """
    Calculate the expectations of every active regulation and levy.

    Levy levels, regulation remedial costs and transport-measure vessel capacities are
    read over the remaining timeline; global warming potentials at each policy's
    emissions lifetime.

    Parameters
    ----------
    regulations
        All regulations in the simulation.
    levies
        All levies in the simulation.
    emissions
        All emissions in the simulation.
    vessels
        All vessels in the simulation.
    emissions_lifetime
        Model-wide emissions lifetime, in years; a policy's own lifetime replaces it.
    timeline
        Simulation timeline, days.
    idx
        Current time-step index.
    """
    for regulation in regulations.values():
        if not regulation.active:
            continue

        _calculate_regulation_expectation(
            regulation, emissions, vessels, emissions_lifetime, timeline, idx
        )

    for levy in levies.values():
        if not levy.active:
            continue

        _calculate_levy_expectation(levy, emissions, emissions_lifetime, timeline, idx)


def _calculate_regulation_expectation(
    regulation: Regulation,
    emissions: dict[str, Emission],
    vessels: dict[str, Vessel],
    emissions_lifetime: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """Set the regulation's remedial cost, capacities and global warming potentials."""
    times = timeline[idx:]
    expectation = regulation.expectation

    expectation.set_remedial_cost(idx, regulation.remedial_cost.get(times))

    if regulation.measure in _TRANSPORT_MEASURES:
        for vessel_name, own_capacity in regulation.vessel_capacity.items():
            if own_capacity is None:
                capacity = vessels[vessel_name].nominal_capacity.get(times)
            else:
                capacity = own_capacity.get(times)

            expectation.set_vessel_capacity(idx, vessel_name, capacity)

    _calculate_global_warming_potentials(regulation, emissions, emissions_lifetime)


def _calculate_levy_expectation(
    levy: Levy,
    emissions: dict[str, Emission],
    emissions_lifetime: float,
    timeline: FloatArray,
    idx: int,
) -> None:
    """Set the levy's level and global warming potentials."""
    levy.expectation.set_level(idx, levy.level.get(timeline[idx:]))

    _calculate_global_warming_potentials(levy, emissions, emissions_lifetime)


def _calculate_global_warming_potentials(
    policy: Levy | Regulation,
    emissions: dict[str, Emission],
    emissions_lifetime: float,
) -> None:
    """Set the policy's global warming potentials at its emissions lifetime."""
    if policy.emissions_lifetime is not None:
        emissions_lifetime = policy.emissions_lifetime.get()

    for emission_name, own_potential in policy.global_warming_potential.items():
        if own_potential is None:
            potential = emissions[emission_name].global_warming_potential
        else:
            potential = own_potential

        policy.expectation.set_global_warming_potential(
            emission_name, potential.get(emissions_lifetime)
        )
