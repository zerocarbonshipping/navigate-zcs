# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Technology packages: building, combined effects, cost flows, charges."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandID
from navigate.core.technology_package import TechnologyPackage
from navigate.simulation.economics.flows import (
    Component,
    add_capex_flow,
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
) -> tuple[list[TechnologyPackage], dict[int, int]]:
    """
    Sort technologies by CAPEX and organize them into cumulative packages.

    Parameters
    ----------
    technologies
        Technologies to organize into packages.

    Returns
    -------
    list[TechnologyPackage]
        Technology packages from empty to full.
    dict[int, int]
        Map from a package index to the index, in ``technologies``, of the technology
        that package adds.
    """
    sorted_pairs = sorted(enumerate(technologies), key=lambda p: p[1].capex.get())
    sorted_techs = [t for _, t in sorted_pairs]
    packages = [
        TechnologyPackage(sorted_techs[:i]) for i in range(len(sorted_techs) + 1)
    ]
    package_to_technology_map = {
        i: sorted_pairs[i - 1][0] for i in range(1, len(sorted_pairs) + 1)
    }

    return packages, package_to_technology_map


def _refresh_combined_effects(package: TechnologyPackage) -> None:
    """
    Refresh a package's combined savings, powers and transfer curves.

    The residual-energy calculation reads these instead of recombining the
    technologies on every call.

    Parameters
    ----------
    package
        Technology package whose combined effects are refreshed in place.
    """
    technologies = package.technologies

    arr_sp = np.array([t.shore_power_capacity.get() for t in technologies])
    package.shore_power_capacity = float(np.sum(arr_sp))

    compound_savings: dict[EnergyDemandID, float] = {}
    compound_powers: dict[EnergyDemandID, float] = {}

    # savings compound: each technology saves its fraction of what the others leave
    for energy_id in EnergyDemandID:
        arr = np.array([t.energy_saving[energy_id].get() for t in technologies])
        compound_savings[energy_id] = 1.0 - float(np.prod(1.0 - arr))

    for energy_id in EnergyDemandID:
        arr = np.array([t.external_power[energy_id].get() for t in technologies])
        compound_powers[energy_id] = float(np.sum(arr))

    package.compound_savings = compound_savings
    package.compound_powers = compound_powers

    transfer_curves: dict[tuple[EnergyDemandID, EnergyDemandID], list[CurveInput]] = {}

    for source in EnergyDemandID:
        for destination in EnergyDemandID:
            curves: list[CurveInput] = []

            for tech in technologies:
                obj = tech.power_transfer[(source, destination)]

                if isinstance(obj, Scalar) and obj.get() == 0.0:
                    continue

                curves.append(obj)

            if curves:
                transfer_curves[(source, destination)] = curves

    package.transfer_curves = transfer_curves


def preprocess_packages(
    packages: list[TechnologyPackage], cost_flows: PackageCostFlows, time: float
) -> None:
    """
    Refresh every package's combined effects and move its cost flows to a new time.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, ordered by increasing size.
    cost_flows
        Package cost flows; the flows of the previous decision time are dropped.
    time
        Investment decision time, days.
    """
    cost_flows.time = time
    cost_flows.by_horizon.clear()

    for pkg in packages:
        if not pkg.is_empty:
            _refresh_combined_effects(pkg)


def get_package_cost_flows(
    packages: list[TechnologyPackage], cost_flows: PackageCostFlows, horizon: float
) -> list[FloatArray]:
    """
    Return each package's cumulative CAPEX and OPEX cost flow over a horizon.

    The flows start at the decision time of ``cost_flows`` and span the ``horizon``
    years the installation serves, the last partial year prorated. A replacement whose
    lifetime outlasts the horizon is charged for the share of it the horizon holds.
    The flows are built on the first request for a horizon and kept until
    ``preprocess_packages`` moves the time on.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, ordered by increasing size.
    cost_flows
        Package cost flows of the current decision time.
    horizon
        Time the installation serves, years.

    Returns
    -------
    list[FloatArray]
        Cost flow of each package, USD/year; zero for the empty package.
    """
    key = round(horizon, ROUND_OFF)
    flows = cost_flows.by_horizon.get(key)

    if flows is None:
        flows = _build_package_cost_flows(packages, key, cost_flows.time)
        cost_flows.by_horizon[key] = flows

    return flows


def _build_package_cost_flows(
    packages: list[TechnologyPackage], horizon: float, time: float
) -> list[FloatArray]:
    """Build each package's cost flow over a horizon from its technologies."""
    # packages are nested, package i holding the first i technologies of the last
    cumulative = np.zeros(get_flow_size(lead_time=0.0, lifetime=horizon), dtype=float)
    flows = [cumulative]

    for technology in packages[-1].technologies:
        component = _build_technology_component(technology, horizon, time)
        cumulative = cumulative + component.get_cost_flow()
        flows.append(cumulative)

    return [trim_flow_to_lifetime(flow, horizon) for flow in flows]


def npv_for_newbuilds(
    packages_saving: list[FloatArray],
    cost_flows: list[FloatArray],
    discount_rate: float,
) -> FloatArray:
    """
    Calculate the NPV of installing each package on a newbuild.

    Parameters
    ----------
    packages_saving
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
    n_pkgs = len(packages_saving)
    npv = np.zeros(n_pkgs, dtype=float)

    for pkg_idx in range(1, n_pkgs):
        cash_flow = packages_saving[pkg_idx] - cost_flows[pkg_idx]
        npv[pkg_idx] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def npv_for_retrofit_steps(
    pkg_idx: int,
    package_savings: list[FloatArray],
    cost_flows: list[FloatArray],
    remaining: float,
    discount_rate: float,
) -> FloatArray:
    """
    Calculate the NPV of retrofitting from a package to each larger package.

    Entry ``step`` is the NPV of the jump from ``pkg_idx`` to ``pkg_idx + step``: the
    saving flow of package ``pkg_idx``, trimmed to the remaining lifetime, less the
    jump's incremental cost flow over the same years.

    Parameters
    ----------
    pkg_idx
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
    n_pkgs = len(package_savings)
    savings_flow = trim_flow_to_lifetime(package_savings[pkg_idx], remaining)
    max_steps = n_pkgs - pkg_idx
    npv = np.full(max_steps, -np.inf, dtype=float)
    npv[0] = 0.0

    for step in range(1, max_steps):
        inc_cost_flow = cost_flows[pkg_idx + step] - cost_flows[pkg_idx]
        cash_flow = savings_flow - inc_cost_flow
        npv[step] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def annual_costs_for_retrofit_steps(
    pkg_idx: int,
    cost_flows: list[FloatArray],
    remaining: float,
    discount_rate: float,
) -> FloatArray:
    """
    Levelize the cost of each retrofit step over the remaining lifetime.

    Mirrors the incremental cost flows of ``npv_for_retrofit_steps``: entry ``step`` is
    the constant yearly charge that recovers the cost of jumping from ``pkg_idx`` to
    ``pkg_idx + step`` over the ``remaining`` years the vessel still serves.

    Parameters
    ----------
    pkg_idx
        Package level the vessels currently sit at.
    cost_flows
        Cost flow of each package over the remaining lifetime, USD/year.
    remaining
        Remaining vessel lifetime, years.
    discount_rate
        Discount rate of the levelization, fraction.

    Returns
    -------
    FloatArray
        Constant yearly charge per retrofit step (0 for the stay option), USD/year.
    """
    max_steps = len(cost_flows) - pkg_idx
    annual = np.zeros(max_steps, dtype=float)

    for step in range(1, max_steps):
        inc_cost_flow = cost_flows[pkg_idx + step] - cost_flows[pkg_idx]
        annual[step] = levelize_package_cost(inc_cost_flow, remaining, discount_rate)

    return annual


def calculate_package_charter_rates(
    packages: list[TechnologyPackage], cost_flows: PackageCostFlows, vessel: Vessel
) -> FloatArray:
    """
    Levelize each package's cost, installed at build, over the vessel lifetime.

    The vessel cost of capital levelizes it, so the charge is consistent with the
    freight-rate NPVs it feeds; the adoption decision keeps its own discount rate.

    Parameters
    ----------
    packages
        All technology packages, from empty to full.
    cost_flows
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

    return np.array(
        [
            levelize_package_cost(cost_flow, lifetime, discount_rate)
            for cost_flow in get_package_cost_flows(packages, cost_flows, lifetime)
        ]
    )


def levelize_package_cost(
    cost_flow: FloatArray, window: float, discount_rate: float
) -> float:
    """
    Levelize a technology cost flow into a USD/year charge over a service window.

    The cost flow spans the window with its last partial year prorated, as
    ``get_package_cost_flows`` builds it. It is divided by the NPV of the operating-year
    flow over the same window, so that discounting the constant charge over the window
    at `discount_rate` reproduces the NPV of the cost flow exactly.

    Parameters
    ----------
    cost_flow
        Yearly technology cost flow (CAPEX, OPEX, and replacements) over the window,
        from the install time.
    window
        Time the installation serves, years: the vessel lifetime for a newbuild install,
        the remaining vessel lifetime for a retrofit.
    discount_rate
        Discount rate of the levelization, fraction.

    Returns
    -------
    float
        Constant yearly charge in USD/year.
    """
    if window <= 0.0:
        return 0.0

    # the leveling flow prorates the final partial year as the cost flow does, so
    # the charge is recovered over exactly `window` years
    level_flow = expand_to_flow(window, 1.0)

    return calculate_levelized_cost(cost_flow, level_flow, discount_rate)


def _build_technology_component(
    technology: Technology, horizon: float, time_initial: float
) -> Component:
    component = Component(0.0, horizon, time_initial)
    component.initialize_machinery_component(technology)

    add_capex_flow(component, technology.capex.get)
    add_fixed_opex(component, technology.opex.get)

    return component
