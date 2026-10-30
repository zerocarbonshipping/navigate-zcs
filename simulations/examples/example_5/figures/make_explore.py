# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
"""Write simulations/examples/example_5/explore.ipynb (run from the repository root).

Then run figures/make_case_map.py: this script writes the notebook without the map.
"""
import json

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

session1 = json.load(open("docs/workshop/01-run-a-simple-case.ipynb", encoding="utf-8"))
setup = "".join(session1["cells"][5]["source"])
setup = setup.replace('EXAMPLE = Path("simulations/examples/example_4")',
                      'EXAMPLE = Path("simulations/examples/example_5")')
assert "example_5" in setup
old = 'elif Path("../../navigate").is_dir():'
assert old in setup
setup = setup.replace(old, 'elif Path("../../../navigate").is_dir():\n'
                           '    # This notebook sits in simulations/examples/example_5/, three levels down.\n'
                           '    os.chdir("../../..")\n'
                           '    print("Moved up to the repository root.")\n' + old)
cut = setup.index("\n\ndef show(")
setup = setup[:cut].rstrip() + "\n"

INTRO = """\
# Example 5: Caribbean shipping under global and EU rules

How are the Caribbean's own ships affected by a global fuel standard (the IMO
Net-Zero Framework), the EU ETS and FuelEU?

The case has two fleets:

- **The regional fleet:** 330 domestic and intra-Caribbean ships (tugs, ferries,
  general cargo ships and small tankers). Nearly all are under 5,000 GT, the
  size at which all three policies start, so none of them covers these ships
  today.
- **The international fleet:** 40 container feeders on a Miami - Jamaica -
  Trinidad - Martinique loop. All three policies cover them.

New fuels are made in Trinidad, on the US Gulf Coast or in Chile, and shipped
to the ports. Every source, and every value that had to be invented, is listed in
`README.md` next to this notebook.

The notebook follows Session 1's layout:
1. run the three decks and compare them;
2. change a few levers and see what moves.

Running everything takes about five minutes.

**Note on calibration:** the regional fleet is not calibrated to the region. It
burns about 36 % more fuel in 2026 than the IMO CARES study finds (419 kt
against 309 kt), because each library ship class is a world average and
Caribbean ships are smaller. Read the results as differences between decks,
not as the region's real totals."""

CASE = """\
## The three decks

| Deck | Policies | Who they cover |
|---|---|---|
| `example_5_no_policy.nav` | none | nobody |
| `example_5_current_rules.nav` | global fuel standard, EU ETS, FuelEU | the international ships only, as today |
| `example_5_extended.nav` | the same | the regional ships too |

The extended deck stands for two possibilities:
- the region adopts the standard for its own ships;
- the EU ETS review brings ships of 400 - 5,000 GT in. Martinique is an EU
  outermost region, so this would reach ships calling there.

The cell below runs the three decks and draws two figures, one for each fleet.
In each figure:
- the top row shows emissions and the yearly fuel and policy bill;
- the bottom row shows the fuel mix, one panel per deck."""

MACHINERY = '''\
# @title The machinery (nothing to edit)
import argparse
import contextlib
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from navigate.calculator._table_data import TableData
from navigate.manager import SimulationManager

_STYLE_DIR = str(Path("docs/workshop").resolve())
if _STYLE_DIR not in sys.path:
    sys.path.insert(0, _STYLE_DIR)

from _style import (AXIS, GRID, INK, SUBINK, TICK, fuel_colour, fuel_label,
                    fuel_sorted, scen_colour, swatch)

# A few lever combinations make this version of Navigate's solver hang on one
# year. This caps the method that hangs and solves that year again with another
# one; runs that solve today are unchanged. See docs/workshop/_solver.py.
from _solver import guard_interior_point

guard_interior_point()

ARGS = argparse.Namespace(data_dir=Path("./assumptions"), solver=None)
DECKS = {"no policy": "example_5_no_policy.nav",
         "current rules": "example_5_current_rules.nav",
         "extended": "example_5_extended.nav"}
FLEETS = {"regional": "reg_", "international": "intl_"}

# none < current < extended, as an ordered ramp like the reference scenarios'
DECK_COLOUR = {"no policy": swatch("black", 5),
               "current rules": swatch("blue", 7),
               "extended": swatch("blue", 8)}


def colour(case):
    return DECK_COLOUR.get(case, scen_colour(case))


def run_deck(deck, tweak=None):
    """Parse a deck, optionally modify it, solve it, return the manager."""
    m = SimulationManager()
    with contextlib.redirect_stdout(io.StringIO()):
        m.read_deck(EXAMPLE / deck, ARGS)
        if tweak is not None:
            tweak(m)
        m.run()
    return m


def summarise(m, prefix):
    """One fleet group's results: emissions, the bill, the fuel mix and the ships."""
    years = m.get_dateline().astype("datetime64[Y]").astype(int) + 1970
    out = {"years": years, "wtw": 0., "bill": 0., "ships": 0., "fuels": {}}
    for name, fleet in m.nodes.fleets.items():
        if not name.startswith(prefix):
            continue
        p = fleet.profile
        out["wtw"] = out["wtw"] + np.nan_to_num(p.get_total_equivalent_WTW()) / 1e3      # kt
        out["bill"] = out["bill"] + (np.nan_to_num(p.get_total_fuel_expenses())
                                     + np.nan_to_num(p.get_regulation_expenses())) / 1e6  # M USD
        out["ships"] = out["ships"] + sum(np.nan_to_num(v) for v in p.get_existing_vessels().values())
        for fuel, energy in p.get_consumed_energy().items():
            out["fuels"][fuel] = out["fuels"].get(fuel, 0.) + np.nan_to_num(energy) / 1e6  # PJ
    return out


def _style_axes(ax):
    ax.grid(color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TICK, labelsize=10)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)


def plot_cases(cases, title):
    """Emissions and the yearly bill on top, one fuel-mix panel per case below."""
    order = list(cases)
    fig = plt.figure(figsize=(11, 8.2), constrained_layout=True)
    grid = fig.add_gridspec(2, len(order), height_ratios=[1, 1.05])
    top = grid[0, :].subgridspec(1, 2, wspace=0.08)
    axE, axB = fig.add_subplot(top[0, 0]), fig.add_subplot(top[0, 1])
    mix = [fig.add_subplot(grid[1, 0])]
    mix += [fig.add_subplot(grid[1, k], sharex=mix[0], sharey=mix[0]) for k in range(1, len(order))]

    for case in order:
        r = cases[case]
        axE.plot(r["years"], r["wtw"], lw=2.4, marker=".", ms=7, label=case, color=colour(case))
        axB.plot(r["years"], r["bill"], lw=2.4, marker=".", ms=7, label=case, color=colour(case))
    axE.set_title("Well-to-wake emissions", fontsize=12.5, color=INK, loc="left")
    axE.set_ylabel("kt CO2e per year", fontsize=10.5, color=SUBINK)
    axB.set_title("Fuel and policy bill", fontsize=12.5, color=INK, loc="left")
    axB.set_ylabel("million USD per year", fontsize=10.5, color=SUBINK)
    for ax in (axE, axB):
        ax.set_ylim(bottom=0.)
        _style_axes(ax)
    axE.legend(fontsize=10.5, frameon=False, labelcolor=SUBINK, loc="lower left")

    fuels = fuel_sorted({f for r in cases.values() for f, e in r["fuels"].items() if e.sum() > 0})
    for ax, case in zip(mix, order):
        r = cases[case]
        ax.stackplot(r["years"], [r["fuels"].get(f, 0 * r["years"]) for f in fuels],
                     colors=[fuel_colour(f) for f in fuels], labels=[fuel_label(f) for f in fuels],
                     linewidth=0, alpha=0.9)
        ax.set_title(case, fontsize=11, color=INK, loc="left")
        _style_axes(ax)
    mix[0].set_ylabel("PJ of fuel per year", fontsize=10.5, color=SUBINK)
    handles, labels = mix[0].get_legend_handles_labels()
    fig.legend(handles[::-1], labels[::-1], loc="outside right center", fontsize=9.5,
               frameon=False, labelcolor=SUBINK)
    fig.suptitle(title, fontsize=13.5, color=INK, x=0.01, ha="left")
    plt.show()


def table(cases):
    """Cumulative emissions and bill, 2026-2050, and the oil share in 2050."""
    print(f"  {'':16}{'WTW 2026-2050':>16}{'bill 2026-2050':>17}{'oil share 2050':>17}")
    for case, r in cases.items():
        total = sum(e[-1] for e in r["fuels"].values()) or 1.
        oil = r["fuels"].get("fossil_fuel_oil", np.zeros(1))[-1] / total
        print(f"  {case:16}{r['wtw'].sum() / 1e3:12.1f} Mt{r['bill'].sum() / 1e3:12.2f} bn$"
              f"{100 * oil:15.0f} %")


# ---- the levers, each a change to the freshly parsed deck --------------------
def scale_forecast(name, factor):
    def tweak(m):
        if name in m.nodes.forecasts:          # the no-policy deck has no standard
            f = m.nodes.forecasts[name]
            f.set_multiplier(f.get_multiplier() * float(factor))
    return tweak


def set_variable(name, value):
    def tweak(m):
        m.nodes.variables[name].set_value(float(value))
    return tweak


def transport_cost(factor):
    def tweak(m):
        m.general_nodes.bunker_logistics.set_transport_cost("*", 0.02 * float(factor))
    return tweak


def caribbean_renewables(usd_per_mwh):
    def tweak(m):
        m.nodes.regions["caribbean"].set_source_opex("renewable", float(usd_per_mwh))
    return tweak


SITES = {"trinidad": "producer_trinidad", "gulf coast": "producer_americas",
         "chile": "producer_chile"}


def fuel_sites(sites):
    """Keep only the production sites listed; the others build nothing."""
    unknown = set(sites) - set(SITES)
    assert not unknown, f"unknown sites {unknown}; choose from {list(SITES)}"
    def tweak(m):
        for site, producer in SITES.items():
            if site not in sites:
                m.nodes.producers[producer].set_maximum_development(0.)
    return tweak


def chile_electricity(case):
    """The library's Americas case standing for Chilean wind: "low" (the deck) or "mid".

    Only the Chile region reads electricity_cost_americas_low in this deck, so
    "mid" copies the mid case's values into that forecast.
    """
    assert case in ("low", "mid"), 'CHILE_ELECTRICITY is "low" or "mid"'
    def tweak(m):
        if case == "low":
            return
        mid = m.nodes.forecasts["electricity_cost_americas_mid"]
        rows = [[str(d.astype("datetime64[D]")), float(mid.calculate(x))]
                for d, x in zip(mid.get_x_date(), mid.get_x())]
        low = m.nodes.forecasts["electricity_cost_americas_low"]
        low.set_multiplier(1.)
        low.set_table(TableData(rows=rows))
        low.replace_reference_table(m.general_nodes.model_definition.get_start_date())
    return tweak


def gfs(covers=None, start=2028, base_target=None, direct_target=None,
        tier_1_price=100., tier_2_price=380.):
    """Rebuild the global fuel standard in a deck that has one.

    The targets are % cuts in GHG fuel intensity against 93.3 gCO2e/MJ, by year,
    joined linearly and held flat after the last year given. Before `start` there
    is no target and no price. The deck carries the standard as two regulations
    that add up, so gfs_tier_2 charges the difference between the two prices.
    """
    base_target = base_target or {2028: 4, 2030: 8, 2035: 30}
    direct_target = direct_target or {2028: 17, 2030: 21, 2035: 43}
    assert start >= 2026, "the run starts in 2026"
    assert tier_2_price >= tier_1_price, "Tier 2 is the dearer tier"
    patterns = {"nobody": [], "international": ["intl_*"], "all": ["intl_*", "reg_*"]}

    def target_rows(cuts):
        years = sorted(cuts)
        allowed = [1. - cuts[y] / 100. for y in years]
        rows = [["01-01-2025", 1.], [f"31-12-{start - 1}", 1.],
                [f"01-01-{start}", float(np.interp(start, years, allowed))]]
        return rows + [[f"01-01-{y}", a] for y, a in zip(years, allowed) if y > start]

    def price_rows(price):
        return [["01-01-2025", 0.], [f"31-12-{start - 1}", 0.],
                [f"01-01-{start}", float(price)], ["01-01-2050", float(price)]]

    def tweak(m):
        if "gfs_tier_1" not in m.nodes.regulations:
            print("This deck has no global fuel standard; the GFS settings are ignored.")
            return
        start_date = m.general_nodes.model_definition.get_start_date()
        for name, rows in (("gfs_direct_compliance_target", target_rows(direct_target)),
                           ("gfs_base_target", target_rows(base_target)),
                           ("gfs_tier_1_price", price_rows(tier_1_price)),
                           ("gfs_tier_2_extra_price", price_rows(tier_2_price - tier_1_price))):
            forecast = m.nodes.forecasts[name]
            forecast.set_table(TableData(rows=rows))
            forecast.replace_reference_table(start_date)   # dates to days since the start
        if covers is not None:
            for name in ("gfs_tier_1", "gfs_tier_2"):
                regulation = m.nodes.regulations[name]
                regulation.set_include_vessel("*", "FALSE")
                for pattern in patterns[covers]:
                    regulation.set_include_vessel(pattern, "TRUE")
    return tweak


def both(*tweaks):
    def tweak(m):
        for t in tweaks:
            if t is not None:
                t(m)
    return tweak
'''

RUN_REF = '''\
# @title Run the three decks and compare them (about 5 minutes)
REF = {case: run_deck(deck) for case, deck in DECKS.items()}

for group, prefix in FLEETS.items():
    cases = {case: summarise(m, prefix) for case, m in REF.items()}
    plot_cases(cases, f"The {group} fleet")
    table(cases)'''

READ = """\
## What the three decks show

- **Today's rules leave the regional fleet where it was without any policy.**
  Its lines for "no policy" and "current rules" lie on top of each other. This
  is partly a limit of Navigate:
  - Navigate prices a new fuel at what it costs to make and deliver. The
    feeders' demand does not raise the price for anyone else.
  - So nothing reaches the regional ships through the fuel market.
  - The real spill-overs are outside the model: freight rates, bunker
    suppliers' margins, and port infrastructure that the feeders' demand pays
    for.
- **Covering the regional ships cuts their emissions, at a price.** Much of the
  extra bill is remedial payments: paying 380 USD per ton is cheaper than
  switching fuel for many of these ships.
- **The feeders gain when the regional fleet is covered.** The larger demand gets
  more plants built, and the feeders burn more ammonia."""

YOURS_MD = """\
## Your scenario

Set the levers, then run the cell. It solves the deck you pick, with your
changes, and compares it with the same deck as shipped. A run takes about a
minute and a half.

**The global fuel standard can be rewritten from here.** The settings apply to
the current rules and extended decks; the no-policy deck has no standard.
- **Who it covers:** `GFS_COVERS` set to `"nobody"`, `"international"` or
  `"all"`. Leave it at `None` to keep what the deck says.
- **When it starts:** `GFS_START`.
- **How tight it is:** the two targets, as % cuts by year against the 2008
  reference of 93.3 gCO2e/MJ. Points are joined linearly and held flat after
  the last one, so add a 2040 or 2050 point to keep tightening.
- **What a deficit costs:** the two tier prices.

The defaults are the IMO Net-Zero Framework as approved in draft at MEPC 83.
The example below adds a tightening after 2035; those points are INVENTED for
illustration and do not come from any text.

Two of the other levers need a note:
- `FUEL_SITES` lists the production sites that may build. Each one makes:
  - Trinidad: blue ammonia, e-ammonia and e-methanol;
  - the Gulf Coast: the same three, plus bio-methanol;
  - Chile: e-ammonia and e-methanol, on cheaper wind but 4,700 - 5,250 nm away.

  Navigate sizes each site on a fuel's whole gap, whatever it costs (a known
  producer-planning bug), so Chile's cheaper power does not win it a larger
  share. Switching sites off is the honest way to compare cheap-and-far with
  near-and-dearer. A port sells each fuel at the supply-weighted average
  delivered cost of the plants serving it.
- `CHILE_ELECTRICITY` picks the library's Americas cost case that stands for
  Chilean wind: `"low"` (the deck) or `"mid"`, Trinidad's.
- `CARIBBEAN_RENEWABLES` replaces the library's Americas electricity cost,
  which the deck uses as a proxy for Trinidad's renewables."""

YOURS = '''\
# ===========================================================================
#  YOUR SCENARIO.  Set the levers, then run this cell.
#
#  As an example, the global fuel standard keeps tightening after 2035, to zero
#  by 2050 (INVENTED points, marked below). Delete the 2040 and 2050 points to
#  return to the deck's standard.
# ===========================================================================
DECK              = "current rules"   # "no policy", "current rules" or "extended"

# ---- the global fuel standard (defaults: the MEPC 83 draft) ------------------
GFS_COVERS        = None     # None = as the deck says; "nobody", "international" or "all"
GFS_START         = 2028     # the first year it applies
GFS_BASE_TARGET   = {2028: 4, 2030: 8, 2035: 30,      # % cut against 93.3 gCO2e/MJ
                     2040: 65, 2050: 100}             # INVENTED example points
GFS_DIRECT_TARGET = {2028: 17, 2030: 21, 2035: 43,
                     2040: 80, 2050: 100}             # INVENTED example points
GFS_TIER_1_PRICE  = 100      # USD/t CO2e for a deficit between the two targets
GFS_TIER_2_PRICE  = 380      # USD/t CO2e for a deficit beyond the base target

# ---- the other levers: multipliers, so 1.0 is the deck -----------------------
#                              suggested span   what 1.0 means in the deck
OIL_PRICE            = 1.0   # 0.7 - 2.0   485 USD/t, flat to 2050
TRANSPORT_COST       = 1.0   # 0.5 - 3.0   0.02 USD per ton per nautical mile (INVENTED)
BUILD_SHARE          = 1.0   # 0.25 - 4.0  the region gets 2 % of shipping's plant building (INVENTED)

FUEL_SITES           = ["trinidad", "gulf coast", "chile"]   # any of the three
CHILE_ELECTRICITY    = "low"    # "low" (49 USD/MWh in 2026, 33 by 2050) or "mid" (62 and 41)
CARIBBEAN_RENEWABLES = None     # None = the library's Americas cost (62 USD/MWh in 2026, 41 by 2050);
                                # or a flat value in USD/MWh, e.g. 85, Jamaica's solar contracts (2016-17)
# ===========================================================================

tweak = both(gfs(GFS_COVERS, GFS_START, GFS_BASE_TARGET, GFS_DIRECT_TARGET,
                 GFS_TIER_1_PRICE, GFS_TIER_2_PRICE),
             scale_forecast("fossil_fuel_oil_price_global", OIL_PRICE),
             transport_cost(TRANSPORT_COST),
             set_variable("caribbean_share_of_build", 0.02 * BUILD_SHARE),
             fuel_sites(FUEL_SITES),
             chile_electricity(CHILE_ELECTRICITY),
             caribbean_renewables(CARIBBEAN_RENEWABLES) if CARIBBEAN_RENEWABLES else None)

yours = run_deck(DECKS[DECK], tweak)
for group, prefix in FLEETS.items():
    cases = {"reference": summarise(REF[DECK], prefix), "your scenario": summarise(yours, prefix)}
    plot_cases(cases, f"The {group} fleet: {DECK}, as shipped and with your levers")
    table(cases)'''

LIMITS = """\
## Before quoting a number

These limits apply to every result above:
- **The regional fleet is not calibrated.** In 2026 it burns 419 kt of fuel and
  emits 1.59 Mt CO2e well-to-wake. The IMO CARES study puts these ships at 309
  kt and about 1.0 Mt CO2e, so the model is about 36 % too high on fuel. Each
  library ship class is a world average, and Caribbean ships are smaller (most
  CARES tugs are 250 - 300 GT). The gap is left in on purpose; compare the
  decks with each other, not with the region's real totals.
- **Where fuel is made:** with several sites on, each builds about the same
  amount of a fuel, whatever it costs. Use `FUEL_SITES` to compare.
- **The global fuel standard is not adopted.** As shipped:
  - its prices are set only to 2030, and its targets only to 2035; both are
    held flat after that, unless you change them above;
  - surplus units pool freely, which the framework restricts.
- **Exemptions:** the extended deck ignores the outermost-region exemptions,
  which run until 2030 for the EU ETS and 2029 for FuelEU.

For a larger sweep of these levers, use the Center's own tool, horizon-zcs,
rather than running this cell many times."""

nb = new_notebook(cells=[
    new_markdown_cell(INTRO),
    new_code_cell(setup),
    new_markdown_cell(CASE),
    new_code_cell(MACHINERY),
    new_code_cell(RUN_REF),
    new_markdown_cell(READ),
    new_markdown_cell(YOURS_MD),
    new_code_cell(YOURS),
    new_markdown_cell(LIMITS),
])
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb.metadata["language_info"] = {"name": "python"}
out = "simulations/examples/example_5/explore.ipynb"
open(out, "w", encoding="utf-8", newline="\n").write(nbformat.writes(nb))
print("wrote", out)
