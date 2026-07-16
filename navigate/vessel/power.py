# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.calculator import Curve, Surface, Variable
from navigate.core import Scalar
from navigate.util import to_numpy
from navigate.vessel import Vessel


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
            speed_minimum = load.get_x_min()

        # calculate the maximum speed in case the
        # maximum power is lower than the maximum
        # of the speed-power curve/surface
        speed_maximum = _calculate_speed_extremum(vessel, power_maximum, load)

        # in case the propulsion load is not
        # defined by a strictly increasing
        # function, the reverse lookup returns
        # None which has to be handled
        if speed_minimum is None:
            speed_minimum = load.get_x_min()

        if speed_maximum is None:
            speed_maximum = load.get_x_max()

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
