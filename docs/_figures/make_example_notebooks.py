# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Write and run the notebooks of the Examples pages.

Run from the repository root:

    python docs/_figures/make_example_notebooks.py                # all of them
    python docs/_figures/make_example_notebooks.py two-fleets     # one

For the examples whose deck has no workshop session of its own (example_4 is
Session 1's, the world fleet Session 2's), writes one executed notebook each, in
one of two forms:

- A PAGE, docs/examples/<page>.ipynb, when docs/examples/_pages/<page>.md exists.
  The notebook is the Examples page itself on the site and the Colab notebook,
  one document. The .md holds the page's prose; each line `{{ name }}` in it is
  replaced by cells (see SLOTS below): the map, the Setup cell (removed from the
  site, which shows the stored outputs), the run and lever cells, the deck in
  tabs (Session 3's show_deck, from docs/workshop/_deck.py) and the
  prompt-bank entries. The deck and the prompts reach the site as the stored
  output and copied text, so run this again after changing either. Relative
  links become links to the site, which work in both.
- An EXPLORE notebook, docs/examples/<page>-explore.ipynb, next to a
  hand-written <page>.md, for the examples not moved to the page form yet.

The Colab badge and the Setup cell are taken from Session 1, so a change there
reaches these notebooks the next time this runs. The case map travels as a
base64 PNG in markdown, the only form every viewer shows (see
map_to_notebook.py).

Executes on the `navigate-zcs` kernel with PYTHONUTF8 set, then saves the
standard python3 kernelspec, as docs/workshop/AGENTS.md asks.
"""

import base64
import os
import pathlib
import posixpath
import re
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_map_png  # noqa: E402

SESSION_1 = pathlib.Path("docs/workshop/01-run-a-simple-case.ipynb")
OUT = pathlib.Path("docs/examples")
PAGES = OUT / "_pages"
BANK = pathlib.Path("docs/workshop/prompt-bank.md")
SITE_ROOT = "https://zerocarbonshipping.github.io/navigate-zcs/workshop-preview"
SITE = f"{SITE_ROOT}/examples"
GITHUB = "https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop"
NOT_ON_SITE = ("workshop/prompt-bank.md", "workshop/building-a-deck.md")
COLAB = ("https://colab.research.google.com/github/zerocarbonshipping/navigate-zcs/"
         "blob/workshop-colab/docs/workshop/01-run-a-simple-case.ipynb")

EXAMPLES = {
    "mainline-and-feeders": {
        "title": "A mainline and its feeders",
        "question": "How do two ship sizes on connected routes choose fuels when the "
                    "ports supply them unevenly?",
        "deck": "simulations/examples/example_1",
        "map": ("svg", "examples/mainline_feeders_map"),
        "alt": "Map of a container mainline from Singapore to Rotterdam via Suez, "
               "feeders from Rotterdam to Hamburg and Aalborg, and a European "
               "bio-methanol plant",
        "deck_files": [("example_1.nav", ["example_1.nav"]),
                       ("Fleets", ["includes/mainlines.inc", "includes/feeders.inc",
                                   "includes/mainlines_curves.inc", "includes/feeders_curves.inc"]),
                       ("Routes", ["includes/route.inc", "includes/ports.inc",
                                   "includes/bunker_logistics.inc"]),
                       ("Fuel", ["includes/fuel_production.inc", "includes/regions.inc",
                                 "includes/producer.inc"]),
                       ("Regulation", ["includes/cii.inc", "includes/eu_ets.inc",
                                       "includes/fuel_eu.inc", "includes/net_zero_framework.inc"]),
                       ("Decisions and report", ["includes/decision_processes.inc",
                                                 "includes/report.inc"])],
        "sensitivities": [
            ("OIL_PRICE", 2.0, ["fossil_fuel_oil_price_global"], "0.7 - 2.0",
             "485 USD/t, flat to 2050"),
            ("EU_ETS_PRICE", 1.0, ["eu_ets_carbon_credit_price"], "0.5 - 3.0",
             "126 USD/t in 2026, 417 by 2050"),
            ("BIOMASS_COST", 1.0, ["feedstock_biomethanol_gasification_cost"], "0.25 - 2.0",
             "65 USD per dry t of the biomass bio-methanol is made from, flat")],
        "sensitivity_example": "As an example, OIL_PRICE is set to 2.0: the fuel oil price doubled",
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("EU_ETS_PRICE", 1.0, "eu_ets_carbon_credit_price", "EU ETS carbon price"),
                   ("BIOMASS_COST", 1.0, "feedstock_biomethanol_gasification_cost",
                    "cost of the biomass bio-methanol is made from")],
    },
    "south-pacific": {
        "title": "Island trade in the South Pacific",
        "question": "Can a regional bulk trade switch to biodiesel when only its main "
                    "ports supply it?",
        "deck": "simulations/examples/example_2",
        "map": ("svg", "examples/south_pacific_map"),
        "alt": "Map of a bulk trade between Australia, New Zealand, Fiji, Samoa and "
               "Tonga, with FAME from Europe bunkered in Australia and New Zealand only",
        "deck_files": [("example_2.nav", ["example_2.nav"]),
                       ("Fleet", ["includes/fleet.inc", "includes/energy_efficiencies.inc",
                                  "includes/fleet_curves.inc",
                                  "includes/energy_efficiencies_curves.inc"]),
                       ("Route", ["includes/route.inc", "includes/ports.inc",
                                  "includes/bunker_logistics.inc"]),
                       ("Fuel", ["includes/fuel_production.inc", "includes/regions.inc",
                                 "includes/producer.inc"]),
                       ("Regulation", ["includes/cii.inc", "includes/net_zero_framework.inc"]),
                       ("Decisions", ["includes/decision_processes.inc"])],
        "sensitivities": [
            ("OIL_PRICE", 2.0, ["fossil_fuel_oil_price_global"], "0.7 - 2.0",
             "485 USD/t, flat to 2050"),
            ("COOKING_OIL_COST", 1.0, ["used_cooking_oil_cost_europe"], "0.25 - 2.0",
             "1,130 USD/t of the used cooking oil FAME is made from, flat")],
        "sensitivity_example": "As an example, OIL_PRICE is set to 2.0: the fuel oil price doubled",
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("COOKING_OIL_COST", 1.0, "used_cooking_oil_cost_europe",
                    "cost of the used cooking oil FAME is made from")],
    },
    "rhine": {
        "title": "Inland waterways in Germany",
        "question": "What e-fuel price and CO2 price lead fleet owners and operators to "
                    "switch fuel?",
        "deck": "simulations/examples/example_6",
        # page form: the deck's files, grouped as the page shows them
        "deck_files": [("The deck", ["example_6.nav"]),
                       ("Placeholders", ["includes/placeholders.inc"]),
                       ("Fleet", ["includes/fleet.inc"]),
                       ("Route", ["includes/route.inc"]),
                       ("Fuels and ports", ["includes/fuels.inc", "includes/ports.inc",
                                            "includes/bunker_logistics.inc"]),
                       ("CO2 price", ["includes/co2_price.inc"]),
                       ("Decision processes", ["includes/calibration.inc"]),
                       ("Report", ["includes/report.inc"])],
        "map": ("png", "rhine_inland_map.png"),
        "alt": "Map of an inland trade on the Rhine in Germany from Duisburg upstream "
               "to Mannheim, calling at Cologne, Koblenz and Mainz, with every fuel "
               "bought at the two ends",
        # page form, as Session 1's sensitivities: (name, example value, the forecasts
        # it multiplies, suggested span, what 1.0 means in the deck)
        "sensitivities": [
            ("OIL_PRICE", 1.0, ["fossil_fuel_oil_price_global"], "0.7 - 2.0",
             "485 USD/t (11.8 USD/GJ), flat to 2050"),
            ("LNG_PRICE", 1.0, ["liquefied_natural_gas_price_global"], "0.7 - 1.6",
             "436 USD/t (8.7 USD/GJ), flat to 2050"),
            ("CO2_PRICE", 1.0, ["germany_co2_price"], "0.0 - 10.0",
             "65 USD/t CO2 in 2026, 150 by 2050 (INVENTED); 0.0 = no CO2 price"),
            ("E_DIESEL_PRICE", 0.2, ["rhine_e_diesel_price"], "0.1 - 1.0",
             "103 USD/GJ in 2026, 71 by 2050"),
            ("E_METHANOL_PRICE", 1.0, ["rhine_e_methanol_price"], "0.1 - 1.0",
             "84 USD/GJ in 2026, 57 by 2050"),
            ("FAME_PRICE", 1.0, ["rhine_fame_price"], "0.2 - 1.0",
             "45 USD/GJ, flat to 2050"),
            ("HULL_PRICE", 1.0, ["rhine_hull_capex"], "0.5 - 2.0",
             "6 M USD for the hull (INVENTED)")],
        "sensitivity_example": ("As an example, E_DIESEL_PRICE is set to 0.2: e-diesel at a "
                                "fifth of the deck's price"),
    },
    "caribbean": {
        "title": "Caribbean shipping under global and EU rules",
        "question": "How are a region's own ships affected by global and EU rules, "
                    "today and if extended to them?",
        "deck": "simulations/examples/example_5",
        # page form: the one deck, today's rules, run three ways by whom the four
        # regulations cover; the levers move the extended run
        "run_setup": (
            'POLICIES = ["gfs_tier_1", "gfs_tier_2", "eu_ets", "fuel_eu"]\n\n\n'
            "def cover(*patterns):\n"
            '    """The four regulations cover the vessels matching these patterns, and no other."""\n'
            "    def tweak(m):\n"
            "        for name in POLICIES:\n"
            "            regulation = m.nodes.regulations[name]\n"
            '            regulation.set_include_vessel("*", "FALSE")\n'
            "            for pattern in patterns:\n"
            '                regulation.set_include_vessel(pattern, "TRUE")\n'
            "    return tweak\n\n\n"),
        "runs": {"no policy": "cover()",
                 "current rules": 'cover("intl_*")',
                 "extended": 'cover("intl_*", "reg_*")'},
        "lever_deck": "extended",
        "deck_files": [("example_5.nav", ["example_5.nav"]),
                       ("Fleet", ["includes/fleet.inc", "includes/converter_available.inc"]),
                       ("Route", ["includes/route.inc", "includes/ports.inc",
                                  "includes/bunker_logistics.inc"]),
                       ("Fuel", ["includes/fuel_production.inc", "includes/regions.inc",
                                 "includes/producer.inc"]),
                       ("Policy", ["includes/policy_gfs.inc", "includes/policy_eu.inc",
                                   "includes/extend_to_regional.inc"]),
                       ("Report", ["includes/report.inc"])],
        "sensitivities": [
            ("OIL_PRICE", 2.0, ["fossil_fuel_oil_price_global"], "0.7 - 2.0",
             "485 USD/t, flat to 2050"),
            ("LNG_PRICE", 1.0, ["liquefied_natural_gas_price_global"], "0.7 - 1.6",
             "436 USD/t, flat to 2050"),
            ("GFS_TIER_1_PRICE", 1.0, ["gfs_tier_1_price"], "0.5 - 4.0",
             "100 USD/t CO2e from 2028 (Tier 2 adds 280 more)"),
            ("EU_ETS_PRICE", 1.0, ["eu_ets_carbon_credit_price"], "0.5 - 3.0",
             "126 USD/t in 2026, 417 by 2050"),
            ("AMERICAS_ELECTRICITY_PRICE", 1.0, ["electricity_cost_americas_mid"], "0.6 - 1.4",
             "62 USD/MWh in 2026, 41 by 2050: the power e-fuels are made from")],
        "sensitivity_example": "As an example, OIL_PRICE is set to 2.0: the fuel oil price doubled",
        "map": ("png", "caribbean_case_map.png"),
        "alt": "Map of the Caribbean case: Miami, Kingston, Point Lisas and "
               "Fort-de-France, the feeders' and the regional loops, and fuel shipped "
               "in from Trinidad, the US Gulf Coast and Chile",
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("GFS_TIER_1_PRICE", 1.0, "gfs_tier_1_price",
                    "price of the global fuel standard's first tier"),
                   ("AMERICAS_ELECTRICITY_PRICE", 1.0, "electricity_cost_americas_mid",
                    "electricity price in the Americas, where e-fuels are made")],
    },
    "two-fleets": {
        "title": "Two fleets in the Baltic",
        "question": "How much do the owners' efficiency choices matter on the same trade?",
        "deck": "simulations/examples/example_3",
        "map": ("svg", "examples/baltic_map"),
        "alt": "Map of the Baltic case: mid-range tankers between Helsinki, Stockholm "
               "and Gdansk, coastal tankers between Helsinki, Tallinn and Stockholm, and "
               "a European e-ammonia plant delivering to Helsinki and Stockholm",
        "deck_files": [("example_3.nav", ["example_3.nav"]),
                       ("Fleets", ["includes/regular_fleet.inc", "includes/efficient_fleet.inc",
                                   "includes/regular_fleet_curves.inc",
                                   "includes/efficient_fleet_curves.inc"]),
                       ("Route", ["includes/route.inc", "includes/ports.inc",
                                  "includes/bunker_logistics.inc"]),
                       ("Fuel", ["includes/fuel_production.inc", "includes/regions.inc",
                                 "includes/producer.inc"]),
                       ("Regulation", ["includes/cii.inc", "includes/eu_ets.inc",
                                       "includes/fuel_eu.inc", "includes/net_zero_framework.inc"]),
                       ("Decisions", ["includes/decision_processes.inc"])],
        "sensitivities": [
            ("OIL_PRICE", 2.0, ["fossil_fuel_oil_price_global"], "0.7 - 2.0",
             "485 USD/t, flat to 2050"),
            ("EU_ETS_PRICE", 1.0, ["eu_ets_carbon_credit_price"], "0.5 - 3.0",
             "126 USD/t in 2026, 417 by 2050"),
            ("EUROPE_ELECTRICITY_PRICE", 1.0, ["electricity_cost_europe_mid"], "0.6 - 1.4",
             "72 USD/MWh in 2026, 53 by 2050: the power e-ammonia is made from")],
        "sensitivity_example": "As an example, OIL_PRICE is set to 2.0: the fuel oil price doubled",
        # the question is fleet against fleet: each class's two fleets, side by side
        "extra_figure": (
            "plot_fleet_emissions(_m, {\n"
            '    "MR tankers (~47,000 DWT)": {"regular": "mid_range_regular",\n'
            '                                 "efficient": "mid_range_efficient"},\n'
            '    "Coastal tankers (~7,500 DWT)": {"regular": "coastal_regular",\n'
            '                                     "efficient": "coastal_efficient"},\n'
            '}, {"regular": "#4c4c4c", "efficient": "#377070"})\n'),
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("EU_ETS_PRICE", 1.0, "eu_ets_carbon_credit_price", "EU ETS carbon price"),
                   ("EUROPE_ELECTRICITY_PRICE", 1.0, "electricity_cost_europe_mid",
                    "electricity price in Europe, where e-ammonia is made")],
    },
}


def map_png(kind, ref):
    if kind == "png":
        return (HERE / ref).read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        render_map_png.HERE = pathlib.Path(tmp)
        (pathlib.Path(tmp) / ref).parent.mkdir(parents=True, exist_ok=True)
        return render_map_png.render(ref).read_bytes()


def session_1_cells():
    nb = nbformat.read(SESSION_1, as_version=4)
    badge = nb.cells[0]
    setup = next(c for c in nb.cells
                 if c.cell_type == "code" and c.source.startswith("# @title Setup"))
    return badge, setup, nb.metadata


md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell


def badge_cell(badge, notebook):
    return md(badge.source.replace(
        COLAB, COLAB.replace("docs/workshop/01-run-a-simple-case.ipynb",
                             f"docs/examples/{notebook}")))


def map_cell(ex):
    b64 = base64.b64encode(map_png(*ex["map"])).decode("ascii")
    return md(f"![{ex['alt']}](data:image/png;base64,{b64})")


def setup_cell(ex, setup):
    head = setup.source.split("# Load the example deck.")[0].rstrip()
    cell = code(
        head + "\n\n\n# The example deck.\n"
        f'EXAMPLE = Path("{ex["deck"]}")\n'
        "assert EXAMPLE.is_dir(), (\n"
        '    f"{EXAMPLE} not found under {Path.cwd()}. On Colab the setup cell clones the "\n'
        '    f"{BRANCH!r} branch, so this deck has to be committed and pushed there."\n'
        ")\n", metadata=dict(setup.metadata))
    cell.metadata.pop("execution", None)
    return cell


def run_cells(ex, heading, quiet=False):
    """The cell that runs the case, after its introduction; and what levers compare with.

    Quiet, the cell prints nothing and its figure carries the numbers instead.
    """
    nav = f"{ex['deck']}/{pathlib.Path(ex['deck']).name}.nav"
    head_lines = (
        "# @title Run the case and see the results\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        "import matplotlib.pyplot as plt\n\n"
        "# The workshop's figure and the functions that fill it, shared with the\n"
        "# Examples pages: docs/workshop/_results.py.\n"
        'sys.path.insert(0, str(Path("docs/workshop").resolve()))\n'
        "from _results import compare, plot_cases, print_summary, run_case, scale, summarise\n"
        "from _solver import guard_interior_point\n\n"
        "guard_interior_point()\n\n")
    hidden = {"cellView": "form", "jupyter": {"source_hidden": True}, "tags": ["hide-input"]}
    cells = []
    decks = ex.get("decks")
    runs = ex.get("runs")
    if quiet and runs:
        # One deck solved several ways, each with its own tweak; levers move one of them.
        labels = list(runs)
        named = ", ".join(labels[:-1]) + " and " + labels[-1]
        table = "".join(f'    "{label}": {expr},\n' for label, expr in runs.items())
        ways = {2: "two", 3: "three", 4: "four"}.get(len(runs), str(len(runs)))
        cells.append(md(f"{heading}The cell below solves the deck from 2026 to 2050 "
                        f"{ways} ways, {named}, and draws their well-to-wake "
                        "emissions, their freight rate and the fuel they burn, side by side."))
        cells.append(code(
            head_lines + ex.get("run_setup", "")
            + f'NAV = Path("{nav}")\n'
            "RUNS = {\n" + table + "}\n"
            "cases = {label: summarise(run_case(NAV, tweak)) for label, tweak in RUNS.items()}\n"
            "plot_cases(cases, annotate=True)\n"
            "plt.show()\n\n"
            "# The levers below move this run:\n"
            f'REF_TWEAK, ref = RUNS["{ex["lever_deck"]}"], cases["{ex["lever_deck"]}"]\n',
            metadata=hidden))
        against = f"the {ex['lever_deck']} run"
    elif decks:
        # Several decks: run each, show them side by side, move levers on one.
        navs = ",\n".join(f'    "{label}": Path("{ex["deck"]}/{name}")' for label, name in decks)
        cells.append(md(f"{heading}The cell below solves each of the "
                        f"case's {len(decks)} decks from 2026 to 2050 and draws their "
                        "well-to-wake emissions, their freight rate and the fuel they "
                        "burn, side by side."))
        loop = ("for label, nav in NAVS.items():\n"
                "    cases[label] = summarise(run_case(nav))\n"
                "plot_cases(cases, annotate=True)\n") if quiet else (
                "for label, nav in NAVS.items():\n"
                '    print(f"--- {label}")\n'
                "    cases[label] = summarise(run_case(nav))\n"
                "    print_summary(cases[label])\n"
                "plot_cases(cases)\n")
        cells.append(code(
            head_lines
            + "NAVS = {\n" + navs + ",\n}\n"
            "cases = {}\n"
            + loop +
            "plt.show()\n\n"
            "# The levers below move this deck:\n"
            f'NAV, ref = NAVS["{ex["lever_deck"]}"], cases["{ex["lever_deck"]}"]\n',
            metadata=hidden))
        against = f"the {ex['lever_deck']} deck"
    else:
        cells.append(md(f"{heading}The cell below solves the case from "
                        "2026 to 2050 and draws its well-to-wake emissions, its freight "
                        "rate and the fuel it burns."))
        extra = ex.get("extra_figure", "") if quiet else ""
        cells.append(code(
            head_lines
            + f'NAV = Path("{nav}")\n'
            + ("REF_TWEAK = None\n"
               "_m = run_case(NAV)\n"
               "ref = summarise(_m)\n"
               'plot_cases({"reference": ref}, annotate=True)\n' if quiet else
               "%time ref = summarise(run_case(NAV))\n"
               "print_summary(ref)\n"
               'plot_cases({"reference": ref})\n')
            + "plt.show()\n"
            + (f"\n{extra}plt.show()\n" if extra else ""),
            metadata=hidden))
        against = "the reference"
    if quiet:
        # as in Session 1, the lever cell shows the levers only: the rest is here
        table = "".join(f'    "{n}": {fs!r},\n' for n, _, fs, _, _ in ex["sensitivities"])
        ref_label = ex.get("lever_deck", "reference")
        cells[-1].source = cells[-1].source.replace(
            "from _results import compare, plot_cases,",
            "from _results import compare_with_previous, plot_cases,"
            + (" plot_fleet_emissions," if ex.get("extra_figure") else ""))
        cells[-1].source += (
            "\n\n# ===========================================================================\n"
            "#  The machinery for the sensitivity analysis. Nothing to edit here: the\n"
            "#  levers are further down.\n"
            "# ===========================================================================\n"
            "# each lever, and the forecasts it multiplies\n"
            "LEVERS = {\n" + table + "}\n"
            "_RUNS = []      # the scenarios solved so far, newest last: (levers, summary)\n\n\n"
            "def run_your_scenario():\n"
            '    """Solve the levers set in the YOUR SCENARIO cell and compare with\n'
            f'    {against} and with the scenario solved before it."""\n'
            "    changed = [(n, globals()[n]) for n in LEVERS if globals()[n] != 1.0]\n"
            "    if not changed:\n"
            '        print("Every lever is still at 1.0, so this would just re-solve the deck.")\n'
            '        print("Change one of the numbers above and run this cell again.")\n'
            "        return\n"
            "    tweaks = ([REF_TWEAK] if REF_TWEAK else []) + [scale(f, v) for n, v in changed\n"
            "                                                   for f in LEVERS[n]]\n\n"
            "    def your_scenario(m):\n"
            "        for t in tweaks:\n"
            "            t(m)\n\n"
            '    label = ",  ".join(f"{n} x {v}" for n, v in changed)\n'
            f'    compare_with_previous(NAV, ref, your_scenario, label, _RUNS, ref_label="{ref_label}")\n'
            "    plt.show()\n")
    return cells, against


def sensitivity_cells(ex, heading, against):
    """The page form's lever cell, laid out as Session 1's YOUR SCENARIO cell."""
    sens = ex["sensitivities"]
    width = max(len(n) for n, *_ in sens)
    example = ex["sensitivity_example"]
    first = next(n for n, v, *_ in sens if v != 1.0)
    rows = "\n".join(f"{n:<{width}} = {v:<4}  #  {span:<15} {what}" for n, v, _, span, what in sens)
    intro = md(f"{heading}Each number multiplies what the deck already says, so 1.0 is "
               f"{against}. Set one, run the cell, and compare with {against} and with "
               f"the scenario you ran before. {example}.")
    return [intro, code(
        "# ===========================================================================\n"
        "#  YOUR SCENARIO.  Set a lever, then run this cell: it solves your scenario\n"
        f"#  and compares it with {against} and with the scenario you ran before it.\n"
        "#\n"
        "#  Every number is a MULTIPLIER on what the deck already says, so 1.0 is the\n"
        "#  deck. The right-hand column says what each 1.0 is worth, so you can judge\n"
        "#  whether a factor of two is a big change or a small one.\n"
        "#\n"
        f"#  {example}.\n"
        f"#  Set {first} back to 1.0 to start from the deck.\n"
        "#\n"
        f"#{'':{width + 11}}suggested span  what 1.0 means in the deck\n"
        f"{rows}\n"
        "# ===========================================================================\n\n"
        "run_your_scenario()\n")]


def lever_cells(ex, heading, against):
    width = max(len(n) for n, *_ in ex["levers"])
    lever_lines = "\n".join(f"{n:<{width}} = {v:<4}  # {what}" for n, v, _, what in ex["levers"])
    table = ",\n".join(f'          "{f}": {n}' for n, _, f, _ in ex["levers"])
    example = ex.get("lever_example", "As an example, the fuel oil price is doubled.")
    intro = md(f"{heading}Each number multiplies what the deck "
               "already says, so 1.0 is the reference. Set one, run the cell, and "
               f"compare with {against}. {example}")
    return [intro,
            code(
        "# ===========================================================================\n"
        "#  YOUR SCENARIO. Every number is a MULTIPLIER: 1.0 is the deck as it is.\n"
        "# ===========================================================================\n"
        f"{lever_lines}\n\n"
        "LEVERS = {\n" + table + "}\n"
        "TWEAKS = [scale(f, v) for f, v in LEVERS.items() if v != 1.0]\n\n\n"
        "def your_scenario(m):\n"
        "    for t in TWEAKS:\n"
        "        t(m)\n\n\n"
        "compare(NAV, ref, your_scenario)\n"
        "plt.show()\n")]


def build_explore(page):
    """docs/examples/<page>-explore.ipynb, the companion of a hand-written page."""
    ex = EXAMPLES[page]
    badge, setup, metadata = session_1_cells()

    cells = [badge_cell(badge, f"{page}-explore.ipynb"),
             md(f"# Explore: {ex['title']}\n\n{ex['question']}\n\n"
                f"The case, its deck and its results are described on its "
                f"[Examples page]({SITE}/{page}.html)."),
             map_cell(ex),
             md("## STEP 1: Setup\n\nRun the cell below on Colab or locally to "
                "set up Navigate and find the example deck."),
             setup_cell(ex, setup)]
    run, against = run_cells(ex, "## STEP 2: Run the case\n\n")
    cells += run
    cells += lever_cells(ex, "## STEP 3: Move one lever\n\n", against)
    cells.append(md(
        "## Go further\n\n"
        f"- Edit the deck itself in `{ex['deck']}/` on a [local installation]"
        "(https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation).\n"
        f"- See the other cases on the [Examples page]({SITE}/index.html)."))

    return nbformat.v4.new_notebook(cells=cells, metadata=dict(metadata))


# ------------------------------------------------------------------ page form
LINK = re.compile(r"\]\((?!https?:|#|data:)([^)\s]+)\)")
SLOT = re.compile(r"^\{\{ (.+?) \}\}$", re.M)


def absolute_links(text, base):
    """Point relative links at the site: they resolve there but not in Colab."""
    def to_url(match):
        path, _, anchor = match.group(1).partition("#")
        target = posixpath.normpath(posixpath.join(base, path))
        if target in NOT_ON_SITE:
            url = f"{GITHUB}/docs/{target}"
        else:
            url = f"{SITE_ROOT}/{posixpath.splitext(target)[0]}.html"
        return f"]({url}{'#' + anchor if anchor else ''})"
    return LINK.sub(to_url, text)


def details(summary, body):
    """A fold that both the site and Colab render; the blank lines keep its body Markdown."""
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def deck_cell(ex):
    """The deck as tabs, coloured as in VS Code, as Session 3 shows its deck."""
    tabs = "".join(f'    "{title}": {files!r},\n' for title, files in ex["deck_files"])
    return code(
        "# @title The deck, tab by tab\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, str(Path("docs/workshop").resolve()))\n'
        "from _deck import show_deck\n\n"
        "show_deck(EXAMPLE, {\n" + tabs + "})\n",
        metadata={"cellView": "form", "jupyter": {"source_hidden": True},
                  "tags": ["hide-input"]})


def bank_entry(key):
    text = BANK.read_text(encoding="utf-8")
    body = text.split(f"<!-- bank:{key} -->")[1].split(f"<!-- /bank:{key} -->")[0]
    # the entry's map is the one at the top of the page already
    body = "\n".join(line for line in body.splitlines() if not line.startswith("!["))
    return absolute_links(body.strip(), "workshop")


def build_page(page):
    """docs/examples/<page>.ipynb from _pages/<page>.md: the page and the Colab notebook."""
    ex = EXAMPLES[page]
    badge, setup, metadata = session_1_cells()
    run, against = run_cells(ex, "", quiet=True)
    removed ={"cellView": "form", "jupyter": {"source_hidden": True}, "tags": ["remove-cell"]}

    # SLOTS: what each {{ name }} line of the page source becomes
    def slot(name):
        if name == "badge":
            return [badge_cell(badge, f"{page}.ipynb")]
        if name == "map":
            return [map_cell(ex)]
        if name == "setup":
            cell = setup_cell(ex, setup)
            cell.metadata = dict(removed)
            return [cell]
        if name == "run":
            return run
        if name == "levers":
            return sensitivity_cells(ex, "### Move one lever\n\n", against)
        if name == "deck":
            return [deck_cell(ex)]
        if name.startswith("prompt "):
            key, _, title = name[len("prompt "):].partition(": ")
            return [md(details(title, bank_entry(key)))]
        raise ValueError(f"{page}.md: unknown slot {{{{ {name} }}}}")

    src = (PAGES / f"{page}.md").read_text(encoding="utf-8")
    src = re.sub(r"\A<!--.*?-->\s*", "", src, flags=re.S)
    cells = []
    for i, piece in enumerate(SLOT.split(src)):
        if i % 2:
            cells += slot(piece)
        elif piece.strip():
            cells.append(md(absolute_links(piece.strip(), "examples")))

    return nbformat.v4.new_notebook(cells=cells, metadata=dict(metadata))


def run_and_write(page):
    as_page = (PAGES / f"{page}.md").exists()
    nb = build_page(page) if as_page else build_explore(page)
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    NotebookClient(nb, kernel_name="navigate-zcs", timeout=1800,
                   resources={"metadata": {"path": str(OUT)}}).execute()
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python",
                                 "name": "python3"}
    for cell in nb.cells:
        cell.metadata.pop("execution", None)
    nbformat.validate(nb)
    body = nbformat.writes(nb)
    for bad in ("â€", "Ã", str(pathlib.Path.home()), "NicolasCampion"):
        assert bad not in body, f"{page}: output holds {bad!r}"
    dest = OUT / (f"{page}.ipynb" if as_page else f"{page}-explore.ipynb")
    dest.write_bytes((body + "\n").encode("utf-8"))
    print(f"wrote {dest}")


if __name__ == "__main__":
    for p in sys.argv[1:] or list(EXAMPLES):
        run_and_write(p)
