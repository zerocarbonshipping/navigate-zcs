# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the regulation results of the bunkering LP to the expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_regulation_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the LP solution of each active regulation to its expectation.

    Per policed vessel the regulated emissions and energy, and under INDIVIDUAL its
    remedial units; per FLEXIBLE regulation the pooled remedial units and the shadow
    price of the pooled threshold: the cost of a unit of emissions, set by the remedial
    cost or by the cheapest compliant fuel available at scale.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    idx = alg.idx

    for r, v in alg.regulation_emission_terms:
        expectation = alg.regulations[r].expectation
        emissions = alg.regulation_emission_terms[r, v].getValue()
        energy = alg.regulation_energy_terms[r, v].getValue()

        expectation.set_vessel_emissions(idx, v, emissions)
        expectation.set_vessel_energy(idx, v, energy)

    for (r, v), remedial_factor in alg.remedial_factor_individual.items():
        expectation = alg.regulations[r].expectation
        expectation.set_vessel_remedial_units(idx, v, remedial_factor.X)

    for r, remedial_factor in alg.remedial_factor_flexibility.items():
        expectation = alg.regulations[r].expectation
        constraint = alg.regulation_threshold_flexibility[r]

        expectation.set_pooled_remedial_units(idx, remedial_factor.X)
        expectation.set_pooled_shadow_price(idx, -constraint.Pi)
