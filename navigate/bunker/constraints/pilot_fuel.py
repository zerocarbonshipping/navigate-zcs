# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Add the constraints that dual-fuel converters burn their minimum pilot-fuel share."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.bunker._build import get_constraint
from navigate.bunker.utils import get_converters, get_port_converters

if TYPE_CHECKING:
    import navigate.bunker.solver as gp
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm
    from navigate.core.nodes.vessel import Vessel


def update_pilot_fuel_constraints(alg: BunkerAlgorithm, vessel: Vessel) -> None:
    r"""
    Add the constraints that dual-fuel converters burn enough pilot fuel.

    For each dual-fuel converter c and leg (i, e), and analogously per port p
    with the port spend y (vessel index omitted):

        (1 - \phi_c) \sum_{f in pilot(c)} \lambda_{c,f} x_{c,f,i,e}
            - \phi_c \sum_{f in main(c)} \lambda_{c,f} x_{c,f,i,e} >= 0

    i.e. the pilot fuels carry at least the fraction \phi of the converter's fuel
    energy, where \phi is the converter's minimum pilot fuel fraction and \lambda
    the effective lower heating value (GJ/t). Dual-fuel combustion needs a
    pilot-fuel share to ignite the main fuel. The propulsion converter gets no
    port rows: it serves no port energy demand.

    Parameters
    ----------
    alg
        The algorithm instance.
    vessel
        Vessel for which constraints are added.
    """
    v = vessel.name
    route = vessel.route
    usable_fuels = vessel.usable_fuels
    port_converters = get_port_converters(vessel)
    leg_idx = route.get_leg_indices()
    port_idx = range(route.get_number_of_ports())

    for c, converter in get_converters(vessel).items():
        if not converter.is_dual_fuel():
            continue

        fraction = converter.minimum_pilot_fuel.get()

        pilot_fuels = [
            fuel.name
            for fuel_type in converter.pilot_fuel_types
            for fuel in alg.fuels_per_fuel_type[fuel_type]
            if fuel.name in usable_fuels
        ]

        main_fuels = [
            fuel.name
            for fuel_type in converter.main_fuel_types
            for fuel in alg.fuels_per_fuel_type[fuel_type]
            if fuel.name in usable_fuels
        ]

        for port_start, port_end in leg_idx:
            sea_key = (v, c, port_start, port_end)
            constraint = get_constraint(
                alg, alg.pilot_fuel_sea, sea_key, ">=", "pilot_fuel_at_sea"
            )

            _apply_pilot_fuel_coefficients(
                alg,
                constraint,
                alg.spend_sea,
                v,
                c,
                (port_start, port_end),
                pilot_fuels,
                main_fuels,
                fraction,
            )

        if c not in port_converters:
            continue

        for p in port_idx:
            port_key = (v, c, p)
            constraint = get_constraint(
                alg, alg.pilot_fuel_port, port_key, ">=", "pilot_fuel_in_port"
            )

            _apply_pilot_fuel_coefficients(
                alg,
                constraint,
                alg.spend_port,
                v,
                c,
                (p,),
                pilot_fuels,
                main_fuels,
                fraction,
            )


def _apply_pilot_fuel_coefficients(
    alg: BunkerAlgorithm,
    constraint: gp.Constr,
    spend: dict[tuple, gp.Var],
    v: str,
    c: str,
    indices: tuple[int, ...],
    pilot_fuels: list[str],
    main_fuels: list[str],
    fraction: float,
) -> None:
    """
    Apply the pilot- and main-fuel coefficients of one pilot-fuel row.

    Parameters
    ----------
    alg
        The algorithm instance.
    constraint
        Row to apply the coefficients to.
    spend
        Spend variables of the row's domain (``alg.spend_sea`` or ``alg.spend_port``).
    v
        Vessel name.
    c
        Converter name.
    indices
        Leg or port indices of the row; each fuel's variable is keyed
        ``(v, c, f, *indices)``.
    pilot_fuels
        Names of the converter's usable pilot fuels.
    main_fuels
        Names of the converter's usable main fuels.
    fraction
        Minimum pilot fuel fraction of the converter.
    """
    change_coefficient = alg.model.chgCoeff
    effective_lhv = alg.effective_lhv

    for f in pilot_fuels:
        change_coefficient(
            constraint,
            spend[(v, c, f, *indices)],
            (1.0 - fraction) * effective_lhv[(v, c, f)],
        )

    for f in main_fuels:
        change_coefficient(
            constraint, spend[(v, c, f, *indices)], -fraction * effective_lhv[(v, c, f)]
        )
