# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Write and run the explore notebooks of the Examples pages.

Run from the repository root:

    python docs/_figures/make_example_notebooks.py                # all three
    python docs/_figures/make_example_notebooks.py two-fleets     # one

Writes docs/examples/<page>-explore.ipynb, executed, for the examples whose deck
has no workshop session of its own (example_4 is Session 1's, the world fleet
Session 2's). The Colab badge and the Setup cell are taken from Session 1, so a
change there reaches these notebooks the next time this runs. The case map
travels as a base64 PNG in markdown, the only form every viewer shows (see
map_to_notebook.py).

Executes on the `navigate-zcs` kernel with PYTHONUTF8 set, then saves the
standard python3 kernelspec, as docs/workshop/AGENTS.md asks.
"""

import base64
import os
import pathlib
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_map_png  # noqa: E402

SESSION_1 = pathlib.Path("docs/workshop/01-run-a-simple-case.ipynb")
OUT = pathlib.Path("docs/examples")
SITE = "https://zerocarbonshipping.github.io/navigate-zcs/workshop-preview/examples"
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
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("COOKING_OIL_COST", 1.0, "used_cooking_oil_cost_europe",
                    "cost of the used cooking oil FAME is made from")],
    },
    "rhine": {
        "title": "Inland waterways in Germany",
        "question": "Does a national CO2 price move owners to drop-in fuels or new engines?",
        "deck": "simulations/examples/example_6",
        "decks": [("reference", "example_6_reference.nav"),
                  ("CO2 price", "example_6_co2_price.nav")],
        "lever_deck": "CO2 price",
        "map": ("png", "rhine_inland_map.png"),
        "alt": "Map of an inland trade on the Rhine in Germany from Duisburg upstream "
               "to Mannheim, calling at Cologne, Koblenz and Mainz, with European fuel "
               "production delivering to the two ends",
        "levers": [("OIL_PRICE", 2.0, "fossil_fuel_oil_price_global", "fuel oil price"),
                   ("CO2_PRICE", 1.0, "germany_co2_price",
                    "Germany's CO2 price, 65 to 150 USD/t (INVENTED)"),
                   ("HULL_PRICE", 1.0, "rhine_hull_capex",
                    "newbuild price of the hull, 6 M USD (INVENTED)")],
    },
    "caribbean": {
        "title": "Caribbean shipping under global and EU rules",
        "question": "How are a region's own ships affected by global and EU rules, "
                    "today and if extended to them?",
        "deck": "simulations/examples/example_5",
        "decks": [("no policy", "example_5_no_policy.nav"),
                  ("current rules", "example_5_current_rules.nav"),
                  ("extended", "example_5_extended.nav")],
        "lever_deck": "extended",
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


def build(page):
    ex = EXAMPLES[page]
    badge, setup, metadata = session_1_cells()
    nav = f"{ex['deck']}/{pathlib.Path(ex['deck']).name}.nav"

    cells = []
    md = nbformat.v4.new_markdown_cell
    code = nbformat.v4.new_code_cell

    cells.append(md(badge.source.replace(
        COLAB, COLAB.replace("docs/workshop/01-run-a-simple-case.ipynb",
                             f"docs/examples/{page}-explore.ipynb"))))
    cells.append(md(f"# Explore: {ex['title']}\n\n{ex['question']}\n\n"
                    f"The case, its deck and its results are described on its "
                    f"[Examples page]({SITE}/{page}.html)."))
    b64 = base64.b64encode(map_png(*ex["map"])).decode("ascii")
    cells.append(md(f"![{ex['alt']}](data:image/png;base64,{b64})"))

    cells.append(md("## STEP 1: Setup\n\nRun the cell below on Colab or locally to "
                    "set up Navigate and find the example deck."))
    head = setup.source.split("# Load the example deck.")[0].rstrip()
    cells.append(code(
        head + "\n\n\n# The example deck.\n"
        f'EXAMPLE = Path("{ex["deck"]}")\n'
        "assert EXAMPLE.is_dir(), (\n"
        '    f"{EXAMPLE} not found under {Path.cwd()}. On Colab the setup cell clones the "\n'
        '    f"{BRANCH!r} branch, so this deck has to be committed and pushed there."\n'
        ")\n", metadata=dict(setup.metadata)))
    cells[-1].metadata.pop("execution", None)

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
    decks = ex.get("decks")
    if decks:
        # Several decks: run each, show them side by side, move levers on one.
        navs = ",\n".join(f'    "{label}": Path("{ex["deck"]}/{name}")' for label, name in decks)
        cells.append(md("## STEP 2: Run the case\n\nThe cell below solves each of the "
                        f"case's {len(decks)} decks from 2026 to 2050 and draws their "
                        "well-to-wake emissions, their freight rate and the fuel they "
                        "burn, side by side."))
        cells.append(code(
            head_lines
            + "NAVS = {\n" + navs + ",\n}\n"
            "cases = {}\n"
            "for label, nav in NAVS.items():\n"
            '    print(f"--- {label}")\n'
            "    cases[label] = summarise(run_case(nav))\n"
            "    print_summary(cases[label])\n"
            "plot_cases(cases)\n"
            "plt.show()\n\n"
            "# The levers below move this deck:\n"
            f'NAV, ref = NAVS["{ex["lever_deck"]}"], cases["{ex["lever_deck"]}"]\n',
            metadata=hidden))
        against = f"the {ex['lever_deck']} deck"
    else:
        cells.append(md("## STEP 2: Run the case\n\nThe cell below solves the case from "
                        "2026 to 2050 and draws its well-to-wake emissions, its freight "
                        "rate and the fuel it burns."))
        cells.append(code(
            head_lines
            + f'NAV = Path("{nav}")\n'
            "%time ref = summarise(run_case(NAV))\n"
            "print_summary(ref)\n"
            'plot_cases({"reference": ref})\n'
            "plt.show()\n",
            metadata=hidden))
        against = "the reference"

    width = max(len(n) for n, *_ in ex["levers"])
    lever_lines = "\n".join(f"{n:<{width}} = {v:<4}  # {what}" for n, v, _, what in ex["levers"])
    table = ",\n".join(f'          "{f}": {n}' for n, _, f, _ in ex["levers"])
    cells.append(md("## STEP 3: Move one lever\n\nEach number multiplies what the deck "
                    "already says, so 1.0 is the reference. Set one, run the cell, and "
                    f"compare with {against}. As an example, the fuel oil price is "
                    "doubled."))
    cells.append(code(
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
        "plt.show()\n"))

    cells.append(md(
        "## Go further\n\n"
        f"- Edit the deck itself in `{ex['deck']}/` on a [local installation]"
        "(https://github.com/zerocarbonshipping/navigate-zcs/blob/dev-workshop/README.md#installation).\n"
        f"- See the other cases on the [Examples page]({SITE}/index.html)."))

    nb = nbformat.v4.new_notebook(cells=cells, metadata=dict(metadata))
    return nb


def run_and_write(page):
    nb = build(page)
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
    dest = OUT / f"{page}-explore.ipynb"
    dest.write_bytes((body + "\n").encode("utf-8"))
    print(f"wrote {dest}")


if __name__ == "__main__":
    for p in sys.argv[1:] or list(EXAMPLES):
        run_and_write(p)
