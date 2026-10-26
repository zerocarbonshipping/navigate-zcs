# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Technology packages: building, combined effects, cost flows, NPVs and charges."""

from __future__ import annotations

import itertools
import math
from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandID
from navigate.core.technology_package import TechnologyPackage
from navigate.simulation.economics.flows import (
    Component,
    add_capex,
    add_fixed_opex,
    expand_to_flow,
    get_flow_size,
    trim_flow_to_lifetime,
)
from navigate.simulation.economics.metric import (
    calculate_levelized_cost,
    calculate_net_present_value,
)
from navigate.util import ROUND_OFF

if TYPE_CHECKING:
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.technology_package import PackageCostFlows
    from navigate.core.types_ import CurveInput
    from navigate.util.types_ import FloatArray


def build_technology_packages(
    technologies: list[Technology],
) -> list[TechnologyPackage]:
    """
    Sort technologies by CAPEX and organize them into cumulative packages.

    Parameters
    ----------
    technologies
        Technologies to organize into packages.

    Returns
    -------
    list[TechnologyPackage]
        Technology packages from empty to full: package ``i + 1`` is the first to hold
        technology ``i`` of the CAPEX order.
    """
    ordered = sorted(technologies, key=lambda technology: technology.capex.get())
    return [TechnologyPackage(ordered[:i]) for i in range(len(ordered) + 1)]


def get_technologies_by_capex(packages: list[TechnologyPackage]) -> list[Technology]:
    """
    Return the technologies in CAPEX order, the order the packages add them in.

    Parameters
    ----------
    packages
        All technology packages, from empty to full.

    Returns
    -------
    list[Technology]
        Technologies of the full package, cheapest first.
    """
    return packages[-1].technologies


def _calculate_combined_effects(package: TechnologyPackage) -> None:
    """
    Calculate a package's combined savings, powers, transfer curves and shore power.

    The residual-energy calculation reads these instead of recombining the
    technologies on every call.

    Parameters
    ----------
    package
        Technology package whose combined effects are calculated in place.
    """
    technologies = package.technologies
    energy_savings = [technology.energy_saving for technology in technologies]
    external_powers = [technology.external_power for technology in technologies]
    capacities = [technology.shore_power_capacity.get() for technology in technologies]

    savings = {}
    powers = {}

    for energy_id in EnergyDemandID:
        # savings compound: each technology saves its fraction of what the others leave
        retained = [1.0 - saving[energy_id].get() for saving in energy_savings]
        savings[energy_id] = 1.0 - math.prod(retained)

        added = [power[energy_id].get() for power in external_powers]
        powers[energy_id] = math.fsum(added)

    transfer_curves = {}

    for pair in itertools.product(EnergyDemandID, EnergyDemandID):
        curves = [technology.power_transfer[pair] for technology in technologies]
        transferring = [curve for curve in curves if _transfers_power(curve)]

        if transferring:
            transfer_curves[pair] = transferring

    package.energy_saving = savings
    package.external_power = powers
    package.transfer_curves = transfer_curves
    package.shore_power_capacity = math.fsum(capacities)


def _transfers_power(curve: CurveInput) -> bool:
    """Return whether a power-transfer curve transfers any power."""
    return not (isinstance(curve, Scalar) and curve.get() == 0.0)


def update_packages(
    packages: list[TechnologyPackage], package_cost_flows: PackageCostFlows, time: float
) -> None:
    """
    Update every package's combined effects and move the cost flows to a new time.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, ordered by increasing size.
    package_cost_flows
        Package cost flows; the flows of the previous decision time are dropped.
    time
        Investment decision time, days.
    """
    package_cost_flows.time = time
    package_cost_flows.by_horizon.clear()

    for package in packages:
        _calculate_combined_effects(package)


def get_package_cost_flows(
    packages: list[TechnologyPackage],
    package_cost_flows: PackageCostFlows,
    horizon: float,
) -> list[FloatArray]:
    """
    Return each package's cumulative CAPEX and OPEX cost flow over a horizon.

    The flows start at the decision time of ``package_cost_flows`` and span the
    ``horizon`` years the installation serves, the last partial year prorated. A
    replacement whose lifetime outlasts the horizon is charged for the share of it the
    horizon holds. The flows are built on the first request for a horizon and kept until
    ``update_packages`` moves the time on.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, ordered by increasing size.
    package_cost_flows
        Package cost flows of the current decision time.
    horizon
        Time the installation serves, years.

    Returns
    -------
    list[FloatArray]
        Cost flow of each package, USD/year; zero for the empty package.
    """
    key = round(horizon, ROUND_OFF)
    flows = package_cost_flows.by_horizon.get(key)

    if flows is None:
        flows = _build_package_cost_flows(packages, key, package_cost_flows.time)
        package_cost_flows.by_horizon[key] = flows

    return flows


def _build_package_cost_flows(
    packages: list[TechnologyPackage], horizon: float, time: float
) -> list[FloatArray]:
    """Build each package's cost flow over a horizon from its technologies."""
    # packages nest: package i holds the first i technologies of the full package
    cumulative = np.zeros(get_flow_size(lead_time=0.0, lifetime=horizon))
    flows = [cumulative]

    for technology in packages[-1].technologies:
        component = _build_technology_component(technology, horizon, time)
        cumulative = cumulative + component.get_cost_flow()
        flows.append(cumulative)

    return [trim_flow_to_lifetime(flow, horizon) for flow in flows]


def _build_technology_component(
    technology: Technology, horizon: float, time: float
) -> Component:
    """Build a technology's CAPEX and OPEX cost component over a horizon."""
    component = Component(0.0, horizon, time)
    component.attach_machinery_cycle(technology)

    add_capex(component, technology.capex.get)
    add_fixed_opex(component, technology.opex.get)

    return component


def calculate_newbuild_npv(
    package_savings: list[FloatArray],
    cost_flows: list[FloatArray],
    discount_rate: float,
) -> FloatArray:
    """
    Calculate the NPV of installing each package on a newbuild.

    Parameters
    ----------
    package_savings
        Yearly saving flow of each package over the vessel lifetime, USD/year.
    cost_flows
        Cost flow of each package over the vessel lifetime, USD/year.
    discount_rate
        Discount rate of the investment, fraction.

    Returns
    -------
    FloatArray
        NPV of each package, USD; zero for the empty package.
    """
    npv = np.zeros(len(package_savings))

    for package_idx in range(1, len(npv)):
        cash_flow = package_savings[package_idx] - cost_flows[package_idx]
        npv[package_idx] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def calculate_retrofit_npv(
    package_idx: int,
    package_savings: list[FloatArray],
    cost_flows: list[FloatArray],
    remaining: float,
    discount_rate: float,
) -> FloatArray:
    """
    Calculate the NPV of retrofitting from a package to each larger package.

    Entry ``step`` is the NPV of the jump from ``package_idx`` to
    ``package_idx + step``: the saving flow of package ``package_idx``, trimmed to the
    remaining lifetime, less the jump's incremental cost flow over the same years.

    Parameters
    ----------
    package_idx
        Package the vessels currently sit at.
    package_savings
        Yearly saving flow of each package, USD/year.
    cost_flows
        Cost flow of each package over the remaining lifetime, USD/year.
    remaining
        Remaining vessel lifetime, years.
    discount_rate
        Discount rate of the investment, fraction.

    Returns
    -------
    FloatArray
        NPV of each retrofit step, USD; zero for the stay option.
    """
    savings_flow = trim_flow_to_lifetime(package_savings[package_idx], remaining)
    n_steps = len(package_savings) - package_idx
    npv = np.zeros(n_steps)

    for step in range(1, n_steps):
        step_cost = cost_flows[package_idx + step] - cost_flows[package_idx]
        cash_flow = savings_flow - step_cost
        npv[step] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def calculate_retrofit_charter_rates(
    package_idx: int,
    cost_flows: list[FloatArray],
    remaining: float,
    discount_rate: float,
) -> FloatArray:
    """
    Levelize the cost of each retrofit step over the remaining lifetime.

    Mirrors the incremental cost flows of ``calculate_retrofit_npv``: entry ``step`` is
    the constant yearly charge that recovers the cost of jumping from ``package_idx``
    to ``package_idx + step`` over the ``remaining`` years the vessel still serves.

    Parameters
    ----------
    package_idx
        Package the vessels currently sit at.
    cost_flows
        Cost flow of each package over the remaining lifetime, USD/year.
    remaining
        Remaining vessel lifetime, years.
    discount_rate
        Discount rate of the levelization, fraction.

    Returns
    -------
    FloatArray
        Constant yearly charge of each retrofit step, USD/year; zero for the stay
        option.
    """
    n_steps = len(cost_flows) - package_idx
    rates = np.zeros(n_steps)

    for step in range(1, n_steps):
        step_cost = cost_flows[package_idx + step] - cost_flows[package_idx]
        rates[step] = _levelize_package_cost(step_cost, remaining, discount_rate)

    return rates


def calculate_package_charter_rates(
    packages: list[TechnologyPackage],
    package_cost_flows: PackageCostFlows,
    vessel: Vessel,
) -> FloatArray:
    """
    Levelize each package's cost, installed at build, over the vessel lifetime.

    The vessel cost of capital levelizes it, so the charge is consistent with the
    freight-rate NPVs it feeds; the adoption decision keeps its own discount rate.

    Parameters
    ----------
    packages
        All technology packages, from empty to full.
    package_cost_flows
        Package cost flows of the current decision time.
    vessel
        Vessel whose lifetime and cost of capital govern the levelization.

    Returns
    -------
    FloatArray
        Constant yearly charge per package, USD/year.
    """
    lifetime = vessel.lifetime.get()
    discount_rate = vessel.cost_of_capital.get()
    flows = get_package_cost_flows(packages, package_cost_flows, lifetime)

    rates = [_levelize_package_cost(flow, lifetime, discount_rate) for flow in flows]

    return np.array(rates)


def _levelize_package_cost(
    cost_flow: FloatArray, horizon: float, discount_rate: float
) -> float:
    """
    Levelize a technology cost flow into a USD/year charge over a horizon.

    The cost flow spans the horizon with its last partial year prorated, as
    ``get_package_cost_flows`` builds it. It is divided by the NPV of the operating-year
    flow over the same horizon, so that discounting the constant charge over the horizon
    at ``discount_rate`` reproduces the NPV of the cost flow exactly.

    Parameters
    ----------
    cost_flow
        Yearly technology cost flow (CAPEX, OPEX, and replacements) over the horizon,
        from the install time.
    horizon
        Time the installation serves, years: the vessel lifetime for a newbuild install,
        the remaining vessel lifetime for a retrofit.
    discount_rate
        Discount rate of the levelization, fraction.

    Returns
    -------
    float
        Constant yearly charge in USD/year.
    """
    # the leveling flow prorates the final partial year as the cost flow does, so
    # the charge is recovered over exactly the horizon
    level_flow = expand_to_flow(horizon, 1.0)

    return calculate_levelized_cost(cost_flow, level_flow, discount_rate)
