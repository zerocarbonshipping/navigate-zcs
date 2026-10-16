# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the constraints that fuel spend and shore power cover each energy demand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import EnergyDemandID
from navigate.simulation.bunker._build import get_constraint

if TYPE_CHECKING:
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
    v = vessel.name
    expectation = vessel.expectation
    route = vessel.route
    leg_idx = route.get_legs()
    port_idx = range(route.get_number_of_ports())

    demands_sea = expectation.get_energy_sea_leg(idx=alg.idx)
    demands_port = expectation.get_energy_port(idx=alg.idx)

    # at sea all three demands are served
    _update_sea_energy_conservation(
        alg, vessel, EnergyDemandID.PROPULSION, demands_sea, leg_idx
    )
    _update_sea_energy_conservation(
        alg, vessel, EnergyDemandID.ELECTRICAL, demands_sea, leg_idx
    )
    _update_sea_energy_conservation(
        alg, vessel, EnergyDemandID.HEAT, demands_sea, leg_idx
    )

    # in port there is no propulsion demand
    _update_port_energy_conservation(
        alg, vessel, EnergyDemandID.ELECTRICAL, demands_port, port_idx
    )

    # the shore-power variables join the electrical port rows created just above
    change_coefficient = alg.model.chgCoeff
    for p in port_idx:
        if (v, p) in alg.shore_power:
            constraint = alg.energy_conservation_port[(v, p, EnergyDemandID.ELECTRICAL)]
            change_coefficient(constraint, alg.shore_power[v, p], 1.0)

    _update_port_energy_conservation(
        alg, vessel, EnergyDemandID.HEAT, demands_port, port_idx
    )


def _update_sea_energy_conservation(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    energy_type: EnergyDemandID,
    demands: dict[EnergyDemandID, list[FloatLike]],
    leg_idx: tuple[tuple[int, int], ...],
) -> None:
    """
    Create or update the sea energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    energy_type
        Energy demand the rows conserve.
    demands
        Sea energy demands per type, in GJ; one value per leg.
    leg_idx
        Leg indices of the vessel's route.
    """
    v = vessel.name
    expectation = vessel.expectation
    converter = vessel.power_system.get_converter_by_energy_type(energy_type)
    c = converter.name
    efficiency = converter.efficiency.get()
    demand = demands[energy_type]
    fuels = alg.fuels_per_converter[(v, c)]
    spend_sea = alg.spend_sea
    change_coefficient = alg.model.chgCoeff

    for leg, (port_start, port_end) in enumerate(leg_idx):
        key = (v, port_start, port_end, energy_type)

        constraint = get_constraint(
            alg, alg.energy_conservation_sea, key, "==", "energy_conservation_at_sea"
        )
        constraint.rhs = float(demand[leg])

        for f in fuels:
            change_coefficient(
                constraint,
                spend_sea[v, c, f, port_start, port_end],
                efficiency * expectation.get_effective_lhv(c, f),
            )


def _update_port_energy_conservation(
    alg: BunkerAlgorithm,
    vessel: Vessel,
    energy_type: EnergyDemandID,
    demands: dict[EnergyDemandID, list[FloatLike]],
    port_idx: range,
) -> None:
    """
    Create or update the port energy-conservation rows of one energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel whose rows are updated.
    energy_type
        Energy demand the rows conserve.
    demands
        Port energy demands per type, in GJ; one value per port.
    port_idx
        Port indices of the vessel's route.
    """
    v = vessel.name
    expectation = vessel.expectation
    converter = vessel.power_system.get_converter_by_energy_type(energy_type)
    c = converter.name
    efficiency = converter.efficiency.get()
    demand = demands[energy_type]
    fuels = alg.fuels_per_converter[(v, c)]
    spend_port = alg.spend_port
    change_coefficient = alg.model.chgCoeff

    for p in port_idx:
        key = (v, p, energy_type)

        constraint = get_constraint(
            alg, alg.energy_conservation_port, key, "==", "energy_conservation_in_port"
        )
        constraint.rhs = float(demand[p])

        for f in fuels:
            change_coefficient(
                constraint,
                spend_port[v, c, f, p],
                efficiency * expectation.get_effective_lhv(c, f),
            )
