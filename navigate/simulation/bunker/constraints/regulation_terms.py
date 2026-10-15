# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Build the regulated expressions and right-hand sides of regulation constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import navigate.core.enum_ as enum_
import navigate.simulation.bunker.solver as gp
from navigate.core.enum_ import RegulationMeasureID
from navigate.simulation.bunker.utils import get_converters, get_port_converters
from navigate.simulation.policy import (
    calculate_cargo_miles_in_policy_jurisdiction,
    calculate_nominal_cargo_miles_in_policy_jurisdiction,
    leg_jurisdiction_fraction,
)
from navigate.util import TON_TO_GRAM

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
        M = \sum_t \phi_t e_t z_t    (emissions, reporting only)
        Q = \sum_t \phi_t \lambda_t z_t    (energy, reporting only)

    where z is a spend or shore-power variable, \phi its jurisdiction fraction
    (intra at a regulated port and 0 at any other, for port spend and shore
    power; intra/inter/extra for sea legs by their ports' membership), k its
    regulation spend coefficient, e its emission factor, and \lambda its
    effective lower heating value (1 for shore power, already in GJ). T enters
    the threshold constraints; M and Q are stored for reporting.

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
    expectation = vessel.expectation

    coefficients = alg.regulation_spend_coefficient
    emission_factors = alg.regulation_emission_factor
    shore_power_coefficients = alg.shore_power_regulation_coefficient
    shore_power_emission_factors = alg.shore_power_regulation_emission_factor

    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    fuels_per_converter = alg.fuels_per_converter

    route = vessel.route
    ports = route.ports
    jurisdiction = regulation.jurisdiction

    intra_fraction = regulation.intra_fraction.get(alg.time)
    inter_fraction = regulation.inter_fraction.get(alg.time)
    extra_fraction = regulation.extra_fraction.get(alg.time)

    # a port inside the jurisdiction is intra-jurisdiction, one outside unregulated
    port_fractions = [intra_fraction if port in jurisdiction else 0.0 for port in ports]

    terms: list[_Term] = []

    # in ports
    for p, fraction in enumerate(port_fractions):
        terms.extend(
            _Term(
                alg.spend_port[v, c, f, p],
                fraction * coefficients[(v, c, f, r)],
                fraction * emission_factors[(v, c, f, r)],
                fraction * expectation.get_effective_lhv(c, f),
            )
            for c in port_converters
            for f in fuels_per_converter[v, c]
        )

    # at sea, weighted per leg by its ports' jurisdiction membership
    for port_start, port_end in route.get_legs():
        fraction = leg_jurisdiction_fraction(
            ports[port_start],
            ports[port_end],
            jurisdiction,
            intra_fraction,
            inter_fraction,
            extra_fraction,
        )

        terms.extend(
            _Term(
                alg.spend_sea[v, c, f, port_start, port_end],
                fraction * coefficients[(v, c, f, r)],
                fraction * emission_factors[(v, c, f, r)],
                fraction * expectation.get_effective_lhv(c, f),
            )
            for c in converters
            for f in fuels_per_converter[v, c]
        )

    # shore power, at the ports where the vessel can connect
    for p, fraction in enumerate(port_fractions):
        if (v, p, r) not in shore_power_coefficients:
            continue

        terms.append(
            _Term(
                alg.shore_power[v, p],
                fraction * shore_power_coefficients[(v, p, r)],
                fraction * shore_power_emission_factors[(v, p, r)],
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


def get_regulation_vessel_threshold(
    alg: BunkerAlgorithm, regulation: Regulation, v: str
) -> float:
    """
    Get a vessel's threshold under a regulation at the current time-step.

    The thresholds are evaluated once per build in
    ``calculate_regulation_coefficients``; non-policed vessels carry zero.

    Parameters
    ----------
    alg
        The algorithm instance.
    regulation
        Regulation being considered.
    v
        Vessel name.

    Returns
    -------
    float
        Threshold of the vessel, in the unit of the regulation's threshold.
    """
    return alg.regulation_vessel_threshold[(regulation.name, v)]


def get_regulation_vessel_rhs(
    alg: BunkerAlgorithm, regulation: Regulation, v: str
) -> tuple[float, float]:
    """
    Calculate a vessel's threshold right-hand side and measure under a regulation.

    Parameters
    ----------
    alg
        The algorithm instance.
    regulation
        Regulation being considered.
    v
        Vessel name.

    Returns
    -------
    tuple[float, float]
        Right-hand side of the vessel's threshold constraint, and the vessel's
        measure: 1 for ABSOLUTE, 0 for INTENSITY, and the capacity-scaled cargo
        miles in the jurisdiction for the transport measures.
    """
    vessel = alg.vessels[v]
    threshold = get_regulation_vessel_threshold(alg, regulation, v)

    measure = regulation.measure

    if measure == RegulationMeasureID.ABSOLUTE:
        vessel_measure = 1.0
        rhs = threshold

    elif measure == RegulationMeasureID.INTENSITY:
        # the energy of an intensity regulation depends on the bunker solution, so
        # its threshold sits inside the spend coefficient and the rhs is zero
        vessel_measure = 0.0
        rhs = 0.0

    elif measure == RegulationMeasureID.TRANSPORT:
        vessel_measure = calculate_cargo_miles_in_policy_jurisdiction(
            regulation, vessel, alg.time, alg.idx
        )
        vessel_measure *= regulation.expectation.get_vessel_capacity(
            v, alg.idx
        ) / vessel.nominal_capacity.get(alg.time)
        vessel_measure /= TON_TO_GRAM
        rhs = threshold * vessel_measure

    elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:
        vessel_measure = calculate_nominal_cargo_miles_in_policy_jurisdiction(
            regulation, vessel, alg.time, alg.idx
        )
        vessel_measure *= regulation.expectation.get_vessel_capacity(
            v, alg.idx
        ) / vessel.nominal_capacity.get(alg.time)
        vessel_measure /= TON_TO_GRAM
        rhs = threshold * vessel_measure

    else:
        raise ValueError("Bug in code, Regulation 'Measure' not defined correctly.")

    return rhs, vessel_measure


def update_regulation_individual_rhs(alg: BunkerAlgorithm) -> None:
    """
    Update the per-vessel right-hand sides and measures of INDIVIDUAL regulations.

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

            rhs, vessel_measure = get_regulation_vessel_rhs(alg, regulation, v)
            alg.regulation_measure[(r, v)] = vessel_measure
            alg.regulation_rhs_individual[(r, v)] = rhs


def update_regulation_flexibility_rhs(alg: BunkerAlgorithm) -> None:
    """
    Update the pooled right-hand sides and vessel measures of FLEXIBLE regulations.

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
            if regulation.vessel_is_policed(v):
                vessel_rhs, vessel_measure = get_regulation_vessel_rhs(
                    alg, regulation, v
                )
                rhs += vessel_rhs * alg.multipliers[v]

                alg.regulation_measure[(r, v)] = vessel_measure
                alg.regulation_rhs_flexibility[(r, v)] = vessel_rhs

        alg.regulation_total_rhs_flexibility[r] = rhs
