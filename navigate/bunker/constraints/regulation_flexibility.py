# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_helpers import calculate_regulation_emission_term


def update_flexibility_regulation_threshold_constraints(alg: BunkerAlgorithm) -> None:
    """
    Add flexibility regulation threshold constraints across all policed vessels.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for r, rhs in alg.regulation_total_rhs_flexibility.items():

        regulation = alg.regulations[r]

        terms = 0.

        for v, vessel in alg.vessels.items():

            if not regulation.vessel_is_policed(v):
                continue

            coefficients_v, emissions_v, energy_v = calculate_regulation_emission_term(alg, vessel, regulation)
            terms += coefficients_v * alg.multipliers[v]

            # save terms for later
            alg.regulation_emission_terms[(r, v)] = emissions_v
            alg.regulation_energy_terms[(r, v)] = energy_v

        lhs = terms - alg.remedial_factor_flexibility[r]

        # remove and re-add the constraint (coefficients change each build)
        if r in alg.regulation_threshold_flexibility:
            alg.model.remove(alg.regulation_threshold_flexibility[r])

        name = "regulation_threshold_flexibility_{}".format(r)
        alg.regulation_threshold_flexibility[r] = alg.model.addConstr(lhs <= rhs, name=name)
