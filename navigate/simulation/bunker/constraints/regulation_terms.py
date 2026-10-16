# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Build the regulated expressions and right-hand sides of regulation constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import navigate.core.enum_ as enum_
import navigate.simulation.bunker.solver as gp
from navigate.simulation.bunker.utils import get_port_converters

if TYPE_CHECKING:
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


class _Term(NamedTuple):
    """A regulated variable with its constraint, emission and energy weights."""

    variable: gp.Var
    weight: float
    emission: float
    energy: float


def calculate_regulation_terms(
    alg: BunkerAlgorithm, vessel: Vessel, regulation: Regulation
) -> tuple[list[tuple[gp.Var, float]], gp.LinExpr, gp.LinExpr]:
    r"""
    Calculate the three regulated terms of a vessel under a regulation.

    Over every variable the regulation can weigh for the vessel -- port spend and
    shore power at each port, and sea spend on each leg -- the three terms share
    one variable list and differ only in their weights:

        T = \sum_t \phi_t k_t z_t    (constraint term)
        M = \sum_t \phi_t e_t z_t    (emissions)
        Q = \sum_t \phi_t \lambda_t z_t    (energy)

    where z is a spend or shore-power variable, \phi the regulation's jurisdiction
    fraction of its port or leg and e its emission coefficient, both read from the
    regulation's expectation, k its regulation spend coefficient, and \lambda its
    effective lower heating value (1 for shore power, already in GJ). T enters
    the threshold constraints; M and Q are evaluated at the solution, for the
    threshold adjustment and for the regulation's compliance and flexibility market.

    A variable whose fraction is 0 stays in the list at weight 0, so between
    builds the list only grows, as the vessel's variables do.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which regulatory impact is calculated.
    regulation
        Regulation being considered.

    Returns
    -------
    tuple[list[tuple[gp.Var, float]], gp.LinExpr, gp.LinExpr]
        T as each variable with its weight, a variable appearing once as each is
        keyed by a distinct converter, fuel and port or leg; then M and Q.
    """
    v = vessel.name
    r = regulation.name
    idx = alg.idx
    expectation = regulation.expectation
    vessel_expectation = vessel.expectation

    coefficients = alg.regulation_spend_coefficient
    shore_power_coefficients = alg.shore_power_regulation_coefficient

    port_converters = get_port_converters(vessel)
    fuels_per_converter = vessel.fuels_per_converter

    route = vessel.route

    port_fractions: list[float] = []
    for port in route.ports:
        port_fractions.append(expectation.get_port_fraction(port.name, idx))

    terms: list[_Term] = []

    # in ports
    for p, fraction in enumerate(port_fractions):
        terms.extend(
            _Term(
                alg.spend_port[v, c, f, p],
                fraction * coefficients[(v, c, f, r)],
                fraction * expectation.get_emission_coefficient((v, c, f), idx),
                fraction * vessel_expectation.get_effective_lhv(c, f),
            )
            for c in port_converters
            for f in fuels_per_converter[c]
        )

    # at sea
    legs = zip(route.get_legs(), route.get_leg_keys(), strict=True)
    for (port_start, port_end), leg in legs:
        fraction = float(expectation.get_leg_fraction(leg, idx))

        terms.extend(
            _Term(
                alg.spend_sea[v, c, f, port_start, port_end],
                fraction * coefficients[(v, c, f, r)],
                fraction * expectation.get_emission_coefficient((v, c, f), idx),
                fraction * vessel_expectation.get_effective_lhv(c, f),
            )
            for c, burned in fuels_per_converter.items()
            for f in burned
        )

    # shore power, at the ports where the vessel can connect
    for p, (port, fraction) in enumerate(zip(route.ports, port_fractions, strict=True)):
        if (v, p, r) not in shore_power_coefficients:
            continue

        emission = expectation.get_shore_power_emission_coefficient(port.name, idx)

        terms.append(
            _Term(
                alg.shore_power[v, p],
                fraction * shore_power_coefficients[(v, p, r)],
                fraction * emission,
                fraction,
            )
        )

    variables = [term.variable for term in terms]
    emission_weights = [term.emission for term in terms]
    energy_weights = [term.energy for term in terms]

    constraint_terms = [(term.variable, term.weight) for term in terms]
    emissions = gp.create_linear_expression(emission_weights, variables)
    energy = gp.create_linear_expression(energy_weights, variables)

    return constraint_terms, emissions, energy


def update_regulation_individual_rhs(alg: BunkerAlgorithm) -> None:
    """
    Update the per-vessel right-hand sides of INDIVIDUAL regulations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, regulation in alg.active_regulations.items():
        if regulation.scheme != enum_.RegulationSchemeID.INDIVIDUAL:
            continue

        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            allowance = regulation.expectation.get_vessel_allowance(v, alg.idx)
            alg.regulation_rhs_individual[(r, v)] = allowance


def update_regulation_flexibility_rhs(alg: BunkerAlgorithm) -> None:
    """
    Update the pooled right-hand sides of FLEXIBLE regulations.

    The pool sums the allowances of the policed vessels, weighted by multipliers.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for r, regulation in alg.active_regulations.items():
        if regulation.scheme != enum_.RegulationSchemeID.FLEXIBLE:
            continue

        rhs = 0.0
        for v in alg.vessels:
            if not regulation.vessel_is_policed(v):
                continue

            allowance = regulation.expectation.get_vessel_allowance(v, alg.idx)
            rhs += allowance * alg.multipliers[v]

        alg.regulation_total_rhs_flexibility[r] = rhs
