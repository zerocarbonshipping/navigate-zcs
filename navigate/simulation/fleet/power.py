# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Power capacity checks, technical speed limits and load convexity of vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Expression, Scalar
from navigate.core.enum_ import PORT_ENERGY_DEMANDS, EnergyDemandID
from navigate.core.node_type import is_surface, is_variable
from navigate.exceptions import PowerCapacityError
from navigate.util import TOLERANCE, energy_to_power, power_to_energy

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import SurfaceInput
    from navigate.simulation.fleet._trip import ReferenceTrip
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_mean_speed_bounds(
    speeds_min: FloatArray,
    speeds_max: FloatArray,
    speeds: FloatArray,
) -> tuple[float, float]:
    """
    Calculate a vessel's minimum and maximum mean speed from its technical bounds.

    Only the conditions that take sea time are passed: a condition with a zero time
    share bounds no speed.

    Parameters
    ----------
    speeds_min
        Minimum speed per sailed condition, knots.
    speeds_max
        Maximum speed per sailed condition, knots.
    speeds
        Speed per sailed condition, knots.

    Returns
    -------
    tuple[float, float]
        Minimum and maximum mean speed achievable by the vessel, knots.
    """
    low = np.min(speeds_min)
    high = np.max(speeds_max)

    if np.isfinite(low) and np.isfinite(high) and low < high:
        return low, high

    # technical bounds that are infinite or inverted fall back on the envelope of the
    # given speeds
    return np.min(speeds), np.max(speeds)


def calculate_technical_speed_limits(
    vessel: Vessel, trip: ReferenceTrip
) -> tuple[FloatArray, FloatArray]:
    """
    Calculate a vessel's minimum and maximum achievable speed from its propulsion load.

    Only the propulsion load sets the limits: a minimum load on the electrical or heat
    converter is ignored, although in extreme cases it could bind the speed.

    Parameters
    ----------
    vessel
        Vessel whose speed limits are calculated.
    trip
        Reference trip holding the sailing conditions.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Minimum and maximum speed per condition, knots.
    """
    load = vessel.propulsion_load

    # a scalar or variable load has no speed to look up, and an expression can only
    # be evaluated, not read as a table; the other speed bounds govern instead
    if isinstance(load, Expression | Scalar) or is_variable(load):
        return _unbounded_speed_limits(trip)

    # the load is a Curve or a Surface
    converter = vessel.propulsion_converter
    minimum_load = converter.minimum_load
    power_max = converter.power_capacity.get()

    # the power capacity may cap the speed below the load's largest speed
    speed_max = _calculate_speed_at_power(load, power_max, trip)
    speed_min = None

    if minimum_load is not None:
        power_min = minimum_load.get() * power_max
        speed_min = _calculate_speed_at_power(load, power_min, trip)

    # without a minimum load, or when the reverse lookup returns None for a load that
    # is not strictly increasing, the load's own speed range applies
    if speed_min is None:
        speed_min = load.x[0]

    if speed_max is None:
        speed_max = load.x[-1]

    # the limits are per condition, as the capacity utilization moves the power limit
    return (
        _expand_speed_to_conditions(trip, speed_min),
        _expand_speed_to_conditions(trip, speed_max),
    )


def loads_are_convex(vessel: Vessel) -> bool:
    """
    Check whether every load at sea is convex.

    The propulsion, electrical and heat loads at sea can all depend on the speed and
    capacity utilization.

    Parameters
    ----------
    vessel
        Vessel whose loads are checked.

    Returns
    -------
    bool
        Whether every load at sea is convex.
    """
    propulsion = _load_is_convex(vessel.propulsion_load)
    electrical = _load_is_convex(vessel.electrical_load_at_sea)
    heat = _load_is_convex(vessel.heat_load_at_sea)

    return propulsion and electrical and heat


def verify_power_capacity(vessels: list[Vessel], idx: int) -> None:
    """
    Verify converter power capacity of each vessel at a time step.

    Checking at the current time-step alone covers every LP built from it: a
    vessel-expectation write at a time-step broadcasts over the remaining horizon, so
    each future expected-bunkering build reads the same demands and times.

    Parameters
    ----------
    vessels
        Vessels entering a bunkering LP of the time-step.
    idx
        Current time-step index.

    Raises
    ------
    PowerCapacityError
        If any vessel has an energy demand that exceeds what its serving converter
        can deliver.
    """
    for vessel in vessels:
        _verify_vessel_power_capacity(vessel, idx)


def _verify_vessel_power_capacity(vessel: Vessel, idx: int) -> None:
    """
    Verify that installed converter power covers every energy demand of a vessel.

    Each demand is compared per sailing condition and per port: the energy a converter
    delivers over a step cannot exceed its power capacity times the time spent on that
    step. Since speed, and thus load, is constant within a condition, the comparison
    per condition bounds the load at every operating speed. Port demands must fit the
    onboard converter alone; shore power gives no allowance. A route-wide condition
    overloaded alike on several legs is reported once.

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

    times_sea = [float(time) for time in expectation.get_time_sea_condition(idx)]
    times_port = [float(time) for time in expectation.get_time_port(idx)]
    energies_sea = expectation.get_energy_sea_condition(idx=idx)
    energies_port = expectation.get_energy_port(idx=idx)

    labels_sea = _name_conditions(vessel.route)
    labels_port = [f"port {port}" for port in vessel.route.ports]

    domains = (
        (energies_sea, times_sea, labels_sea, EnergyDemandID),
        (energies_port, times_port, labels_port, PORT_ENERGY_DEMANDS),
    )

    overloads: list[str] = []

    for energies, times, labels, demand_types in domains:
        for demand_type in demand_types:
            converter = vessel.get_converter(demand_type)
            demands = [float(energy) for energy in energies[demand_type]]
            overloads += _find_overloads(converter, demand_type, demands, times, labels)

    if overloads:
        details = "\n".join(dict.fromkeys(overloads))
        raise PowerCapacityError(
            f"{vessel}: energy demand exceeds installed converter power:\n{details}"
        )


def get_total_power_capacity(vessel: Vessel) -> float:
    """
    Return the total installed converter power capacity of a vessel.

    Parameters
    ----------
    vessel
        Vessel whose converters are summed.

    Returns
    -------
    float
        Total installed power across the converters, MW.
    """
    return sum(converter.power_capacity.get() for converter in vessel.get_converters())


def _unbounded_speed_limits(trip: ReferenceTrip) -> tuple[FloatArray, FloatArray]:
    """
    Give a vessel no technical speed limit, expanded to one value per condition.

    Parameters
    ----------
    trip
        Reference trip holding the sailing conditions.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Minimum and maximum speed per condition, both unbounded.
    """
    return (
        _expand_speed_to_conditions(trip, -np.inf),
        _expand_speed_to_conditions(trip, np.inf),
    )


def _calculate_speed_at_power(
    load: Curve | Surface, power: float, trip: ReferenceTrip
) -> FloatLike | None:
    """
    Calculate the vessel speed at which a given power is reached.

    Parameters
    ----------
    load
        Propulsion load of the vessel.
    power
        Minimum or maximum power of the converter, MW.
    trip
        Reference trip holding the capacity utilizations.

    Returns
    -------
    FloatLike | None
        The speed at which the power is reached, knots, one per capacity utilization
        for a surface, or `None` when the load is not strictly increasing.
    """
    if is_surface(load):
        return load.reverse_lookup(power, y=trip.utilizations)

    return load.reverse_lookup(power)


def _expand_speed_to_conditions(trip: ReferenceTrip, speed: FloatLike) -> FloatArray:
    """
    Give a speed as one value per sailing condition.

    Parameters
    ----------
    trip
        Reference trip holding the sailing conditions.
    speed
        One speed for every condition, or one speed per condition, knots.

    Returns
    -------
    FloatArray
        Speed per condition, knots.
    """
    return np.full(len(trip.speeds), speed, dtype=float)


def _load_is_convex(load: SurfaceInput) -> bool:
    """
    Check whether a propulsion, electrical or heat load is convex.

    Parameters
    ----------
    load
        Load of a vessel.

    Returns
    -------
    bool
        Whether the load is convex.
    """
    if isinstance(load, Expression):
        # an expression can only be evaluated, not read as a table, so its
        # convexity is unknown
        return False

    if isinstance(load, Scalar) or is_variable(load):
        return True

    # the load is a Curve or a Surface
    return load.is_convex()


def _find_overloads(
    converter: Converter,
    demand_type: EnergyDemandID,
    energies: list[float],
    times: list[float],
    labels: list[str],
) -> list[str]:
    """
    Find the steps where an energy demand exceeds a converter's deliverable energy.

    Parameters
    ----------
    converter
        Converter serving the demand.
    demand_type
        Energy demand type being verified.
    energies
        Energy demand per step, GJ/year.
    times
        Time spent on each step, days/year.
    labels
        Name of each step, used in the overload messages.

    Returns
    -------
    list[str]
        One message per overloaded step.
    """
    power_capacity = converter.power_capacity.get()
    demand_name = demand_type.name.lower()
    overloads = []

    for label, energy, time in zip(labels, energies, times, strict=True):
        deliverable = power_to_energy(power_capacity, time)

        if energy - deliverable <= TOLERANCE * max(1.0, deliverable):
            continue

        implied_power = energy_to_power(energy, time) if time > 0.0 else np.inf
        overloads.append(
            f"  {demand_name} demand on {label} requires "
            f"{implied_power:.2f} MW but {converter} has "
            f"{power_capacity:.2f} MW installed."
        )

    return overloads


def _name_conditions(route: Route) -> list[str]:
    """
    Name each sailing condition of a route as its deck states it.

    A condition that is the only one on its leg is that leg, named by its ports; any
    other condition is named by its entry in the leg's speed Curve.

    Parameters
    ----------
    route
        Route holding the sailing conditions.

    Returns
    -------
    list[str]
        Name of each condition, in the order of `Route.get_conditions`.
    """
    legs = route.get_legs()
    ports = route.ports

    names = []
    for leg, entry in route.get_conditions():
        origin, destination = legs[leg]
        leg_name = f"the leg from {ports[origin]} to {ports[destination]}"

        if route.conditions_per_leg[leg] == 1:
            names.append(leg_name)
        else:
            names.append(f"condition {entry} on {leg_name}")

    return names
