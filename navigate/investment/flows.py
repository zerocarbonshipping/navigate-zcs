# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from math import floor
from typing import TYPE_CHECKING, Callable

import numpy as np

from navigate.core.misc import EMPTY_FLOAT, ROUND_OFF, YEAR
from navigate.core.unit import YEAR_TO_DAYS

if TYPE_CHECKING:
    from navigate.fuel.region import Region
    from navigate.vessel.converter import Converter
    from navigate.vessel.power_system import PowerSystem
    from navigate.vessel.tank import Tank
    from navigate.vessel.technology import Technology


class Component:
    """
    Convenience struct for storing cost/WTT flows, time context, and callables.
    """
    def __init__(self) -> None:

        # callables (locked via Region at anchor times)
        self._lifetime: Callable[[float], float] | None = None
        self._replacement: Callable[[float], float] = lambda t: 0.0

        # time context shared across methods
        self.lead_time: float | None = None        # lead time of the asset, years
        self.time_initial: float | None = None     # time of investment decision, days since start of simulation
        self.time_commence: float | None = None    # time of operation commencement, days since start of simulation
        self.time_end: float | None = None         # time at cease of production, days since start of simulation

        # flows
        self._year_offset: np.ndarray = EMPTY_FLOAT
        self.year_flow: np.ndarray = EMPTY_FLOAT
        self.capex_flow: np.ndarray = EMPTY_FLOAT
        self.opex_flow: np.ndarray = EMPTY_FLOAT
        self.tied_capital_flow: np.ndarray = EMPTY_FLOAT
        self.wtt_flow: dict[str, np.ndarray] = {}

        # cached overlap schedules (computed during initialization)
        self.constant_overlap: np.ndarray | None = None
        self.staircase_segments: list[tuple[float, np.ndarray]] | None = None
        self.replacement_times: list[float] | None = None

    def initialize_flow(self, lead_time: float,
                        lifetime: float,
                        time_initial: float,
                        emissions=None
                        ) -> None:
        """
        Initialize flow containers and store shared time context.

        Parameters
        ------------
        emissions
            All emissions in the simulation.
        lead_time
            Asset lead time (years).
        lifetime
            Asset lifetime (years).
        time_initial
            Time of investment decision (days since start of simulation).
        """

        if emissions is None:
            emissions = {}

        self.capex_flow = _initialize_flow(lead_time, lifetime)
        self.opex_flow = _initialize_flow(lead_time, lifetime)
        self.tied_capital_flow = _initialize_flow(lead_time, lifetime)

        for emission in emissions:
            self.wtt_flow[emission] = _initialize_flow(lead_time, lifetime)

        self.lead_time = lead_time
        self._year_offset = np.arange(self.get_length(), dtype=float)
        self._update_time_context(time_initial)

    def initialize_process_component(self, region: Region, process_name: str) -> None:

        lifetime = region.get_process_lifetime(process_name)
        if lifetime is not None:
            self._lifetime = lambda time: lifetime.get(time)

        self._replacement = lambda time: region.get_process_replacement(process_name).get(time)

        self.compute_overlap_schedule()

    def initialize_machinery_component(self, machinery: Converter | PowerSystem | Tank | Technology) -> None:

        lifetime = machinery.lifetime
        if lifetime is not None:
            self._lifetime = lambda time: lifetime.get(time)

        self._replacement = lambda time: machinery.replacement.get(time)

        self.compute_overlap_schedule()

    def compute_overlap_schedule(self) -> None:
        """Pre-compute the staircase overlap segments and replacement times."""
        if self._lifetime is None:
            return

        self.staircase_segments = _compute_staircase_segments(self)
        self.replacement_times = _compute_replacement_times(self)

    def get_commence_index(self):
        return _bin_index(self.time_commence, self.time_initial, self.get_length())

    def add_capex_flow(self, capex_flow: np.ndarray) -> None:
        self.capex_flow += capex_flow

    def add_opex_flow(self, opex_flow: np.ndarray) -> None:
        self.opex_flow += opex_flow

    def add_tied_capital_flow(self, tied_capital_flow: np.ndarray) -> None:
        self.tied_capital_flow += tied_capital_flow

    def add_wtt_flow(self, emission_name: str, wtt_flow: np.ndarray) -> None:
        self.wtt_flow[emission_name] += wtt_flow

    def _update_time_context(self, time_initial: float) -> None:
        """Recompute time fields and constant overlap from a new investment time."""
        self.time_initial = time_initial
        self.time_commence = _future_time(time_initial, self.lead_time)
        self.time_end = _future_time(time_initial, self.get_length())
        self.year_flow = _future_time(time_initial, self._year_offset)
        self.constant_overlap = _overlap_year_bins(self.year_flow, self.time_commence, self.time_end) / YEAR_TO_DAYS

    def reset_flow(self, time_initial: float) -> None:
        """
        Zero all flow arrays and update time context, preserving array dimensions.

        After reset the Component is in the same state as a freshly allocated one
        with the same lead_time/lifetime. The caller must follow up with
        ``compute_overlap_schedule`` to recompute the overlap schedule.
        """
        self.capex_flow.fill(0)
        self.opex_flow.fill(0)
        self.tied_capital_flow.fill(0)
        for wtt in self.wtt_flow.values():
            wtt.fill(0)

        self._update_time_context(time_initial)
        self.staircase_segments = None
        self.replacement_times = None

    def add_component(self, component: "Component") -> None:
        self.add_capex_flow(component.capex_flow)
        self.add_opex_flow(component.opex_flow)
        self.add_tied_capital_flow(component.tied_capital_flow)

        for emission_name, emission_flow in component.wtt_flow.items():
            self.add_wtt_flow(emission_name, emission_flow)

    def get_length(self) -> int:
        return self.capex_flow.size

    def has_lifetime(self) -> bool:
        return True if self._lifetime is not None else False

    def get_lifetime(self, time: float) -> float:
        return self._lifetime(time)

    def get_replacement(self, time: float) -> float:
        return self._replacement(time)

    def get_cost_flow(self) -> np.ndarray:
        return self.opex_flow + self.capex_flow


def build_production_flow(component: Component, production: float) -> np.ndarray:
    """
    Expand a fixed annual production (tons/year) into a calendar-year flow vector.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ------------
    component
        Component for which production flow is calculated.
    production
        Constant production rate in tons per year.

    Returns
    --------
    np.ndarray
        Production flow per calendar year over the horizon `lead_time + lifetime`.
    """

    return _build_constant_flow(component, production)


def build_cargo_flow(component: Component, cargo: np.ndarray, timeline: np.ndarray) -> np.ndarray:
    """
    Expand a variable annual cargo-miles (cargo-miles/year) into a calendar-year flow vector.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ------------
    component
        Component for which cargo-mile flow is calculated.
    cargo
        Variable cargo-mile rate in tons per year.

    Returns
    --------
    np.ndarray
        Cargo-mile flow per calendar year over the horizon `lead_time + lifetime`.
    """

    return _build_variable_flow(component, cargo, timeline)


def add_capex_flow(component: Component,
                   capex: Callable[[float], float]) -> None:
    """
    Add initial CAPEX spread over the construction period and recurring CAPEX at the end of a component's lifetime.

    Parameters
    ------------
    component
        Component for which CAPEX costs are added.
    capex
        Callable returning CAPEX locked at the time of investment and recurring CAPEX at the end of the lifetime.
    """

    _add_initial_capex_flow(component=component, capex=capex)
    _add_recurring_capex_flow(component=component, capex=capex, partial=True)


def add_fixed_opex(component: Component, value: Callable[[float], float]) -> None:
    """
    Add any fixed/locked cost into the cost flow.

    Parameters
    ------------
    component
        Component for which OPEX costs are added.
    value
        Callable returning per-year cost locked at anchor time (days).

    Returns
    --------
    None
        Accumulates into `component.cost_flow`.
    """

    fixed = _build_staircase_flow(component=component, value=value)
    component.add_opex_flow(fixed)


def add_variable_opex(component: Component,
                      metric: Callable[[float], float],
                      cost: Callable[[np.ndarray], np.ndarray]) -> None:
    """
    Add variable cost (metric × price) into the unified cost flow.

    Parameters
    ------------
    component
        Component for which OPEX costs are added.
    metric
        Callable returning locked metric (e.g., tons/year) at anchor time (days).
    cost
        Callable returning price as a function of absolute time (days). Vectorized over arrays of days.

    Returns
    --------
    None
        Accumulates into `component.cost_flow`.
    """

    fixed = _build_staircase_flow(component=component, value=metric)
    variable = cost(component.year_flow)
    component.add_opex_flow(fixed * variable)


def add_fixed_wtt(component: Component,
                  wtt_callables: dict[str, Callable[[float], float]]) -> None:
    """
    Add fixed/locked WTT for multiple emissions in a single pass over staircase segments.

    Parameters
    ------------
    component
        Component for which WTT emissions are added.
    wtt_callables
        Mapping of emission name to callable returning locked WTT factor at anchor time (days).
    """

    if not wtt_callables:
        return

    if not component.has_lifetime():
        time_initial = component.time_initial
        overlap = component.constant_overlap

        for emission_name, wtt in wtt_callables.items():
            component.add_wtt_flow(emission_name, wtt(time_initial) * overlap)

        return

    segments = component.staircase_segments
    n = component.get_length()
    flows = {e: np.zeros(n, dtype=float) for e in wtt_callables}

    for anchor_time, normalized_overlap in segments:
        for emission_name, wtt in wtt_callables.items():
            flows[emission_name] += wtt(anchor_time) * normalized_overlap

    for emission_name, flow in flows.items():
        component.add_wtt_flow(emission_name, flow)


def add_variable_wtt(component: Component,
                     metric: Callable[[float], float],
                     wtt_callables: dict[str, Callable[[np.ndarray], np.ndarray]]) -> None:
    """
    Add variable WTT (metric × factor) for multiple emissions.

    Computes the staircase flow for the shared metric once, then multiplies
    by each emission's variable WTT factor.

    Parameters
    ------------
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


def timeline_to_yearly(asset, idx, timeline):
    """
    Define the appropriate dates (yearly) for which to calculate the cost-flow of a business case.
    This is necessary in order to ensure all cost-flows are comparable.

    Parameters
    ----------
    asset : Vessel | Plant
        Asset for which cost flow will be calculated.
    idx : int
        Current time-step index.
    timeline : np.ndarray
        Simulation timeline.

    Returns
    -------
    np.ndarray
        Yearly times (in days) for the lifetime of an asset.
    """

    lifetime = asset.lifetime.get()

    start = timeline[idx]
    end = start + lifetime * YEAR

    # define interpolation timeline and time-step sizes
    times = np.arange(start, end, YEAR)

    return times


def get_age_flow(lead_time: float, lifetime: float) -> np.ndarray:
    """
    Initialize a vector of ones with the necessary length for the yearly cost-flow of an asset.
    This can be used to calculate age levelization.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    np.ndarray
        A vector of ones.
    """

    return np.ones(get_flow_shape(lead_time, lifetime), dtype=float)


def build_operating_age_flow(lead_time: float, lifetime: float) -> np.ndarray:
    """
    Build the per-calendar-year operating fraction over the horizon `lead_time + lifetime`.

    The flow is zero during the construction lead time and one during operational years, with the
    first and last partial years prorated by their overlap with the operating window. It mirrors
    `Component.constant_overlap` and is the leveling basis for age-levelized charter rates, so that
    cost is spread only over the years the asset actually operates (matching the cost and cargo-mile
    flows, which are likewise zero during lead time).

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset (years).
    lifetime
        Operational lifetime of the asset (years).

    Returns
    -------
    np.ndarray
        Operating fraction per calendar-year bin over the horizon `lead_time + lifetime`.
    """

    n = get_flow_size(lead_time, lifetime)
    year_starts = np.arange(n, dtype=float) * YEAR_TO_DAYS
    commence = lead_time * YEAR_TO_DAYS
    end = n * YEAR_TO_DAYS

    return _overlap_year_bins(year_starts, commence, end) / YEAR_TO_DAYS


def get_flow_shape(lead_time: float, lifetime: float) -> tuple[int]:
    """
    Get the shape of the vector required to store an asset's construction and lifetime operations in yearly increments.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    tuple
        Shape of the vector required to hold a property.
    """

    return (get_flow_size(lead_time, lifetime),)


def get_flow_size(lead_time: float, lifetime: float) -> int:
    """
    Get the size of the vectors required to store an asset's lifetime operations in yearly increments.
    The number of years used in the allocation of the flow is equal to the ceil of the lifetime to account for
    lifetimes with decimals.

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

    return int(np.ceil(lead_time + lifetime))


def _add_initial_capex_flow(component: Component, capex: Callable[[float], float]) -> None:
    """
    Add initial CAPEX spread over the construction period.

    The full initial CAPEX is locked at the time of investment decision (`time_initial`)
    and then distributed across the construction lead time into calendar-year bins.
    This method only deposits into `component.capex_flow` and does not modify tied up capital.
    Tied up capital for the initial CAPEX is handled separately via `_add_initial_tied_capital_flow`.

    Parameters
    ------------
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

    if lead_time > 0.:

        # calculate the timeline over which
        # the initial CAPEX is spread
        full_years = int(np.floor(lead_time))
        fraction = full_years / lead_time

        if full_years > 0:

            # evenly distribute CAPEX across over
            # full-year lead time [0, full_years)
            delta[:full_years] += capex_t * fraction / max(full_years, 1)

        # add residual CAPEX to the last
        # partial year of construction
        delta[full_years] += capex_t * (1. - fraction)

    else:
        delta[0] += capex_t

    # add the initial capex spread over
    # lead time into the capex flow
    capex_flow += delta

    # calculate the depreciation schedule
    # of the tied capital
    _add_initial_tied_capital_flow(component, delta)


def _add_recurring_capex_flow(component: Component, capex: Callable[[float], float], *, partial: bool = False) -> None:
    """
    Add recurring CAPEX at the end of a component's lifetime.

    Replacement timing for the first interval is determined by the component lifetime
    locked at the time of investment decision (`time_initial`), with the first tranche
    installed at commencement. Each subsequent replacement interval is anchored at the
    replacement time (properties locked at `time_replace`).

    Deposits replacement CAPEX into `component.capex_flow` at the appropriate calendar-year
    bin and adds the corresponding tied up capital tranche using straight-line depreciation
    from the replacement bin start, over the component lifetime locked at the replacement year.

    Parameters
    ------------
    component
        Component for which recurring CAPEX costs are added.
    capex
        Callable returning recurring CAPEX at the replacement time (days since start of simulation).
    partial
        If True, scale the replacement CAPEX by the fraction of the next component lifetime
        that fits within the remaining horizon.
    """

    # recurring CAPEX only matters if the component
    # has a lifetime shorter than the asset lifetime
    if not component.has_lifetime():
        return

    time_initial = component.time_initial
    time_end = component.time_end

    capex_flow = component.capex_flow

    for time_replace in component.replacement_times:

        # replacement CAPEX locked at replacement event
        replace_t = component.get_replacement(time_replace)
        capex_t = capex(time_replace) * replace_t

        # optionally scale by fraction of lifetime that fits to the horizon
        if partial:
            lifetime_t = component.get_lifetime(time_replace)
            remaining_years = (time_end - time_replace) / YEAR_TO_DAYS
            if remaining_years < lifetime_t:
                capex_t *= max(remaining_years, 0.) / lifetime_t

        # deposit into the appropriate calendar bin
        idx = _bin_index(time_replace, time_initial, component.get_length())
        capex_flow[idx] += capex_t

        # depreciate this replacement tranche over
        # lifetime locked at replacement year
        lifetime_replace = component.get_lifetime(time_replace)
        _add_straight_line_depreciation(component, idx, capex_t, lifetime_replace)


def _add_initial_tied_capital_flow(component: Component, delta: np.ndarray) -> None:
    """
    Add the tied capital depreciation for the initial CAPEX delta.

    Tied up capital is built from two parts:
      1) Construction-in-Progress (CIP): cumulative initial CAPEX during construction bins
         before commencement.
      2) Straight-line depreciation from commencement (bin-start convention) with no residual
         value, applied as two tranches:
            - non-replaceable share: (1 - replace(time_initial)) depreciated over the full
              remaining asset horizon
            - replaceable share: replace(time_initial) depreciated over the component lifetime
              locked at time_initial

    Parameters
    ------------
    component
        Component for which tied up capital is added.
    delta
        Initial CAPEX deposits per calendar-year bin (typically produced by `_add_initial_capex_flow`).
    """
    time_initial = component.time_initial

    tied_capital_flow = component.tied_capital_flow
    year_flow = component.year_flow

    commence_idx = component.get_commence_index()

    # calculate the tied up capital accrued over
    # the construction period of the asset
    if commence_idx > 0:
        tied_capital_flow[:commence_idx] += np.cumsum(delta[:commence_idx])

    # calculate the total capex that
    # needs to be depreciated
    basis = delta.sum()

    # split initial basis into non-replaceable
    # and replaceable tranches
    if component.has_lifetime():
        replace_t = component.get_replacement(time_initial)
        lifetime_t = component.get_lifetime(time_initial)
    else:
        replace_t = 0.
        lifetime_t = 0.

    basis_asset = basis * (1. - replace_t)
    basis_component = basis * replace_t

    # define the time horizon over
    # which the asset is depreciated
    year_flow = component.year_flow
    lifetime_full = (component.time_end - year_flow[commence_idx]) / YEAR_TO_DAYS

    # non-replaceable share depreciates over full asset horizon
    _add_straight_line_depreciation(component, commence_idx, basis_asset, lifetime_full)

    # replaceable share depreciates over component lifetime
    _add_straight_line_depreciation(component, commence_idx, basis_component, lifetime_t)


def _add_straight_line_depreciation(component: Component,
                                    idx_start: int,
                                    basis: float,
                                    years_total: float) -> None:
    """
    Add straight-line depreciated tied up capital into a tied up capital flow vector.

    Tied up capital is evaluated at the start of each calendar-year bin (bin-start convention).
    No residual value is assumed; the tied up capital declines linearly from `basis` at
    `year_flow[idx_start]` to zero after `years_total` years.

    Parameters
    ------------
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

    if basis <= 0. or years_total <= 0.:
        return

    time_start = year_flow[idx_start]

    for i in range(idx_start, tied_capital_flow.size):

        age = (year_flow[i] - time_start) / YEAR_TO_DAYS
        remaining = basis * (1. - age / years_total)

        if remaining <= 0.:
            break

        tied_capital_flow[i] += remaining


def _compute_staircase_segments(component: Component) -> list[tuple[float, np.ndarray]]:
    """
    Walk the replacement timeline and compute the normalized overlap
    array for each segment.

    Each segment represents one component lifetime interval. The returned
    list contains (anchor_time, normalized_overlap) pairs where anchor_time
    is the time at which the value callable should be evaluated and
    normalized_overlap is the overlap per calendar-year bin as a fraction
    of a year.

    Parameters
    ----------
    component
        Component whose lifetime/replacement schedule to walk.

    Returns
    -------
    list[tuple[float, np.ndarray]]
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

    time = _future_time(time_commence, component.get_lifetime(time_invest))
    while time < time_end:
        xs.append(time)
        anchors.append(time)
        time = _future_time(time, component.get_lifetime(time))

    segments = []
    for i, x_start in enumerate(xs):
        x_end = xs[i + 1] if i + 1 < len(xs) else time_end
        if x_end <= x_start:
            continue
        overlap_days = _overlap_year_bins(year_flow, x_start, x_end)
        segments.append((anchors[i], overlap_days / YEAR_TO_DAYS))

    return segments


def _compute_replacement_times(component: Component) -> list[float]:
    """
    Walk the replacement timeline and return the times at which
    the component is replaced (excluding initial installation).

    Parameters
    ----------
    component
        Component whose lifetime/replacement schedule to walk.

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
        lifetime_t = component.get_lifetime(time_anchor)
        time_replace = _future_time(time_install, lifetime_t)
        if time_replace >= time_end:
            break
        times.append(time_replace)
        time_install = time_replace
        time_anchor = time_replace

    return times


def _build_staircase_flow(component: Component, value: Callable[[float], float]) -> np.ndarray:
    """
    Build a piecewise-constant flow that locks at installation and then at every replacement.
    The first operational calendar year is correctly handled via overlap; no special scaling
    is required because overlaps already reflect fractional lead time.

    Parameters
    ----------
    component
        Component for which value flow is calculated.
    out
        Target array to fill (overwrites).
    value
        Callable returning the locked value at the anchor time (days).

    Returns
    -------
    np.ndarray
        Piecewise constant flow vector.
    """

    # if the component lifetime is the same as
    # the asset lifetime, the staircase is a
    # constant value with zeros during lead time
    # and prorated value in the commencement year
    if not component.has_lifetime():
        return _build_constant_flow(component, value(component.time_initial))

    out = np.zeros(component.get_length(), dtype=float)
    for anchor_time, normalized_overlap in component.staircase_segments:
        out += value(anchor_time) * normalized_overlap

    return out


def _build_constant_flow(component: Component, value: float) -> np.ndarray:
    """
    Build a constant flow over the lifetime of a component.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ------------
    component
        Component for which flow is calculated.
    value
        Yearly rate.

    Returns
    --------
    np.ndarray
        Flow per calendar year over the horizon `lead_time + lifetime`.
    """

    return value * component.constant_overlap


def _build_variable_flow(component: Component, value: np.ndarray, timeline: np.ndarray) -> np.ndarray:
    """
    Build a variable flow over the lifetime of a component.

    Zeros are applied during construction lead time. The first operational year is
    automatically fractional via overlap between the operation window and the first
    calendar-year bin.

    Parameters
    ------------
    component
        Component for which flow is calculated.
    value
        Yearly rate.
    timeline
        Timeline at which `value` is defined.

    Returns
    --------
    np.ndarray
        Flow per calendar year over the horizon `lead_time + lifetime`.
    """

    time_commence = component.time_commence
    time_end = component.time_end
    year_flow = component.year_flow

    overlap_days = _overlap_year_bins(year_flow, time_commence, time_end)

    return np.interp(year_flow, timeline, value) * (overlap_days / YEAR_TO_DAYS)


def _future_time(time: float, years: int | float | np.ndarray) -> float | np.ndarray:
    """
    Add a year-based duration to an absolute time expressed in days.

    Parameters
    ------------
    time
        Absolute time in days.
    years
        Duration in calendar years.

    Returns
    --------
    float
        New absolute time in days (time + years * YEAR_TO_DAYS).
    """

    return time + years * YEAR_TO_DAYS


def _bin_index(time: float, time_initial: float, n_years: int) -> int:
    """
    Map an absolute time to its calendar-year bin index (clamped to the horizon).

    Parameters
    ------------
    time
        Absolute time in days.
    time_initial
        Start time of the first bin in days.
    n_years
        Number of calendar-year bins.

    Returns
    --------
    int
        Zero-based bin index clamped to [0, n_years-1].
    """

    idx = int((time - time_initial) // YEAR_TO_DAYS)
    if idx < 0:
        return 0
    if idx >= n_years:
        return n_years - 1
    return idx


def _overlap_year_bins(times: float | np.ndarray, a: float, b: float) -> np.ndarray:
    """
    Vectorized overlap between [a, b) and each calendar bin [t_i, t_i + YEAR_TO_DAYS).

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
    np.ndarray
        Overlap length per bin in days (same length as `times_days` slice provided).
    """

    left = np.maximum(times, a)
    right = np.minimum(times + YEAR_TO_DAYS, b)
    return np.clip(right - left, 0., YEAR_TO_DAYS)


def _initialize_flow(lead_time: float, lifetime: float) -> np.ndarray:
    """
    Initialize a vector of zeros with the necessary length for the yearly cost-flow of an asset.

    Parameters
    ----------
    lead_time
        Lead time for constructing the asset.
    lifetime
        Lifetime of the asset.

    Returns
    -------
    np.ndarray
        A vector of zeros.
    """

    return np.zeros(get_flow_shape(lead_time, lifetime), dtype=float)


# TODO: Legacy methods retained until fuel conversion code is refactored -----------------------------------------------
def as_equal_installments(lifetime, cost):
    """
    Expand a single cost into a cost-flow of equal installments over the remaining lifetime of the asset.

    Parameters
    ----------
    cost : float
        Cost.
    lifetime : float
        Lifetime of the asset.

    Returns
    -------
    np.ndarray
        Cost-flow for the remainder of the asset's lifetime.
    """

    return expand_to_flow(lifetime, cost / lifetime)


def get_remaining_cost_flow(cost_flow, remaining_lifetime, initial=True):
    """
    Get the cost-flow relevant for the remainder of an existing vessel's lifetime.

    Parameters
    ----------
    cost_flow : np.ndarray
        Cost flow
    remaining_lifetime : float
        Remaining lifetime of the vessel.
    initial : bool
        If true then return from the start of the cost flow, otherwise from the end.

    Returns
    -------
    np.ndarray
        Cost-flow for the remainder of the vessel's lifetime.
    """

    remaining_lifetime = round(remaining_lifetime, ROUND_OFF)
    size = get_flow_size(lead_time=0., lifetime=remaining_lifetime)

    if initial:
        remaining_cost = cost_flow[:size]
    else:
        remaining_cost = cost_flow[cost_flow.size - size:]

    correct_flow_residual(remaining_lifetime, remaining_cost)

    return remaining_cost


def expand_to_flow(lifetime, value):
    """
    Expand a yearly property of an asset to a flow over the lifetime of the asset.

    Parameters
    ----------
    lifetime : float
        Lifetime of an asset.
    value : float
        Yearly value of operations.

    Returns
    -------
    np.ndarray
        A vector filled with 'value'.
    """

    flow = np.full(get_flow_shape(lead_time=0., lifetime=lifetime), value)
    correct_flow_residual(lifetime, flow)

    return flow


def correct_flow_residual(lifetime, *costs):
    """
    If the lifetime of an asset is not an integer, then the cost in the last year which is only partial has to be
    corrected to reflect the cost is only incurred in a fraction of that year.

    Parameters
    ----------
    lifetime : float
        Lifetime of the vessel.
    costs : np.ndarray
        List of cost-flows for which the last time-step should be corrected.
    """

    partial, residual = get_flow_residual(lifetime)
    if partial:
        for cost in costs:
            cost[-1] *= residual


def get_flow_residual(lifetime):
    """
    Get the residual multiplier used to account for only partial
    operation in the last year of the lifetime of an asset.

    Parameters
    ----------
    lifetime : float
        Lifetime of the vessel

    Returns
    -------
    float
        Residual cost multiplier.
    """

    partial = lifetime < get_flow_size(lead_time=0., lifetime=lifetime)
    residual = lifetime - floor(lifetime)

    return partial, residual
