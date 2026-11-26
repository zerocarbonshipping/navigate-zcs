# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The leadership demo's helpers.

They solve the scenarios, read the results files and draw the cards and charts the notebook shows, in the Center's palette.

The notebook runs in the case folder, a copy of notebook 2's global case with
overlay/ on top and results/ as bundled/; every path here is relative to it.
"""

from __future__ import annotations

import contextlib
import html
import io
import json
import os
import shutil
import subprocess
import threading
import time
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path
from statistics import median

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import polars as pl
from IPython.display import HTML, display

# ---- the case ----

SCENARIOS = {
    "basecase_no_regulation": "No regulation",
    "basecase_mid_regulation": "Mid regulation",
    "basecase_strong_regulation": "Strong regulation",
}
REGULATION = {
    "basecase_no_regulation": "Fuel chosen on cost alone",
    "basecase_mid_regulation": "EU ETS, FuelEU and a moderate global fuel standard",
    "basecase_strong_regulation": "EU ETS, FuelEU and a strict global fuel standard",
}
# the regulations of the case, by their node names in the decks
RULES = {"eu_ets": "EU ETS", "fuel_eu": "FuelEU", "gfs": "Global fuel standard"}
COARSE_YEARS = (2026, 2027, 2030, 2034, 2038, 2042, 2046, 2050)
STUDY = "demo"

# the levers of the study
LEVERS = {
    "OIL_PRICE": "Fuel oil price",
    "LNG_PRICE": "LNG price",
    "EFUEL_ELECTRICITY_PRICE": "Electricity for e-fuels",
    "BIOMASS_SHARE_FOR_SHIPPING": "Biomass for shipping",
    "TRADE_GROWTH": "Trade growth",
    "EU_ETS_PRICE": "EU ETS price",
    "GLOBAL_STANDARD_TARGET": "Global standard target",
    "GLOBAL_STANDARD_PENALTY": "Global standard penalty",
}

# fuels by family, in stacking order; LNG and the rest of fossil origin are not alternative fuels
FUEL_FAMILIES = {
    "Fuel oil": ("fossil_fuel_oil", "heavy_fuel_oil", "marine_gas_oil"),
    "LNG and LPG": ("liquefied_natural_gas", "liquefied_petroleum_gas"),
    "Blue ammonia": ("ammonia_blue",),
    "Biofuels": (
        "methanol_bio",
        "methane_bio",
        "ethanol_bio",
        "oil_bio",
        "fatty_acid_methyl_ester",
    ),
    "E-fuels": (
        "methane_electro",
        "methanol_electro",
        "diesel_electro",
        "ammonia_electro",
    ),
}
FOSSIL_FAMILIES = ("Fuel oil", "LNG and LPG")

# ---- the Center's palette (Lantern's theme.yaml) and type ----

INK, BODY, MUTED, RULE, WASH = "#323232", "#585858", "#8c8c8c", "#dcdcdc", "#f2f2f2"
SCENARIO_COLORS = {
    "basecase_no_regulation": "#e8c17b",  # yellow_5
    "basecase_mid_regulation": "#68a4c2",  # blue_5
    "basecase_strong_regulation": "#457b7b",  # green_5
}
FAMILY_COLORS = {
    "Fuel oil": "#585858",  # black_5
    "LNG and LPG": "#bebebe",  # black_2
    "Blue ammonia": "#97c8e4",  # blue_4
    "Biofuels": "#c28080",  # peach_5
    "E-fuels": "#457b7b",  # green_5
}
RULE_COLORS = {
    "eu_ets": "#e2af7c",  # orange_3
    "fuel_eu": "#938ea4",  # purple_5
    "gfs": "#3d5f87",  # blue_7
}
RAISES, LOWERS = "#c28080", "#457b7b"  # peach_5, green_5
HORIZON_TINT, NAVIGATE_TINT, LANTERN_TINT = "#fceec8", "#d4eefa", "#dcf0d6"  # level 2

FONT = "'Aktiv Grotesk', 'Calibri Light', Calibri, Inter, system-ui, sans-serif"
STYLE = f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;600&display=swap" rel="stylesheet">
<style>
  .zcs {{ font-family: {FONT}; font-weight: 300; color: {INK}; background: #fff; padding: 22px 24px;
          border-radius: 16px; line-height: 1.4; }}
  .zcs b {{ font-weight: 600; }}
  .zcs .eyebrow {{ font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: {MUTED}; }}
  .zcs .title {{ font-size: 26px; font-weight: 200; margin: 2px 0 16px; }}
  .zcs .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }}
  .zcs .card {{ border: 1px solid {RULE}; border-radius: 14px; padding: 16px 18px; background: #fff; }}
  .zcs .muted {{ color: {MUTED}; font-size: 13px; }}
  .zcs .body {{ color: {BODY}; font-size: 14px; }}
  .zcs .big {{ font-size: 42px; font-weight: 200; line-height: 1.05; letter-spacing: -.01em; }}
  .zcs .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; }}
  .zcs code {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; color: {BODY};
               background: {WASH}; padding: 2px 7px; border-radius: 6px; }}
  @keyframes zcs-pulse {{ 0%, 100% {{ opacity: .35; }} 50% {{ opacity: 1; }} }}
</style>
"""


def show_html(body: str) -> None:
    """Show HTML in the Center's style."""
    display(HTML(STYLE + f'<div class="zcs">{body}</div>'))


# an animated figure plays once it is mostly on screen, so the audience sees it from its first frame
PLAY_ON_SIGHT = """
const plot = document.getElementById("{plot_id}");
const play = () => Plotly.animate(plot, null, {frame: {duration: 900, redraw: true}, mode: "immediate",
                                               transition: {duration: 700, easing: "cubic-in-out"}});
if ("IntersectionObserver" in window) {
  const watcher = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) { watcher.disconnect(); setTimeout(play, 500); }
  }, {threshold: 0.6});
  watcher.observe(plot);
} else {
  setTimeout(play, 500);
}
"""


def show_figure(figure: go.Figure, animated: bool = False) -> None:
    """Show a Plotly figure in the Center's style; an animated one plays on sight."""
    figure.update_layout(
        font={"family": FONT, "color": INK, "size": 14, "weight": 300},
        paper_bgcolor="#fff",
        plot_bgcolor="#fff",
        hoverlabel={"font": {"family": FONT}},
    )
    page = figure.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        auto_play=False,
        post_script=PLAY_ON_SIGHT if animated else None,
        config={"displaylogo": False, "responsive": True},
    )
    display(
        HTML(
            f'<div style="background:#fff; border-radius:16px; padding:8px">{page}</div>'
        )
    )


def show(*pages: str, titles: tuple[str, ...] = (), height: int = 380) -> None:
    """Show Lantern's pages side by side, each in a frame, as notebooks 1 and 2 do."""
    frames = ""
    for page, title in zip(pages, titles or ("",) * len(pages), strict=True):
        source = Path(page).read_text(encoding="utf-8")
        frames += (
            f'<div style="flex: 1 1 360px; padding: 14px 6px 0">'
            f'<div class="eyebrow" style="padding-left:18px">{title}</div>'
            f'<iframe srcdoc="{html.escape(source)}" '
            f'style="width: 100%; height: {height}px; border: 0"></iframe></div>'
        )
    display(
        HTML(
            STYLE
            + '<div class="zcs" style="display: flex; flex-wrap: wrap; padding: 0">'
            f"{frames}</div>"
        )
    )


# ---- setup ----


def ready() -> None:
    """Show that the three tools are installed, with their versions."""
    tools = [
        ("Navigate", "navigate-zcs", NAVIGATE_TINT),
        ("Horizon", "horizon-zcs", HORIZON_TINT),
        ("Lantern", "lantern-zcs", LANTERN_TINT),
    ]
    chips = "".join(
        f'<div class="card" style="background:{tint}; border-color:{tint}">'
        f'<div class="eyebrow">{name}</div><div style="font-size:22px; font-weight:200">{version(package)}</div></div>'
        for name, package, tint in tools
    )
    show_html(
        f'<div class="eyebrow">Setup</div><div class="title">✓ Ready: the world fleet case is loaded</div>'
        f'<div class="grid">{chips}</div>'
    )


# ---- 1. Navigate ----


def solve(live: str) -> None:
    """
    Solve the reference scenarios live on the coarse grid, or take them from bundled/.

    live is "mid regulation", "all three" or "none: bundled results". A live run
    that fails falls back to its bundled result, so the demo goes on.
    """
    chosen = {
        "mid regulation": ["basecase_mid_regulation"],
        "all three": list(SCENARIOS),
    }.get(live, [])
    Path("parquets").mkdir(exist_ok=True)
    runs = {
        scenario: {"steps": 0, "state": "bundled", "seconds": 0.0}
        for scenario in SCENARIOS
    }
    # unbuffered, Navigate's progress lines arrive as it prints them
    environment = os.environ | {"PYTHONUNBUFFERED": "1"}
    processes = {}
    started = time.monotonic()
    for scenario in SCENARIOS:
        if scenario in chosen:
            command = ["navigate", f"{scenario}.nav", "--set", "GRID=coarse"]
            processes[scenario] = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=environment,
            )
            runs[scenario]["state"] = "solving"
            threading.Thread(
                target=_follow, args=(processes[scenario], runs[scenario]), daemon=True
            ).start()
        else:
            shutil.copy(Path("bundled", "parquets", f"{scenario}.parquet"), "parquets")

    board = display(HTML(STYLE + _progress(runs)), display_id=True)
    while any(process.poll() is None for process in processes.values()):
        for scenario, process in processes.items():
            if process.poll() is None:
                runs[scenario]["seconds"] = time.monotonic() - started
        board.update(HTML(STYLE + _progress(runs)))
        time.sleep(0.5)
    for scenario, process in processes.items():
        if process.returncode == 0:
            runs[scenario]["state"] = "solved"
        else:
            shutil.copy(Path("bundled", "parquets", f"{scenario}.parquet"), "parquets")
            runs[scenario]["state"] = "failed"
    board.update(HTML(STYLE + _progress(runs)))


def _follow(process: subprocess.Popen[str], run: dict) -> None:
    # Navigate prints "Date: 2034-01-01" as it starts each time step
    assert process.stdout is not None
    for line in process.stdout:
        if line.startswith("Date:"):
            run["steps"] += 1


def _progress(runs: dict) -> str:
    rows = ""
    for scenario, run in runs.items():
        color = SCENARIO_COLORS[scenario]
        cells = ""
        for step, year in enumerate(COARSE_YEARS):
            done = (
                run["state"] in ("solved", "bundled", "failed")
                or step < run["steps"] - 1
            )
            current = run["state"] == "solving" and step == run["steps"] - 1
            fill = color if done or current else WASH
            if run["state"] in ("bundled", "failed"):
                fill = f"{color}66"  # a bundled result, lighter than a live solve
            pulse = "animation: zcs-pulse 1s ease-in-out infinite;" if current else ""
            cells += (
                f'<div style="flex:1; text-align:center"><div style="height:10px; border-radius:5px; '
                f'background:{fill}; {pulse}"></div><div class="muted" style="font-size:11px; '
                f'margin-top:4px">{year}</div></div>'
            )
        status = {
            "solving": f"solving · {run['seconds']:.0f} s",
            "solved": f"✓ solved live in {run['seconds']:.0f} s",
            "bundled": "bundled result",
            "failed": "live run failed · bundled result",
        }[run["state"]]
        # a live run shows the command it runs, on a line of its own under its row
        live = run["state"] != "bundled"
        how = "solved live" if live else "solved before the meeting"
        command = (
            f'<div style="grid-column: 1 / -1; margin-top:-4px"><code>'
            f"$ navigate {scenario}.nav --set GRID=coarse</code></div>"
            if live
            else ""
        )
        rows += (
            f'<div style="display:grid; grid-template-columns: 210px 1fr 180px; gap:10px 18px; '
            f'align-items:center; padding:12px 0; border-top:1px solid {RULE}">'
            f'<div><span class="dot" style="background:{color}"></span>{SCENARIOS[scenario]}'
            f'<div class="muted" style="margin-top:2px">{how}</div></div>'
            f'<div style="display:flex; gap:6px">{cells}</div><div class="body" style="text-align:right">'
            f"{status}</div>{command}</div>"
        )
    return (
        f'<div class="zcs"><div class="eyebrow">Navigate</div><div class="title">The world fleet, '
        f"2026 to 2050: 23 ship classes, five fuel-supply regions, eight time steps</div>{rows}</div>"
    )


def _read(scenario: str) -> pl.DataFrame:
    return pl.read_parquet(Path("parquets", f"{scenario}.parquet")).with_columns(
        year=pl.col("date").dt.year()
    )


def _emissions(results: pl.DataFrame) -> pl.DataFrame:
    """Return the well-to-wake emissions of the world fleet by year, in Mt CO2e per year."""
    return (
        results.filter(kind="global", attribute="total_equivalent_wtw")
        .select("year", megatonnes=pl.col("value") / 1e6)
        .sort("year")
    )


def _cost(results: pl.DataFrame) -> pl.DataFrame:
    """Return what the fleets paid per transport work by year, in USD per 1,000 tonne-km (1,000 / 1.852 t-nm)."""
    return (
        results.filter(
            pl.col("kind") == "fleet",
            pl.col("attribute").is_in(["expenses", "cargo_miles"]),
        )
        .group_by("year")
        .agg(
            (
                pl.col("value").filter(attribute="expenses").sum()
                / pl.col("value").filter(attribute="cargo_miles").sum()
                * 1000
                / 1.852
            ).alias("usd")
        )
        .sort("year")
    )


def _fuel_mix(results: pl.DataFrame) -> pl.DataFrame:
    """Return each fuel family's share of the energy the fleet consumed, by year, in percent."""
    family = pl.lit("Other")
    for name, fuels in reversed(FUEL_FAMILIES.items()):
        family = (
            pl.when(pl.col("key1").is_in(fuels)).then(pl.lit(name)).otherwise(family)
        )
    energy = (
        results.filter(kind="global", attribute="consumed_energy")
        .group_by("year", family.alias("family"))
        .agg(pl.col("value").sum())
    )
    return energy.with_columns(
        share=pl.col("value") / pl.col("value").sum().over("year") * 100
    )


def _sparkline(values: list[float], color: str) -> str:
    low, high = min(values), max(values)
    points = " ".join(
        f"{i * 200 / (len(values) - 1):.1f},{44 - (v - low) / (high - low or 1) * 40:.1f}"
        for i, v in enumerate(values)
    )
    return (
        f'<svg viewBox="0 0 200 48" width="100%" height="48" preserveAspectRatio="none">'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>'
    )


def _signed(percent: float) -> str:
    return f"{percent:+.0f} %".replace("-", "\u2212")


def scorecards() -> None:
    """Show a card per scenario: emissions, alternative fuels and cost, 2026 against 2050."""
    cards = ""
    for scenario, name in SCENARIOS.items():
        results = _read(scenario)
        emissions, cost = _emissions(results), _cost(results)
        mix = _fuel_mix(results).filter(year=2050)
        alternative = mix.filter(~pl.col("family").is_in(FOSSIL_FAMILIES))[
            "share"
        ].sum()
        first, last = emissions["megatonnes"][0], emissions["megatonnes"][-1]
        cost_first, cost_last = cost["usd"][0], cost["usd"][-1]
        color = SCENARIO_COLORS[scenario]
        cards += f"""
        <div class="card" style="border-top: 4px solid {color}">
          <div style="font-size:20px; font-weight:300">{name}</div>
          <div class="muted" style="min-height:36px">{REGULATION[scenario]}</div>
          <div class="eyebrow" style="margin-top:14px">Emissions, 2026 → 2050</div>
          <div class="big" data-count="{(last / first - 1) * 100:.0f}" data-signed="1">{_signed((last / first - 1) * 100)}</div>
          <div class="body">{first / 1000:.2f} → {last / 1000:.2f} Gt CO₂e a year, well to wake</div>
          {_sparkline(emissions["megatonnes"].to_list(), color)}
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px">
            <div><div class="eyebrow">Alternative fuels 2050</div>
              <div style="font-size:30px; font-weight:200" data-count="{alternative:.0f}">{alternative:.0f} %</div>
              <div class="muted">of the energy burnt</div></div>
            <div><div class="eyebrow">Cost of transport</div>
              <div style="font-size:30px; font-weight:200" data-count="{(cost_last / cost_first - 1) * 100:.0f}" data-signed="1">{_signed((cost_last / cost_first - 1) * 100)}</div>
              <div class="muted">{cost_first:.1f} → {cost_last:.1f} USD per 1,000 t-km</div></div>
          </div>
        </div>"""
    show_html(
        f'<div class="eyebrow">What Navigate found</div><div class="title">Regulation decides where '
        f'the fleet lands in 2050</div><div class="grid">{cards}</div>{COUNT_UP}'
    )


# the cards' numbers count up from zero as they appear; without scripts they show as written
COUNT_UP = """<script>
document.querySelectorAll("[data-count]").forEach(element => {
  const target = parseFloat(element.dataset.count), start = performance.now();
  const sign = element.dataset.signed && target > 0 ? "+" : "";
  const step = now => {
    const progress = Math.min((now - start) / 1400, 1), eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = (sign + Math.round(target * eased) + " %").replace("-", "\u2212");
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
});
</script>"""


def fuel_mix() -> None:
    """Show the fuel mix of each scenario, morphing year by year from 2026 to 2050."""
    mixes = pl.concat(
        [
            _fuel_mix(_read(scenario)).with_columns(scenario=pl.lit(name))
            for scenario, name in SCENARIOS.items()
        ]
    )
    names = list(reversed(SCENARIOS.values()))  # no regulation on top
    years = sorted(mixes["year"].unique())

    def bars(year: int) -> list[go.Bar]:
        shares = mixes.filter(year=year)
        traces = []
        for family, color in FAMILY_COLORS.items():
            by_scenario = dict(
                shares.filter(family=family).select("scenario", "share").iter_rows()
            )
            values = [by_scenario.get(name, 0.0) for name in names]
            traces.append(
                go.Bar(
                    y=names,
                    x=values,
                    name=family,
                    orientation="h",
                    marker={"color": color, "line": {"width": 0}},
                    text=[f"{v:.0f}%" if v >= 6 else "" for v in values],
                    textposition="inside",
                    insidetextfont={
                        "color": "#fff"
                        if family in ("Fuel oil", "E-fuels", "Biofuels")
                        else INK
                    },
                    hovertemplate="%{y}<br>" + family + ": %{x:.1f} %<extra></extra>",
                )
            )
        return traces

    def year_mark(year: int) -> list[dict]:
        return [
            {
                "text": str(year),
                "x": 1,
                "y": 1.02,
                "xref": "paper",
                "yref": "paper",
                "xanchor": "right",
                "yanchor": "bottom",
                "showarrow": False,
                "font": {"size": 54, "color": "#bebebe", "weight": 200},
            }
        ]

    figure = go.Figure(
        data=bars(years[0]),
        frames=[
            go.Frame(
                data=bars(year), name=str(year), layout={"annotations": year_mark(year)}
            )
            for year in years
        ],
    )
    steps = [
        {
            "label": str(year),
            "method": "animate",
            "args": [
                [str(year)],
                {
                    "mode": "immediate",
                    "frame": {"duration": 900, "redraw": True},
                    "transition": {"duration": 700, "easing": "cubic-in-out"},
                },
            ],
        }
        for year in years
    ]
    figure.update_layout(
        title={
            "text": "Fuel mix of the world fleet, share of the energy burnt",
            "font": {"size": 20, "weight": 200},
        },
        barmode="stack",
        height=470,
        margin={"l": 150, "r": 30, "t": 130, "b": 110},
        bargap=0.35,
        xaxis={
            "range": [0, 100],
            "ticksuffix": " %",
            "gridcolor": WASH,
            "zeroline": False,
        },
        yaxis={"ticksuffix": "   "},
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.04,
            "xanchor": "left",
            "yanchor": "bottom",
            "traceorder": "normal",
            "font": {"size": 13},
        },
        annotations=year_mark(years[0]),
        sliders=[
            {
                "steps": steps,
                "x": 0.1,
                "len": 0.9,
                "y": -0.12,
                "yanchor": "top",
                "currentvalue": {"visible": False},
                "tickcolor": MUTED,
                "font": {"color": MUTED, "size": 12},
                "bordercolor": RULE,
                "bgcolor": WASH,
                "pad": {"t": 0},
            }
        ],
        updatemenus=[
            {
                "type": "buttons",
                "showactive": False,
                "x": 0,
                "y": -0.12,
                "xanchor": "left",
                "yanchor": "top",
                "pad": {"t": 0, "r": 10},
                "bgcolor": "#fff",
                "bordercolor": RULE,
                "buttons": [
                    {
                        "label": "▶ Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 900, "redraw": True},
                                "fromcurrent": False,
                                "transition": {
                                    "duration": 700,
                                    "easing": "cubic-in-out",
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    )
    show_figure(figure, animated=True)


def _collected(results: pl.DataFrame) -> pl.DataFrame:
    """Return what each regulation collected from the fleet by year, in billions of USD a year."""
    # remedial units are paid to the regulator; flexibility units only change hands between ships
    return results.filter(kind="regulation", attribute="remedial_expenses").select(
        "year", rule="node", billions=pl.col("value") / 1e9
    )


def collected() -> None:
    """Show what the regulations collect from the fleet each year, in the two regulated scenarios."""
    regulated = {
        scenario: _collected(_read(scenario))
        for scenario in SCENARIOS
        if scenario != "basecase_no_regulation"
    }
    cards = ""
    for scenario, frame in regulated.items():
        peak = frame.filter(rule="gfs").sort("billions").row(-1, named=True)
        total = frame.filter(year=2050)["billions"].sum()
        cards += f"""
        <div class="card">
          <div class="eyebrow">{SCENARIOS[scenario]} · global fuel standard</div>
          <div class="big">{peak["billions"]:.0f} bn USD</div>
          <div class="body">a year at its peak, in {peak["year"]}</div>
          <div class="muted" style="margin-top:6px">All three rules: {total:.0f} bn USD in 2050</div>
        </div>"""
    show_html(
        f'<div class="eyebrow" style="margin-bottom:10px">What the rules collect</div>'
        f'<div class="grid">{cards}</div>'
        f'<div class="muted" style="margin-top:10px">What ships pay the regulator for the units they '
        f"lack; the units FuelEU and the global standard let ships trade among themselves are left out. "
        f"No regulation collects nothing.</div>"
    )

    figure = make_subplots(
        rows=1,
        cols=2,
        shared_yaxes=True,
        horizontal_spacing=0.05,
        subplot_titles=[SCENARIOS[scenario] for scenario in regulated],
    )
    for column, (scenario, frame) in enumerate(regulated.items(), start=1):
        years = sorted(frame["year"].unique())
        for rule, name in RULES.items():
            by_year = dict(
                frame.filter(rule=rule).select("year", "billions").iter_rows()
            )
            figure.add_trace(
                go.Scatter(
                    x=years,
                    y=[by_year.get(year, 0.0) for year in years],
                    name=name,
                    legendgroup=rule,
                    showlegend=column == 1,
                    stackgroup=scenario,
                    mode="lines",
                    line={"width": 1.5, "color": "#fff"},
                    fillcolor=RULE_COLORS[rule],
                    hovertemplate=f"{name}: %{{y:.0f}} bn USD<extra></extra>",
                ),
                row=1,
                col=column,
            )
    figure.update_layout(
        height=440,
        margin={"l": 70, "r": 20, "t": 90, "b": 50},
        hovermode="x unified",
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.16,
            "xanchor": "left",
            "yanchor": "bottom",
        },
    )
    figure.update_annotations(font={"size": 16, "color": INK})
    figure.update_xaxes(gridcolor=WASH, zeroline=False)
    figure.update_yaxes(gridcolor=WASH, zeroline=False, rangemode="tozero")
    figure.update_yaxes(title="Collected, bn USD a year", row=1, col=1)
    show_figure(figure)


# ---- 2. Horizon ----


def use_bundled_study() -> None:
    """Take the study Horizon ran before the meeting, as it wrote it."""
    shutil.rmtree("study", ignore_errors=True)
    shutil.copytree(Path("bundled", "study"), "study")
    show_html(
        f'<div class="eyebrow">Horizon</div><div class="title" style="margin:0">✓ The '
        f"{_study_size()} futures Horizon ran before the meeting are loaded</div>"
    )


def _study_size() -> int:
    """Return the number of futures in the study."""
    return len(
        json.loads(Path("study", "study.json").read_text(encoding="utf-8"))["runs"]
    )


def _study_archive() -> pl.DataFrame:
    """Return every future's results; the column sample holds its run's id, such as demo_sample001."""
    return pl.read_parquet(Path("study", f"{STUDY}_archive.parquet")).with_columns(
        year=pl.col("date").dt.year()
    )


def target(cut: float) -> None:
    """Show how many futures cut emissions by at least cut percent from 2026 to 2050, each future a line."""
    archive = _study_archive()
    years = sorted(archive["year"].unique())
    paths = {
        sample: _emissions(results)["megatonnes"].to_list()
        for (sample,), results in archive.group_by("sample", maintain_order=True)
    }
    cuts = {sample: (1 - path[-1] / path[0]) * 100 for sample, path in paths.items()}
    reached = sum(achieved >= cut for achieved in cuts.values())
    scenario = _emissions(_read("basecase_mid_regulation"))
    scenario_cut = (1 - scenario["megatonnes"][-1] / scenario["megatonnes"][0]) * 100
    show_html(
        f'<div class="eyebrow">Horizon · mid regulation across {len(paths)} futures</div>'
        f'<div style="display:flex; align-items:baseline; gap:18px; flex-wrap:wrap">'
        f'<div class="big">{reached} of {len(paths)}</div><div class="title" style="margin:0">'
        f"futures cut emissions by {cut:g} % or more from 2026 to 2050</div></div>"
        f'<div class="muted">Well to wake. The median future cuts them by {median(cuts.values()):.0f} %, '
        f"the mid regulation scenario by {scenario_cut:.0f} %.</div>"
    )

    groups = {  # colour, legend entry and its place in the legend
        True: (LOWERS, f"{reached} reach the cut", 1),
        False: (RAISES, f"{len(paths) - reached} fall short", 2),
    }
    figure = go.Figure()
    for number, (sample, path) in enumerate(paths.items(), start=1):
        meets = cuts[sample] >= cut
        color, label, rank = groups[meets]
        figure.add_trace(
            go.Scatter(
                x=years,
                y=path,
                mode="lines",
                name=label,
                legendgroup=label,
                legendrank=rank,
                showlegend=label not in {trace.name for trace in figure.data},
                line={"width": 1.2, "color": color},
                opacity=0.45,
                hovertemplate=f"Future {number}: {_signed(-cuts[sample])} by 2050<extra></extra>",
            )
        )
    figure.add_trace(
        go.Scatter(
            x=scenario["year"],
            y=scenario["megatonnes"],
            mode="lines",
            name="Mid regulation scenario",
            legendrank=3,
            line={"width": 3, "color": SCENARIO_COLORS["basecase_mid_regulation"]},
            hovertemplate="Mid regulation: %{y:.0f} Mt<extra></extra>",
        )
    )
    start = median(path[0] for path in paths.values())
    figure.add_hline(
        y=start * (1 - cut / 100),
        line={"dash": "dash", "color": INK, "width": 1.2},
        annotation_text=f"{_signed(-cut)} from 2026",
        annotation_position="top left",
        annotation_font={"color": INK, "size": 13},
    )
    figure.update_layout(
        title={
            "text": "Well-to-wake emissions of each future, 2026 to 2050",
            "font": {"size": 20, "weight": 200},
        },
        height=460,
        margin={"l": 70, "r": 20, "t": 110, "b": 50},
        hovermode="closest",
        legend={
            "orientation": "h",
            "x": 0,
            "y": 1.02,
            "xanchor": "left",
            "yanchor": "bottom",
        },
        xaxis={"gridcolor": WASH, "zeroline": False},
        yaxis={
            "title": "Mt CO₂e a year",
            "gridcolor": WASH,
            "zeroline": False,
            "rangemode": "tozero",
        },
    )
    show_figure(figure)


def _study_outcomes() -> pl.DataFrame:
    """Return per future its lever values, and its emissions and cost in 2050."""
    runs = json.loads(Path("study", "study.json").read_text(encoding="utf-8"))["runs"]
    values = pl.DataFrame(
        [
            {"sample": run["run_id"], **{t: float(run["values"][t]) for t in LEVERS}}
            for run in runs
        ]
    )
    final = _study_archive().filter(year=2050)
    emissions = final.filter(kind="global", attribute="total_equivalent_wtw").select(
        "sample", megatonnes=pl.col("value") / 1e6
    )
    cost = (
        final.filter(pl.col("kind") == "fleet")
        .group_by("sample")
        .agg(
            (
                pl.col("value").filter(attribute="expenses").sum()
                / pl.col("value").filter(attribute="cargo_miles").sum()
                * 1000
                / 1.852
            ).alias("usd")
        )
    )
    return values.join(emissions, on="sample").join(cost, on="sample").sort("sample")


def _spearman(outcomes: pl.DataFrame, token: str, outcome: str) -> float:
    """Return the rank correlation of a lever with an outcome across the futures."""
    return outcomes.select(pl.corr(token, outcome, method="spearman")).item()


def drivers() -> None:
    """Show what moves the 2050 outcome: each lever's rank correlation with emissions and with cost across the futures."""
    outcomes = _study_outcomes()
    tokens = [token for token in LEVERS if outcomes[token].n_unique() > 1]
    emissions = {token: _spearman(outcomes, token, "megatonnes") for token in tokens}
    order = sorted(tokens, key=lambda token: abs(emissions[token]))
    figure = go.Figure()
    panels = (("megatonnes", "Emissions in 2050"), ("usd", "Cost of transport in 2050"))
    for column, (outcome, title) in enumerate(panels):
        values = [_spearman(outcomes, token, outcome) for token in order]
        figure.add_trace(
            go.Bar(
                x=values,
                y=[LEVERS[token] for token in order],
                orientation="h",
                xaxis=f"x{column + 1}",
                marker={"color": [RAISES if v > 0 else LOWERS for v in values]},
                text=[f"{v:+.2f}" for v in values],
                textposition="outside",
                cliponaxis=False,
                textfont={"color": BODY, "size": 12},
                hovertemplate="%{y}: %{x:+.2f}<extra>" + title + "</extra>",
            )
        )
    figure.update_layout(
        title={
            "text": "What moves the 2050 outcome: higher lever value → "
            "<span style='color:#9f5959'><b>raises</b></span> or "
            "<span style='color:#296565'><b>lowers</b></span> it",
            "font": {"size": 20, "weight": 200},
        },
        height=440,
        margin={"l": 190, "r": 40, "t": 100, "b": 50},
        showlegend=False,
        bargap=0.3,
        xaxis={
            "domain": [0, 0.44],
            "range": [-1, 1],
            "title": "Emissions in 2050",
            "gridcolor": WASH,
            "zerolinecolor": MUTED,
            "tickvals": [-1, -0.5, 0, 0.5, 1],
            "ticktext": ["\u22121", "\u22120.5", "0", "+0.5", "+1"],
        },
        xaxis2={
            "domain": [0.56, 1],
            "range": [-1, 1],
            "title": "Cost of transport in 2050",
            "gridcolor": WASH,
            "zerolinecolor": MUTED,
            "tickvals": [-1, -0.5, 0, 0.5, 1],
            "ticktext": ["\u22121", "\u22120.5", "0", "+0.5", "+1"],
        },
        yaxis={"gridcolor": "#fff"},
    )
    show_figure(figure)
    show_html(
        f'<div class="muted">Spearman rank correlation across the {len(outcomes)} futures: +1 means the '
        f"outcome rises whenever the lever does, 0 that the lever makes no consistent difference.</div>"
    )


# ---- 3. Lantern ----


def _on_colab() -> bool:
    """Return whether the kernel runs on Colab, whose runtimes come with the package google.colab."""
    try:
        return find_spec("google.colab") is not None
    except ModuleNotFoundError:  # no google package at all
        return False


# the viewer open_lantern started, a ThreadingHTTPServer, under "server"
_viewer: dict = {}


def open_lantern(*paths: str) -> None:
    """
    Start Lantern's viewer of the paths in this kernel and offer it in a new browser tab.

    Lantern reads the plots.yaml of the folder it is imported in, so this runs in
    the case folder. On Colab the tab goes through Colab's proxy of the port; a
    browser that blocks it can show the viewer in the notebook instead.
    """
    import lantern.server  # here, not at the top: Lantern finds plots.yaml in the folder it is imported in
    import lantern.session

    if "server" in _viewer:  # a second run of the cell replaces the viewer
        _viewer["server"].shutdown()
        _viewer["server"].server_close()
    with contextlib.redirect_stdout(io.StringIO()):  # Lantern's loading lines
        session = lantern.session.Session([Path(path) for path in paths])
    _viewer["server"] = server = lantern.server.make_server(session, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    on_colab = _on_colab()
    address = "" if on_colab else f"http://127.0.0.1:{port}/"
    find = (
        f"const url = await google.colab.kernel.proxyPort({port}, {{cache: false}});"
        if on_colab
        else f"const url = '{address}';"
    )
    show_html(f"""
      <div style="display:flex; align-items:center; gap:28px; flex-wrap:wrap">
        <a id="open-lantern-{port}" href="{address or "#"}" target="_blank" rel="noopener"
           style="display:inline-flex; align-items:center; gap:14px; background:{INK}; color:#fff; text-decoration:none;
                  padding:18px 30px; border-radius:40px; font-size:20px; font-weight:600; letter-spacing:.01em;
                  box-shadow: 0 6px 24px rgba(50,50,50,.18)">
          <svg width="26" height="30" viewBox="0 0 26 30" fill="none" stroke="#fff" stroke-width="1.6"
               stroke-linecap="round" stroke-linejoin="round"><path d="M8,5 a5,5 0 0 1 10,0"/>
            <path d="M5,8 L21,8 L19,11 L7,11 Z"/><path d="M7,11 L6,25 L20,25 L19,11"/><path d="M4,28 L22,28"/>
            <path d="M13,15 c3,3.5 3,6.5 0,8.5 c-3,-2 -3,-5 0,-8.5 Z" fill="{HORIZON_TINT}"/></svg>
          Open Lantern ↗
        </a>
        <div><div style="font-size:18px">Every plot Lantern can draw, in a new tab</div>
          <div class="muted">The three scenarios and the {_study_size()} futures · port {port} ·
            <a href="#" id="here-{port}" style="color:{MUTED}">trouble opening it? show it here</a></div></div>
      </div>
      <div id="frame-{port}"></div>
      <script>
        (async () => {{
          {find}
          document.getElementById("open-lantern-{port}").href = url;
          document.getElementById("here-{port}").onclick = event => {{
            event.preventDefault();
            const frame = document.createElement("iframe");
            frame.src = url;
            frame.style = "width:100%; height:820px; border:1px solid {RULE}; border-radius:14px; margin-top:18px";
            document.getElementById("frame-{port}").replaceChildren(frame);
            try {{ google.colab.output.setIframeHeight(0, true, {{maxHeight: 5000}}); }} catch (error) {{}}
          }};
        }})();
      </script>""")
