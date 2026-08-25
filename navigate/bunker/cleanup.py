# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.bunker.bunker_algorithm import BunkerAlgorithm

import numpy as np


def remove_redundant_vessel(alg: BunkerAlgorithm, v: str) -> None:
    """
    Remove all parameters related to a redundant vessel.

    Parameters
    ----------
    alg
        The algorithm instance.
    v
        Name of vessel being removed from the model.
    """

    # remove all non-model related attributes
    del alg.vessels[v]
    del alg.multipliers[v]

    # clean up pre-computed values
    for key in list(alg.effective_lhv):
        if key[0] == v:
            del alg.effective_lhv[key]

    # remove primary variables
    remove_model_attribute_and_dict_element(alg, v, alg.bunker)
    remove_model_attribute_and_dict_element(alg, v, alg.spend_sea)
    remove_model_attribute_and_dict_element(alg, v, alg.spend_port)
    remove_model_attribute_and_dict_element(alg, v, alg.mass_tank)
    remove_model_attribute_and_dict_element(alg, v, alg.shore_power)

    # remove primary constraints
    remove_model_attribute_and_dict_element(alg, v, alg.energy_conservation_sea)
    remove_model_attribute_and_dict_element(alg, v, alg.energy_conservation_port)
    remove_model_attribute_and_dict_element(alg, v, alg.power_capacity_sea)
    remove_model_attribute_and_dict_element(alg, v, alg.power_capacity_port)
    remove_model_attribute_and_dict_element(alg, v, alg.pilot_fuel_sea)
    remove_model_attribute_and_dict_element(alg, v, alg.pilot_fuel_port)
    remove_model_attribute_and_dict_element(alg, v, alg.mass_conservation)
    remove_model_attribute_and_dict_element(alg, v, alg.mass_sufficient)
    remove_model_attribute_and_dict_element(alg, v, alg.tank_capacity)
    remove_model_attribute_and_dict_element(alg, v, alg.bunker_equals_spent)
    remove_model_attribute_and_dict_element(alg, v, alg.fuel_inertia)
    remove_model_attribute_and_dict_element(alg, v, alg.fair_share_fuel)


def remove_redundant_fuels_from_ports(alg: BunkerAlgorithm) -> None:
    """
    Remove redundant bunker variables and availability/inertia constraints related to fuels in ports.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    # remove vessel variables
    for (v, p, f) in list(alg.bunker.keys()):

        port = alg.vessels[v].route.ports[p]

        if not port.is_bunkering_allowed(f):

            # remove bunker variable
            if (v, p, f) in alg.bunker:

                alg.model.remove(alg.bunker[v, p, f])
                del alg.bunker[v, p, f]

    # remove vessel constraints
    for (v, p, f) in list(alg.fuel_inertia.keys()):

        # notice 'p' is the port name, not the port index
        port = alg.ports[p]

        if not port.is_bunkering_allowed(f):

            # remove fuel inertia constraint
            if (v, p, f) in alg.fuel_inertia:

                alg.model.remove(alg.fuel_inertia[v, p, f])
                del alg.fuel_inertia[v, p, f]

    # remove fair-share constraints
    for (v, p, f) in list(alg.fair_share_fuel.keys()):

        # notice 'p' is the port name, not the port index
        port = alg.ports[p]

        available = port.is_bunkering_allowed(f)
        supply = port.expectation.get_bunker_supply(f, alg.idx)

        if (not available) or (not np.isfinite(supply)):

            if (v, p, f) in alg.fair_share_fuel:

                alg.model.remove(alg.fair_share_fuel[v, p, f])
                del alg.fair_share_fuel[v, p, f]


def remove_redundant_regulations(alg: BunkerAlgorithm) -> None:
    """
    Remove redundant slack variables and constraint related to regulations.

    Parameters
    ----------
    alg
        The algorithm instance.
    """

    for key in list(alg.remedial_factor_individual.keys()):

        if key not in alg.regulation_rhs_individual:

            # remove variable
            alg.model.remove(alg.remedial_factor_individual[key])
            del alg.remedial_factor_individual[key]

            # remove constraint
            alg.model.remove(alg.regulation_threshold_individual[key])
            del alg.regulation_threshold_individual[key]

    for key in list(alg.remedial_factor_flexibility.keys()):

        if key not in alg.regulation_total_rhs_flexibility:

            # remove variable
            alg.model.remove(alg.remedial_factor_flexibility[key])
            del alg.remedial_factor_flexibility[key]

            # remove constraint
            alg.model.remove(alg.regulation_threshold_flexibility[key])
            del alg.regulation_threshold_flexibility[key]


def remove_model_attribute_and_dict_element(
    alg: BunkerAlgorithm, to_remove: str | tuple, tuple_dict: dict, positions: tuple[int, ...] = (0,),
) -> None:
    """
    Removes a variable or constraint from the LP model and deletes it from the dict it is stored in.

    Parameters
    ----------
    alg
        The algorithm instance.
    to_remove
        Part of a key to a tuple dictionary.
    tuple_dict
        Dict from which to remove elements.
    positions
        Positions in the tupledict keys that should match 'to_remove'.
    """

    if not isinstance(to_remove, tuple):
        to_remove = (to_remove,)

    for key, attribute in list(tuple_dict.items()):

        if all(to == key[position] for to, position in zip(to_remove, positions)):

            alg.model.remove(attribute)
            del tuple_dict[key]
