# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.constraints._common import get_constraint
from navigate.core.enum_ import EnergyDemandTypeID


def update_energy_conservation_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that converter fuel spend covers each energy demand.

    Each energy demand is served by its own converter c: propulsion, electrical,
    and heat at sea; electrical and heat in port. For each demand d and leg (i, e)
    or port p (vessel index omitted):

        \eta_c \sum_{f in fuels(c)} \lambda_{c,f} x_{c,f,i,e} = E_{d,i,e}
        \eta_c \sum_{f in fuels(c)} \lambda_{c,f} y_{c,f,p} + s_p [d = electrical] = E_{d,p}

    where \eta is the converter efficiency, \lambda the effective lower heating
    value (GJ/t), x and y the annual fuel mass spend at sea and in port, s the
    annual shore power (GJ), and E the annual energy demand (GJ). Converts fuel
    mass to delivered energy and pins it to the demand; shore power substitutes
    fuel for the electrical demand in port.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are updated.
    """

    v = vessel.get_name()
    expectation = vessel.expectation
    power_system = vessel.power_system
    route = vessel.route
    leg_idx = route.get_leg_indices()
    port_idx = range(route.get_number_of_ports())

    demands_sea = expectation.get_regional_energy_sea(idx=alg.idx)
    demands_port = expectation.get_energy_port(idx=alg.idx)

    # at sea all three demands are served
    _update_sea_energy_conservation(alg, v, EnergyDemandTypeID.PROPULSION,
                                    power_system.propulsion, demands_sea, leg_idx)
    _update_sea_energy_conservation(alg, v, EnergyDemandTypeID.ELECTRICAL,
                                    power_system.electrical, demands_sea, leg_idx)
    _update_sea_energy_conservation(alg, v, EnergyDemandTypeID.HEAT,
                                    power_system.heat, demands_sea, leg_idx)

    # in port there is no propulsion demand
    _update_port_energy_conservation(alg, v, EnergyDemandTypeID.ELECTRICAL,
                                     power_system.electrical, demands_port, port_idx)

    # the shore-power variables join the electrical port rows created just above
    change_coefficient = alg.model.chgCoeff
    for p in port_idx:

        if (v, p) in alg.shore_power:
            constraint = alg.energy_conservation_port[(v, p, EnergyDemandTypeID.ELECTRICAL)]
            change_coefficient(constraint, alg.shore_power[v, p], 1.0)

    _update_port_energy_conservation(alg, v, EnergyDemandTypeID.HEAT,
                                     power_system.heat, demands_port, port_idx)


def _update_sea_energy_conservation(alg: BunkerAlgorithm,
                                    v: str,
                                    energy_type: EnergyDemandTypeID,
                                    converter: Converter,
                                    demands: dict,
                                    leg_idx: tuple
                                    ) -> None:
    """
    Create or update the sea energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Vessel name.
    energy_type
        Energy demand the rows conserve.
    converter
        Converter serving the demand.
    demands
        Sea energy demands per type; one value per leg.
    leg_idx
        Leg indices of the vessel's route.
    """

    c = converter.get_name()
    efficiency = converter.efficiency.get()
    demand = demands[energy_type]
    fuels = alg.fuels_per_converter[(v, c)]
    effective_lhv = alg.effective_lhv
    spend_sea = alg.spend_sea
    change_coefficient = alg.model.chgCoeff

    for leg, (port_start, port_end) in enumerate(leg_idx):

        key = (v, port_start, port_end, energy_type)

        constraint = get_constraint(alg, alg.energy_conservation_sea, key, "==", "energy_conservation_at_sea")
        constraint.rhs = demand[leg]

        for f in fuels:
            change_coefficient(constraint, spend_sea[v, c, f, port_start, port_end], efficiency * effective_lhv[(v, c, f)])


def _update_port_energy_conservation(alg: BunkerAlgorithm,
                                     v: str,
                                     energy_type: EnergyDemandTypeID,
                                     converter: Converter,
                                     demands: dict,
                                     port_idx: range
                                     ) -> None:
    """
    Create or update the port energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Vessel name.
    energy_type
        Energy demand the rows conserve.
    converter
        Converter serving the demand.
    demands
        Port energy demands per type; one value per port.
    port_idx
        Port indices of the vessel's route.
    """

    c = converter.get_name()
    efficiency = converter.efficiency.get()
    demand = demands[energy_type]
    fuels = alg.fuels_per_converter[(v, c)]
    effective_lhv = alg.effective_lhv
    spend_port = alg.spend_port
    change_coefficient = alg.model.chgCoeff

    for p in port_idx:

        key = (v, p, energy_type)

        constraint = get_constraint(alg, alg.energy_conservation_port, key, "==", "energy_conservation_in_port")
        constraint.rhs = demand[p]

        for f in fuels:
            change_coefficient(constraint, spend_port[v, c, f, p], efficiency * effective_lhv[(v, c, f)])
