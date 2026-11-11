# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Transfer the energy prices and demands of the energy-conservation rows."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import BunkerScopeID

if TYPE_CHECKING:
    from navigate.simulation.bunker._solver import Constraint
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def transfer_dual_solution(alg: BunkerAlgorithm) -> None:
    """
    Transfer the energy prices and right-hand sides of the energy-conservation rows.

    The objective scales each vessel's terms by its number of vessels, so the energy
    price divided by that number is the price per vessel; the right-hand side is
    already per vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    if alg.scope != BunkerScopeID.EXPECTED:
        return

    idx = alg.idx

    # the sea rows are keyed by a leg's stops, the expectation by its route position
    leg_positions: dict[str, dict[tuple[int, int], int]] = {}

    for v, vessel in alg.vessels.items():
        legs = vessel.route.get_legs()
        leg_positions[v] = {(i, e): leg for leg, (i, e) in enumerate(legs)}

    for (v, i, e, demand_type), constraint in alg.energy_conservation_sea.items():
        expectation = alg.vessels[v].expectation
        leg = leg_positions[v][i, e]
        pi = _calculate_energy_price(alg, constraint) / alg.multipliers[v]
        rhs = alg.model.rhs(constraint)

        expectation.set_energy_conservation_pi_sea(demand_type, leg, idx, pi)
        expectation.set_energy_conservation_rhs_sea(demand_type, leg, idx, rhs)

    for (v, p, demand_type), constraint in alg.energy_conservation_port.items():
        expectation = alg.vessels[v].expectation
        pi = _calculate_energy_price(alg, constraint) / alg.multipliers[v]
        rhs = alg.model.rhs(constraint)

        expectation.set_energy_conservation_pi_port(demand_type, p, idx, pi)
        expectation.set_energy_conservation_rhs_port(demand_type, p, idx, rhs)


def _calculate_energy_price(alg: BunkerAlgorithm, constraint: Constraint) -> float:
    r"""
    Calculate the price of energy on an energy-conservation row.

    Where the row has a demand, the price is its dual value \pi_i. Where it has none,
    the demand cannot fall below zero, so every value up to the price at which the
    first unit would be supplied is a dual value, and the solver may report any one of
    them. The price is then that upper end:

        \pi_i + \min_j d_j / a_{ij}

    over the variables j able to supply the row, those with a positive coefficient
    a_{ij} and a positive upper bound, where d_j is the reduced cost of j. As
    d_j = c_j - \sum_r a_{rj} \pi_r, \pi_i cancels: the price is the cost c_j of the
    cheapest variable, net of the dual values of its other rows, per unit of energy.
    A row no variable can supply keeps its dual value.

    Parameters
    ----------
    alg
        The algorithm instance.
    constraint
        Energy-conservation row priced.

    Returns
    -------
    float
        Price of energy on the row, scaled by the vessel's multiplier as the objective
        is, in USD/GJ.
    """
    model = alg.model
    dual = model.dual(constraint)

    if model.rhs(constraint) > alg.options.solution_tolerance:
        return dual

    supply_costs: list[float] = []

    for variable, coefficient in model.terms(constraint):
        if coefficient > 0.0 and model.upper_bound(variable) > 0.0:
            supply_costs.append(model.reduced_cost(variable) / coefficient)

    return dual + min(supply_costs, default=0.0)
