# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
"""Draw the gfs limit of the mid-regulation scenario against a delayed start.

Run from the repository root:  python docs/_figures/make_gfs_delay_chart.py

Writes docs/_figures/gfs_delay_chart.png, the figure of Session 5's global-study
prompt "The cost of waiting". It is the gfs_target_reduction chart of Session 3,
with the delayed pathway the prompt describes drawn over it: every date before
2050 moved DELAY years later, the 2050 target kept. The reference values are read
from simulations/scenarios/0_includes/mid_regulation.inc, so the chart follows
the scenario if the Center revises it; only DELAY is written here.
"""
import pathlib
import re
import sys
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "docs" / "workshop"))
from _style import AXIS, GRID, INK, SUBINK, TICK, scen_colour  # noqa: E402

INC = ROOT / "simulations" / "scenarios" / "0_includes" / "mid_regulation.inc"
OUT = pathlib.Path(__file__).resolve().parent / "gfs_delay_chart.png"

DELAY = 5     # years, the example in the prompt


def read_forecast(text, name):
    """The Table rows and Multiplier of one Forecast node in an .inc file."""
    block = re.search(r'Forecast\s+"%s"\s*\{(.*?)\n\}' % re.escape(name), text, re.S)
    if not block:
        sys.exit(f"no Forecast {name!r} in {INC}")
    rows = re.findall(r'"(\d\d-\d\d-\d{4})"\s+([\d.]+)', block.group(1))
    multiplier = re.search(r"Multiplier\s*=\s*([\d.]+)", block.group(1))
    return ([datetime.strptime(d, "%d-%m-%Y") for d, _ in rows],
            [float(v) for _, v in rows],
            float(multiplier.group(1)) if multiplier else 1.0)


def delayed(dates):
    """Every date before 2050 moved DELAY years later; the 2050 rows stay."""
    return [d if d.year >= 2050 else d.replace(year=d.year + DELAY) for d in dates]


def penalty_start(dates, values):
    return next(d for d, v in zip(dates, values) if v > 0)


text = INC.read_text(encoding="utf-8")
dates, fractions, multiplier = read_forecast(text, "gfs_target_reduction")
p_dates, p_values, _ = read_forecast(text, "gfs_remedial_unit")
cases = {"reference": (dates, penalty_start(p_dates, p_values)),
         "delayed start": (delayed(dates), penalty_start(delayed(p_dates), p_values))}

fig, ax = plt.subplots(figsize=(8, 3.5))
colours = {"reference": scen_colour("reference"),
           "delayed start": scen_colour("your scenario")}
for label, (when, penalty_from) in cases.items():
    absolute = [v * multiplier for v in fractions]
    if when[0] > dates[0]:
        # flat before its first row (Extrapolate = FLAT), so draw it from the start
        when, absolute = [dates[0], *when], [absolute[0], *absolute]
    ax.plot(when, absolute, marker="o", ms=4, lw=2, label=label, color=colours[label])
    ax.axvline(penalty_from, color=colours[label], lw=1, ls=":")
    ax.annotate(f"penalty from {penalty_from.year}", (penalty_from, 8), xytext=(4, 0),
                textcoords="offset points", fontsize=7.5, color=colours[label],
                rotation=90, va="bottom")
ax.annotate(f"{fractions[-1] * multiplier:.1f} in 2050 for both", (dates[-1], fractions[-1] * multiplier),
            xytext=(-8, -16), textcoords="offset points", ha="right", fontsize=8, color=SUBINK)
ax.set_title("gfs_target_reduction: the WTW intensity limit every vessel is held to",
             fontsize=10, color=INK, loc="left")
ax.set_ylabel("gCO2eq/MJ", fontsize=8, color=SUBINK)
ax.set_ylim(bottom=0)
ax.legend(fontsize=8, frameon=False, labelcolor=SUBINK, loc="upper right")
ax.grid(color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.tick_params(colors=TICK, labelsize=8)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(AXIS)
fig.tight_layout()
fig.savefig(OUT, dpi=200)
print(f"wrote {OUT}")
