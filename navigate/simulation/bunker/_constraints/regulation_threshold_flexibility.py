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

        \sum_{v policed} n_v T_{r,v} - w_r <= R_r

    where T is a vessel's term of calculate_regulation_terms (see
    regulation_threshold_individual), n the number of vessels it represents, w the
    remedial units bought for the pool, and R the pooled threshold bound
    (update_regulation_rhs_flexibility). Vessels over their individual target are
    balanced by vessels under it; only the pooled excess is priced through the
    remedial variable.

    T is a variable of its own here, free and defined by a constraint per policed
    vessel:

        \sum_t \phi_t k_t z_t - T_{r,v} = 0

    so that the selection among equally cheap solutions can hold the term of a
    vessel by the bounds of one variable (_rules.py).

    The rows are rewritten in place each build: every variable the definition of
    a term has ever held is written again, at weight 0 where its jurisdiction
    fraction is 0. The term of a vessel that left the pool is removed with its
    definition (_cleanup.py).

    The flexibility market reads the pooled non-compliance against w within a noise
    bound derived from the form of these rows (flexibility_market.py); a change to
    their form changes that bound.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    rows = alg.regulation_threshold_flexibility
    definitions = alg.pooled_term_definition
    model = alg.model

    for r, rhs in alg.regulation_rhs_flexibility.items():
        constraint = get_constraint(
            alg, rows, r, "<=", "regulation_threshold_flexibility", priced=True
        )
        model.set_rhs(constraint, rhs)
        model.set_coefficient(constraint, alg.remedial_factor_flexibility[r], -1.0)

    for key, pooled_term in alg.pooled_term.items():
        r, v = key
        vessel = alg.vessels[v]
        regulation = alg.regulations[r]

        terms, emissions, energy = calculate_regulation_terms(alg, vessel, regulation)

        # kept for the selection rules and the transfer of the regulation solution
        alg.regulation_emission_terms[key] = emissions
        alg.regulation_energy_terms[key] = energy

        definition = get_constraint(
            alg, definitions, key, "==", "pooled_term_definition"
        )

        for variable, weight in terms:
            model.set_coefficient(definition, variable, weight)

        model.set_coefficient(definition, pooled_term, -1.0)
        model.set_coefficient(rows[r], pooled_term, alg.counts[v])


def is_pooled(alg: BunkerAlgorithm, regulation_name: str, vessel_name: str) -> bool:
    """
    Check whether a regulation of the LP pools a vessel of the LP.

    Parameters
    ----------
    alg
        The algorithm instance.
    regulation_name
        Name of the regulation.
    vessel_name
        Name of the vessel.

    Returns
    -------
    bool
        True if the regulation is active and FLEXIBLE, the vessel is in the LP and
        the regulation polices it.
    """
    if regulation_name not in alg.regulation_rhs_flexibility:
        return False

    if vessel_name not in alg.vessels:
        return False

    return alg.regulations[regulation_name].vessel_is_policed(vessel_name)


def update_regulation_rhs_flexibility(alg: BunkerAlgorithm) -> None:
    """
    Update the pooled right-hand sides of FLEXIBLE regulations.

    The pool sums the allowances of the policed vessels, weighted by their counts.

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

            allowance = regulation.expectation.vessel_allowance[v][alg.idx]
            rhs += allowance * alg.counts[v]

        alg.regulation_rhs_flexibility[r] = rhs
