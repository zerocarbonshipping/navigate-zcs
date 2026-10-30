# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Solve a deck and draw Session 1's results figure for it.

The functions are Session 1's (`01-run-a-simple-case.ipynb`, STEP 2), with the
deck passed in rather than fixed, so that the Examples pages and their
notebooks show results the same way the workshop does. Sessions 1, 2 and 4
still define their own copies.
"""

import argparse
import contextlib
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from navigate.illustrations.plots._figure import plot_stack_with_lines
from navigate.illustrations.plots._units import get_best_unit_energy, get_best_unit_mass
from navigate.manager import SimulationManager

from _style import (AXIS, GRID, INK, SUBINK, TICK, fuel_colour, fuel_label,
                    fuel_sorted, scen_colour)

ARGS = argparse.Namespace(data_dir=Path("./assumptions"), solver=None)
FOSSIL = {"fossil_fuel_oil", "liquefied_natural_gas"}


def run_case(nav, tweak=None, quiet=True):
    """Parse the deck, optionally modify it, solve it, return the manager.

    Quiet, it drops the progress lines and prints each warning once: some decks
    repeat the same one every year of the run.
    """
    m = SimulationManager()
    if not quiet:
        m.read_deck(Path(nav), ARGS)
        if tweak is not None:
            tweak(m)
        m.run()
        return m
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
        m.read_deck(Path(nav), ARGS)
        if tweak is not None:
            tweak(m)
        m.run()
    for line in dict.fromkeys(err.getvalue().splitlines()):
        if line.strip():
            print(line, file=sys.stderr)
    return m


def years_of(m):
    return m.get_dateline().astype("datetime64[Y]").astype(int) + 1970


def scale(forecast_name, factor):
    """Multiply a forecast by `factor`, keeping what the deck already set.

    set_multiplier REPLACES the Multiplier rather than compounding with it, and
    several library forecasts ship a non-unity one, so writing the factor
    straight in would delete it.
    """
    def tweak(m):
        f = m.nodes.forecasts[forecast_name]
        f.set_multiplier(f.get_multiplier() * float(factor))
    return tweak


def freight_rate(m):
    """What moving the cargo cost each year, in USD per thousand cargo-miles.

    What the ships paid that year, as Navigate's global_expenses chart shows it:
    each ship's charter rate (CAPEX and OPEX, levelised) from the year it was
    built; fuel conversions; fuel, levies and compliance, any surplus earned
    taken off. Divided by the cargo-miles the ships moved that year. This
    version of Navigate books no spending on efficiency technology, so none is
    in it.
    """
    def num(x):
        return np.nan_to_num(np.asarray(x, dtype=float))

    miles = 0.
    for fleet in m.nodes.fleets.values():
        hulls = fleet.profile.get_existing_vessels()
        for vessel in fleet.get_vessels():
            miles = miles + num(hulls[vessel.get_name()]) * num(vessel.profile.get_cargo_miles())
    paid = num(m.profile.get_expenses())
    return 1e3 * np.divide(paid, miles, out=np.zeros_like(miles), where=miles > 0)


def summarise(m):
    """One solve, read from the totals Navigate's own charts plot."""
    years = years_of(m)
    wtw = np.nan_to_num(np.asarray(
        m.profile.get_total_equivalent_WTW(), dtype=float))

    energy, by_year = {}, {}
    for fuel, series in m.profile.get_consumed_energy().items():
        values = np.nan_to_num(np.asarray(series, dtype=float))
        if values.sum() <= 0:
            continue
        energy[fuel] = float(values.sum())
        by_year[fuel] = values
    grand = sum(energy.values())
    last_all = sum(float(v[-1]) for v in by_year.values())
    last_alt = sum(float(v[-1]) for f, v in by_year.items() if f not in FOSSIL)

    return {"years": years,
            "wtw": wtw / 1e3,                                  # kt CO2e per year
            "mix": {k: 100. * v / grand for k, v in energy.items()},
            # PJ per year, stacked in Navigate's own fuel order
            "by_year": {f: by_year[f] / 1e6 for f in fuel_sorted(by_year)},
            # USD per THOUSAND cargo-miles, as everywhere else in the workshop
            "freight": freight_rate(m),
            "alt_last": 100. * last_alt / last_all if last_all else 0.}


def print_summary(s):
    """The headline numbers of one summarise() result."""
    years = s["years"]
    for label, value, unit in (
            (f"well-to-wake in {years[0]}", f"{s['wtw'][0]:,.0f}", "kt CO2e/yr"),
            (f"well-to-wake in {years[-1]}", f"{s['wtw'][-1]:,.0f}", "kt CO2e/yr"),
            ("cumulative over the horizon", f"{s['wtw'].sum():,.0f}", "kt CO2e"),
            (f"alternative fuels in {years[-1]}", f"{s['alt_last']:.1f}", "%"),
            (f"freight rate in {years[-1]}", f"{s['freight'][-1]:,.2f}",
             "USD per k cargo-mile")):
        print(f"  {label:30} {value:>9}  {unit}")


def plot_cases(cases):
    """Emissions, the fuel bunkered and the freight rate, one line or panel per case.

    `cases` maps a label ("reference", "your scenario") to what summarise()
    returns. Emissions and cost on top, one fuel-mix panel per case below.
    """
    from matplotlib.ticker import MaxNLocator

    order = list(cases)
    TITLE, LABEL, TICK_SIZE = 12.5, 10.5, 10
    # Navigate's own units and axis labels (navigate/illustrations/plots/_units.py)
    mass_div, mass_unit = get_best_unit_mass(
        max(c["wtw"].max() for c in cases.values()) * 1e3)      # kt -> t
    energy_div, energy_unit = get_best_unit_energy(
        max(np.sum(list(c["by_year"].values()), axis=0).max() for c in cases.values())
        * 1e6, default=9)                                         # PJ -> GJ

    fig = plt.figure(figsize=(11, 8.2), constrained_layout=True)
    grid = fig.add_gridspec(2, len(order), height_ratios=[1, 1.05])
    top_grid = grid[0, :].subgridspec(1, 2, wspace=0.08)
    axE = fig.add_subplot(top_grid[0, 0])
    axC = fig.add_subplot(top_grid[0, 1])
    mix_axes = [fig.add_subplot(grid[1, 0])]
    mix_axes += [fig.add_subplot(grid[1, k], sharex=mix_axes[0], sharey=mix_axes[0])
                 for k in range(1, len(order))]

    for s in order:
        axE.plot(cases[s]["years"], cases[s]["wtw"] * 1e3 / mass_div, lw=2.4, marker=".", ms=7,
                 label=s, color=scen_colour(s))
    axE.set_title("Well-to-wake emissions", fontsize=TITLE, color=INK, loc="left")
    axE.set_ylabel(f"WTW CO$_2$-eq. [{mass_unit}]", fontsize=LABEL, color=SUBINK)
    axE.set_ylim(bottom=0.)
    if len(order) > 1:
        axE.legend(fontsize=LABEL, frameon=False, labelcolor=SUBINK, loc="lower left")

    for s in order:
        axC.plot(cases[s]["years"], cases[s]["freight"], lw=2.4, marker=".", ms=7,
                 label=s, color=scen_colour(s))
    axC.set_title("Freight rate: what moving the cargo cost", fontsize=TITLE,
                  color=INK, loc="left")
    axC.set_ylabel("Freight rate [USD/k cargo-mile]", fontsize=LABEL, color=SUBINK)
    axC.set_ylim(bottom=0.)
    # Navigate has no rebate or subsidy funded from what a regulator collects,
    # so a scheme that recycled its revenue would sit lower than this.
    axC.text(.03, .04,
             "Carbon and compliance payments are in this rate." + chr(10)
             + "None of what regulators collect is paid back:" + chr(10)
             + "the model has no rebate or subsidy funded from it.",
             transform=axC.transAxes, fontsize=8.5, color=SUBINK,
             va="bottom", ha="left", linespacing=1.5)

    fuels = fuel_sorted({f for c in cases.values() for f in c["by_year"]})
    for ax, s in zip(mix_axes, order):
        stack = [cases[s]["by_year"].get(f, np.zeros(len(cases[s]["years"])))
                 for f in fuels]
        # drawn the way Navigate's global_fuel_consumed chart draws it
        plot_stack_with_lines(ax, cases[s]["years"],
                              [v * 1e6 / energy_div for v in stack],
                              [fuel_label(f) for f in fuels],
                              [fuel_colour(f) for f in fuels])
        ax.set_title(f"Fuel consumed, {s}", fontsize=TITLE, color=INK, loc="left")
        ax.margins(x=0)
    mix_axes[0].set_ylabel(f"Fuel consumed [{energy_unit}]", fontsize=LABEL, color=SUBINK)
    fig.legend(*mix_axes[0].get_legend_handles_labels(), fontsize=LABEL,
               frameon=False, labelcolor=SUBINK, ncol=len(fuels),
               loc="outside lower center")

    for ax in (axE, axC, *mix_axes):
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(color=GRID, lw=.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=TICK, labelsize=TICK_SIZE, length=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(AXIS)

    return fig


def compare(nav, ref, tweak):
    """Solve the deck with `tweak`, print it against `ref` and draw both."""
    yours = summarise(run_case(nav, tweak))
    cols = [("reference", ref), ("your scenario", yours)]
    print(f"  {'':32}" + "".join(f" {n:>14}" for n, _ in cols) + f" {'change':>10}")
    for name, get, fmt, pp in (
            (f"well-to-wake in {ref['years'][-1]}, kt/yr", lambda c: c["wtw"][-1], ",.0f", False),
            ("cumulative, kt", lambda c: c["wtw"].sum(), ",.0f", False),
            # a share is already a percentage, so it moves in POINTS, not per cent
            (f"alternative fuels in {ref['years'][-1]}, %", lambda c: c["alt_last"], ".1f", True),
            (f"freight rate in {ref['years'][-1]}, USD/k mile", lambda c: c["freight"][-1], ",.2f", False)):
        r, y = get(ref), get(yours)
        change = f"{y - r:+.1f} pp" if pp else f"{100. * (y / r - 1.):+.1f} %"
        print(f"  {name:32} {r:14{fmt}} {y:14{fmt}} {change:>10}")
    return plot_cases({"reference": ref, "your scenario": yours})
