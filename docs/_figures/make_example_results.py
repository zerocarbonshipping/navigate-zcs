# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Solve each example deck once and save its results figure for the Examples pages.

Run from the repository root:

    python docs/_figures/make_example_results.py              # every example
    python docs/_figures/make_example_results.py two-fleets   # one of them

Writes docs/examples/figures/<page>.png and prints the headline numbers. A page
listed in NAVIGATE_CHARTS also gets Navigate's own chart redrawn in the workshop
palette, from the plot_data.pkl of a run made beforehand with
`python -m navigate <deck>.nav -d ./assumptions`.
"""

import base64
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib
import nbformat

matplotlib.use("Agg")

sys.path.insert(0, str(Path("docs/workshop").resolve()))

from _results import plot_cases, print_summary, run_case, summarise  # noqa: E402
from _solver import guard_interior_point  # noqa: E402
from _style import navigate_charts  # noqa: E402

DECKS = {"trade-route": "simulations/examples/example_4/example_4.nav",
         "two-fleets": "simulations/examples/example_3/example_3.nav",
         "mainline-and-feeders": "simulations/examples/example_1/example_1.nav",
         "south-pacific": "simulations/examples/example_2/example_2.nav"}

# page: (plot folder of the run, chart) - the figure that shows what the case compares
NAVIGATE_CHARTS = {"two-fleets": ("plots_analysis", "fleet_emission_absolute.png")}

# page: (notebook, first line of the cell) - a figure taken from a notebook's saved
# output, for decks too slow to solve here (the global scenarios take about 25
# minutes each) or cases of several decks, which their explore notebook already
# runs side by side (make_example_notebooks.py)
RUN = "# @title Run the case and see the results"
SESSION_FIGURES = {"world-fleet": ("docs/workshop/02-run-a-global-case.ipynb",
                                   "# @title Figure: compare the three scenarios"),
                   "caribbean": ("docs/examples/caribbean-explore.ipynb", RUN),
                   "rhine": ("docs/examples/rhine-explore.ipynb", RUN)}

OUT = Path("docs/examples/figures")


def session_figure(notebook, first_line):
    """The PNG saved in the output of the notebook cell starting with `first_line`."""
    nb = nbformat.read(notebook, as_version=4)
    cell = next(c for c in nb.cells
                if c.cell_type == "code" and c.source.startswith(first_line))
    png = next(o.data["image/png"] for o in cell.outputs if "image/png" in o.get("data", {}))
    return base64.b64decode(png)


def main(pages):
    guard_interior_point()
    OUT.mkdir(parents=True, exist_ok=True)
    for page in pages:
        if page in SESSION_FIGURES:
            (OUT / f"{page}.png").write_bytes(session_figure(*SESSION_FIGURES[page]))
            print(page, "taken from", SESSION_FIGURES[page][0])
            continue
        s = summarise(run_case(DECKS[page]))
        print(page)
        print_summary(s)
        fig = plot_cases({"reference": s})
        fig.savefig(OUT / f"{page}.png", dpi=110)
        if page in NAVIGATE_CHARTS:
            folder, chart = NAVIGATE_CHARTS[page]
            with tempfile.TemporaryDirectory() as tmp:
                navigate_charts(str(Path(DECKS[page]).parent), tmp, folder)
                shutil.copy(Path(tmp) / chart, OUT / f"{page}-{Path(chart).stem}.png")


if __name__ == "__main__":
    main(sys.argv[1:] or [*DECKS, *SESSION_FIGURES])
