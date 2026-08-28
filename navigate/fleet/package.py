# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from math import ceil

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.vessel import Vessel
from navigate.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    expand_to_flow,
    get_flow_residual,
)
from navigate.economics.metric import calculate_levelized_cost, calculate_net_present_value


class Package:
    """
    A precomputed bundle of technologies for efficient residual-energy evaluation.

    Precomputes compound savings, compound external powers, and non-zero
    transfer curves so that downstream consumers (``calculate_residual_energy``
    and friends) avoid redundant per-call work.

    Precomputed state is refreshed every time-step via ``precompute()``
    (called from ``preprocess_packages``), since technology properties
    may be time-dependent.
    """

    def __init__(self, technologies: list[Technology]):

        self._technologies: list[Technology] = technologies

        self._compound_savings: dict[EnergyDemandTypeID, float] = {}
        self._compound_powers: dict[EnergyDemandTypeID, float] = {}
        self._transfer_curves: dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID], list[Curve | Scalar]] = {}
        self._shore_power_capacity: float = 0.

        self.cost_flow: np.ndarray | None = None

    @property
    def is_empty(self) -> bool:
        return len(self._technologies) == 0

    @property
    def technologies(self) -> list[Technology]:
        return self._technologies

    @property
    def compound_savings(self) -> dict[EnergyDemandTypeID, float]:
        return self._compound_savings

    @property
    def compound_powers(self) -> dict[EnergyDemandTypeID, float]:
        return self._compound_powers

    @property
    def transfer_curves(self) -> dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID],
                                      list[Curve | Scalar]]:
        return self._transfer_curves

    @property
    def includes_transfer(self) -> bool:
        return bool(self._transfer_curves)

    @property
    def shore_power_capacity(self) -> float:
        return self._shore_power_capacity

    def __len__(self) -> int:
        return len(self._technologies)

    def __iter__(self):
        return iter(self._technologies)

    def __getitem__(self, index):
        return self._technologies[index]

    def __bool__(self) -> bool:
        return len(self._technologies) > 0

    def precompute(self):
        """Refresh compound savings, powers, and transfer curves from current technology state."""

        self._compound_savings.clear()
        self._compound_powers.clear()
        self._transfer_curves.clear()

        # Shore power capacity: sum across technologies
        arr_sp = np.array([t.shore_power_capacity.get() for t in self._technologies])
        self._shore_power_capacity = float(np.sum(arr_sp))

        # Compound savings: 1 - prod(1 - saving_i) per energy type
        for energy_id in EnergyDemandTypeID:
            arr = np.array([t.get_energy_saving(energy_id).get() for t in self._technologies])
            self._compound_savings[energy_id] = 1. - float(np.prod(1. - arr))

        # Compound powers: sum(power_i) per energy type
        for energy_id in EnergyDemandTypeID:
            arr = np.array([t.get_external_power(energy_id).get() for t in self._technologies])
            self._compound_powers[energy_id] = float(np.sum(arr))

        # Transfer curves: collect only non-zero (source, destination) pairs
        for source in EnergyDemandTypeID:
            for destination in EnergyDemandTypeID:

                curves: list[Curve | Scalar] = []

                for tech in self._technologies:
                    obj = tech.get_power_transfer(source, destination)

                    if isinstance(obj, Scalar) and obj.get() == 0.:
                        continue

                    curves.append(obj)

                if curves:
                    self._transfer_curves[(source, destination)] = curves


def preprocess_packages(packages: list[Package],
                        vessels: list[Vessel],
                        time: float
                        ) -> None:
    """
    Refresh all precomputed state on each Package and compute cost flows.

    For each package:
      - Recomputes compound savings, powers, and transfer curves.
      - Computes cumulative CAPEX+OPEX cost_flow and stores it.

    Parameters
    ----------
    packages
        All technology packages (from empty to full), ordered by increasing size.
    vessels
        Fleet vessels (used to determine maximum lifetime).
    time
        Current simulation time (days since start), used as the investment decision time.
    """

    lifetime = int(np.ceil(max(v.lifetime.get() for v in vessels)))

    # Empty-package component and cost
    empty_component = Component()
    empty_component.initialize_flow(0., lifetime, time)
    packages[0].cost_flow = np.zeros(lifetime, dtype=float)

    last_package = packages[-1]
    cumulative_component = empty_component

    for i, technology in enumerate(last_package.technologies):
        tech_component = _build_technology_component(technology, lifetime, time)

        new_cumulative = Component()
        new_cumulative.initialize_flow(0., lifetime, time)
        new_cumulative.add_component(cumulative_component)
        new_cumulative.add_component(tech_component)
        cumulative_component = new_cumulative

        pkg = packages[i + 1]
        pkg.cost_flow = new_cumulative.get_cost_flow()

    # Precompute energy state for all non-empty packages
    for pkg in packages:
        if not pkg.is_empty:
            pkg.precompute()


def npv_for_newbuilds(packages_saving: list[np.ndarray],
                      packages: list[Package],
                      discount_rate: float):

    n_pkgs = len(packages_saving)
    npv = np.zeros(n_pkgs, dtype=float)

    for pkg_idx in range(1, n_pkgs):
        cash_flow = packages_saving[pkg_idx] - packages[pkg_idx].cost_flow
        npv[pkg_idx] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def npv_for_retrofit_steps(pkg_idx: int,
                           package_savings: list[np.ndarray],
                           packages: list[Package],
                           remaining: float,
                           discount_rate: float):

    n_pkgs = len(package_savings)
    savings_flow = _trim_flow_to_life(package_savings[pkg_idx], remaining)
    max_steps = n_pkgs - pkg_idx
    npv = np.full(max_steps, -np.inf, dtype=float)
    npv[0] = 0.

    for step in range(1, max_steps):
        inc_cost_flow = _incremental_cost_flow(packages, pkg_idx, step, remaining)
        cash_flow = savings_flow - inc_cost_flow
        npv[step] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def _incremental_cost_flow(packages: list[Package],
                           pkg_idx: int,
                           step: int,
                           remaining: float) -> np.ndarray:
    """Cost flow of jumping from `pkg_idx` to `pkg_idx + step`, trimmed to the remaining lifetime."""

    inc_cost_flow = packages[pkg_idx + step].cost_flow - packages[pkg_idx].cost_flow

    return _trim_flow_to_life(inc_cost_flow, remaining)


def annual_costs_for_retrofit_steps(pkg_idx: int,
                                    packages: list[Package],
                                    remaining: float,
                                    discount_rate: float) -> np.ndarray:
    """
    Levelized USD/year charge per retrofit step, amortized over the remaining vessel lifetime.

    Mirrors the incremental cost flows of ``npv_for_retrofit_steps``: entry ``step`` is the
    constant yearly charge that recovers the cost of jumping from ``pkg_idx`` to
    ``pkg_idx + step`` over the ``remaining`` years the vessel still serves.

    Parameters
    ----------
    pkg_idx
        Package level the vessels currently sit at.
    packages
        All technology packages (from empty to full), ordered by increasing size.
    remaining
        Remaining vessel lifetime in years.
    discount_rate
        Discount rate used for the levelization.

    Returns
    -------
    np.ndarray
        Constant yearly charge per retrofit step (0 for the stay option), USD/year.
    """

    max_steps = len(packages) - pkg_idx
    annual = np.zeros(max_steps, dtype=float)

    for step in range(1, max_steps):
        inc_cost_flow = _incremental_cost_flow(packages, pkg_idx, step, remaining)
        annual[step] = _levelize_trimmed(inc_cost_flow, remaining, discount_rate)

    return annual


def levelize_package_cost(cost_flow: np.ndarray,
                          window: float,
                          discount_rate: float) -> float:
    """
    Levelize a technology cost flow into a constant USD/year charge over a service window.

    The flow is trimmed to the window (with the last partial year prorated) and divided by the
    NPV of the operating-year flow over the same window, so that discounting the constant charge
    over the window at `discount_rate` reproduces the NPV of the trimmed cost flow exactly.

    Parameters
    ----------
    cost_flow
        Yearly technology cost flow (CAPEX, OPEX, and replacements) from the install time.
    window
        Years the installation serves: the vessel lifetime for a newbuild install, the
        remaining vessel lifetime for a retrofit.
    discount_rate
        Discount rate used for the levelization.

    Returns
    -------
    float
        Constant yearly charge in USD/year.
    """

    if window <= 0.:
        return 0.

    return _levelize_trimmed(_trim_flow_to_life(cost_flow, window), window, discount_rate)


def _levelize_trimmed(trimmed: np.ndarray, window: float, discount_rate: float) -> float:
    """Levelize a cost flow already trimmed to `window` years into a constant USD/year charge."""

    # the leveling flow prorates the final partial year to match the trimmed
    # cost flow, so the charge is recovered over `window` years rather than
    # the padded whole-year horizon
    level_flow = expand_to_flow(window, 1.)

    return calculate_levelized_cost(trimmed, level_flow, discount_rate)


def _build_technology_component(technology: Technology, vessel_lifetime: float, time_initial: float) -> Component:

    component = Component()

    component.initialize_flow(0., vessel_lifetime, time_initial)
    component.initialize_machinery_component(technology)

    capex = lambda time: technology.CAPEX.get(time)
    opex = lambda time: technology.OPEX.get(time)

    add_capex_flow(component, capex)
    add_fixed_opex(component, opex)

    return component


def _trim_flow_to_life(flow: np.ndarray, remaining_life: float):

    n = int(ceil(remaining_life))
    partial, residual = get_flow_residual(remaining_life)

    trimmed = flow[:n].copy()
    if partial:
        trimmed[-1] *= residual

    return trimmed
