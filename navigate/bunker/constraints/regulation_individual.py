# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_terms import calculate_regulation_emission_term


def update_individual_regulation_threshold_constraints(alg: BunkerAlgorithm) -> None:
    """
    Add individual regulation threshold constraints for each regulation-vessel pair.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for (r, v), rhs in alg.regulation_rhs_individual.items():

        key = (r, v)
        regulation = alg.regulations[r]
        vessel = alg.vessels[v]

        coefficients, emissions, energy = calculate_regulation_emission_term(alg, vessel, regulation)
        lhs = coefficients - alg.remedial_factor_individual[r, v]

        # save terms for later
        alg.regulation_emission_terms[(r, v)] = emissions
        alg.regulation_energy_terms[(r, v)] = energy

        # remove and re-add the constraint (coefficients change each build)
        if key in alg.regulation_threshold_individual:
            alg.model.remove(alg.regulation_threshold_individual[key])

        name = "regulation_threshold_individual_{}_{}".format(*key)
        alg.regulation_threshold_individual[key] = alg.model.addConstr(lhs <= rhs, name=name)
