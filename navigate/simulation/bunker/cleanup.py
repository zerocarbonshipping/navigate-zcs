# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Remove the LP variables and constraints of vessels, fuels and regulations gone."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import navigate.simulation.bunker.solver as gp
    from navigate.core.enum_ import EnergyDemandID
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def remove_redundant_vessel(alg: BunkerAlgorithm, v: str) -> None:
    """
    Remove a vessel, its multiplier and its LP variables and constraints.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Name of vessel being removed from the model.
    """
    del alg.vessels[v]
    del alg.multipliers[v]

    _remove_vessel_elements(alg, v, alg.bunker)
    _remove_vessel_elements(alg, v, alg.spend_sea)
    _remove_vessel_elements(alg, v, alg.spend_port)
    _remove_vessel_elements(alg, v, alg.mass_tank)
    _remove_vessel_elements(alg, v, alg.shore_power)

    _remove_vessel_elements(alg, v, alg.energy_conservation_sea)
    _remove_vessel_elements(alg, v, alg.energy_conservation_port)
    _remove_vessel_elements(alg, v, alg.pilot_fuel_sea)
    _remove_vessel_elements(alg, v, alg.pilot_fuel_port)
    _remove_vessel_elements(alg, v, alg.mass_conservation)
    _remove_vessel_elements(alg, v, alg.mass_sufficient)
    _remove_vessel_elements(alg, v, alg.tank_capacity)
    _remove_vessel_elements(alg, v, alg.bunker_equals_spent)
    _remove_vessel_elements(alg, v, alg.fuel_inertia)
    _remove_vessel_elements(alg, v, alg.fair_share_fuel)


def remove_redundant_fuels_from_ports(alg: BunkerAlgorithm) -> None:
    """
    Remove the LP elements of fuels ports stop bunkering, and caps on unlimited supply.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for v, p, f in list(alg.bunker):
        port = alg.vessels[v].route.ports[p]

        if not port.is_bunkering_allowed(f):
            alg.model.remove(alg.bunker.pop((v, p, f)))

    for v, port_name, f in list(alg.fuel_inertia):
        port = alg.ports[port_name]

        if not port.is_bunkering_allowed(f):
            alg.model.remove(alg.fuel_inertia.pop((v, port_name, f)))

    for v, port_name, f in list(alg.fair_share_fuel):
        port = alg.ports[port_name]
        supply = port.expectation.get_bunker_supply(f, alg.idx)

        if not port.is_bunkering_allowed(f) or not np.isfinite(supply):
            alg.model.remove(alg.fair_share_fuel.pop((v, port_name, f)))


def remove_redundant_regulations(alg: BunkerAlgorithm) -> None:
    """
    Remove the remedial factors and threshold constraints of regulations gone.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for key in list(alg.remedial_factor_individual):
        if key not in alg.regulation_rhs_individual:
            alg.model.remove(alg.remedial_factor_individual.pop(key))
            alg.model.remove(alg.regulation_threshold_individual.pop(key))

    for key in list(alg.remedial_factor_flexibility):
        if key not in alg.regulation_total_rhs_flexibility:
            alg.model.remove(alg.remedial_factor_flexibility.pop(key))
            alg.model.remove(alg.regulation_threshold_flexibility.pop(key))


def _remove_vessel_elements[
    K: tuple[str, *tuple[str | int | EnergyDemandID, ...]],
    E: (gp.Var, gp.Constr),
](alg: BunkerAlgorithm, v: str, container: dict[K, E]) -> None:
    """
    Remove a vessel's variables or constraints from the LP model and their dict.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Name of the vessel, the first element of the keys removed.
    container
        Variable or constraint dict of one family on the algorithm.
    """
    for key in list(container):
        if key[0] == v:
            alg.model.remove(container.pop(key))
