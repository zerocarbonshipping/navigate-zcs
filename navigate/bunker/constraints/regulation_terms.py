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
from navigate.bunker.utils import get_converter_fuels, get_converters, get_port_converters
from navigate.core.enum_ import RegulationMeasureID
from navigate.core.unit import TON_TO_GRAM
from navigate.policy import (
    calculate_cargo_miles_in_policy_jurisdiction,
    calculate_nominal_cargo_miles_in_policy_jurisdiction,
)


def calculate_regulation_emission_term(alg: BunkerAlgorithm, vessel: Vessel, regulation: Regulation) -> tuple:
    """
    Calculate the regulation emission term for a vessel under a given regulation.

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

    v = vessel.get_name()
    r = regulation.get_name()

    # extract the various coefficients needed
    coefficients = alg.regulation_spend_coefficient
    emission_factors = alg.regulation_emission_factor
    effective_lhv = alg.effective_lhv

    # extract the converters and fuels of the vessel
    converters = get_converters(vessel)
    port_converters = get_port_converters(vessel)
    converter_fuels = get_converter_fuels(vessel)

    # extract route information for the regulations
    route = vessel.route
    ports = route.ports

    intra_fraction = regulation.intra_fraction.get(alg.time)
    inter_fraction = regulation.inter_fraction.get(alg.time)
    extra_fraction = regulation.extra_fraction.get(alg.time)

    jurisdiction = regulation.jurisdiction
    regulated_ports = [p for p in range(len(ports)) if ports[p] in jurisdiction]

    # in ports
    terms = []
    if intra_fraction > 0.:

        terms = [((intra_fraction * coefficients[(v, c, f, r)],
                   intra_fraction * emission_factors[(v, c, f, r)],
                   intra_fraction * effective_lhv[(v, c, f)]),
                  alg.spend_port[v, c, f, p])

                 for c in port_converters
                 for f in converter_fuels[c]
                 for p in regulated_ports]

    # at sea
    for (pi, pe) in route.get_leg_indices():

        port_i = ports[pi]
        port_e = ports[pe]

        if (port_i in jurisdiction) and (port_e in jurisdiction):

            # intra jurisdiction legs
            fraction = intra_fraction

        elif (((port_i in jurisdiction) and (port_e not in jurisdiction))
              or ((port_i not in jurisdiction) and (port_e in jurisdiction))):

            # inter jurisdiction legs
            fraction = inter_fraction

        else:

            # extra jurisdiction legs
            fraction = extra_fraction

        if fraction > 0.:

            terms.extend([((fraction * coefficients[(v, c, f, r)],
                            fraction * emission_factors[(v, c, f, r)],
                            fraction * effective_lhv[(v, c, f)]),
                           alg.spend_sea[v, c, f, pi, pe])

                          for c in converters
                          for f in converter_fuels[c]])

    # shore power at regulated ports (always intra-jurisdiction)
    if intra_fraction > 0.:
        sp_reg_ef = alg.shore_power_regulation_ef
        sp_reg_coeff = alg.shore_power_regulation_coeff

        for p in regulated_ports:
            if (v, p, r) in sp_reg_coeff:
                terms.append(((intra_fraction * sp_reg_coeff[(v, p, r)],
                               intra_fraction * sp_reg_ef[(v, p, r)],
                               intra_fraction * 1.0),
                              alg.shore_power[v, p]))

    if terms:

        c, v = zip(*terms)
        c_coefficients, c_emissions, c_energy = zip(*c)

        constraints = gp.LinExpr(c_coefficients, v)
        emissions = gp.LinExpr(c_emissions, v)
        energy = gp.LinExpr(c_energy, v)

    else:
        # in case none of the ports in the
        # jurisdiction match the ports on the
        # vessels route, initialize an empty
        # expression
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

    return alg.regulation_vessel_threshold[(regulation.get_name(), v)]


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

        m = 1.
        rhs = threshold

    elif measure == RegulationMeasureID.INTENSITY:

        # notice that the rhs of an intensity regulation is zero
        # because the threshold is moved inside the coefficient
        # since the energy is a function of the bunker solution
        m = 0.
        rhs = 0.

    elif measure == RegulationMeasureID.TRANSPORT:

        m = calculate_cargo_miles_in_policy_jurisdiction(regulation, vessel, alg.time, alg.idx)
        m *= regulation.expectation.get_vessel_capacity(v, alg.idx) / vessel.nominal_capacity.get(alg.time)
        m /= TON_TO_GRAM
        rhs = threshold * m

    elif measure == RegulationMeasureID.TRANSPORT_NOMINAL:

        m = calculate_nominal_cargo_miles_in_policy_jurisdiction(regulation, vessel, alg.time, alg.idx)
        m *= regulation.expectation.get_vessel_capacity(v, alg.idx) / vessel.nominal_capacity.get(alg.time)
        m /= TON_TO_GRAM
        rhs = threshold * m

    else:
        raise ValueError("Bug in code, Regulation 'Measure' not defined correctly.")

    return rhs, m


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

            rhs, m = get_regulation_vessel_rhs(alg, regulation, v)
            alg.regulation_measure[(r, v)] = m
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

                rhs_v, m_v = get_regulation_vessel_rhs(alg, regulation, v)
                rhs += rhs_v * alg.multipliers[v]

                alg.regulation_measure[(r, v)] = m_v
                alg.regulation_rhs_flexibility[(r, v)] = rhs_v

        alg.regulation_total_rhs_flexibility[r] = rhs
