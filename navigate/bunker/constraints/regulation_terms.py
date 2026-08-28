# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.regulation import Regulation
    from navigate.core.nodes.vessel import Vessel

import navigate.bunker.solver as gp
import navigate.core.enum_ as enum_
from navigate.bunker.utils import get_converters, get_port_converters
from navigate.core.enum_ import RegulationMeasureID
from navigate.core.unit import TON_TO_GRAM
from navigate.policy import (
    calculate_cargo_miles_in_policy_jurisdiction,
    calculate_nominal_cargo_miles_in_policy_jurisdiction,
    leg_jurisdiction_fraction,
)


def calculate_regulation_emission_term(alg: BunkerAlgorithm, vessel: Vessel, regulation: Regulation) -> tuple:
    r"""
    Calculate the three regulated linear expressions of a vessel under a regulation.

    Over the vessel's regulated spend -- port spend, sea spend, and shore power --
    the three expressions share one term list and differ only in their weights:

        T = \sum_t \phi_t k_t z_t    (constraint term)
        M = \sum_t \phi_t e_t z_t    (emissions, reporting only)
        Q = \sum_t \phi_t \lambda_t z_t    (energy, reporting only)

    where z is a spend or shore-power variable, \phi its jurisdiction fraction
    (intra in port and for shore power; intra/inter/extra for sea legs by their
    ports' membership), k its regulation spend coefficient, e its emission
    factor, and \lambda its effective lower heating value (1 for shore power,
    already in GJ). T enters the threshold constraints; M and Q are stored for
    reporting.

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
    tuple[LinExpr, LinExpr, LinExpr]
        Constraint expression, emission expression, and energy expression.
    """

    v = vessel.name
    r = regulation.name

    # extract the various coefficients needed
    coefficients = alg.regulation_spend_coefficient
    emission_factors = alg.regulation_emission_factor
    effective_lhv = alg.effective_lhv

    # extract the converters and fuels of the vessel
    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    fuels_per_converter = alg.fuels_per_converter

    # extract route information for the regulations
    route = vessel.route
    ports = route.ports

    intra_fraction = regulation.intra_fraction.get(alg.time)
    inter_fraction = regulation.inter_fraction.get(alg.time)
    extra_fraction = regulation.extra_fraction.get(alg.time)

    jurisdiction = regulation.jurisdiction
    regulated_ports = [p for p in range(len(ports)) if ports[p] in jurisdiction]

    # in ports (always intra-jurisdiction)
    port_terms = []
    if intra_fraction > 0.:

        port_terms = [((intra_fraction * coefficients[(v, c, f, r)],
                        intra_fraction * emission_factors[(v, c, f, r)],
                        intra_fraction * effective_lhv[(v, c, f)]),
                       alg.spend_port[v, c, f, p])

                      for c in port_converters
                      for f in fuels_per_converter[v, c]
                      for p in regulated_ports]

    # at sea, weighted per leg by its ports' jurisdiction membership
    sea_terms = []
    for (port_start, port_end) in route.get_leg_indices():

        fraction = leg_jurisdiction_fraction(ports[port_start], ports[port_end], jurisdiction,
                                             intra_fraction, inter_fraction, extra_fraction)

        if fraction > 0.:

            sea_terms.extend([((fraction * coefficients[(v, c, f, r)],
                                fraction * emission_factors[(v, c, f, r)],
                                fraction * effective_lhv[(v, c, f)]),
                               alg.spend_sea[v, c, f, port_start, port_end])

                              for c in converters
                              for f in fuels_per_converter[v, c]])

    # shore power at regulated ports (always intra-jurisdiction)
    shore_power_terms = []
    if intra_fraction > 0.:
        shore_power_emission_factors = alg.shore_power_regulation_emission_factor
        shore_power_coefficients = alg.shore_power_regulation_coefficient

        for p in regulated_ports:
            if (v, p, r) in shore_power_coefficients:
                shore_power_terms.append(((intra_fraction * shore_power_coefficients[(v, p, r)],
                                           intra_fraction * shore_power_emission_factors[(v, p, r)],
                                           intra_fraction * 1.0),
                                          alg.shore_power[v, p]))

    terms = port_terms + sea_terms + shore_power_terms

    if terms:

        weights, variables = zip(*terms)
        constraint_weights, emission_weights, energy_weights = zip(*weights)

        constraints = gp.LinExpr(constraint_weights, variables)
        emissions = gp.LinExpr(emission_weights, variables)
        energy = gp.LinExpr(energy_weights, variables)

    else:
        # no port or leg of the route is regulated
        constraints = gp.LinExpr()
        emissions = gp.LinExpr()
        energy = gp.LinExpr()

    return constraints, emissions, energy


def get_regulation_vessel_threshold(alg: BunkerAlgorithm, regulation: Regulation, v: str) -> float:
    """
    Get the regulation threshold for a vessel at the current algorithm time.

    The values are evaluated once per build in 'calculate_regulation_coefficients';
    non-policed vessels carry a threshold of zero.

    Parameters
    ----------
    alg
        The algorithm instance.
    regulation
        The regulation object.
    v
        Vessel name.

    Returns
    -------
    float
        The threshold value.
    """

    return alg.regulation_vessel_threshold[(regulation.name, v)]


def get_regulation_vessel_rhs(alg: BunkerAlgorithm, regulation: Regulation, v: str) -> tuple[float, float]:
    """
    Calculate the right-hand side (RHS) value for a regulation equation for a vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    regulation
        The regulation object containing the details and measure type.
    v
        The identifier of the vessel for which the RHS is calculated.

    Returns
    -------
    tuple[float, float]
        The computed RHS and measure value based on the provided regulation and vessel.
    """

    vessel = alg.vessels[v]
    threshold = get_regulation_vessel_threshold(alg, regulation, v)

    measure = regulation.measure

    if measure == RegulationMeasureID.ABSOLUTE:

        vessel_measure = 1.
        rhs = threshold

    elif measure == RegulationMeasureID.INTENSITY:

        # notice that the rhs of an intensity regulation is zero
        # because the threshold is moved inside the coefficient
        # since the energy is a function of the bunker solution
        vessel_measure = 0.
        rhs = 0.

    elif measure == RegulationMeasureID.TRANSPORT:

        vessel_measure = calculate_cargo_miles_in_policy_jurisdiction(regulation, vessel, alg.time, alg.idx)
        vessel_measure *= regulation.expectation.get_vessel_capacity(v, alg.idx) / vessel.nominal_capacity.get(alg.time)
        vessel_measure /= TON_TO_GRAM
        rhs = threshold * vessel_measure

    elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:

        vessel_measure = calculate_nominal_cargo_miles_in_policy_jurisdiction(regulation, vessel, alg.time, alg.idx)
        vessel_measure *= regulation.expectation.get_vessel_capacity(v, alg.idx) / vessel.nominal_capacity.get(alg.time)
        vessel_measure /= TON_TO_GRAM
        rhs = threshold * vessel_measure

    else:
        raise ValueError("Bug in code, Regulation 'Measure' not defined correctly.")

    return rhs, vessel_measure


def update_regulation_individual_rhs(alg: BunkerAlgorithm) -> None:
    """
    Updates the right-hand side values for individual regulations specific to each vessel.

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
    Updates the right-hand side (RHS) for regulations marked as flexible.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for r, regulation in alg.active_regulations.items():

        if regulation.scheme != enum_.RegulationSchemeID.FLEXIBLE:
            continue

        rhs = 0.
        for v in alg.vessels:

            if regulation.vessel_is_policed(v):

                vessel_rhs, vessel_measure = get_regulation_vessel_rhs(alg, regulation, v)
                rhs += vessel_rhs * alg.multipliers[v]

                alg.regulation_measure[(r, v)] = vessel_measure
                alg.regulation_rhs_flexibility[(r, v)] = vessel_rhs

        alg.regulation_total_rhs_flexibility[r] = rhs
