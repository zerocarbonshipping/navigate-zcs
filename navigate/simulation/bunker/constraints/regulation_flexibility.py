# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the fleet-pooled threshold constraints of FLEXIBLE-scheme regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint
from navigate.simulation.bunker.constraints.regulation_terms import (
    calculate_regulation_terms,
)

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_flexibility_regulation_threshold_constraints(alg: BunkerAlgorithm) -> None:
    r"""
    Add the fleet-pooled threshold constraint of each FLEXIBLE-scheme regulation.

    For each regulation r:

        \sum_{v policed} M_v E_{r,v} - w_r <= R_r

    where E is a vessel's T of calculate_regulation_terms (see
    regulation_individual), M the number of vessels it represents, w the remedial
    units bought for the pool, and R the pooled threshold bound
    (update_regulation_flexibility_rhs). Vessels over their individual target are
    balanced by vessels under it; only the pooled excess is priced through the
    remedial variable.

    The row is rewritten in place each build: every variable it has ever held for
    a vessel still in the model is written again, at weight 0 where its
    jurisdiction fraction is 0 or its vessel is not policed.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    change_coefficient = alg.model.chgCoeff
    rows = alg.regulation_threshold_flexibility

    for r, rhs in alg.regulation_total_rhs_flexibility.items():
        constraint = get_constraint(
            alg, rows, r, "<=", "regulation_threshold_flexibility"
        )
        constraint.rhs = rhs

        regulation = alg.regulations[r]

        for v, vessel in alg.vessels.items():
            is_policed = regulation.vessel_is_policed(v)
            multiplier = alg.multipliers[v] if is_policed else 0.0

            terms, emissions, energy = calculate_regulation_terms(
                alg, vessel, regulation
            )

            # kept for transferring the regulation solution after the solve
            if is_policed:
                alg.regulation_emission_terms[(r, v)] = emissions
                alg.regulation_energy_terms[(r, v)] = energy

            for variable, weight in terms:
                change_coefficient(constraint, variable, weight * multiplier)

        change_coefficient(constraint, alg.remedial_factor_flexibility[r], -1.0)
