# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Remove the LP elements of vessels, fuels, shore power and regulations gone."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.simulation.bunker._constraints.fair_share_fuel import (
    is_fair_share_constrained,
)
from navigate.simulation.bunker._constraints.regulation_threshold_flexibility import (
    is_pooled,
)
from navigate.simulation.bunker._constraints.shore_power_limit import (
    can_draw_shore_power,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.simulation.bunker._build import VesselKey
    from navigate.simulation.bunker._solver import Constraint, Variable
    from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm


def remove_redundant_vessel(alg: BunkerAlgorithm, v: str) -> None:
    """
    Remove a vessel, its count and its LP variables and constraints.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Name of vessel being removed from the model.
    """
    del alg.vessels[v]
    del alg.counts[v]

    model = alg.model

    _remove_vessel_elements(v, alg.bunker, model.remove_variable)
    _remove_vessel_elements(v, alg.bunker_peak, model.remove_variable)
    _remove_vessel_elements(v, alg.spend_sea, model.remove_variable)
    _remove_vessel_elements(v, alg.spend_port, model.remove_variable)
    _remove_vessel_elements(v, alg.mass_tank, model.remove_variable)
    _remove_vessel_elements(v, alg.shore_power, model.remove_variable)

    _remove_vessel_elements(v, alg.energy_conservation_sea, model.remove_constraint)
    _remove_vessel_elements(v, alg.energy_conservation_port, model.remove_constraint)
    _remove_vessel_elements(v, alg.pilot_fuel_sea, model.remove_constraint)
    _remove_vessel_elements(v, alg.pilot_fuel_port, model.remove_constraint)
    _remove_vessel_elements(v, alg.shore_power_limit, model.remove_constraint)
    _remove_vessel_elements(v, alg.mass_conservation, model.remove_constraint)
    _remove_vessel_elements(v, alg.mass_sufficient, model.remove_constraint)
    _remove_vessel_elements(v, alg.tank_capacity, model.remove_constraint)
    _remove_vessel_elements(v, alg.bunkered_equals_spent, model.remove_constraint)
    _remove_vessel_elements(v, alg.bunker_below_peak, model.remove_constraint)
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
        if f not in alg.vessels[v].bunkerable_fuels[p]:
            alg.model.remove_variable(alg.bunker.pop((v, p, f)))
            alg.model.remove_constraint(alg.bunker_below_peak.pop((v, p, f)))

    still_bunkerable = {(v, f) for v, _, f in alg.bunker}

    for key in list(alg.bunker_peak):
        if key not in still_bunkerable:
            alg.model.remove_variable(alg.bunker_peak.pop(key))

    for v, port_name, f in list(alg.fuel_inertia):
        port = alg.ports[port_name]

        if not port.allow_bunkering[f]:
            alg.model.remove_constraint(alg.fuel_inertia.pop((v, port_name, f)))

    for v, port_name, f in list(alg.fair_share_fuel):
        port = alg.ports[port_name]

        if not is_fair_share_constrained(port, f, alg.idx):
            alg.model.remove_constraint(alg.fair_share_fuel.pop((v, port_name, f)))


def remove_redundant_shore_power(alg: BunkerAlgorithm) -> None:
    """
    Remove the shore power, with its limit, that vessels can no longer draw at a port.

    Parameters
    ----------
    alg
        The algorithm instance.
    """
    for v, p in list(alg.shore_power):
        if not can_draw_shore_power(alg.vessels[v], p, alg.idx):
            alg.model.remove_variable(alg.shore_power.pop((v, p)))
            alg.model.remove_constraint(alg.shore_power_limit.pop((v, p)))


def remove_redundant_regulations(alg: BunkerAlgorithm) -> None:
    """
    Remove the variables and constraints of regulations and of pooled vessels gone.

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
        if key not in alg.regulation_rhs_flexibility:
            alg.model.remove_variable(alg.remedial_factor_flexibility.pop(key))
            alg.model.remove_constraint(alg.regulation_threshold_flexibility.pop(key))

    for r, v in list(alg.pooled_term):
        if not is_pooled(alg, r, v):
            alg.model.remove_variable(alg.pooled_term.pop((r, v)))
            alg.model.remove_constraint(alg.pooled_term_definition.pop((r, v)))


def _remove_vessel_elements[K: VesselKey, E: (Variable, Constraint)](
    v: str, container: dict[K, E], remove: Callable[[E], None]
) -> None:
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
