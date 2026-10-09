# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Technology packages: precomputed combined effects, cost flows and their NPVs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core import Scalar
from navigate.core.enum_ import EnergyDemandTypeID
from navigate.economics.flows import (
    Component,
    add_capex_flow,
    add_fixed_opex,
    expand_to_flow,
    trim_flow_to_lifetime,
)
from navigate.economics.metric import (
    calculate_levelized_cost,
    calculate_net_present_value,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.core.types_ import CurveInput
    from navigate.util.types_ import FloatArray


class Package:
    """
    A bundle of technologies with their combined effects precomputed.

    The residual-energy calculation reads the combined savings, external powers and
    non-zero transfer curves instead of recombining the technologies on every call.
    ``preprocess_packages`` refreshes them every time-step, as technology properties
    may depend on time.

    Parameters
    ----------
    technologies
        Technologies in the package.
    """

    def __init__(self, technologies: list[Technology]) -> None:
        self._technologies: list[Technology] = technologies

        self._compound_savings: dict[EnergyDemandTypeID, float] = {}
        self._compound_powers: dict[EnergyDemandTypeID, float] = {}
        self._transfer_curves: dict[
            tuple[EnergyDemandTypeID, EnergyDemandTypeID], list[CurveInput]
        ] = {}
        self._shore_power_capacity: float = 0.0

        self.cost_flow: FloatArray = np.zeros(0, dtype=float)

    @property
    def is_empty(self) -> bool:
        """Whether the package holds no technology."""
        return len(self._technologies) == 0

    @property
    def technologies(self) -> list[Technology]:
        """Technologies in the package."""
        return self._technologies

    @property
    def compound_savings(self) -> dict[EnergyDemandTypeID, float]:
        """Combined energy-saving fraction per energy demand type."""
        return self._compound_savings

    @property
    def compound_powers(self) -> dict[EnergyDemandTypeID, float]:
        """Summed external power per energy demand type, MW."""
        return self._compound_powers

    @property
    def transfer_curves(
        self,
    ) -> dict[tuple[EnergyDemandTypeID, EnergyDemandTypeID], list[CurveInput]]:
        """Power-transfer curves per (source, destination) pair with any transfer."""
        return self._transfer_curves

    @property
    def includes_transfer(self) -> bool:
        """Whether any technology transfers power between energy demand types."""
        return bool(self._transfer_curves)

    @property
    def shore_power_capacity(self) -> float:
        """Summed shore power connection capacity, MW."""
        return self._shore_power_capacity

    def __len__(self) -> int:
        return len(self._technologies)

    def __iter__(self) -> Iterator[Technology]:
        return iter(self._technologies)

    def __getitem__(self, index: int) -> Technology:
        return self._technologies[index]

    def __bool__(self) -> bool:
        return len(self._technologies) > 0

    def precompute(self) -> None:
        """Refresh the combined savings, powers and transfer curves."""
        self._compound_savings.clear()
        self._compound_powers.clear()
        self._transfer_curves.clear()

        arr_sp = np.array([t.shore_power_capacity.get() for t in self._technologies])
        self._shore_power_capacity = float(np.sum(arr_sp))

        # savings compound: each technology saves its fraction of what the others leave
        for energy_id in EnergyDemandTypeID:
            arr = np.array(
                [t.energy_saving[energy_id].get() for t in self._technologies]
            )
            self._compound_savings[energy_id] = 1.0 - float(np.prod(1.0 - arr))

        for energy_id in EnergyDemandTypeID:
            arr = np.array(
                [t.external_power[energy_id].get() for t in self._technologies]
            )
            self._compound_powers[energy_id] = float(np.sum(arr))

        for source in EnergyDemandTypeID:
            for destination in EnergyDemandTypeID:
                curves: list[CurveInput] = []

                for tech in self._technologies:
                    obj = tech.power_transfer[(source, destination)]

                    if isinstance(obj, Scalar) and obj.get() == 0.0:
                        continue

                    curves.append(obj)

                if curves:
                    self._transfer_curves[(source, destination)] = curves


def preprocess_packages(
    packages: list[Package], vessels: list[Vessel], time: float
) -> None:
    """
    Refresh every package's combined effects and cumulative CAPEX and OPEX cost flow.

    Parameters
    ----------
    packages
        All technology packages, from empty to full, ordered by increasing size.
    vessels
        Fleet vessels; the longest lifetime sets the cost-flow horizon.
    time
        Investment decision time, days.
    """
    lifetime = int(np.ceil(max(v.lifetime.get() for v in vessels)))

    empty_component = Component(0.0, lifetime, time)
    packages[0].cost_flow = np.zeros(lifetime, dtype=float)

    last_package = packages[-1]
    cumulative_component = empty_component

    for i, technology in enumerate(last_package.technologies):
        tech_component = _build_technology_component(technology, lifetime, time)

        new_cumulative = Component(0.0, lifetime, time)
        new_cumulative.add_component(cumulative_component)
        new_cumulative.add_component(tech_component)
        cumulative_component = new_cumulative

        pkg = packages[i + 1]
        pkg.cost_flow = new_cumulative.get_cost_flow()

    for pkg in packages:
        if not pkg.is_empty:
            pkg.precompute()


def npv_for_newbuilds(
    packages_saving: list[FloatArray], packages: list[Package], discount_rate: float
) -> FloatArray:
    """
    Calculate the NPV of installing each package on a newbuild.

    A package's cost flow covers the fleet's longest vessel lifetime; it is cut to
    the saving flow, which covers the lifetime of the vessel the package goes on.

    Parameters
    ----------
    packages_saving
        Yearly saving flow of each package over the vessel's lifetime, USD/year.
    packages
        All technology packages, from empty to full.
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
        saving_flow = packages_saving[pkg_idx]
        cost_flow = packages[pkg_idx].cost_flow[: len(saving_flow)]
        cash_flow = saving_flow - cost_flow
        npv[pkg_idx] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def npv_for_retrofit_steps(
    pkg_idx: int,
    package_savings: list[FloatArray],
    packages: list[Package],
    remaining: float,
    discount_rate: float,
) -> FloatArray:
    """
    Calculate the NPV of retrofitting from a package to each larger package.

    Entry ``step`` is the NPV of the jump from ``pkg_idx`` to ``pkg_idx + step``: the
    saving flow of package ``pkg_idx`` less the jump's incremental cost flow, both
    trimmed to the remaining lifetime.

    Parameters
    ----------
    pkg_idx
        Package the vessels currently sit at.
    package_savings
        Yearly saving flow of each package, USD/year.
    packages
        All technology packages, from empty to full.
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
        inc_cost_flow = _incremental_cost_flow(packages, pkg_idx, step, remaining)
        cash_flow = savings_flow - inc_cost_flow
        npv[step] = calculate_net_present_value(cash_flow, discount_rate)

    return npv


def _incremental_cost_flow(
    packages: list[Package], pkg_idx: int, step: int, remaining: float
) -> FloatArray:
    """Cost flow from `pkg_idx` to `pkg_idx + step`, trimmed to remaining lifetime."""
    inc_cost_flow = packages[pkg_idx + step].cost_flow - packages[pkg_idx].cost_flow

    return trim_flow_to_lifetime(inc_cost_flow, remaining)


def annual_costs_for_retrofit_steps(
    pkg_idx: int, packages: list[Package], remaining: float, discount_rate: float
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
    packages
        All technology packages (from empty to full), ordered by increasing size.
    remaining
        Remaining vessel lifetime, years.
    discount_rate
        Discount rate of the levelization, fraction.

    Returns
    -------
    FloatArray
        Constant yearly charge per retrofit step (0 for the stay option), USD/year.
    """
    max_steps = len(packages) - pkg_idx
    annual = np.zeros(max_steps, dtype=float)

    for step in range(1, max_steps):
        inc_cost_flow = _incremental_cost_flow(packages, pkg_idx, step, remaining)
        annual[step] = _levelize_trimmed(inc_cost_flow, remaining, discount_rate)

    return annual


def levelize_package_cost(
    cost_flow: FloatArray, window: float, discount_rate: float
) -> float:
    """
    Levelize a technology cost flow into a USD/year charge over a service window.

    The flow is trimmed to the window (with the last partial year prorated) and divided
    by the NPV of the operating-year flow over the same window, so that discounting the
    constant charge over the window at `discount_rate` reproduces the NPV of the trimmed
    cost flow exactly.

    Parameters
    ----------
    cost_flow
        Yearly technology cost flow (CAPEX, OPEX, and replacements) from the install
        time.
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

    return _levelize_trimmed(
        trim_flow_to_lifetime(cost_flow, window), window, discount_rate
    )


def _levelize_trimmed(
    trimmed: FloatArray, window: float, discount_rate: float
) -> float:
    """Levelize a cost flow already trimmed to `window` years into a USD/year charge."""
    # the leveling flow prorates the final partial year as the trimmed cost flow
    # does, so the charge is recovered over exactly `window` years
    level_flow = expand_to_flow(window, 1.0)

    return calculate_levelized_cost(trimmed, level_flow, discount_rate)


def _build_technology_component(
    technology: Technology, vessel_lifetime: float, time_initial: float
) -> Component:
    component = Component(0.0, vessel_lifetime, time_initial)
    component.initialize_machinery_component(technology)

    add_capex_flow(component, technology.capex.get)
    add_fixed_opex(component, technology.opex.get)

    return component
