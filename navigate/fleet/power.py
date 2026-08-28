# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.variable import Variable
from navigate.core.nodes.vessel import Vessel
from navigate.core.unit import MWD_TO_GJ
from navigate.exceptions import PowerCapacityError
from navigate.util import TOLERANCE, to_numpy


def calculate_speed_bounds(speeds_min: np.ndarray,
                           speeds_max: np.ndarray,
                           speeds: np.ndarray,
                           ) -> tuple[float, float]:
    """
    Calculate the minimum and maximum mean speed achievable by a vessel based on its technical minimum and maximum.

    Parameters
    ----------
    speeds_min
        Minimum speed per leg.
    speeds_max
        Maximum speed per leg.
    speeds
        Speed per leg.

    Returns
    -------
    tuple[float, float]
        Minimum and maximum mean speed achievable by the vessel.
    """

    low = np.min(speeds_min)
    high = np.max(speeds_max)

    if np.isfinite(low) and np.isfinite(high) and (low < high):
        return low, high

    # fallback: use reference distribution envelope
    low = np.min(speeds)
    high = np.max(speeds)

    return low, high


def calculate_technical_speed_limits(vessel: Vessel) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculate the minimum and maximum achievable speeds for a vessel based on its propulsion load and propulsion system.

    Notice that the technical minimum/maximum speed is only defined as a function of the propulsion load.
    Meaning that if a minimum load is defined for the electrical or heat converter, this information is ignored
    although this could in theory be the bindind speed constraint in extreme cases.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Minimum speed per leg and maximum speed per leg.
    """

    load = vessel.propulsion_load

    if isinstance(load, Scalar):
        return -np.inf, np.inf

    # must per definition either be Variable, Curve or Surface
    elif load.is_variable():
        return -np.inf, np.inf

    # must per definition be Curve or Surface
    else:

        converter = vessel.power_system.propulsion
        power_maximum = converter.power_capacity.get()
        minimum_load = converter.minimum_load

        # the minimum speed can either be found
        # as a fraction of the power or simply using
        # the lowest value in the speed-power curve
        if minimum_load is not None:
            power_minimum = minimum_load.get() * power_maximum
            speed_minimum = _calculate_speed_extremum(vessel, power_minimum, load)

        else:
            # use minimum from speed-power curve/surface
            speed_minimum = load.x[0]

        # calculate the maximum speed in case the
        # maximum power is lower than the maximum
        # of the speed-power curve/surface
        speed_maximum = _calculate_speed_extremum(vessel, power_maximum, load)

        # in case the propulsion load is not
        # defined by a strictly increasing
        # function, the reverse lookup returns
        # None which has to be handled
        if speed_minimum is None:
            speed_minimum = load.x[0]

        if speed_maximum is None:
            speed_maximum = load.x[-1]

        # ensure the minimum and maximum speeds
        # are given per leg because the capacity
        # utilization can impact the power limit
        speed_minimum = _expand_speed_to_legs(vessel, speed_minimum)
        speed_maximum = _expand_speed_to_legs(vessel, speed_maximum)

        return speed_minimum, speed_maximum


def loads_are_convex(vessel: Vessel) -> bool:
    """
    Check whether all loads at sea are based on a convex function. This is necessary since both the propulsion load,
    electrical load, and heat load at sea can depend on the speed and capacity utilization

    Parameters
    ----------
    vessel
        Vessel for which loads are checked.

    Returns
    -------
    bool
        Whether all loads are based on a convex function.
    """

    propulsion = _load_is_convex(vessel.propulsion_load)
    electrical = _load_is_convex(vessel.electrical_load_at_sea)
    heat = _load_is_convex(vessel.heat_load_at_sea)

    return propulsion and electrical and heat


def verify_power_capacity(vessel: Vessel, idx: int) -> None:
    """
    Verify that installed converter power covers every energy demand of a vessel.

    Each demand is compared per leg and per port: the energy a converter delivers over
    a step cannot exceed its power capacity times the time spent on that step. Since
    speed, and thus load, is constant within a leg, the per-leg comparison bounds the
    load at every operating speed. Port demands must fit the onboard converter alone;
    shore power gives no allowance.

    Parameters
    ----------
    vessel
        Vessel whose energy demands are verified.
    idx
        Current time-step index.

    Raises
    ------
    PowerCapacityError
        If any energy demand exceeds what the serving converter can deliver.
    """

    expectation = vessel.expectation
    power_system = vessel.power_system

    times_sea = expectation.get_time_sea(idx)
    times_port = expectation.get_time_port(idx)
    energies_sea = expectation.get_energy_sea(idx=idx)
    energies_port = expectation.get_energy_port(idx=idx)

    domains = (
        (energies_sea, times_sea, "leg", EnergyDemandTypeID),
        (energies_port, times_port, "port", EnergyDemandTypePortID),
    )

    violations = []

    for energies, times, step_label, demand_types in domains:

        for demand_type in demand_types:
            converter = power_system.get_converter_by_energy_type(demand_type)
            violations += _find_capacity_violations(converter, demand_type, energies[demand_type], times, step_label)

    if violations:
        raise PowerCapacityError("{}: energy demand exceeds installed converter power:\n{}"
                                 .format(vessel, "\n".join(violations)))


def _find_capacity_violations(converter: Converter,
                              demand_type: EnergyDemandTypeID,
                              energies: list[float],
                              times: list[float],
                              step_label: str
                              ) -> list[str]:
    """
    Compare one energy demand against a converter's deliverable energy per leg or port.

    Parameters
    ----------
    converter
        Converter serving the demand.
    demand_type
        Energy demand type being verified.
    energies
        Energy demand per step (GJ).
    times
        Time spent on each step (days).
    step_label
        Name of the step dimension ("leg" or "port") used in violation messages.

    Returns
    -------
    One message per step whose demand exceeds the deliverable energy.
    """

    power_capacity = converter.power_capacity.get()
    violations = []

    for step, (energy, time) in enumerate(zip(energies, times)):

        deliverable = power_capacity * time * MWD_TO_GJ

        if energy - deliverable <= TOLERANCE * max(1., deliverable):
            continue

        implied_power = energy / (time * MWD_TO_GJ) if time > 0. else float("inf")
        violations.append("  {} demand on {} {} requires {:.2f} MW but {} has {:.2f} MW installed."
                          .format(demand_type.name.lower(), step_label, step,
                                  implied_power, converter, power_capacity))

    return violations


def _expand_speed_to_legs(vessel, speed: float | list[float]) -> np.ndarray:
    a = np.asarray(speed, dtype=float)

    if a.ndim == 0:
        n = vessel.route.get_number_of_legs()
        a = np.full(n, float(a), dtype=float)

    return a


def _calculate_speed_extremum(vessel: Vessel, power: float, load: Curve | Surface) -> float | list[float]:
    """
    Calculate the speed at which a given minimum or maximum power is reached for a vessel.

    Parameters
    ----------
    vessel
        Vessel for which speed extremum is calculated.
    power
        Either minimum or maximum power of the converter.
    load
        Propulsion load function of the vessel.

    Returns
    -------
    float | list[float]
        The speed(s) at which the power is reached.
    """

    if load.is_surface():
        utilization = to_numpy(vessel.route.capacity_utilizations)
        speed = load.reverse_lookup(power, y=utilization, interpolate=True)
    else:
        speed = load.reverse_lookup(power, interpolate=True)

    return speed


def _load_is_convex(load: Scalar | Variable | Curve | Surface) -> bool:
    """
    Check whether a propulsion, electrical, or heat load level is based on a convex function.

    Parameters
    ----------
    load
        Load of a vessel.

    Returns
    -------
    bool
        Whether the load level is based on a convex function.
    """

    if isinstance(load, Scalar):
        return True

    # must per definition either be Variable, Curve or Surface
    elif load.is_variable():
        return True

    # must per definition be Curve or Surface
    else:
        return load.is_convex()
