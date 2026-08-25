# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

from navigate.bunker.constraints.regulation_terms import calculate_regulation_emission_term


def update_flexibility_regulation_threshold_constraints(alg: BunkerAlgorithm) -> None:
    r"""
    Add the fleet-pooled threshold constraint of each FLEXIBLE-scheme regulation.

    For each regulation r:

        \sum_{v policed} M_v E_{r,v} - w_r <= R_r

    where E is a vessel's regulated constraint term (the coefficient expression of
    calculate_regulation_emission_term -- see regulation_individual for how it
    differs from the stored emission and energy expressions), M the number of
    vessels it represents, w the remedial units bought for the pool, and R the
    pooled threshold bound (update_regulation_flexibility_rhs). Vessels over their
    individual target are balanced by vessels under it; only the pooled excess is
    priced through the remedial variable.

    The constraint is removed and re-added each build instead of mutated in place:
    which spend variables enter E changes between builds (legs move between
    jurisdiction fractions), so the row's sparsity pattern is not stable.

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

        if r in alg.regulation_threshold_flexibility:
            alg.model.remove(alg.regulation_threshold_flexibility[r])

        name = "regulation_threshold_flexibility_{}".format(r)
        alg.regulation_threshold_flexibility[r] = alg.model.addConstr(lhs <= rhs, name=name)
