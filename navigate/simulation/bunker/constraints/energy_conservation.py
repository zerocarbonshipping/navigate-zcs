# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the constraints that fuel spend and shore power cover each energy demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID
from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.vessel import Vessel
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.util.types_ import FloatLike


def update_energy_conservation_constraints(
    alg: BunkerAlgorithm, vessel: Vessel
) -> None:
    r"""
    Add the constraints that converter fuel spend covers each energy demand.

    Each energy demand is served by its own converter c: propulsion, electrical,
    and heat at sea; electrical and heat in port. For each demand d and leg (i, e)
    or port p (vessel index omitted):

        \eta_c \sum_{f in fuels(c)} \lambda_{c,f} x_{c,f,i,e} = E_{d,i,e}
        \eta_c \sum_{f in fuels(c)} \lambda_{c,f} y_{c,f,p}
        + s_p [d = electrical] = E_{d,p}

    where \eta is the converter efficiency, \lambda the effective lower heating
    value in GJ/t, x and y the annual fuel mass spend at sea and in port, s the
    annual shore power in GJ, and E the annual energy demand in GJ. Converts fuel
    mass to delivered energy and pins it to the demand; shore power substitutes
    fuel for the electrical demand in port.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """
    expectation = vessel.expectation
    route = vessel.route

    legs = route.get_legs()
    stops = range(route.get_number_of_ports())

    demands_sea = expectation.get_energy_sea_leg(idx=alg.idx)
    demands_port = expectation.get_energy_port(idx=alg.idx)

    for demand_type in EnergyDemandID:
        _update_sea_rows(alg, vessel, demand_type, demands_sea[demand_type], legs)

    for demand_type in PORT_ENERGY_DEMANDS:
        _update_port_rows(alg, vessel, demand_type, demands_port[demand_type], stops)


def _update_sea_rows(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    demand_type: EnergyDemandID,
    demand: list[FloatLike],
    legs: tuple[tuple[int, int], ...],
) -> None:
    """
    Create or update the sea energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    demand_type
        Energy demand the rows conserve.
    demand
        Sea energy demand per leg, in GJ.
    legs
        Origin and destination stop indices of each leg of the vessel's route.
    """
    v = vessel.name
    converter = vessel.get_converter_by_energy_type(demand_type)
    c = converter.name
    energy_per_ton = _calculate_energy_per_ton(vessel, converter)

    rows = alg.energy_conservation_sea
    spend_sea = alg.spend_sea
    change_coefficient = alg.model.chgCoeff

    for leg, (i, e) in enumerate(legs):
        key = (v, i, e, demand_type)
        constraint = get_constraint(alg, rows, key, "==", "energy_conservation_at_sea")
        constraint.rhs = float(demand[leg])

        for f, coefficient in energy_per_ton.items():
            change_coefficient(constraint, spend_sea[v, c, f, i, e], coefficient)


def _update_port_rows(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    demand_type: EnergyDemandID,
    demand: list[FloatLike],
    stops: range,
) -> None:
    """
    Create or update the port energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    demand_type
        Energy demand the rows conserve.
    demand
        Port energy demand per stop, in GJ.
    stops
        Stop indices of the vessel's route.
    """
    v = vessel.name
    converter = vessel.get_converter_by_energy_type(demand_type)
    c = converter.name
    energy_per_ton = _calculate_energy_per_ton(vessel, converter)

    rows = alg.energy_conservation_port
    spend_port = alg.spend_port
    shore_power = alg.shore_power
    change_coefficient = alg.model.chgCoeff

    for p in stops:
        key = (v, p, demand_type)
        constraint = get_constraint(alg, rows, key, "==", "energy_conservation_in_port")
        constraint.rhs = float(demand[p])

        for f, coefficient in energy_per_ton.items():
            change_coefficient(constraint, spend_port[v, c, f, p], coefficient)

        if demand_type == EnergyDemandID.ELECTRICAL and (v, p) in shore_power:
            change_coefficient(constraint, shore_power[v, p], 1.0)


def _calculate_energy_per_ton(vessel: Vessel, converter: Converter) -> dict[str, float]:
    """
    Calculate the energy a converter delivers per ton of each of its fuels.

    Parameters
    ----------
    vessel
        Vessel the converter belongs to.
    converter
        Converter whose fuels are converted.

    Returns
    -------
    dict[str, float]
        Efficiency times effective lower heating value per fuel name, in GJ/t.
    """
    c = converter.name
    efficiency = converter.efficiency.get()
    lhv = vessel.expectation.get_effective_lhv
    fuels = vessel.fuels_per_converter[c]

    return {f: efficiency * lhv(c, f) for f in fuels}
