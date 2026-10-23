# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Remove the LP variables and constraints of vessels, fuels and regulations gone."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.enum_ import EnergyDemandID
    from navigate.simulation.bunker import solver
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

    model = alg.model

    _remove_vessel_elements(v, alg.bunker, model.remove_variable)
    _remove_vessel_elements(v, alg.spend_sea, model.remove_variable)
    _remove_vessel_elements(v, alg.spend_port, model.remove_variable)
    _remove_vessel_elements(v, alg.mass_tank, model.remove_variable)
    _remove_vessel_elements(v, alg.shore_power, model.remove_variable)

    _remove_vessel_elements(v, alg.energy_conservation_sea, model.remove_constraint)
    _remove_vessel_elements(v, alg.energy_conservation_port, model.remove_constraint)
    _remove_vessel_elements(v, alg.pilot_fuel_sea, model.remove_constraint)
    _remove_vessel_elements(v, alg.pilot_fuel_port, model.remove_constraint)
    _remove_vessel_elements(v, alg.mass_conservation, model.remove_constraint)
    _remove_vessel_elements(v, alg.mass_sufficient, model.remove_constraint)
    _remove_vessel_elements(v, alg.tank_capacity, model.remove_constraint)
    _remove_vessel_elements(v, alg.bunker_equals_spent, model.remove_constraint)
    _remove_vessel_elements(v, alg.fuel_inertia, model.remove_constraint)
    _remove_vessel_elements(v, alg.fair_share_fuel, model.remove_constraint)


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

        if not port.bunkering_allowed[f]:
            alg.model.remove_variable(alg.bunker.pop((v, p, f)))

    for v, port_name, f in list(alg.fuel_inertia):
        port = alg.ports[port_name]

        if not port.bunkering_allowed[f]:
            alg.model.remove_constraint(alg.fuel_inertia.pop((v, port_name, f)))

    for v, port_name, f in list(alg.fair_share_fuel):
        port = alg.ports[port_name]
        supply = port.expectation.get_bunker_supply(f, alg.idx)

        if not port.bunkering_allowed[f] or not np.isfinite(supply):
            alg.model.remove_constraint(alg.fair_share_fuel.pop((v, port_name, f)))


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
            alg.model.remove_variable(alg.remedial_factor_individual.pop(key))
            alg.model.remove_constraint(alg.regulation_threshold_individual.pop(key))

    for key in list(alg.remedial_factor_flexibility):
        if key not in alg.regulation_total_rhs_flexibility:
            alg.model.remove_variable(alg.remedial_factor_flexibility.pop(key))
            alg.model.remove_constraint(alg.regulation_threshold_flexibility.pop(key))


def _remove_vessel_elements[
    K: tuple[str, *tuple[str | int | EnergyDemandID, ...]],
    E: (solver.Variable, solver.Constraint),
](v: str, container: dict[K, E], remove: Callable[[E], None]) -> None:
    """
    Remove a vessel's variables or constraints from the LP model and their dict.

    Parameters
    ----------
    v
        Name of the vessel, the first element of the keys removed.
    container
        Variable or constraint dict of one family on the algorithm.
    remove
        The model's remover of the family's element kind.
    """
    for key in list(container):
        if key[0] == v:
            remove(container.pop(key))
