# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0
"""Draw example_5's case map and put it at the top of explore.ipynb.

Run from the repository root:  python simulations/examples/example_5/figures/make_case_map.py

Writes figures/case_map.svg and figures/case_map.png, then puts the PNG, base64,
in the notebook's first markdown cell. The geometry, label solver and checks are
docs/_figures/make_gulf_asia_map.py's, and the raster is
docs/_figures/render_map_png.py's, both imported unchanged; only their output
folder is pointed here, so nothing under docs/ is written.

Positions follow the deck: the ports in route.inc, the production sites and
their delivery distances in bunker_logistics.inc.
"""
import base64
import json
import math
import pathlib
import sys

import nbformat

ROOT = pathlib.Path(__file__).resolve().parents[4]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "docs" / "_figures"))
sys.path.insert(0, str(ROOT / "docs" / "workshop"))
import make_gulf_asia_map as g  # noqa: E402
import render_map_png as r  # noqa: E402
from _style import fuel_colour  # noqa: E402

# ----------------------------------------------------------------- projection
W, H = 940.0, 500.0
LAT0, LAT1 = 6.0, 33.5
SY = H / (LAT1 - LAT0)
SX = SY * math.cos(math.radians((LAT0 + LAT1) / 2.0))
LON0 = -78.0 - W / SX / 2.0
LON1 = LON0 + W / SX


def xy(lon, lat):
    return (lon - LON0) * SX, (LAT1 - lat) * SY


g.xy, g.W, g.H = xy, W, H

# --------------------------------------------------------------- case content
MIAMI, KINGSTON = (-80.12, 25.77), (-76.80, 17.95)
TRINIDAD, FDF = (-61.50, 10.40), (-61.07, 14.60)
HOUSTON = (-94.90, 29.40)

PORTS = [(*MIAMI, "Miami", "US · fossil fuels and LNG only"),
         (*KINGSTON, "Kingston", "Jamaica · tugs · LNG"),
         (*TRINIDAD, "Point Lisas", "Trinidad · tugs and ferries"),
         (*FDF, "Fort-de-France", "Martinique · EU · tugs and ferries")]

FUELS = {"blue ammonia": "ammonia_blue", "e-ammonia": "ammonia_electro",
         "e-methanol": "methanol_electro", "bio-methanol": "methanol_bio"}
FUEL_COLOURS = {label: fuel_colour(name) for label, name in FUELS.items()}

PLANTS = [(-62.9, 8.9, "Trinidad fuel plants", "278 nm to Martinique, 1,100 to Jamaica",
           ["blue ammonia", "e-ammonia", "e-methanol"]),
          (*HOUSTON, "US Gulf Coast fuel plants", "shipped 1,300 - 2,100 nm",
           ["blue ammonia", "e-ammonia", "e-methanol", "bio-methanol"]),
          # Chile is off the map: the icons sit where its fuel enters the window,
          # in the Gulf of Panama, on its way to the canal.
          (-80.6, 6.9, "Chilean e-fuels, from Magallanes", "4,700 - 5,250 nm through Panama",
           ["e-ammonia", "e-methanol"])]

# The feeders' loop, route.inc: Miami - Kingston (Windward Passage) - Trinidad -
# Martinique - back to Miami north of the Antilles.
FEEDER = [MIAMI, (-79.6, 25.2), (-79.4, 24.0), (-78.0, 23.0), (-75.5, 22.0),
          (-74.0, 20.4), (-74.6, 19.0), (-76.0, 17.6), KINGSTON,
          (-75.0, 16.6), (-70.0, 14.8), (-65.0, 12.6), (-62.4, 11.0), (-61.9, 10.7), TRINIDAD,
          (-61.9, 10.75), (-61.7, 11.6), (-61.4, 13.0), (-61.4, 14.2), FDF,
          (-61.6, 15.2), (-63.5, 17.0), (-64.6, 18.2), (-67.0, 20.0), (-71.0, 21.8),
          (-75.0, 24.0), (-77.6, 26.2), (-79.4, 26.2), MIAMI]

# The regional cargo ships' and tankers' loop: Trinidad - Martinique - Kingston.
# Drawn a little south of the feeders' legs so the two loops read apart.
REGIONAL = [TRINIDAD, (-61.85, 10.6), (-61.9, 10.85), (-61.2, 11.6), (-60.9, 13.0),
            (-60.8, 14.3), FDF, (-61.6, 14.4), (-66.0, 15.6), (-71.0, 16.6),
            (-75.4, 17.2), KINGSTON, (-76.0, 16.7), (-71.0, 14.2), (-66.0, 12.0),
            (-62.6, 11.1), (-61.95, 10.55), TRINIDAD]

DELIVERY = [("gulf_kingston", [HOUSTON, (-93.0, 27.5), (-89.0, 24.5), (-86.0, 22.2),
                               (-84.0, 19.6), (-80.0, 17.0), (-77.6, 16.7), KINGSTON]),
            ("gulf_martinique", [HOUSTON, (-93.5, 27.0), (-89.5, 23.5), (-86.0, 21.0),
                                 (-83.5, 17.5), (-78.0, 14.5), (-70.0, 13.6),
                                 (-64.0, 14.0), (-61.5, 14.5), FDF]),
            ("chile_kingston", [(-80.0, 6.6), (-79.6, 7.6), (-79.55, 8.9), (-79.9, 9.4),
                                (-79.0, 12.5), (-77.6, 16.2), KINGSTON])]

SEA_EXEMPT_BOXES = [(-80.6, 25.3, -79.7, 26.3),     # Miami
                    (-77.3, 17.5, -76.5, 18.3),     # Kingston harbour
                    (-62.0, 10.0, -61.2, 10.8),     # Gulf of Paria
                    (-61.3, 14.3, -60.9, 14.8),     # Fort-de-France bay
                    (-95.5, 28.9, -94.4, 29.9),     # Houston ship channel
                    (-80.2, 8.6, -79.3, 9.6)]       # Panama Canal

C_OCEAN, C_LAND, C_BORDER = "#eaf6fb", "#dcdcdc", "#ffffff"
C_ROUTE, C_REGIONAL, C_PORT = "#b55f2e", "#716b86", "#3d5f87"
C_DELIV = "#8c8c8c"
C_EU = "#3d5f87"
C_TEXT, C_SUB = "#323232", "#585858"
g.C_TEXT = C_TEXT

FEEDER_SHIPS = [2, 10, 23]
REGIONAL_SHIPS = [7, 13]
SHIP_SCALE = 1.5

TRIM = {"feeder": 11.0, "regional": 11.0, "gulf_kingston": 12.0, "gulf_martinique": 12.0,
        "chile_kingston": 18.0}
MIN_TAIL = {"feeder": 20.0, "regional": 18.0, "gulf_kingston": 16.0, "gulf_martinique": 16.0,
            "chile_kingston": 16.0}

LEGEND_BOX = [8, H - 222, 236, H - 8]

PORT_CANDS = [
    [(13, 3, "start"), (-13, 3, "end"), (13, -12, "start"), (-13, -12, "end")],
    [(-13, -10, "end"), (-13, 3, "end"), (13, -14, "start"), (0, 26, "middle"),
     (-6, -52, "end"), (-12, -54, "end"), (-6, -58, "end")],
    [(-13, 22, "end"), (13, 22, "start"), (-13, 3, "end"), (0, 30, "middle")],
    [(13, -6, "start"), (13, 8, "start"), (13, -20, "start"), (-13, -16, "end")],
]
PLANT_CANDS = [(16, 4, "start"), (16, 18, "start"), (-30, 26, "middle"), (0, 30, "middle"),
               (24, -26, "start"), (-26, -26, "end"), (0, -26, "middle"),
               (-26, 2, "end"), (-26, 14, "end"), (-40, -8, "end"), (-60, 4, "end"),
               (-90, 32, "start"), (-120, 32, "start"), (-130, 48, "start"), (30, -4, "start"),
               (36, -14, "start"), (-60, -30, "start"), (-20, -32, "start")]


def ship_on_route(route, seg, scale):
    """g.ship_on_route, with the glyph mirrored on westbound legs.

    Rotating the side profile by more than 90 degrees turns it upside down,
    deckhouse under the hull; a ship heading west is drawn facing left instead.
    """
    (x0, y0), (x1, y1) = xy(*route[seg]), xy(*route[seg + 1])
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
    flip = ""
    if abs(angle) > 90.0:
        angle -= math.copysign(180.0, angle)
        flip = " scale(-1 1)"
    w, h = 16.0 * scale, 14.0 * scale
    svg = (f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({angle:.1f}){flip} '
           f'translate({-w / 2:.1f} {-h / 2:.1f}) scale({scale})">'
           f'<path d="{g.SHIP}" fill="{C_TEXT}" stroke="#ffffff" stroke-width="1.4" '
           f'stroke-linejoin="round"/></g>')
    rad = max(w, h) / 2.0 + 2.0
    return svg, [cx - rad, cy - rad, cx + rad, cy + rad]


def main():
    gj = json.loads((ROOT / "docs" / "_figures" / "ne_110m_countries.geojson")
                    .read_text(encoding="utf-8"))
    rings = g.rings_of(gj)
    on_land = g.make_land_test(rings)
    for name, route in [("feeder", FEEDER), ("regional", REGIONAL), *DELIVERY]:
        bad = g.verify_route(route, on_land, SEA_EXEMPT_BOXES)
        assert not bad, f"{name} crosses land at {bad[:5]}"

    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:940px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="Map of example 5: international feeders on a Miami - Kingston - '
        f'Trinidad - Martinique loop, the regional cargo ships and tankers on a '
        f'Trinidad - Martinique - Kingston loop, tugs and ferries in the ports, and '
        f'new fuels made in Trinidad, on the US Gulf Coast and in Chile">')
    add('<defs>'
        f'<marker id="e5arw" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_ROUTE}"/></marker>'
        f'<marker id="e5reg" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_REGIONAL}"/></marker>'
        f'<marker id="e5sup" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="4.5" '
        f'markerHeight="4.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_DELIV}"/></marker>'
        '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')

    paths = []
    for ring in rings:
        pts = g.simplify(g.clip_rect([xy(*p) for p in ring], 0, 0, W, H), tol=0.6)
        if len(pts) >= 3:
            paths.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    add(f'<path d="{"".join(paths)}" fill="{C_LAND}" stroke="{C_BORDER}" '
        f'stroke-width="1.0" stroke-linejoin="round" fill-rule="evenodd"/>')

    # Martinique, the EU's jurisdiction here: a translucent halo, not type
    ex, ey = xy(*FDF)
    add(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="19" fill="{C_EU}" fill-opacity="0.13" '
        f'stroke="{C_EU}" stroke-opacity="0.45" stroke-width="1" stroke-dasharray="3 3"/>')

    lay = g.Layout()
    lay.reserve(LEGEND_BOX)
    lay.reserve([W - 252, H - 22, W - 6, H - 4])

    def reserve_polyline(points, half=4.0, step=7.0):
        for a, b in zip(points, points[1:]):
            seg = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            n = max(1, int(seg / step))
            for k in range(n + 1):
                f = k / n
                lay.reserve([a[0] + f * (b[0] - a[0]) - half, a[1] + f * (b[1] - a[1]) - half,
                             a[0] + f * (b[0] - a[0]) + half, a[1] + f * (b[1] - a[1]) + half])

    ships = ([ship_on_route(FEEDER, s, SHIP_SCALE) for s in FEEDER_SHIPS]
             + [ship_on_route(REGIONAL, s, SHIP_SCALE) for s in REGIONAL_SHIPS])
    for _, box in ships:
        lay.reserve(box)

    tips = {}
    for name, route, colour, marker, width in (("feeder", FEEDER, C_ROUTE, "e5arw", 2.6),
                                               ("regional", REGIONAL, C_REGIONAL, "e5reg", 2.6)):
        pts = g.straighten_tail(g.trim_end([xy(*c) for c in route], TRIM[name]), MIN_TAIL[name])
        reserve_polyline(pts, half=3.0)
        add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in pts)}" fill="none" '
            f'stroke="{colour}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round" marker-end="url(#{marker})"/>')
        tips[name] = g.marker_tip(pts, 5.5, width)

    for name, route in DELIVERY:
        pts = g.straighten_tail(g.trim_end([xy(*c) for c in route], TRIM[name]), MIN_TAIL[name])
        reserve_polyline(pts, half=2.5)
        add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in pts)}" fill="none" '
            f'stroke="{C_DELIV}" stroke-width="1.6" stroke-dasharray="7 5" '
            f'marker-end="url(#e5sup)"/>')
        tips[name] = g.marker_tip(pts, 4.5, 1.6)

    for ship_svg, _ in ships:
        add(ship_svg)

    def txt(x, y, s, fs, anchor, fill, weight="400"):
        wt = f' font-weight="{weight}"' if weight != "400" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
                f'text-anchor="{anchor}"{wt}>{s}</text>')

    labels = []
    for lon, lat, *_ in PORTS:
        x, y = xy(lon, lat)
        lay.reserve([x - 7, y - 7, x + 7, y + 7])
    for lon, lat, _, _, fuels in PLANTS:
        x, y = xy(lon, lat)
        span = 13.0 * (len(fuels) - 1)
        lay.reserve([x - span / 2 - 10, y - 10, x + span / 2 + 10, y + 10])

    MORE = [(dx, dy, a) for dy in (-14, 3, 20, -30, 36, -46, 52) for dx, a in
            ((14, "start"), (-14, "end"), (0, "middle"), (30, "start"), (-30, "end"))]
    for (lon, lat, name, sub), cands in zip(PORTS, PORT_CANDS):
        cands = cands + MORE
        x, y = xy(lon, lat)
        bx, by, anchor = lay.pair(x, y, name, sub, 12.5, 9.5, cands)
        labels.append(txt(bx, by, name, 12.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 12, sub, 9.5, anchor, C_SUB))
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="{C_PORT}" '
            f'stroke="#ffffff" stroke-width="1.6"/>')

    for lon, lat, name, sub, fuels in PLANTS:
        x, y = xy(lon, lat)
        span = 13.0 * (len(fuels) - 1)
        for k, fuel in enumerate(fuels):
            add(g.factory(x - span / 2 + k * 13.0, y, FUEL_COLOURS[fuel]))
        bx, by, anchor = lay.pair(x, y, name, sub, 11.5, 9.5, PLANT_CANDS)
        labels.append(txt(bx, by, name, 11.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 11.5, sub, 9.5, anchor, C_SUB))

    SPREAD = [(0, 0), (0, -17), (0, 19), (0, -34), (0, 36), (36, 0), (-36, 0),
              (0, -52), (0, 54), (64, 10), (-64, 10), (0, -70), (0, 72), (90, 0), (-90, 0)]
    PAIR_SPREAD = ([(dx, dy, "start") for dx, dy in SPREAD]
                   + [(dx, dy, "end") for dx, dy in SPREAD])
    notes = [((-71.5, 26.8), "International feeders: 40 ships, about 1,500 TEU",
              "covered by the global fuel standard, EU ETS and FuelEU", C_ROUTE, "600"),
             ((-51.0, 23.5), "Regional cargo ships and tankers: 139",
              "with 144 tugs and 47 ferries in the ports; all under 5,000 GT", C_REGIONAL, "600"),
             ((-71.5, 30.0), "The regional fleet is outside all three policies today;",
              "the extended deck brings it in", C_SUB, "400")]
    for at, top, bot, fill, weight in notes:
        x, y = xy(*at)
        bx, by, anchor = lay.pair(x, y, top, bot, 11.5, 10, PAIR_SPREAD)
        labels.append(txt(bx, by, top, 11.5, anchor, fill, weight))
        labels.append(txt(bx, by + 12.5, bot, 10, anchor, fill))

    out.extend(labels)
    add(txt(W - 10, H - 8, "Basemap: Natural Earth 1:110m (public domain)", 8.5, "end", "#a5a5a5"))

    lgx, lgy = LEGEND_BOX[0] + 2, LEGEND_BOX[1] + 2
    add(f'<rect x="{lgx}" y="{lgy}" width="{LEGEND_BOX[2] - LEGEND_BOX[0] - 4}" '
        f'height="{LEGEND_BOX[3] - LEGEND_BOX[1] - 4}" rx="5" fill="#ffffff" '
        f'fill-opacity="0.92" stroke="#bebebe" stroke-width="0.8"/>')
    row = lgy + 19
    add(f'<circle cx="{lgx + 17}" cy="{row - 3}" r="5.2" fill="{C_PORT}"/>')
    add(txt(lgx + 32, row, "bunker port", 10, "start", C_TEXT))
    row += 18
    add(f'<circle cx="{lgx + 17}" cy="{row - 3}" r="8" fill="{C_EU}" fill-opacity="0.13" '
        f'stroke="{C_EU}" stroke-opacity="0.45" stroke-dasharray="3 3"/>')
    add(txt(lgx + 32, row, "EU jurisdiction (outermost region)", 10, "start", C_TEXT))
    row += 18
    add(txt(lgx + 10, row, "fuel plant, by fuel made:", 9.5, "start", C_SUB))
    for fuel, colour in FUEL_COLOURS.items():
        row += 16
        add(g.factory(lgx + 17, row - 3, colour, scale=0.85))
        add(txt(lgx + 32, row, fuel, 10, "start", C_TEXT))
    for colour, label, dash, width in ((C_ROUTE, "international feeders' loop", "", 2.6),
                                       (C_REGIONAL, "regional cargo and tanker loop", "", 2.6),
                                       (C_DELIV, "fuel shipped to the ports", ' stroke-dasharray="7 5"', 1.6)):
        row += 17
        add(f'<line x1="{lgx + 10}" y1="{row - 3}" x2="{lgx + 25}" y2="{row - 3}" '
            f'stroke="{colour}" stroke-width="{width}"{dash}/>')
        add(txt(lgx + 32, row, label, 10, "start", C_TEXT))
    assert row + 8 <= LEGEND_BOX[3], f"legend overflows its box by {row + 8 - LEGEND_BOX[3]:.0f} px"
    add('</svg>')
    svg = "\n".join(out)

    port_px = {"feeder": xy(*MIAMI), "regional": xy(*TRINIDAD),
               "gulf_kingston": xy(*KINGSTON), "gulf_martinique": xy(*FDF),
               "chile_kingston": xy(*KINGSTON)}
    for name, ((tx, ty), _) in tips.items():
        gap = math.hypot(tx - port_px[name][0], ty - port_px[name][1])
        assert gap >= 5.2 + 0.8 + 1.0, f"{name} arrowhead sits on its port dot ({gap:.1f} px)"

    bs = lay.text_boxes
    worst = min(max(max(a[0] - b[2], b[0] - a[2]), max(a[1] - b[3], b[1] - a[3]))
                for i, a in enumerate(bs) for b in bs[i + 1:])
    assert worst > 0, f"text boxes overlap by {-worst:.1f} px"

    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n\n"
           "Basemap geometry derived from Natural Earth 1:110m Admin 0 countries,\n"
           "which is in the public domain (naturalearthdata.com).\n-->\n")
    (HERE / "case_map.svg").write_text(hdr + svg + "\n", encoding="utf-8")

    # render_map_png reads <STATIC>/<stem>.svg and writes <HERE>/<stem>.png
    r.STATIC, r.HERE = HERE, HERE
    r.render("case_map")
    png = HERE / "case_map.png"

    nb_path = HERE.parent / "explore.ipynb"
    nb = nbformat.read(nb_path, as_version=4)
    b64 = base64.b64encode(png.read_bytes()).decode("ascii")
    image = f"![Map of example 5](data:image/png;base64,{b64})"
    first = nb.cells[0]
    src = first.source
    marker = "![Map of example 5]"
    if marker in src:
        head, _, rest = src.partition(marker)
        rest = rest.split(")", 1)[1]
        src = head + image + rest
    else:
        title, _, body = src.partition("\n")
        src = f"{title}\n\n{image}\n{body}"
    first.source = src
    nb_path.write_text(nbformat.writes(nb), encoding="utf-8", newline="\n")

    print(f"window {LON0:.1f} to {LON1:.1f} E, {LAT0}-{LAT1} N; {len(bs)} labels, "
          f"tightest gap {worst:.1f} px; wrote case_map.svg, case_map.png and the notebook")


if __name__ == "__main__":
    main()
