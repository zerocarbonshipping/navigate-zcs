# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the constraints that dual-fuel converters burn their minimum pilot-fuel share."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._build import get_constraint
from navigate.simulation.bunker.utils import get_converters, get_port_converters

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def update_pilot_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that dual-fuel converters burn enough pilot fuel.

    For each dual-fuel converter c and leg (i, e), and analogously per port p
    with the port spend y (vessel index omitted):

        (1 - \phi_c) \sum_{f in pilot(c)} \lambda_{c,f} x_{c,f,i,e}
            - \phi_c \sum_{f in main(c)} \lambda_{c,f} x_{c,f,i,e} >= 0

    i.e. the pilot fuels carry at least the fraction \phi of the converter's fuel
    energy, where \phi is the converter's minimum pilot fuel fraction and \lambda
    the effective lower heating value in GJ/t. Dual-fuel combustion needs a
    pilot-fuel share to ignite the main fuel. The propulsion converter gets no
    port rows: it serves no port energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are added.
    """
    route = vessel.route
    port_converters = get_port_converters(vessel)

    legs = route.get_legs()
    stops = range(route.get_number_of_ports())

    for c, converter in get_converters(vessel).items():
        if not converter.is_dual_fuel():
            continue

        coefficients = _calculate_pilot_coefficients(vessel, converter)
        _update_sea_rows(alg, vessel, c, coefficients, legs)

        # the propulsion converter serves no port energy demand
        if c in port_converters:
            _update_port_rows(alg, vessel, c, coefficients, stops)


def _update_sea_rows(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    c: str,
    coefficients: dict[str, float],
    legs: tuple[tuple[int, int], ...],
) -> None:
    """
    Create or update the sea pilot-fuel rows of one converter.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    c
        Converter name.
    coefficients
        Pilot-fuel coefficient of each fuel name, in GJ/t.
    legs
        Origin and destination stop indices of each leg of the vessel's route.
    """
    v = vessel.name
    rows = alg.pilot_fuel_sea
    spend_sea = alg.spend_sea
    change_coefficient = alg.model.chgCoeff

    for i, e in legs:
        key = (v, c, i, e)
        constraint = get_constraint(alg, rows, key, ">=", "pilot_fuel_at_sea")

        for f, coefficient in coefficients.items():
            change_coefficient(constraint, spend_sea[v, c, f, i, e], coefficient)


def _update_port_rows(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    c: str,
    coefficients: dict[str, float],
    stops: range,
) -> None:
    """
    Create or update the port pilot-fuel rows of one converter.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    c
        Converter name.
    coefficients
        Pilot-fuel coefficient of each fuel name, in GJ/t.
    stops
        Stop indices of the vessel's route.
    """
    v = vessel.name
    rows = alg.pilot_fuel_port
    spend_port = alg.spend_port
    change_coefficient = alg.model.chgCoeff

    for p in stops:
        key = (v, c, p)
        constraint = get_constraint(alg, rows, key, ">=", "pilot_fuel_in_port")

        for f, coefficient in coefficients.items():
            change_coefficient(constraint, spend_port[v, c, f, p], coefficient)


def _calculate_pilot_coefficients(
    vessel: Vessel, converter: Converter
) -> dict[str, float]:
    """
    Calculate the pilot-fuel coefficient of each usable fuel of a converter.

    Parameters
    ----------
    vessel
        Vessel the converter belongs to.
    converter
        Dual-fuel converter whose fuels are weighted.

    Returns
    -------
    dict[str, float]
        Effective lower heating value per fuel name, weighted by 1 - fraction for
        pilot fuels and by -fraction for main fuels, in GJ/t.
    """
    c = converter.name
    fraction = converter.minimum_pilot_fuel.get()
    lhv = vessel.expectation.get_effective_lhv
    fuels = vessel.fuels_per_converter[c]

    coefficients: dict[str, float] = {}

    for f, fuel in fuels.items():
        is_pilot = fuel.fuel_type in converter.pilot_fuel_types
        weight = 1.0 - fraction if is_pilot else -fraction
        coefficients[f] = weight * lhv(c, f)

    return coefficients
