# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel

from navigate.bunker.constraints._common import get_constraint
from navigate.bunker.utils import extract_times, get_converters, get_port_converters
from navigate.core.unit import DAY_TO_HOURS, MWH_TO_GJ


def update_power_capacity_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that installed converter power covers the fuel spend.

    For each converter c and leg (i, e) (vessel index omitted):

        \sum_{f in fuels(c)} \lambda_{c,f} x_{c,f,i,e} <= P_c t_{i,e} u / \eta_c

    and the same per port p with the port stay t_p and the port spend y. Here
    \lambda is the effective lower heating value (GJ/t), x and y the annual fuel
    mass spend, P the converter's power capacity (MW), t the annual time on the leg
    or in port (days), \eta the converter efficiency, and u the days-to-hours times
    MWh-to-GJ unit conversion. The fuel energy a converter takes in cannot exceed
    what its installed power can convert in the available time.
    # TODO: this constraint is redundant. Just check installed power vs speed-power curve
    # TODO: using LHV is inconsistent with electricity. Should be MWh to GJ unit conversion

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are added.
    """

    v = vessel.get_name()
    route = vessel.route

    time_sea, time_port = extract_times(vessel, alg.idx)
    effective_lhv = alg.effective_lhv
    spend_sea = alg.spend_sea
    spend_port = alg.spend_port
    chgCoeff = alg.model.chgCoeff
    fuels_per_converter = alg.fuels_per_converter
    leg_idx_v = route.get_leg_indices()
    port_idx_v = range(route.get_number_of_ports())

    # at sea
    for c, converter in get_converters(vessel).items():

        eff = converter.efficiency.get()
        power_cap = converter.power_capacity.get()

        for leg, (pi, pe) in enumerate(leg_idx_v):

            key = (v, c, pi, pe)

            constraint = get_constraint(alg, alg.power_capacity_sea, key, "<=", "power_capacity_at_sea")
            constraint.rhs = _power_capacity_rhs(time_sea[leg], eff, power_cap)

            for f in fuels_per_converter[v, c]:
                chgCoeff(constraint, spend_sea[v, c, f, pi, pe], effective_lhv[(v, c, f)])

    # in port (only converters with port energy demand)
    for c, converter in get_port_converters(vessel).items():

        eff = converter.efficiency.get()
        power_cap = converter.power_capacity.get()

        for p in port_idx_v:

            key = (v, c, p)

            constraint = get_constraint(alg, alg.power_capacity_port, key, "<=", "power_capacity_in_port")
            constraint.rhs = _power_capacity_rhs(time_port[p], eff, power_cap)

            for f in fuels_per_converter[v, c]:
                chgCoeff(constraint, spend_port[v, c, f, p], effective_lhv[(v, c, f)])


def _power_capacity_rhs(time: float, efficiency: float, power_capacity: float) -> float:
    """
    The maximum fuel energy (GJ) a converter can take in over an operating period.

    Parameters
    ----------
    time
        Operating time in the period (days).
    efficiency
        Efficiency of the converter.
    power_capacity
        Installed power of the converter (MW).

    Returns
    -------
    The maximum fuel energy (GJ).
    """

    return time / efficiency * (DAY_TO_HOURS * MWH_TO_GJ) * power_capacity
