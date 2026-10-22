# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Build the regulated expressions and right-hand sides of regulation constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import navigate.core.enum_ as enum_
import navigate.simulation.bunker.solver as gp
from navigate.simulation.bunker.utils import get_port_converters

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


class _Weights(NamedTuple):
    """The spend, emission and energy weights of a variable, before its fraction."""

    spend: float
    emission: float
    energy: float


class _Term(NamedTuple):
    """A regulated variable with its jurisdiction fraction and weights."""

    variable: gp.Var
    fraction: float
    weights: _Weights


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
    fraction of its port or leg, e its emission coefficient and k its spend
    coefficient, all read from the regulation's expectation, and \lambda its
    effective lower heating value (1 for shore power, already in GJ). T enters
    the threshold constraints; M and Q are evaluated at the solution, for the
    regulation's compliance and flexibility market.

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
    idx = alg.idx
    route = vessel.route
    ports = route.ports
    expectation = regulation.expectation

    port_converters = get_port_converters(vessel)
    fuels_per_converter = vessel.fuels_per_converter

    port_weights = _calculate_weights(vessel, regulation, port_converters, idx)
    sea_weights = _calculate_weights(vessel, regulation, fuels_per_converter, idx)
    port_fractions = [expectation.get_port_fraction(port.name, idx) for port in ports]

    terms: list[_Term] = []

    # in ports
    for p, fraction in enumerate(port_fractions):
        for (c, f), weights in port_weights.items():
            terms.append(_Term(alg.spend_port[v, c, f, p], fraction, weights))

    # at sea
    for (i, e), leg in zip(route.get_legs(), route.get_leg_keys(), strict=True):
        fraction = float(expectation.get_leg_fraction(leg, idx))

        for (c, f), weights in sea_weights.items():
            terms.append(_Term(alg.spend_sea[v, c, f, i, e], fraction, weights))

    # shore power, at the connections the regulations weigh
    for p, (port, fraction) in enumerate(zip(ports, port_fractions, strict=True)):
        if (v, p) not in alg.regulated_shore_power:
            continue

        spend = expectation.get_shore_power_spend_coefficient((v, port.name), idx)
        emission = expectation.get_shore_power_emission_coefficient(port.name, idx)
        weights = _Weights(spend, emission, 1.0)

        terms.append(_Term(alg.shore_power[v, p], fraction, weights))

    variables = [term.variable for term in terms]
    spends = [term.fraction * term.weights.spend for term in terms]
    emissions = [term.fraction * term.weights.emission for term in terms]
    energies = [term.fraction * term.weights.energy for term in terms]

    constraint_terms = list(zip(variables, spends, strict=True))
    emission_expression = gp.create_linear_expression(emissions, variables)
    energy_expression = gp.create_linear_expression(energies, variables)

    return constraint_terms, emission_expression, energy_expression


def _calculate_weights(
    vessel: Vessel, regulation: Regulation, converters: Iterable[str], idx: int
) -> dict[tuple[str, str], _Weights]:
    """
    Calculate the weights of each fuel of the given converters of a vessel.

    Parameters
    ----------
    vessel
        Vessel whose fuels are weighted.
    regulation
        Regulation whose coefficients weigh the fuels.
    converters
        Names of the converters whose fuels are weighted.
    idx
        Time index the coefficients are read at.

    Returns
    -------
    dict[tuple[str, str], _Weights]
        Spend and emission coefficient and effective lower heating value, in
        GJ/t, per converter and fuel name.
    """
    v = vessel.name
    expectation = regulation.expectation
    lhv = vessel.expectation.get_effective_lhv
    fuels_per_converter = vessel.fuels_per_converter

    weights: dict[tuple[str, str], _Weights] = {}

    for c in converters:
        for f in fuels_per_converter[c]:
            spend = expectation.get_spend_coefficient((v, c, f), idx)
            emission = expectation.get_emission_coefficient((v, c, f), idx)
            weights[c, f] = _Weights(spend, emission, lhv(c, f))

    return weights


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
            alg.regulation_rhs_individual[r, v] = allowance


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
