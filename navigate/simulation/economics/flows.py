# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Yearly cost, WTT and operating flows of assets, and the Component that holds them."""

from __future__ import annotations

from math import floor
from typing import TYPE_CHECKING

import numpy as np

from navigate.util import ROUND_OFF, YEAR

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.power_system import PowerSystem
    from navigate.core.nodes.region import Region
    from navigate.core.nodes.tank import Tank
    from navigate.core.nodes.technology import Technology
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray


class Component:
    """
    Convenience struct for storing cost/WTT flows, time context, and callables.

    Every flow spans the horizon `lead_time + lifetime` in calendar-year bins
    anchored at `time_initial`. Operation commences at `time_commence`, after the
    lead time, and ends at `time_end`, the end of the horizon. `replacement_cycle`
    is None while the component lives as long as the asset; it is attached by
    `initialize_process_component` or `initialize_machinery_component`.

    Parameters
    ----------
    lead_time
        Asset lead time (years).
    lifetime
        Asset lifetime (years).
    time_initial
        Time of investment decision (days since start of simulation).
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

        # flows
        self.capex_flow: FloatArray = _initialize_flow(lead_time, lifetime)
        self.opex_flow: FloatArray = _initialize_flow(lead_time, lifetime)
        self.tied_capital_flow: FloatArray = _initialize_flow(lead_time, lifetime)
        self.wtt_flow: dict[str, FloatArray] = {
            emission: _initialize_flow(lead_time, lifetime) for emission in emissions
        }

        # time context shared across methods, set by _update_time_context
        self.lead_time: float = lead_time
        self._year_offset: FloatArray = np.arange(self.get_length(), dtype=float)
        self.time_initial: float
        self.time_commence: float
        self.time_end: float
        self.year_flow: FloatArray
        self.constant_overlap: FloatArray
        self._update_time_context(time_initial)

        self.replacement_cycle: _ReplacementCycle | None = None

    def initialize_process_component(self, region: Region, process_name: str) -> None:
        """Attach the replacement cycle of a region process that has a lifetime."""
        lifetime = region.process_lifetime[process_name]
        if lifetime is None:
            return

        self.replacement_cycle = _ReplacementCycle(
            lifetime=lambda time: lifetime.get(time),
            replacement=lambda time: region.process_replacement[process_name].get(time),
            component=self,
        )

    def initialize_machinery_component(
        self, machinery: Converter | PowerSystem | Tank | Technology
    ) -> None:
        """Attach the replacement cycle of a machinery item that has a lifetime."""
        lifetime = machinery.lifetime
        if lifetime is None:
            return

        self.replacement_cycle = _ReplacementCycle(
            lifetime=lambda time: lifetime.get(time),
            replacement=lambda time: machinery.replacement.get(time),
            component=self,
        )

    def get_commence_index(self) -> int:
        """Return the calendar-year bin in which operation commences."""
        return _bin_index(self.time_commence, self.time_initial, self.get_length())

    def add_capex_flow(self, capex_flow: FloatArray) -> None:
        """Add a CAPEX flow to the component's CAPEX flow."""
        self.capex_flow += capex_flow

    def add_opex_flow(self, opex_flow: FloatArray) -> None:
        """Add an OPEX flow to the component's OPEX flow."""
        self.opex_flow += opex_flow

    def add_tied_capital_flow(self, tied_capital_flow: FloatArray) -> None:
        """Add a tied-capital flow to the component's tied-capital flow."""
        self.tied_capital_flow += tied_capital_flow

    def add_wtt_flow(self, emission_name: str, wtt_flow: FloatArray) -> None:
        """Add a WTT flow to the component's WTT flow of one emission."""
        self.wtt_flow[emission_name] += wtt_flow

    def _update_time_context(self, time_initial: float) -> None:
        """Recompute time fields and constant overlap from a new investment time."""
        self.time_initial = time_initial
        self.time_commence = _future_time(time_initial, self.lead_time)
        self.time_end = _future_time(time_initial, self.get_length())
        self.year_flow = time_initial + self._year_offset * YEAR
        self.constant_overlap = (
            _overlap_year_bins(self.year_flow, self.time_commence, self.time_end) / YEAR
        )

    def reset_flow(self, time_initial: float) -> None:
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
                lifetime=cycle.lifetime,
                replacement=cycle.replacement,
                component=self,
            )

    def add_component(self, component: Component) -> None:
        """Add every flow of another component of the same horizon to this one."""
        self.add_capex_flow(component.capex_flow)
        self.add_opex_flow(component.opex_flow)
        self.add_tied_capital_flow(component.tied_capital_flow)

        for emission_name, emission_flow in component.wtt_flow.items():
            self.add_wtt_flow(emission_name, emission_flow)

    def get_length(self) -> int:
        """Return the number of calendar-year bins in the horizon."""
        return self.capex_flow.size

    def get_cost_flow(self) -> FloatArray:
        """Return the total cost flow, OPEX plus CAPEX."""
        return self.opex_flow + self.capex_flow


class _ReplacementCycle:
    """
    Lifetime and replacement lookups of a component shorter-lived than its asset.

    The staircase segments and replacement times are walked once, over the time
    context the component holds at construction.

    Parameters
    ----------
    lifetime
        Callable returning the component lifetime (years) locked at a time (days).
    replacement
        Callable returning the replaceable share of the CAPEX locked at a time
        (days).
    component
        Component whose time context the schedules are walked over.
    """

    def __init__(
        self,
        lifetime: Callable[[float], float],
        replacement: Callable[[float], float],
        component: Component,
    ) -> None:
        self.lifetime: Callable[[float], float] = lifetime
        self.replacement: Callable[[float], float] = replacement
        self.staircase_segments: list[tuple[float, FloatArray]] = (
            _compute_staircase_segments(component, lifetime)
        )
        self.replacement_times: list[float] = _compute_replacement_times(
            component, lifetime
        )


def build_production_flow(component: Component, production: float) -> FloatArray:
    """
    Expand a fixed annual production (tons/year) into a calendar-year flow vector.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ----------
    component
        Component for which production flow is calculated.
    production
        Constant production rate in tons per year.

    Returns
    -------
    FloatArray
        Production flow per calendar year over the horizon `lead_time + lifetime`.
    """
    return _build_constant_flow(component, production)


def build_cargo_flow(
    component: Component, cargo: FloatArray, timeline: FloatArray
) -> FloatArray:
    """
    Expand a variable annual cargo-miles (cargo-miles/year) into a calendar-year flow.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ----------
    component
        Component for which cargo-mile flow is calculated.
    cargo
        Variable cargo-mile rate in tons per year.
    timeline
        Timeline at which `cargo` is defined.

    Returns
    -------
    FloatArray
        Cargo-mile flow per calendar year over the horizon `lead_time + lifetime`.
    """
    return _build_variable_flow(component, cargo, timeline)


def add_capex_flow(component: Component, capex: Callable[[float], float]) -> None:
    """
    Add initial CAPEX spread over construction and recurring CAPEX at lifetime end.

    Parameters
    ----------
    component
        Component for which CAPEX costs are added.
    capex
        Callable returning CAPEX locked at the time of investment and recurring CAPEX at
        the end of the lifetime.
    """
    _add_initial_capex_flow(component=component, capex=capex)
    _add_recurring_capex_flow(component=component, capex=capex, partial=True)


def add_fixed_opex(component: Component, value: Callable[[float], float]) -> None:
    """
    Add any fixed/locked cost into the cost flow.

    Parameters
    ----------
    component
        Component for which OPEX costs are added.
    value
        Callable returning per-year cost locked at anchor time (days).
    """
    fixed = _build_staircase_flow(component=component, value=value)
    component.add_opex_flow(fixed)


def add_variable_opex(
    component: Component,
    metric: Callable[[float], float],
    cost: Callable[[FloatArray], FloatArray],
) -> None:
    """
    Add variable cost (metric * price) into the unified cost flow.

    Parameters
    ----------
    component
        Component for which OPEX costs are added.
    metric
        Callable returning locked metric (e.g., tons/year) at anchor time (days).
    cost
        Callable returning price as a function of absolute time (days). Vectorized over
        arrays of days.
    """
    fixed = _build_staircase_flow(component=component, value=metric)
    variable = cost(component.year_flow)
    component.add_opex_flow(fixed * variable)


def add_fixed_wtt(
    component: Component, wtt_callables: dict[str, Callable[[float], float]]
) -> None:
    """
    Add fixed/locked WTT for multiple emissions in one pass over staircase segments.

    Parameters
    ----------
    component
        Component for which WTT emissions are added.
    wtt_callables
        Mapping of emission name to callable returning locked WTT factor at anchor time
        (days).
    """
    if not wtt_callables:
        return

    cycle = component.replacement_cycle
    if cycle is None:
        time_initial = component.time_initial
        overlap = component.constant_overlap

        for emission_name, wtt in wtt_callables.items():
            component.add_wtt_flow(emission_name, wtt(time_initial) * overlap)

        return

    segments = cycle.staircase_segments
    n = component.get_length()
    flows = {e: np.zeros(n, dtype=float) for e in wtt_callables}

    for anchor_time, normalized_overlap in segments:
        for emission_name, wtt in wtt_callables.items():
            flows[emission_name] += wtt(anchor_time) * normalized_overlap

    for emission_name, flow in flows.items():
        component.add_wtt_flow(emission_name, flow)


def add_variable_wtt(
    component: Component,
    metric: Callable[[float], float],
    wtt_callables: dict[str, Callable[[FloatArray], FloatArray]],
) -> None:
    """
    Add variable WTT (metric * factor) for multiple emissions.

    Computes the staircase flow for the shared metric once, then multiplies
    by each emission's variable WTT factor.

    Parameters
    ----------
    component
        Component for which WTT emissions are added.
    metric
        Callable returning locked metric at anchor time (days). Shared across emissions.
    wtt_callables
        Mapping of emission name to callable returning time-dependent WTT factor.
    """
    if not wtt_callables:
        return

    fixed = _build_staircase_flow(component=component, value=metric)
    year_flow = component.year_flow

    for emission_name, wtt in wtt_callables.items():
        variable = wtt(year_flow)
        component.add_wtt_flow(emission_name, fixed * variable)


def timeline_to_yearly(vessel: Vessel, idx: int, timeline: FloatArray) -> FloatArray:
    """
    Define the yearly dates used to calculate a business case's cost-flow.

    This is necessary in order to ensure all cost-flows are comparable.

    Parameters
    ----------
    vessel
        Vessel for which cost flow will be calculated.
    idx
        Current time-step index.
    timeline
        Simulation timeline (days).

    Returns
    -------
    FloatArray
        Yearly times (in days) for the lifetime of the vessel.
    """
    lifetime = vessel.lifetime.get()

    start = timeline[idx]
    end = start + lifetime * YEAR

    return np.arange(start, end, YEAR)


def get_age_flow(lead_time: float, lifetime: float) -> FloatArray:
    """
    Initialize a ones vector sized for an asset's yearly cost-flow.

    This can be used to calculate age levelization.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    FloatArray
        A vector of ones.
    """
    return np.ones(get_flow_shape(lead_time, lifetime), dtype=float)


def build_operating_age_flow(lead_time: float, lifetime: float) -> FloatArray:
    """
    Build the per-calendar-year operating fraction over `lead_time + lifetime`.

    The flow is zero during the construction lead time and one during operational years,
    with the first and last partial years prorated by their overlap with the operating
    window. It mirrors `Component.constant_overlap` and is the leveling basis for
    age-levelized charter rates, so that cost is spread only over the years the asset
    actually operates (matching the cost and cargo-mile flows, which are likewise zero
    during lead time).

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset (years).
    lifetime
        Operational lifetime of the asset (years).

    Returns
    -------
    FloatArray
        Operating fraction per calendar-year bin over the horizon
        `lead_time + lifetime`.
    """
    n = get_flow_size(lead_time, lifetime)
    year_starts = np.arange(n, dtype=float) * YEAR
    commence = lead_time * YEAR
    end = n * YEAR

    return _overlap_year_bins(year_starts, commence, end) / YEAR


def build_operating_flows(
    time_initial: float, lead_time: float, lifetime: float
) -> tuple[FloatArray, FloatArray]:
    """
    Build the lead-aware operating-year grid and overlap fractions at a given time.

    The overlap is zero during the construction lead time and (prorated) one during
    operational years; the year grid gives the absolute calendar time (days) of each
    bin, anchored at the evaluation time. Both span `lead_time + lifetime` years so
    reconstructed cost, production, and age flows share one basis.

    Parameters
    ----------
    time_initial
        Absolute time (days) at which the asset is evaluated.
    lead_time
        Construction lead time (years).
    lifetime
        Operational lifetime (years).

    Returns
    -------
    tuple[FloatArray, FloatArray]
        Absolute year grid (days) and per-year operating fraction.
    """
    overlap = build_operating_age_flow(lead_time, lifetime)
    year_flow = time_initial + np.arange(overlap.size, dtype=float) * YEAR

    return year_flow, overlap


def get_flow_shape(lead_time: float, lifetime: float) -> tuple[int]:
    """
    Get the vector shape for an asset's construction and lifetime operations in years.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    tuple[int]
        Shape of the vector required to hold a property.
    """
    return (get_flow_size(lead_time, lifetime),)


def get_flow_size(lead_time: float, lifetime: float) -> int:
    """
    Get the size of the vectors required to store an asset's lifetime operations.

    The vectors use yearly increments; the number of years is equal to the ceil of
    the lifetime, to account for lifetimes with decimals.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    int
        Size of the vector required to hold a property.
    """
    return int(np.ceil(round(lead_time + lifetime, ROUND_OFF)))


def _add_initial_capex_flow(
    component: Component, capex: Callable[[float], float]
) -> None:
    """
    Add initial CAPEX spread over the construction period.

    The full initial CAPEX is locked at the time of investment decision (`time_initial`)
    and then distributed across the construction lead time into calendar-year bins. This
    method only deposits into `component.capex_flow` and does not modify tied up
    capital. Tied up capital for the initial CAPEX is handled separately via
    `_add_initial_tied_capital_flow`.

    Parameters
    ----------
    component
        Component for which CAPEX costs are added.
    capex
        Callable returning CAPEX locked at the time of investment.
    """
    lead_time = component.lead_time
    time_initial = component.time_initial

    capex_flow = component.capex_flow

    delta = np.zeros(component.get_length(), dtype=float)
    capex_t = capex(time_initial)

    if lead_time > 0.0:
        full_years = int(np.floor(lead_time))
        fraction = full_years / lead_time

        if full_years > 0:
            delta[:full_years] += capex_t * fraction / max(full_years, 1)

        delta[full_years] += capex_t * (1.0 - fraction)

    else:
        delta[0] += capex_t

    capex_flow += delta

    _add_initial_tied_capital_flow(component, delta)


def _add_recurring_capex_flow(
    component: Component, capex: Callable[[float], float], *, partial: bool = False
) -> None:
    """
    Add recurring CAPEX at the end of a component's lifetime.

    Replacement timing for the first interval is determined by the component lifetime
    locked at the time of investment decision (`time_initial`), with the first tranche
    installed at commencement. Each subsequent replacement interval is anchored at the
    replacement time (properties locked at `time_replace`).

    Deposits replacement CAPEX into `component.capex_flow` at the appropriate
    calendar-year bin and adds the corresponding tied up capital tranche using
    straight-line depreciation from the replacement bin start, over the component
    lifetime locked at the replacement year.

    Parameters
    ----------
    component
        Component for which recurring CAPEX costs are added.
    capex
        Callable returning recurring CAPEX at the replacement time (days since start of
        simulation).
    partial
        If True, scale the replacement CAPEX by the fraction of the next component
        lifetime that fits within the remaining horizon.
    """
    # recurring CAPEX only matters if the component
    # has a lifetime shorter than the asset lifetime
    cycle = component.replacement_cycle
    if cycle is None:
        return

    time_initial = component.time_initial
    time_end = component.time_end

    capex_flow = component.capex_flow

    for time_replace in cycle.replacement_times:
        # replacement CAPEX locked at replacement event
        replace_t = cycle.replacement(time_replace)
        capex_t = capex(time_replace) * replace_t

        if partial:
            lifetime_t = cycle.lifetime(time_replace)
            remaining_years = (time_end - time_replace) / YEAR
            if remaining_years < lifetime_t:
                capex_t *= max(remaining_years, 0.0) / lifetime_t

        idx = _bin_index(time_replace, time_initial, component.get_length())
        capex_flow[idx] += capex_t

        # depreciate this replacement tranche over
        # lifetime locked at replacement year
        lifetime_replace = cycle.lifetime(time_replace)
        _add_straight_line_depreciation(component, idx, capex_t, lifetime_replace)


def _add_initial_tied_capital_flow(component: Component, delta: FloatArray) -> None:
    """
    Add the tied capital depreciation for the initial CAPEX delta.

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
        Initial CAPEX deposits per calendar-year bin (typically produced by
        `_add_initial_capex_flow`).
    """
    time_initial = component.time_initial

    tied_capital_flow = component.tied_capital_flow

    commence_idx = component.get_commence_index()

    if commence_idx > 0:
        tied_capital_flow[:commence_idx] += np.cumsum(delta[:commence_idx])

    basis = delta.sum()

    cycle = component.replacement_cycle
    if cycle is not None:
        replace_t = cycle.replacement(time_initial)
        lifetime_t = cycle.lifetime(time_initial)
    else:
        replace_t = 0.0
        lifetime_t = 0.0

    basis_asset = basis * (1.0 - replace_t)
    basis_component = basis * replace_t

    year_flow = component.year_flow
    lifetime_full = (component.time_end - year_flow[commence_idx]) / YEAR

    # non-replaceable share depreciates over full asset horizon
    _add_straight_line_depreciation(component, commence_idx, basis_asset, lifetime_full)

    # replaceable share depreciates over component lifetime
    _add_straight_line_depreciation(
        component, commence_idx, basis_component, lifetime_t
    )


def _add_straight_line_depreciation(
    component: Component, idx_start: int, basis: float, years_total: float
) -> None:
    """
    Add straight-line depreciated tied up capital into a tied up capital flow vector.

    Tied up capital is evaluated at the start of each calendar-year bin (bin-start
    convention). No residual value is assumed; the tied up capital declines linearly
    from `basis` at `year_flow[idx_start]` to zero after `years_total` years.

    Parameters
    ----------
    component
        Component for which depreciation schedule costs are added.
    idx_start
        Index of the first bin where depreciation begins.
    basis
        Initial tied up capital to depreciate (e.g., CAPEX tranche).
    years_total
        Depreciation horizon (years). If non-positive, no changes are applied.
    """
    tied_capital_flow = component.tied_capital_flow
    year_flow = component.year_flow

    if basis <= 0.0 or years_total <= 0.0:
        return

    time_start = year_flow[idx_start]

    for i in range(idx_start, tied_capital_flow.size):
        age = (year_flow[i] - time_start) / YEAR
        remaining = basis * (1.0 - age / years_total)

        if remaining <= 0.0:
            break

        tied_capital_flow[i] += remaining


def _compute_staircase_segments(
    component: Component, lifetime: Callable[[float], float]
) -> list[tuple[float, FloatArray]]:
    """
    Walk the replacement timeline and compute each segment's normalized overlap.

    Each segment represents one component lifetime interval. The returned
    list contains (anchor_time, normalized_overlap) pairs where anchor_time
    is the time at which the value callable should be evaluated and
    normalized_overlap is the overlap per calendar-year bin as a fraction
    of a year.

    Parameters
    ----------
    component
        Component whose time context to walk.
    lifetime
        Callable returning the component lifetime (years) locked at a time (days).

    Returns
    -------
    list[tuple[float, FloatArray]]
        One entry per replacement segment.
    """
    time_invest = component.time_initial
    time_commence = component.time_commence
    time_end = component.time_end
    year_flow = component.year_flow

    # build segment boundaries: xs[i] is the install time,
    # anchors[i] is the value-locking time for segment i
    xs = [time_commence]
    anchors = [time_invest]

    time = _future_time(time_commence, lifetime(time_invest))
    while time < time_end:
        xs.append(time)
        anchors.append(time)
        time = _future_time(time, lifetime(time))

    segments = []
    for i, x_start in enumerate(xs):
        x_end = xs[i + 1] if i + 1 < len(xs) else time_end
        if x_end <= x_start:
            continue
        overlap_days = _overlap_year_bins(year_flow, x_start, x_end)
        segments.append((anchors[i], overlap_days / YEAR))

    return segments


def _compute_replacement_times(
    component: Component, lifetime: Callable[[float], float]
) -> list[float]:
    """
    Walk the replacement timeline and return each replacement time.

    Excludes the initial installation.

    Parameters
    ----------
    component
        Component whose time context to walk.
    lifetime
        Callable returning the component lifetime (years) locked at a time (days).

    Returns
    -------
    list[float]
        Replacement times in days since start of simulation.
    """
    time_invest = component.time_initial
    time_commence = component.time_commence
    time_end = component.time_end

    times = []
    time_install = time_commence
    time_anchor = time_invest

    while True:
        lifetime_t = lifetime(time_anchor)
        time_replace = _future_time(time_install, lifetime_t)
        if time_replace >= time_end:
            break
        times.append(time_replace)
        time_install = time_replace
        time_anchor = time_replace

    return times


def _build_staircase_flow(
    component: Component, value: Callable[[float], float]
) -> FloatArray:
    """
    Build a piecewise-constant flow, locked at installation and each replacement.

    The first operational calendar year is correctly handled via overlap; no special
    scaling is required because overlaps already reflect fractional lead time.

    Parameters
    ----------
    component
        Component for which value flow is calculated.
    value
        Callable returning the locked value at the anchor time (days).

    Returns
    -------
    FloatArray
        Piecewise constant flow vector.
    """
    # if the component lifetime is the same as
    # the asset lifetime, the staircase is a
    # constant value with zeros during lead time
    # and prorated value in the commencement year
    cycle = component.replacement_cycle
    if cycle is None:
        return _build_constant_flow(component, value(component.time_initial))

    out = np.zeros(component.get_length(), dtype=float)
    for anchor_time, normalized_overlap in cycle.staircase_segments:
        out += value(anchor_time) * normalized_overlap

    return out


def _build_constant_flow(component: Component, value: float) -> FloatArray:
    """
    Build a constant flow over the lifetime of a component.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ----------
    component
        Component for which flow is calculated.
    value
        Yearly rate.

    Returns
    -------
    FloatArray
        Flow per calendar year over the horizon `lead_time + lifetime`.
    """
    return value * component.constant_overlap


def _build_variable_flow(
    component: Component, value: FloatArray, timeline: FloatArray
) -> FloatArray:
    """
    Build a variable flow over the lifetime of a component.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ----------
    component
        Component for which flow is calculated.
    value
        Yearly rate.
    timeline
        Timeline at which `value` is defined.

    Returns
    -------
    FloatArray
        Flow per calendar year over the horizon `lead_time + lifetime`.
    """
    time_commence = component.time_commence
    time_end = component.time_end
    year_flow = component.year_flow

    overlap_days = _overlap_year_bins(year_flow, time_commence, time_end)

    flow: FloatArray = np.interp(year_flow, timeline, value) * (overlap_days / YEAR)
    return flow


def _future_time(time: float, years: float) -> float:
    """
    Add a year-based duration to an absolute time expressed in days.

    Parameters
    ----------
    time
        Absolute time in days.
    years
        Duration in calendar years.

    Returns
    -------
    float
        New absolute time in days (time + years * YEAR).
    """
    return time + years * YEAR


def _bin_index(time: float, time_initial: float, n_years: int) -> int:
    """
    Map an absolute time to its calendar-year bin index (clamped to the horizon).

    Parameters
    ----------
    time
        Absolute time in days.
    time_initial
        Start time of the first bin in days.
    n_years
        Number of calendar-year bins.

    Returns
    -------
    int
        Zero-based bin index clamped to [0, n_years-1].
    """
    idx = int((time - time_initial) // YEAR)
    if idx < 0:
        return 0
    if idx >= n_years:
        return n_years - 1
    return idx


def _overlap_year_bins(times: FloatArray, a: float, b: float) -> FloatArray:
    """
    Vectorized overlap between [a, b) and each calendar bin [t_i, t_i + YEAR).

    Parameters
    ----------
    times
        Year-start times in days (monotonic).
    a
        Interval start in days.
    b
        Interval end in days (exclusive).

    Returns
    -------
    FloatArray
        Overlap length per bin in days (same length as `times`).
    """
    left = np.maximum(times, a)
    right = np.minimum(times + YEAR, b)
    overlap: FloatArray = np.clip(right - left, 0.0, YEAR)
    return overlap


def _initialize_flow(lead_time: float, lifetime: float) -> FloatArray:
    """
    Initialize zeros with the necessary length for the yearly cost-flow of an asset.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    FloatArray
        A vector of zeros.
    """
    return np.zeros(get_flow_shape(lead_time, lifetime), dtype=float)


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
    correct_flow_residual(lifetime, trimmed)

    return trimmed


def expand_to_flow(lifetime: float, value: float) -> FloatArray:
    """
    Expand a yearly property of an asset to a flow over the lifetime of the asset.

    Parameters
    ----------
    lifetime
        Lifetime of an asset (years).
    value
        Yearly value of operations.

    Returns
    -------
    FloatArray
        A vector filled with 'value'.
    """
    flow = np.full(get_flow_shape(lead_time=0.0, lifetime=lifetime), value)
    correct_flow_residual(lifetime, flow)

    return flow


def correct_flow_residual(lifetime: float, cost: FloatArray) -> None:
    """
    Correct the last year's cost when an asset's lifetime is not an integer.

    The last year is only partial, so its cost must be corrected to reflect that
    only a fraction of that year is incurred.

    Parameters
    ----------
    lifetime
        Lifetime of the asset (years).
    cost
        Cost-flow whose last time-step is corrected in place.
    """
    partial, residual = get_flow_residual(lifetime)
    if partial:
        cost[-1] *= residual


def get_flow_residual(lifetime: float) -> tuple[bool, float]:
    """
    Get the residual multiplier for a partial final year of operation.

    Used to account for only partial operation in the last year of an asset's
    lifetime.

    Parameters
    ----------
    lifetime
        Lifetime of the asset (years).

    Returns
    -------
    tuple[bool, float]
        Whether the final year is partial, and the residual cost multiplier.
    """
    lifetime = round(lifetime, ROUND_OFF)
    partial = lifetime < get_flow_size(lead_time=0.0, lifetime=lifetime)
    residual = lifetime - floor(lifetime)

    return partial, residual
