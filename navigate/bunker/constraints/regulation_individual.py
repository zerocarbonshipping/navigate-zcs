# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_terms import calculate_regulation_emission_term


def update_individual_regulation_threshold_constraints(alg: BunkerAlgorithm) -> None:
    r"""
    Add the per-vessel threshold constraint of each INDIVIDUAL-scheme regulation.

    For each regulation r and policed vessel v:

        E_{r,v} - w_{r,v} <= R_{r,v}

    where E is the vessel's regulated constraint term -- a linear expression over
    its sea and port fuel spend and shore power, weighted by regulation
    coefficients and jurisdiction fractions: the coefficient expression of
    calculate_regulation_emission_term, which for intensity measures already
    folds in the threshold and is distinct from the emission and energy
    expressions stored for reporting -- w the remedial units bought for the
    vessel, and R the threshold-derived bound (update_regulation_individual_rhs).
    The remedial variable keeps the model feasible when the cap cannot be met;
    its objective cost prices non-compliance.

    The constraint is removed and re-added each build instead of mutated in place:
    which spend variables enter E changes between builds (legs move between
    jurisdiction fractions), so the row's sparsity pattern is not stable.

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

        if key in alg.regulation_threshold_individual:
            alg.model.remove(alg.regulation_threshold_individual[key])

        name = "regulation_threshold_individual_{}_{}".format(*key)
        alg.regulation_threshold_individual[key] = alg.model.addConstr(lhs <= rhs, name=name)
