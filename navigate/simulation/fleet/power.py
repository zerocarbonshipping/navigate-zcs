# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Power capacity checks, technical speed limits and load convexity of vessels."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Expression, Scalar
from navigate.core.enum_ import (
    BunkerScopeID,
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
)
from navigate.core.node_type import is_surface, is_variable
from navigate.core.wrap import to_numpy
from navigate.exceptions import PowerCapacityError
from navigate.util import MWD_TO_GJ, TOLERANCE

if TYPE_CHECKING:
    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.fleet import Fleet
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import SurfaceInput
    from navigate.util.types_ import FloatArray, FloatLike


def calculate_speed_bounds(
    speeds_min: FloatArray,
    speeds_max: FloatArray,
    speeds: FloatArray,
) -> tuple[float, float]:
    """
    Calculate a vessel's minimum and maximum mean speed from its technical bounds.

    Parameters
    ----------
    speeds_min
        Minimum speed per leg, knots.
    speeds_max
        Maximum speed per leg, knots.
    speeds
        Speed per leg, knots.

    Returns
    -------
    tuple[float, float]
        Minimum and maximum mean speed achievable by the vessel, knots.
    """
    low = np.min(speeds_min)
    high = np.max(speeds_max)

    if np.isfinite(low) and np.isfinite(high) and (low < high):
        return low, high

    # technical bounds that are infinite or inverted fall back on the envelope of the
    # given speeds
    low = np.min(speeds)
    high = np.max(speeds)

    return low, high


def calculate_technical_speed_limits(vessel: Vessel) -> tuple[FloatArray, FloatArray]:
    """
    Calculate a vessel's minimum and maximum achievable speed from its propulsion load.

    Only the propulsion load sets the limits: a minimum load on the electrical or heat
    converter is ignored, although in extreme cases it could bind the speed.

    Parameters
    ----------
    vessel
        Vessel whose speed limits are calculated.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Minimum and maximum speed per leg, knots.
    """
    load = vessel.propulsion_load

    if isinstance(load, Expression):
        # an expression can only be evaluated, not read as a table, so it
        # cannot be reverse-looked-up; the other speed bounds govern instead
        return _unbounded_speed_limits(vessel)

    if isinstance(load, Scalar) or is_variable(load):
        return _unbounded_speed_limits(vessel)

    # the load is a Curve or a Surface
    converter = vessel.power_system.propulsion
    power_maximum = converter.power_capacity.get()
    minimum_load = converter.minimum_load

    if minimum_load is not None:
        power_minimum = minimum_load.get() * power_maximum
        speed_minimum = _calculate_speed_extremum(vessel, power_minimum, load)

    else:
        speed_minimum = load.x[0]

    # the power capacity may cap the speed below the load's largest speed
    speed_maximum = _calculate_speed_extremum(vessel, power_maximum, load)

    # the reverse lookup returns None for a load that is not strictly increasing
    if speed_minimum is None:
        speed_minimum = load.x[0]

    if speed_maximum is None:
        speed_maximum = load.x[-1]

    # the limits are per leg, as the capacity utilization moves the power limit
    speeds_minimum = _expand_speed_to_legs(vessel, speed_minimum)
    speeds_maximum = _expand_speed_to_legs(vessel, speed_maximum)

    return speeds_minimum, speeds_maximum


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


def verify_power_capacity(
    fleets: dict[str, Fleet], idx: int, scope: BunkerScopeID
) -> None:
    """
    Verify converter power capacity for every vessel entering a bunkering scope.

    Mirrors the multiplier gating of BunkerAlgorithm.build: only vessels with a
    positive multiplier enter the LP. Expected bunkering builds one LP per future
    time-step, each gated by that step's expected multiplier; the demands and
    times it reads are constant over the remaining horizon within a time-step,
    so gating on the horizon maximum covers every one of those builds.

    Parameters
    ----------
    fleets
        Fleets by name; each vessel the scope admits is verified.
    idx
        Current time-step index.
    scope
        Bunkering scope about to be solved.

    Raises
    ------
    PowerCapacityError
        If any vessel entering the scope has an energy demand that exceeds what its
        serving converter can deliver.
    """
    for fleet in fleets.values():
        for vessel in fleet.vessels:
            if scope == BunkerScopeID.EXISTING:
                multiplier = fleet.expectation.get_existing_multipliers(
                    vessel.name, idx
                )
            else:
                multiplier = np.max(
                    fleet.expectation.get_expected_multipliers(
                        vessel.name, slice(idx, None)
                    )
                )

            if multiplier > 0.0:
                verify_vessel_power_capacity(vessel, idx)


def verify_vessel_power_capacity(vessel: Vessel, idx: int) -> None:
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

    times_sea = [float(time) for time in expectation.get_time_sea(idx)]
    times_port = [float(time) for time in expectation.get_time_port(idx)]
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
            violations += _find_capacity_violations(
                converter,
                demand_type,
                [float(energy) for energy in energies[demand_type]],
                times,
                step_label,
            )

    if violations:
        raise PowerCapacityError(
            "{}: energy demand exceeds installed converter power:\n{}".format(
                vessel, "\n".join(violations)
            )
        )


def get_total_power_capacity(vessel: Vessel) -> float:
    """
    Return the total installed converter power capacity of a vessel.

    Parameters
    ----------
    vessel
        Vessel whose power-system converters are summed.

    Returns
    -------
    float
        Total installed power across the converters, MW.
    """
    return sum(
        converter.power_capacity.get()
        for converter in vessel.power_system.get_converters()
    )


def _find_capacity_violations(
    converter: Converter,
    demand_type: EnergyDemandTypeID,
    energies: list[float],
    times: list[float],
    step_label: str,
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
        Energy demand per step, GJ/year.
    times
        Time spent on each step, days/year.
    step_label
        Name of the step dimension, "leg" or "port", used in violation messages.

    Returns
    -------
    list[str]
        One message per step whose demand exceeds the deliverable energy.
    """
    power_capacity = converter.power_capacity.get()
    violations = []

    for step, (energy, time) in enumerate(zip(energies, times, strict=True)):
        deliverable = power_capacity * time * MWD_TO_GJ

        if energy - deliverable <= TOLERANCE * max(1.0, deliverable):
            continue

        implied_power = energy / (time * MWD_TO_GJ) if time > 0.0 else float("inf")
        violations.append(
            f"  {demand_type.name.lower()} demand on {step_label} {step} requires "
            f"{implied_power:.2f} MW but {converter} has "
            f"{power_capacity:.2f} MW installed."
        )

    return violations


def _unbounded_speed_limits(vessel: Vessel) -> tuple[FloatArray, FloatArray]:
    """
    Give a vessel no technical speed limit, expanded to one value per leg.

    Parameters
    ----------
    vessel
        Vessel for which the speed limits are expanded to legs.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Minimum and maximum speed per leg, both unbounded.
    """
    return _expand_speed_to_legs(vessel, -np.inf), _expand_speed_to_legs(vessel, np.inf)


def _expand_speed_to_legs(vessel: Vessel, speed: FloatLike) -> FloatArray:
    a = np.asarray(speed, dtype=float)

    if a.ndim == 0:
        n = vessel.route.get_number_of_legs()
        a = np.full(n, float(a), dtype=float)

    return a


def _calculate_speed_extremum(
    vessel: Vessel, power: float, load: Curve | Surface
) -> FloatLike | None:
    """
    Calculate the vessel speed at which a given minimum or maximum power is reached.

    Parameters
    ----------
    vessel
        Vessel whose speed extremum is calculated.
    power
        Minimum or maximum power of the converter, MW.
    load
        Propulsion load of the vessel.

    Returns
    -------
    FloatLike | None
        The speed at which the power is reached, knots, one per capacity utilization
        for a surface, or `None` when the load is not strictly increasing.
    """
    if is_surface(load):
        utilization = to_numpy(vessel.route.capacity_utilizations)
        return load.reverse_lookup(power, y=utilization)

    return load.reverse_lookup(power)


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
