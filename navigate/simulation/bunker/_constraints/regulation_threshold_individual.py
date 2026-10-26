# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Update the per-vessel threshold constraints of INDIVIDUAL-scheme regulations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import RegulationSchemeID
from navigate.simulation.bunker._build import get_constraint
from navigate.simulation.bunker._constraints._regulation_terms import (
    calculate_regulation_terms,
)

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_regulation_threshold_individual_constraints(alg: BunkerAlgorithm) -> None:
    r"""
    Update the constraints that hold each policed vessel to its INDIVIDUAL threshold.

    For each regulation r and policed vessel v:

        E_{r,v} - w_{r,v} <= R_{r,v}

    where E is T of calculate_regulation_terms, the vessel's fuel spend and shore
    power weighted by regulation coefficients and jurisdiction fractions (for an
    intensity measure the coefficients fold in the threshold), w the remedial
    units bought for the vessel, and R the threshold-derived bound
    (update_regulation_rhs_individual). The remedial variable keeps the model
    feasible when the cap cannot be met; its objective cost prices non-compliance.

    The row is rewritten in place each build: every variable it has ever held is
    written again, at weight 0 where its jurisdiction fraction is 0.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    rows = alg.regulation_threshold_individual
    remedial_factor_individual = alg.remedial_factor_individual
    model = alg.model

    for key, rhs in alg.regulation_rhs_individual.items():
        r, v = key
        vessel = alg.vessels[v]
        regulation = alg.regulations[r]

        terms, emissions, energy = calculate_regulation_terms(alg, vessel, regulation)

        # kept for transferring the regulation solution after the solve
        alg.regulation_emission_terms[key] = emissions
        alg.regulation_energy_terms[key] = energy

        constraint = get_constraint(
            alg, rows, key, "<=", "regulation_threshold_individual"
        )
        model.set_rhs(constraint, rhs)

        for variable, weight in terms:
            model.set_coefficient(constraint, variable, weight)

        model.set_coefficient(constraint, remedial_factor_individual[key], -1.0)


def update_regulation_rhs_individual(alg: BunkerAlgorithm) -> None:
    """
    Update the per-vessel right-hand sides of INDIVIDUAL regulations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, regulation in alg.active_regulations.items():
        if regulation.scheme != RegulationSchemeID.INDIVIDUAL:
            continue

        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            allowance = regulation.expectation.get_vessel_allowance(v, alg.idx)
            alg.regulation_rhs_individual[r, v] = allowance
