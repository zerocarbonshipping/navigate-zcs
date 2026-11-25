# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Write leadership_demo.ipynb from the cells below, without outputs.

Embeds images/hero.png and images/pipeline.png (make_images.py draws them) and
notebook 2's map. Run it, then execute the notebook to save one run's outputs
(README.md, Refreshing):

    python demo/leadership/build_notebook.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

HERE = Path(__file__).resolve().parent
NOTEBOOK_2 = HERE.parents[1] / "docs" / "notebooks" / "notebook_2" / "notebook_2.ipynb"
COLAB = (
    "https://colab.research.google.com/github/zerocarbonshipping/navigate-zcs/blob/leadership-demo/"
    "demo/leadership/leadership_demo.ipynb"
)
RUNS = "basecase_no_regulation,basecase_mid_regulation,basecase_strong_regulation"


def png(name: str) -> str:
    """Return the image as a data URI."""
    return (
        "data:image/png;base64,"
        + base64.b64encode((HERE / "images" / name).read_bytes()).decode()
    )


def notebook_2_map() -> str:
    """Return notebook 2's map, a data URI."""
    cells = json.loads(NOTEBOOK_2.read_text(encoding="utf-8"))["cells"]
    source = "".join(next(cell for cell in cells if cell.get("id") == "map")["source"])
    return source[source.index("(data:") + 1 : source.rindex(")")]


def markdown(cell_id: str, text: str) -> nbformat.NotebookNode:
    """Return a markdown cell of the text."""
    return new_markdown_cell(text.strip(), id=cell_id)


def code(cell_id: str, text: str) -> nbformat.NotebookNode:
    """Return a code cell of the text."""
    return new_code_cell(text.strip(), id=cell_id)


CELLS = [
    markdown(
        "hero",
        f"![Navigate, Horizon and Lantern: the Center's open-source modelling toolchain]({png('hero.png')})",
    ),
    markdown(
        "presenter",
        f"""
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({COLAB})

> **For the presenter.** Open the notebook in Colab and run the **Setup** cell about five minutes before the
> meeting. In the meeting, run the cells one by one (Shift+Enter) as you talk. The notebook opens with the results
> of an earlier run, so every chart is there before a cell runs.
>
> *Navigate is a research model. The three scenarios test it across degrees of regulation; they are not the
> Center's view of likely futures, and their results are illustrations, not forecasts or advice.*
""",
    ),
    markdown(
        "toolchain",
        f"""
## One toolchain, from a question to a range of answers

![A deck goes into Navigate, which writes a results file that Lantern draws; Horizon runs Navigate across a hundred futures]({png("pipeline.png")})

- **Navigate** simulates the fleet year by year: which ships owners build, retrofit and scrap, which fuels they
  burn, and which fuel plants producers build, each on what they expect prices and rules to bring.
- **Horizon** runs the same case across many futures at once, so every result comes with its range and its drivers.
- **Lantern** turns a run, or a whole study, into interactive plots in the browser.

All three, and the data library behind the case, are open source.
""",
    ),
    markdown(
        "setupmd",
        """
## Setup · run before the meeting

Installs the three tools in this Colab session and loads the case: about two minutes.
""",
    ),
    code(
        "setup",
        """
# @title Setup: install Navigate, Horizon and Lantern, and load the case { display-mode: "form" }
ROOT = "/content"
# ROOT = "/tmp/leadership_demo"  # running locally: any folder of your own, without spaces in its path

# the demo's branch holds its study and the results bundled with it; Horizon and Lantern are pinned to the
# commits the demo was made with, so a later change to either cannot break it
BRANCH = "leadership-demo"
HORIZON = "23f7df9dbaa17546d9336be062111cc836fa4cfb"
LANTERN = "28ffcb25ca9a98ec1c89c42de401150f1dac862a"

import os
import shutil
import subprocess
import sys
from pathlib import Path

repository = Path(ROOT, "navigate-zcs")
if not repository.exists():  # a second run reuses the clone
    subprocess.run(["git", "clone", "-q", "--depth", "1", "-b", BRANCH,
                    "https://github.com/zerocarbonshipping/navigate-zcs", str(repository)], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", str(repository),
                f"git+https://github.com/zerocarbonshipping/horizon-zcs@{HORIZON}",
                f"git+https://github.com/zerocarbonshipping/lantern-zcs@{LANTERN}"], check=True)

# the tools' commands next to this Python, and Navigate's data library from the clone
os.environ["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}"
os.environ["ASSUMPTIONS_DATA_DIR"] = str(repository / "assumptions")

# the case: notebook 2's world fleet, with the demo's study, plots and bundled results on top
case = Path(ROOT, "world_fleet")
shutil.rmtree(case, ignore_errors=True)
shutil.copytree(repository / "docs" / "notebooks" / "notebook_2" / "global_case", case)
shutil.copytree(repository / "demo" / "leadership" / "overlay", case, dirs_exist_ok=True)
shutil.copytree(repository / "demo" / "leadership" / "results", case / "bundled")
os.chdir(case)

# the demo's cards and charts
sys.path.insert(0, str(repository / "demo" / "leadership"))
import showcase

showcase.ready()
""",
    ),
    markdown(
        "question",
        f"""
---

## The question

### What will the world fleet burn to 2050, and how much does regulation change it?

![The reference scenario's geography: five fuel-supply regions shaded by their 2050 electricity cost, with Europe ringed as the EU ETS and FuelEU jurisdiction]({notebook_2_map()})

The case is the Center's reference scenario: the whole international fleet in 23 ship classes, and fuels made in
five supply regions, all from Navigate's open data library. Three scenarios differ only in regulation:

| Scenario | Regulation |
|---|---|
| **No regulation** | none: fuel chosen on cost alone |
| **Mid regulation** | EU ETS + FuelEU + a moderate global fuel standard |
| **Strong regulation** | EU ETS + FuelEU + a strict global fuel standard |
""",
    ),
    markdown(
        "navigatemd",
        """
---

## 1 · Navigate: simulate the world fleet to 2050

Each scenario is one deck and one command. Navigate steps through time, and at each step owners and fuel producers
decide what to build and burn. On a coarse grid of eight time steps a scenario solves in about a minute; mid
regulation solves live, the other two were solved before the meeting.
""",
    ),
    code(
        "solve",
        """
# @title Solve the scenarios { display-mode: "form" }
LIVE = "mid regulation"  # @param ["mid regulation", "all three", "none: bundled results"]
# "all three" solves them side by side, two to three minutes on Colab
showcase.solve(LIVE)
""",
    ),
    code(
        "scorecards",
        """
# @title What Navigate found { display-mode: "form" }
showcase.scorecards()
""",
    ),
    code(
        "fuelmix",
        """
# @title The fuel mix, 2026 to 2050 { display-mode: "form" }
showcase.fuel_mix()
""",
    ),
    markdown(
        "lanternplotsmd",
        """
The same results as Lantern draws them, straight from the results files: hover to read a value, drag to zoom.
""",
    ),
    code(
        "lanternplots",
        f"""
# Lantern draws plots of the results files as web pages; the notebook shows two of them
runs = "{RUNS}"
!lantern parquets --scale 0.8 --plot "headline_emissions[{{runs}}]" --plot "headline_expenses_total[{{runs}}]"

pages = runs.replace(",", "+")
showcase.show(f"plots/headline_emissions/{{pages}}.html", f"plots/headline_expenses_total/{{pages}}.html",
              titles=("Well-to-wake emissions", "What the ships paid, per tonne-km"))
""",
    ),
    markdown(
        "horizonmd",
        """
---

## 2 · Horizon: one future is a guess, so run a hundred

A single run answers *what if* for one set of assumptions. Horizon takes the mid regulation scenario, draws each of
eight assumptions from a range, and runs Navigate once per draw: a hundred futures, solved in parallel. The study is
one short file, `demo.hor`.
""",
    ),
    code(
        "levers",
        """
# @title The assumptions Horizon varies { display-mode: "form" }
showcase.levers()
""",
    ),
    code(
        "futures",
        """
# check the study, then list the futures it draws without running them
!horizon check demo.hor
showcase.futures()
""",
    ),
    markdown(
        "studymd",
        """
A hundred runs take about half an hour on a workstation, so they ran before the meeting. Tick `RUN_STUDY_LIVE` to
run a study of six futures here instead, in about three minutes.
""",
    ),
    code(
        "study",
        """
# @title Load the study { display-mode: "form" }
RUN_STUDY_LIVE = False  # @param {type:"boolean"}
if RUN_STUDY_LIVE:
    !horizon run demo.hor --samples 6
    !horizon collect demo.hor
else:
    showcase.use_bundled_study()
""",
    ),
    markdown(
        "fanmd",
        """
Lantern draws a study as a band: in each year the middle 90 % of the futures, their median dashed, and the one run
closest to it solid, here beside the three scenarios.
""",
    ),
    code(
        "fan",
        """
!lantern parquets study/demo.parquet --scale 0.8 --plot "headline_emissions[{runs},demo/demo]" --plot "headline_expenses_total[{runs},demo/demo]"

pages = runs.replace(",", "+") + "+demo"
showcase.show(f"plots/headline_emissions/{pages}.html", f"plots/headline_expenses_total/{pages}.html",
              titles=("Well-to-wake emissions", "What the ships paid, per tonne-km"))
""",
    ),
    code(
        "cloud",
        """
# @title Every future, emissions against cost { display-mode: "form" }
showcase.futures_cloud()
""",
    ),
    code(
        "drivers",
        """
# @title What moves the result { display-mode: "form" }
showcase.drivers()
""",
    ),
    markdown(
        "lanternmd",
        """
---

## 3 · Lantern: every plot, in the browser

Lantern's viewer holds every plot it can draw of the three scenarios and the hundred futures: fuels, fleets, ports,
fuel plants and regulation. It opens in a new tab.
""",
    ),
    code(
        "open",
        """
# @title Open Lantern { display-mode: "form" }
showcase.open_lantern("parquets", "study/demo.parquet")
""",
    ),
    markdown(
        "close",
        """
---

## What this gives us

- **Fast answers.** A new question is a new deck or a new lever; the world fleet solves in about a minute on the
  coarse grid.
- **Ranges, not single numbers.** Horizon puts a band on every result and shows which assumptions move it.
- **Open and reproducible.** The model, its data library and the tools are open source, and this notebook runs in
  any browser.

[Navigate](https://github.com/zerocarbonshipping/navigate-zcs) ·
[Horizon](https://github.com/zerocarbonshipping/horizon-zcs) ·
[Lantern](https://github.com/zerocarbonshipping/lantern-zcs) ·
[Documentation](https://zerocarbonshipping.github.io/navigate-zcs/)
""",
    ),
]


if __name__ == "__main__":
    notebook = new_notebook(
        cells=CELLS,
        metadata={
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
    )
    nbformat.validate(notebook)
    nbformat.write(notebook, HERE / "leadership_demo.ipynb")
    print(f"wrote leadership_demo.ipynb, {len(CELLS)} cells")
