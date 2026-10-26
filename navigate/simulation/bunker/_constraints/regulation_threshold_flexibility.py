# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the fleet-pooled threshold constraints of FLEXIBLE-scheme regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationSchemeID
from navigate.simulation.bunker._build import get_constraint
from navigate.simulation.bunker._constraints._regulation_terms import (
    calculate_regulation_terms,
)

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_regulation_threshold_flexibility_constraints(alg: BunkerAlgorithm) -> None:
    r"""
    Update the constraints that hold the policed vessels to a FLEXIBLE pooled threshold.

    For each regulation r:

        \sum_{v policed} M_v E_{r,v} - w_r <= R_r

    where E is a vessel's T of calculate_regulation_terms (see
    regulation_threshold_individual), M the number of vessels it represents, w the
    remedial units bought for the pool, and R the pooled threshold bound
    (update_regulation_rhs_flexibility). Vessels over their individual target are
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
    rows = alg.regulation_threshold_flexibility
    remedial_factor_flexibility = alg.remedial_factor_flexibility
    model = alg.model

    for r, rhs in alg.regulation_rhs_flexibility.items():
        constraint = get_constraint(
            alg, rows, r, "<=", "regulation_threshold_flexibility"
        )
        model.set_rhs(constraint, rhs)

        regulation = alg.regulations[r]

        for v, vessel in alg.vessels.items():
            is_policed = regulation.vessel_is_policed(v)
            multiplier = alg.multipliers[v] if is_policed else 0.0

            terms, emissions, energy = calculate_regulation_terms(
                alg, vessel, regulation
            )

            # kept for transferring the regulation solution after the solve
            if is_policed:
                alg.regulation_emission_terms[r, v] = emissions
                alg.regulation_energy_terms[r, v] = energy

            for variable, weight in terms:
                model.set_coefficient(constraint, variable, weight * multiplier)

        model.set_coefficient(constraint, remedial_factor_flexibility[r], -1.0)


def update_regulation_rhs_flexibility(alg: BunkerAlgorithm) -> None:
    """
    Update the pooled right-hand sides of FLEXIBLE regulations.

    The pool sums the allowances of the policed vessels, weighted by multipliers.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, regulation in alg.active_regulations.items():
        if regulation.scheme != RegulationSchemeID.FLEXIBLE:
            continue

        rhs = 0.0
        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            allowance = regulation.expectation.get_vessel_allowance(v, alg.idx)
            rhs += allowance * alg.multipliers[v]

        alg.regulation_rhs_flexibility[r] = rhs
