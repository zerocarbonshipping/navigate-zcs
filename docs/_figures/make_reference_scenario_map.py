# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Generate the reference-scenario world map as an SVG.

Run from anywhere:  python docs/_figures/make_reference_scenario_map.py

Writes docs/_static/reference_scenario_map.svg, the map in
02-run-a-global-case.ipynb and 05-build-your-own-case.ipynb (the global-case card).

To push a change all the way through to the notebooks:

    python docs/_figures/make_reference_scenario_map.py
    python docs/_figures/render_map_png.py reference_scenario
    python docs/_figures/map_to_notebook.py reference_scenario

Every number on the map is read from the assumption library rather than typed:

- PATHWAYS. A region's pathway count is the number of plants copied into it in
  assumptions/modules/installation/default_plant.inc.
- ELECTRICITY COST. The 2050 value of the Forecast each region file in
  assumptions/defaults/installation/Region/ gives as the opex of the
  "renewable" source.

The footnote's claims are asserted against the same files and the scenario
decks: two bunker ports, EU ETS and FuelEU on port_europe only, gfs on both
ports, FAME in Europe only and biogas as the only bio route in the Middle East.
If one fails, the script stops: re-read the deck and change the wording.

Basemap: Natural Earth 1:110m Admin 0 countries (public domain), projected
equirectangular over the whole world and shifted so the empty Pacific falls
outside the frame. The geometry helpers and label metrics are
make_example_4_map.py's, imported from it.
"""

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "docs" / "workshop"))

import make_example_4_map as m4  # noqa: E402
from _style import PALETTE  # noqa: E402

LIBRARY = ROOT / "assumptions"
MODULES = LIBRARY / "modules" / "installation"
DEFAULTS = LIBRARY / "defaults" / "installation"
SCENARIOS = ROOT / "simulations" / "scenarios"

# ----------------------------------------------------------------- projection
# The whole world at 940 px per 360 degrees, from 84 N to 60 S; the frame is the
# 780 px from x = 100, which drops the empty Pacific on both sides.
LON0, LON1 = -180.0, 180.0
LAT0, LAT1 = -60.0, 84.0
W = 940.0
S = W / (LON1 - LON0)
H = (LAT1 - LAT0) * S
SHIFT, FRAME_W = 100, 780


def xy(lon, lat):
    return (lon - LON0) * S, (LAT1 - lat) * S


# --------------------------------------------------------------- map content
# Where each region's disc sits, and where its two-line label goes relative to
# the disc: (lon, lat, anchor, dx, dy) with dy the baseline of the first line.
# Regions are model aggregates; positions are indicative.
REGIONS = {
    "middle_east": ("Middle East", 48.0, 25.0, "middle", 0.0, -36.0),
    "africa":      ("Africa",      20.0, 2.0,  "middle", 0.0, 32.0),
    "americas":    ("Americas",   -85.0, 15.0, "start",  26.0, -4.0),
    "asia":        ("Asia",       100.0, 35.0, "middle", 0.0, 32.0),
    "europe":      ("Europe",      12.0, 50.0, "middle", 0.0, -52.0),
}
DISC_R, RING_R = 17, 32

C_OCEAN, C_GRID, C_EQUATOR = PALETTE["blue"][0], PALETTE["blue"][1], PALETTE["blue"][3]
C_LAND = PALETTE["black"][1]
C_EU = PALETTE["orange"][6]
C_TEXT, C_SUB, C_FAINT, C_FRAME = (PALETTE["black"][8], PALETTE["black"][5],
                                   PALETTE["black"][3], PALETTE["black"][2])
COST_RAMP = PALETTE["blue"][4:9]            # cheapest -> dearest

FOOTNOTES = [
    "gfs — a global well-to-wake intensity standard — covers both ports and every voyage.",
    "Bunkering is aggregated into two ports: one EU, one rest-of-world.",
    "Europe is the only region with a FAME pathway; in the Middle East the only bio "
    "routes are biogas.",
]
CAVEAT = "Regions are model aggregates; disc positions are indicative, not plant sites."

# The Middle East's bio plants; both start from biogas. Asserted below, so a new
# bio plant there stops the script before the footnote goes stale.
BIOGAS_PLANTS = {"plant_methane_bio", "plant_methanol_bio_smr"}


# ------------------------------------------------------------- read the deck
def _read(path):
    return path.read_text(encoding="utf-8")


def read_regions():
    return re.findall(r'^Import Region "(\w+)"', _read(MODULES / "default_region.inc"), re.M)


def read_plants():
    """Plant template -> regions it is copied into."""
    plants = {}
    text = _read(MODULES / "default_plant.inc")
    for template, copy in re.findall(r'^Copy Plant "(\w+)"\s+"(\w+)"', text, re.M):
        assert copy.startswith(template + "_"), copy
        plants.setdefault(template, []).append(copy[len(template) + 1:])
    return plants


def read_forecast_2050(name):
    text = _read(DEFAULTS / "Forecast" / f"{name}.inc")
    match = re.search(r'"01-01-2050"\s+([-\d.]+)', text)
    assert match, f"Forecast {name} has no 2050 row"
    return float(match.group(1))


def read_electricity_cost(region):
    text = _read(DEFAULTS / "Region" / f"{region}.inc")
    match = re.search(r'set_source_opex\("renewable",\s*Forecast\("(\w+)"\)\)', text)
    assert match, f"Region {region} sets no renewable opex"
    return read_forecast_2050(match.group(1))


def jurisdiction(path, regulation):
    text = _read(path)
    block = re.search(r'Regulation "%s" \{(.*?)\n\}' % regulation, text, re.S)
    assert block, f"no Regulation {regulation} in {path}"
    return re.findall(r'Port\("(\w+)"\)', re.search(r"Jurisdiction = \[(.*?)\]", block.group(1)).group(1))


def check_claims(plants, regions):
    ports = re.findall(r'^Import Port "(\w+)"', _read(MODULES / "default_port.inc"), re.M)
    assert sorted(ports) == ["port_europe", "port_global"], f"ports are {ports}"

    for name in ("eu_ets", "fuel_eu"):
        got = jurisdiction(DEFAULTS / "Regulation" / f"{name}.inc", name)
        assert got == ["port_europe"], f"{name} covers {got}"

    for strength in ("mid", "strong"):
        got = jurisdiction(SCENARIOS / "0_includes" / f"{strength}_regulation.inc", "gfs")
        assert sorted(got) == sorted(ports), f"gfs ({strength}) covers {got}"

    fame = [t for t in plants if "methyl_ester" in t]
    assert fame and all(plants[t] == ["europe"] for t in fame), "FAME is not Europe-only"

    bio_me = {t for t, rs in plants.items() if "bio" in t and "middle_east" in rs}
    assert bio_me == BIOGAS_PLANTS, f"Middle East bio plants are {sorted(bio_me)}"

    assert sorted(regions) == sorted(REGIONS), f"regions are {regions}"


# ----------------------------------------------------------------------- draw
def text(add, x, y, s, fs, fill, anchor="start", weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
        f'text-anchor="{anchor}"{w}>{s}</text>')


def draw(rings, data):
    out = []
    add = out.append
    boxes = []
    groups = {}

    def label(x, y, s, fs, fill, anchor="start", weight=None, shift=0, group=None):
        """Draw a line of text; lines of one label share a group, so one box."""
        text(add, x, y, s, fs, fill, anchor, weight)
        box = m4.box_of(x - shift, y, s, fs, anchor, "bold" if weight else "normal")
        if group is not None and group in groups:
            boxes[groups[group]] = m4.union(boxes[groups[group]], box)
        else:
            groups[group] = len(boxes)
            boxes.append(box)

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FRAME_W} {H:.0f}" '
        f'width="100%" style="max-width:{FRAME_W}px;height:auto;font-family:system-ui,'
        f"-apple-system,'Segoe UI',sans-serif\" role=\"img\" aria-label=\"World map of "
        f"the Navigate reference scenario: five fuel-supply regions shaded by their "
        f'2050 electricity cost, with Europe marked as the EU ETS and FuelEU jurisdiction">')
    add(f'<rect width="{FRAME_W}" height="{H:.0f}" fill="{C_OCEAN}"/>')
    add("<!-- the map itself, shifted so the empty Pacific on both sides falls outside the frame -->")
    add(f'<g transform="translate(-{SHIFT} 0)">')

    for lon in range(-150, int(LON1), 30):
        x, _ = xy(lon, 0)
        add(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H:.0f}" stroke="{C_GRID}" stroke-width="0.6"/>')
    for lat in (-30, 0, 30, 60):
        _, y = xy(0, lat)
        add(f'<line x1="0" y1="{y:.0f}" x2="{W:.0f}" y2="{y:.0f}" stroke="{C_GRID}" stroke-width="0.6"/>')

    paths = []
    for ring in rings:
        pts = m4.simplify(m4.clip_rect([xy(*p) for p in ring], 0, 0, W, H))
        if len(pts) >= 3:
            paths.append("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + "Z")
    # stroked in the land colour, not white: the map is about regions, and country
    # borders would only clutter the labels
    add(f'<path d="{"".join(paths)}" fill="{C_LAND}" stroke="{C_LAND}" '
        f'stroke-width="0.7" stroke-linejoin="round" fill-rule="evenodd"/>')

    _, yeq = xy(0, 0)
    add(f'<line x1="0" y1="{yeq:.0f}" x2="{W:.0f}" y2="{yeq:.0f}" stroke="{C_EQUATOR}" '
        f'stroke-width="0.9" stroke-dasharray="5 4"/>')

    ex, ey = xy(*REGIONS["europe"][1:3])
    add(f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="{RING_R}" fill="{C_EU}" fill-opacity="0.07" '
        f'stroke="{C_EU}" stroke-width="1.3" stroke-dasharray="4 3"/>')

    order = sorted(data, key=lambda r: data[r]["cost"])
    for region in order:
        x, y = xy(*REGIONS[region][1:3])
        colour = COST_RAMP[order.index(region)]
        add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{DISC_R}" fill="{colour}" '
            f'fill-opacity="0.95" stroke="#ffffff" stroke-width="1.8"/>')
    for region in order:
        name, lon, lat, anchor, dx, dy = REGIONS[region]
        x, y = xy(lon, lat)
        sub = f'{data[region]["pathways"]} pathways · {data[region]["cost"]:.1f} USD/MWh'
        label(x + dx, y + dy, name, 11.5, C_TEXT, anchor, 600, SHIFT, region)
        label(x + dx, y + dy + 11.5, sub, 9.5, C_SUB, anchor, shift=SHIFT, group=region)

    label(ex - RING_R - 11.7, ey - 6.2, "EU ETS + FuelEU", 10, C_EU, "end", 600, SHIFT, "eu")
    label(ex - RING_R - 11.7, ey + 5.8, "EU port calls only", 9.5, C_EU, "end", shift=SHIFT, group="eu")
    add("</g>")

    for i, line in enumerate(FOOTNOTES):
        label(20, 317 + 13 * i, line, 9.5, C_SUB, group="notes")
    label(20, 317 + 13 * len(FOOTNOTES), CAVEAT, 9, C_FAINT, group="notes")
    label(FRAME_W - 10, H - 10, "Basemap: Natural Earth 1:110m (public domain)", 8.5, C_FAINT, "end")

    # legend
    add(f'<rect x="12" y="14" width="214" height="104" rx="5" fill="#ffffff" '
        f'fill-opacity="0.90" stroke="{C_FRAME}" stroke-width="0.8"/>')
    add(f'<circle cx="31" cy="33" r="8" fill="{COST_RAMP[2]}" stroke="#ffffff" stroke-width="1.4"/>')
    text(add, 46, 36, "fuel-supply region", 10, C_TEXT)
    text(add, 22, 59, "2050 electricity cost", 9.5, C_SUB)
    for i, colour in enumerate(COST_RAMP):
        add(f'<rect x="{22 + 24 * i}" y="65" width="22" height="11" fill="{colour}"/>')
    text(add, 22, 88, "cheaper", 8.5, C_FAINT)
    text(add, 142, 88, "dearer", 8.5, C_FAINT, "end")
    add(f'<circle cx="31" cy="102" r="8" fill="{C_EU}" fill-opacity="0.07" stroke="{C_EU}" '
        f'stroke-width="1.3" stroke-dasharray="3 2.5"/>')
    text(add, 46, 105, "EU ETS + FuelEU jurisdiction", 10, C_TEXT)
    add("</svg>")

    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            gap = max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3])
            assert gap > 0, f"text boxes {i} and {j} overlap by {-gap:.1f} px"
    for b in boxes:
        assert 0 <= b[0] and b[2] <= FRAME_W, f"label box {b} leaves the frame"

    return "\n".join(out), len(paths)


def main():
    regions = read_regions()
    plants = read_plants()
    check_claims(plants, regions)

    data = {}
    for region in regions:
        data[region] = {"pathways": sum(region in rs for rs in plants.values()),
                        "cost": read_electricity_cost(region)}

    gj = json.loads((HERE / "ne_110m_countries.geojson").read_text(encoding="utf-8"))
    rings = m4.rings_of(gj)

    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n\n"
           "Basemap geometry derived from Natural Earth 1:110m Admin 0 countries,\n"
           "which is in the public domain (naturalearthdata.com).\n-->\n")
    svg, n_rings = draw(rings, data)
    out = HERE.parent / "_static" / "reference_scenario_map.svg"
    out.write_text(hdr + svg + "\n", encoding="utf-8")
    print(f"wrote {out.name}: {n_rings} country rings, {len(svg) / 1024:.1f} KB")

    for region in sorted(data, key=lambda r: data[r]["cost"]):
        print(f"  {region:12} {data[region]['pathways']:3} pathways  {data[region]['cost']:6.1f} USD/MWh")


if __name__ == "__main__":
    main()
