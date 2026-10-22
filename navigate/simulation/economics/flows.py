# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Yearly cost, WTT and operating flows of assets, and the Component that holds them."""

from __future__ import annotations

import math
from functools import partial
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.region import Region
    from navigate.core.nodes.tank import Tank
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


class Component:
    """
    Cost and WTT flows of an asset on a calendar-year grid, with their time context.

    Every flow spans the horizon `lead_time + lifetime` in calendar-year bins
    anchored at `time_initial`. Operation commences at `time_commence`, after the
    lead time, and ends at `time_end`, the end of the horizon. `replacement_cycle`
    is None while the component lives as long as the asset; it is attached by
    `attach_process_cycle` or `attach_machinery_cycle`.

    Parameters
    ----------
    lead_time
        Asset lead time, in years.
    lifetime
        Asset lifetime, in years.
    time_initial
        Time of investment decision since the start of the simulation, in days.
    emissions
        Names of the emissions to allocate a WTT flow for.
    """

    def __init__(
        self,
        lead_time: float,
        lifetime: float,
        time_initial: float,
        emissions: Iterable[str] = (),
    ) -> None:
        self.length: int = get_flow_size(lead_time, lifetime)

        # flows
        self.capex_flow: FloatArray = np.zeros(self.length)
        self.opex_flow: FloatArray = np.zeros(self.length)
        self.tied_capital_flow: FloatArray = np.zeros(self.length)
        self.wtt_flow: dict[str, FloatArray] = {}
        for emission in emissions:
            self.wtt_flow[emission] = np.zeros(self.length)

        # time context shared across methods, set by _update_time_context
        self.lead_time: float = lead_time
        self._year_offsets: FloatArray = np.arange(self.length, dtype=float) * YEAR
        self.time_initial: float
        self.time_commence: float
        self.time_end: float
        self.year_flow: FloatArray
        self.constant_overlap: FloatArray
        self._update_time_context(time_initial)

        self.replacement_cycle: _ReplacementCycle | None = None

    def attach_process_cycle(self, region: Region, process_name: str) -> None:
        """Attach the replacement cycle of a region process that has a lifetime."""
        lifetime = region.process_lifetime[process_name]
        if lifetime is None:
            return

        # an event may reassign the replacement share, so it is read at call time
        def replacement(time: float) -> float:
            return region.process_replacement[process_name].get(time)

        self.replacement_cycle = _ReplacementCycle(lifetime.get, replacement, self)

    def attach_machinery_cycle(self, machinery: Converter | Tank | Technology) -> None:
        """Attach the replacement cycle of a machinery item that has a lifetime."""
        lifetime = machinery.lifetime
        if lifetime is None:
            return

        # an event may reassign the replacement share, so it is read at call time
        def replacement(time: float) -> float:
            return machinery.replacement.get(time)

        self.replacement_cycle = _ReplacementCycle(lifetime.get, replacement, self)

    def add_component(self, component: Component) -> None:
        """Add every flow of another component of the same horizon to this one."""
        self.capex_flow += component.capex_flow
        self.opex_flow += component.opex_flow
        self.tied_capital_flow += component.tied_capital_flow

        for key, value in component.wtt_flow.items():
            self.wtt_flow[key] += value

    def reset(self, time_initial: float) -> None:
        """
        Zero all flow arrays and move the component to a new investment time.

        The array dimensions are preserved, and the replacement cycle, if any, is
        walked again over the new time context, so the component is in the same
        state as a freshly constructed one with the same lead time, lifetime and
        cycle callables.
        """
        self.capex_flow.fill(0)
        self.opex_flow.fill(0)
        self.tied_capital_flow.fill(0)
        for wtt in self.wtt_flow.values():
            wtt.fill(0)

        self._update_time_context(time_initial)

        cycle = self.replacement_cycle
        if cycle is not None:
            self.replacement_cycle = _ReplacementCycle(
                cycle.lifetime, cycle.replacement, self
            )

    def get_commence_index(self) -> int:
        """Return the calendar-year bin in which operation commences."""
        return _bin_index(self.time_commence, self.time_initial, self.length)

    def get_cost_flow(self) -> FloatArray:
        """Return the total cost flow, OPEX plus CAPEX."""
        return self.opex_flow + self.capex_flow

    def _update_time_context(self, time_initial: float) -> None:
        """Recompute the time fields and constant overlap from an investment time."""
        self.time_initial = time_initial
        self.time_commence = _future_time(time_initial, self.lead_time)
        self.time_end = _future_time(time_initial, self.length)
        self.year_flow = time_initial + self._year_offsets

        overlap = _overlap_year_bins(self.year_flow, self.time_commence, self.time_end)
        self.constant_overlap = overlap / YEAR


class _ReplacementCycle:
    """
    Lifetime and replacement lookups of a component shorter-lived than its asset.

    The replacement times and staircase segments are walked once, over the time
    context the component holds at construction.

    Parameters
    ----------
    lifetime
        Callable returning the component lifetime, in years, locked at a time, in days.
    replacement
        Callable returning the replaceable share of the CAPEX locked at a time,
        in days.
    component
        Component whose time context the schedules are walked over.
    """

    def __init__(
        self,
        lifetime: Callable[[float], float],
        replacement: Callable[[float], float],
        component: Component,
    ) -> None:
        replacement_times = _compute_replacement_times(component, lifetime)
        staircase_segments = _compute_staircase_segments(component, replacement_times)

        self.lifetime: Callable[[float], float] = lifetime
        self.replacement: Callable[[float], float] = replacement
        self.replacement_times: list[float] = replacement_times
        self.staircase_segments: list[tuple[float, FloatArray]] = staircase_segments


def add_capex(component: Component, capex: Callable[[float], float]) -> None:
    """
    Add initial CAPEX spread over construction and recurring CAPEX at lifetime end.

    Parameters
    ----------
    component
        Component for which CAPEX costs are added.
    capex
        Callable returning the CAPEX locked at a time, in days: the initial CAPEX at
        the investment decision and the recurring CAPEX at each replacement.
    """
    _add_initial_capex_flow(component, capex)
    _add_recurring_capex_flow(component, capex)


def add_fixed_opex(component: Component, opex: Callable[[float], float]) -> None:
    """
    Add a fixed OPEX, locked at installation and each replacement.

    Parameters
    ----------
    component
        Component for which OPEX costs are added.
    opex
        Callable returning the yearly OPEX locked at an anchor time, in days.
    """
    component.opex_flow += _build_staircase_flow(component, opex)


def add_variable_opex(
    component: Component,
    metric: Callable[[float], float],
    price: Callable[[FloatArray], FloatArray],
) -> None:
    """
    Add a variable OPEX, the locked metric times its prevailing price.

    Parameters
    ----------
    component
        Component for which OPEX costs are added.
    metric
        Callable returning the metric (e.g. in tons/year) locked at an anchor time,
        in days.
    price
        Callable returning the price per unit of metric at absolute times, in days.
        Vectorized over arrays of days.
    """
    metric_flow = _build_staircase_flow(component, metric)
    component.opex_flow += metric_flow * price(component.year_flow)


def add_fixed_wtt(component: Component, wtt: Callable[[str, float], float]) -> None:
    """
    Add the fixed WTT of every emission, locked at installation and each replacement.

    Parameters
    ----------
    component
        Component for which WTT emissions are added.
    wtt
        Callable returning the yearly WTT of an emission locked at an anchor time, in
        days.
    """
    for emission in component.wtt_flow:
        emission_wtt = partial(wtt, emission)
        component.wtt_flow[emission] += _build_staircase_flow(component, emission_wtt)


def add_variable_wtt(
    component: Component,
    metric: Callable[[float], float],
    factor: Callable[[str, FloatArray], FloatArray],
) -> None:
    """
    Add the variable WTT of every emission, the locked metric times its factor.

    The staircase flow of the metric is shared across emissions, so it is built once.

    Parameters
    ----------
    component
        Component for which WTT emissions are added.
    metric
        Callable returning the metric locked at an anchor time, in days.
    factor
        Callable returning the WTT factor of an emission per unit of metric at
        absolute times, in days. Vectorized over arrays of days.
    """
    if not component.wtt_flow:
        return

    metric_flow = _build_staircase_flow(component, metric)
    year_flow = component.year_flow

    for emission in component.wtt_flow:
        emission_factor = factor(emission, year_flow)
        component.wtt_flow[emission] += metric_flow * emission_factor


def build_production_flow(component: Component, production: float) -> FloatArray:
    """
    Expand a fixed annual production into a calendar-year flow.

    The flow is zero during the construction lead time, and the first operational
    year is prorated by its overlap with the operation window.

    Parameters
    ----------
    component
        Component for which the production flow is built.
    production
        Constant production rate, in tons/year.

    Returns
    -------
    FloatArray
        Production per calendar year over the horizon `lead_time + lifetime`, in tons.
    """
    return production * component.constant_overlap


def build_cargo_flow(
    component: Component, cargo: FloatArray, timeline: FloatArray
) -> FloatArray:
    """
    Expand variable annual cargo-miles into a calendar-year flow.

    The flow is zero during the construction lead time, and the first operational
    year is prorated by its overlap with the operation window.

    Parameters
    ----------
    component
        Component for which the cargo-mile flow is built.
    cargo
        Variable cargo-mile rate, in cargo-miles/year.
    timeline
        Timeline at which `cargo` is defined, in days.

    Returns
    -------
    FloatArray
        Cargo-miles per calendar year over the horizon `lead_time + lifetime`.
    """
    rate = np.interp(component.year_flow, timeline, cargo)
    flow: FloatArray = rate * component.constant_overlap
    return flow


def build_operating_flows(
    time_initial: float, lead_time: float, lifetime: float
) -> tuple[FloatArray, FloatArray]:
    """
    Build the lead-aware operating-year grid and overlap fractions at a given time.

    The overlap is zero during the construction lead time and one during operational
    years, with the first operational year prorated by its overlap with the operation
    window, as in `Component.constant_overlap`. The year grid gives the absolute
    calendar time of each bin, in days, anchored at the evaluation time. Both span
    `lead_time + lifetime` years, so reconstructed cost, production and age flows
    share one basis and spread cost only over the years the asset operates.

    Parameters
    ----------
    time_initial
        Absolute time at which the asset is evaluated, in days.
    lead_time
        Construction lead time, in years.
    lifetime
        Operational lifetime, in years.

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Absolute year grid, in days, and per-year operating fraction.
    """
    size = get_flow_size(lead_time, lifetime)
    offsets = np.arange(size, dtype=float) * YEAR

    overlap = _overlap_year_bins(offsets, lead_time * YEAR, size * YEAR) / YEAR

    return time_initial + offsets, overlap


def timeline_to_yearly(vessel: Vessel, idx: int, timeline: FloatArray) -> FloatArray:
    """
    Return the yearly times over a vessel's lifetime from a time-step on.

    Every business case's cost flow is evaluated on these times, so the flows are
    comparable.

    Parameters
    ----------
    vessel
        Vessel for which the cost flow is calculated.
    idx
        Current time-step index.
    timeline
        Simulation timeline, in days.

    Returns
    -------
    FloatArray
        Yearly times over the lifetime of the vessel, in days.
    """
    lifetime = vessel.lifetime.get()

    start = timeline[idx]
    end = start + lifetime * YEAR

    return np.arange(start, end, YEAR)


def get_age_flow(lead_time: float, lifetime: float) -> FloatArray:
    """
    Return a vector of ones sized for an asset's yearly flow, to levelize by age.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset, in years.
    lifetime
        Lifetime of the asset, in years.

    Returns
    -------
    FloatArray
        A vector of ones.
    """
    return np.ones(get_flow_size(lead_time, lifetime))


def get_flow_size(lead_time: float, lifetime: float) -> int:
    """
    Get the number of yearly bins needed to hold an asset's construction and operation.

    The number of years is the ceiling of the lead time plus the lifetime, to account
    for durations with decimals.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset, in years.
    lifetime
        Lifetime of the asset, in years.

    Returns
    -------
    int
        Number of yearly bins.
    """
    return math.ceil(round(lead_time + lifetime, ROUND_OFF))


def trim_flow_to_lifetime(flow: FloatArray, lifetime: float) -> FloatArray:
    """
    Trim a yearly flow to its first `lifetime` years, prorating a partial final year.

    Parameters
    ----------
    flow
        Yearly flow covering at least `lifetime` years.
    lifetime
        Years to keep.

    Returns
    -------
    FloatArray
        Trimmed copy; the input flow is left untouched.
    """
    trimmed = flow[: get_flow_size(lead_time=0.0, lifetime=lifetime)].copy()
    _prorate_final_year(trimmed, lifetime)

    return trimmed


def expand_to_flow(lifetime: float, value: float) -> FloatArray:
    """
    Expand a yearly property of an asset to a flow over the lifetime of the asset.

    Parameters
    ----------
    lifetime
        Lifetime of an asset, in years.
    value
        Yearly value of operations.

    Returns
    -------
    FloatArray
        A vector filled with `value`, the partial final year prorated.
    """
    flow = np.full(get_flow_size(lead_time=0.0, lifetime=lifetime), value)
    _prorate_final_year(flow, lifetime)

    return flow


def _bin_index(time: float, time_initial: float, n_years: int) -> int:
    """
    Map an absolute time to its calendar-year bin index, clamped to the horizon.

    Parameters
    ----------
    time
        Absolute time, in days.
    time_initial
        Start time of the first bin, in days.
    n_years
        Number of calendar-year bins.

    Returns
    -------
    int
        Zero-based bin index clamped to [0, n_years - 1].
    """
    idx = int((time - time_initial) // YEAR)
    return min(max(idx, 0), n_years - 1)


def _future_time(time: float, years: float) -> float:
    """
    Add a duration in years to an absolute time in days.

    Parameters
    ----------
    time
        Absolute time, in days.
    years
        Duration, in years.

    Returns
    -------
    float
        New absolute time, in days.
    """
    return time + years * YEAR


def _overlap_year_bins(times: FloatArray, a: float, b: float) -> FloatArray:
    """
    Vectorized overlap between [a, b) and each calendar bin [t_i, t_i + YEAR).

    Parameters
    ----------
    times
        Year-start times, in days (monotonic).
    a
        Interval start, in days.
    b
        Interval end, in days (exclusive).

    Returns
    -------
    FloatArray
        Overlap length per bin, in days (same length as `times`).
    """
    left = np.maximum(times, a)
    right = np.minimum(times + YEAR, b)
    overlap: FloatArray = np.clip(right - left, 0.0, YEAR)
    return overlap


def _compute_replacement_times(
    component: Component, lifetime: Callable[[float], float]
) -> list[float]:
    """
    Walk the replacement timeline and return each replacement time.

    The first tranche is installed at commencement with its lifetime locked at the
    investment decision; each replacement's lifetime is locked at the replacement.
    The initial installation is not a replacement and is excluded.

    Parameters
    ----------
    component
        Component whose time context to walk.
    lifetime
        Callable returning the component lifetime, in years, locked at a time, in days.

    Returns
    -------
    list[float]
        Replacement times, in days since the start of the simulation.
    """
    time_end = component.time_end
    times = []

    time = _future_time(component.time_commence, lifetime(component.time_initial))
    while time < time_end:
        times.append(time)
        time = _future_time(time, lifetime(time))

    return times


def _compute_staircase_segments(
    component: Component, replacement_times: list[float]
) -> list[tuple[float, FloatArray]]:
    """
    Compute the anchor time and normalized overlap of each component lifetime.

    Each segment runs from an installation to the next replacement, or to the end of
    the horizon. Its anchor time is the time at which a locked value is evaluated, and
    its normalized overlap is the overlap per calendar-year bin as a fraction of a
    year.

    Parameters
    ----------
    component
        Component whose time context to walk.
    replacement_times
        Replacement times, in days since the start of the simulation.

    Returns
    -------
    list[tuple[float, FloatArray]]
        One (anchor time, normalized overlap) pair per segment.
    """
    year_flow = component.year_flow

    # the first tranche is installed at commencement but locked at the investment
    installs = [component.time_commence, *replacement_times]
    anchors = [component.time_initial, *replacement_times]
    ends = [*replacement_times, component.time_end]

    segments = []
    for anchor, start, end in zip(anchors, installs, ends, strict=True):
        if end <= start:
            continue

        overlap = _overlap_year_bins(year_flow, start, end)
        segments.append((anchor, overlap / YEAR))

    return segments


def _add_initial_capex_flow(
    component: Component, capex: Callable[[float], float]
) -> None:
    """
    Add the initial CAPEX, spread uniformly over the construction period.

    The full initial CAPEX is locked at the investment decision (`time_initial`) and
    deposited into each calendar-year bin in proportion to its overlap with the
    construction window; without one it falls in the first bin. The tied up capital
    of the deposits is added by `_add_initial_tied_capital_flow`.

    Parameters
    ----------
    component
        Component for which CAPEX costs are added.
    capex
        Callable returning the CAPEX locked at the time of investment, in days.
    """
    time_initial = component.time_initial
    time_commence = component.time_commence
    year_flow = component.year_flow

    capex_t = capex(time_initial)

    if time_commence > time_initial:
        construction = _overlap_year_bins(year_flow, time_initial, time_commence)
        delta = capex_t * construction / (time_commence - time_initial)
    else:
        delta = np.zeros(component.length)
        delta[0] = capex_t

    component.capex_flow += delta
    _add_initial_tied_capital_flow(component, delta)


def _add_initial_tied_capital_flow(component: Component, delta: FloatArray) -> None:
    """
    Add the tied up capital of the initial CAPEX deposits.

    Tied up capital is built from two parts:
      1) Construction-in-Progress (CIP): cumulative initial CAPEX during construction
         bins before commencement.
      2) Straight-line depreciation from commencement (bin-start convention) with no
         residual value, applied as two tranches:
            - non-replaceable share: (1 - replace(time_initial)) depreciated over the
              full remaining asset horizon
            - replaceable share: replace(time_initial) depreciated over the component
              lifetime locked at time_initial

    Parameters
    ----------
    component
        Component for which tied up capital is added.
    delta
        Initial CAPEX deposits per calendar-year bin.
    """
    idx = component.get_commence_index()
    component.tied_capital_flow[:idx] += np.cumsum(delta[:idx])

    cycle = component.replacement_cycle
    if cycle is None:
        replaceable = 0.0
        lifetime_component = 0.0
    else:
        replaceable = cycle.replacement(component.time_initial)
        lifetime_component = cycle.lifetime(component.time_initial)

    basis = delta.sum()
    basis_asset = basis * (1.0 - replaceable)
    basis_component = basis * replaceable
    lifetime_asset = (component.time_end - component.year_flow[idx]) / YEAR

    _add_straight_line_depreciation(component, idx, basis_asset, lifetime_asset)
    _add_straight_line_depreciation(component, idx, basis_component, lifetime_component)


def _add_straight_line_depreciation(
    component: Component, idx_start: int, basis: float, years_total: float
) -> None:
    """
    Add straight-line depreciated tied up capital to the component's flow.

    Tied up capital is evaluated at the start of each calendar-year bin (bin-start
    convention). No residual value is assumed; the tied up capital declines linearly
    from `basis` at `year_flow[idx_start]` to zero after `years_total` years.

    Parameters
    ----------
    component
        Component for which tied up capital is added.
    idx_start
        Index of the first bin where depreciation begins.
    basis
        Initial tied up capital to depreciate (e.g., CAPEX tranche).
    years_total
        Depreciation horizon, in years. If non-positive, no changes are applied.
    """
    if basis <= 0.0 or years_total <= 0.0:
        return

    year_flow = component.year_flow[idx_start:]
    age = (year_flow - year_flow[0]) / YEAR
    remaining = basis * (1.0 - age / years_total)
    component.tied_capital_flow[idx_start:] += np.maximum(remaining, 0.0)


def _add_recurring_capex_flow(
    component: Component, capex: Callable[[float], float]
) -> None:
    """
    Add the recurring CAPEX of each replacement of a shorter-lived component.

    Each replacement's CAPEX is locked at its replacement time and deposited into the
    calendar-year bin holding it, scaled by the share of the component lifetime that
    fits within the remaining horizon. Its tied up capital depreciates straight-line
    from the bin start, over the component lifetime locked at the replacement.

    Parameters
    ----------
    component
        Component for which recurring CAPEX costs are added.
    capex
        Callable returning the recurring CAPEX at a replacement time, in days.
    """
    cycle = component.replacement_cycle
    if cycle is None:
        return

    for time_replace in cycle.replacement_times:
        lifetime = cycle.lifetime(time_replace)
        remaining = (component.time_end - time_replace) / YEAR
        share = min(remaining / lifetime, 1.0)
        capex_t = capex(time_replace) * cycle.replacement(time_replace) * share

        idx = _bin_index(time_replace, component.time_initial, component.length)
        component.capex_flow[idx] += capex_t

        _add_straight_line_depreciation(component, idx, capex_t, lifetime)


def _build_staircase_flow(
    component: Component, value: Callable[[float], float]
) -> FloatArray:
    """
    Build a piecewise-constant flow, locked at installation and each replacement.

    The first operational calendar year is prorated by the overlaps, which already
    reflect a fractional lead time.

    Parameters
    ----------
    component
        Component for which the flow is built.
    value
        Callable returning the locked value at an anchor time, in days.

    Returns
    -------
    FloatArray
        Piecewise-constant flow per calendar year.
    """
    # a component as long-lived as its asset holds one value, zero during the lead
    # time and prorated in the commencement year
    cycle = component.replacement_cycle
    if cycle is None:
        return value(component.time_initial) * component.constant_overlap

    flow = np.zeros(component.length)
    for anchor, overlap in cycle.staircase_segments:
        flow += value(anchor) * overlap

    return flow


def _prorate_final_year(flow: FloatArray, lifetime: float) -> None:
    """
    Scale the final year of a yearly flow by the fraction of it within the lifetime.

    Parameters
    ----------
    flow
        Yearly flow whose final year is prorated in place.
    lifetime
        Lifetime of the asset, in years.
    """
    years = round(lifetime, ROUND_OFF)
    fraction = years - math.floor(years)

    if fraction > 0.0:
        flow[-1] *= fraction
