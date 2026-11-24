# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the regulation results of the bunkering LP to the expectations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._solver import evaluate

if TYPE_CHECKING:
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_regulation_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the LP solution of each active regulation to its expectation.

    Per policed vessel the regulated emissions and energy, and under INDIVIDUAL its
    remedial units; per FLEXIBLE regulation the pooled remedial units and the shadow
    price of the pooled threshold: the cost of a unit of emissions, set by the remedial
    cost or by the cheapest compliant fuel available at scale.

    Remedial units below the solution tolerance are written as none, as the other
    transfers drop a mass or an energy below it: of two solutions of one LP, one
    holds them at zero and another at a rounding residual, and the policy takes a
    regulation with any remedial units as not complied with.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    idx = alg.idx
    tolerance = alg.options.solution_tolerance

    for r, v in alg.regulation_emission_terms:
        expectation = alg.regulations[r].expectation
        emissions = evaluate(alg.model, alg.regulation_emission_terms[r, v])
        energy = evaluate(alg.model, alg.regulation_energy_terms[r, v])

        expectation.vessel_emissions[v][idx] = emissions
        expectation.vessel_energy[v][idx] = energy

    for (r, v), remedial_factor in alg.remedial_factor_individual.items():
        expectation = alg.regulations[r].expectation
        units = alg.model.value(remedial_factor)

        expectation.vessel_remedial_units[v][idx] = _drop_residual(units, tolerance)

    for r, remedial_factor in alg.remedial_factor_flexibility.items():
        expectation = alg.regulations[r].expectation
        constraint = alg.regulation_threshold_flexibility[r]
        units = alg.model.value(remedial_factor)

        expectation.pooled_remedial_units[idx] = _drop_residual(units, tolerance)
        expectation.pooled_shadow_price[idx] = -alg.model.dual(constraint)


def _drop_residual(units: float, tolerance: float) -> float:
    """Return remedial units of the LP solution, as none where below the tolerance."""
    return 0.0 if units < tolerance else units
