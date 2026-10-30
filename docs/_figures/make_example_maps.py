"""Generate the case maps of examples 1 to 3 for the Examples pages.

Run from the repository root:

    python docs/_figures/make_example_maps.py                    # all three
    python docs/_figures/make_example_maps.py south_pacific      # one

Writes docs/_static/examples/<name>_map.svg. The geometry, label solver and
glyphs are make_gulf_asia_map.py's, imported from it, as make_rhine_map.py does.
The projection scales longitude by cos(latitude) at the window's centre, and
longitudes are taken modulo 360 east of the window's west edge, so a window can
cross the 180th meridian (the South Pacific does).

What the maps show comes from the decks:

- example_1: mainline ships from Singapore to Rotterdam via Suez (8,300 nm a leg
  in route.inc), feeders Rotterdam - Hamburg - Aalborg; bio-methanol from a
  plant in the deck's Europe region, which has no location, so it is drawn in
  one place for legibility; every port bunkers it except Aalborg.
- example_2: a regional trip between the five ports of route.inc, which has no
  order of calls, so the loop drawn is one possible order; the deck names
  countries, so each is drawn at its main port. FAME is made in Europe and
  delivered to Australia and New Zealand only (bunker_logistics.inc).
- example_3: two regional trips (route.inc), the mid-range tankers between
  Helsinki, Stockholm and Gdansk, the coastal tankers between Helsinki, Tallinn
  and Stockholm, each drawn in one possible order; e-ammonia from a plant in
  the deck's Europe region, sold at Helsinki and Stockholm only (ports.inc).
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_gulf_asia_map as g  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "workshop"))
from _style import fuel_colour  # noqa: E402

C_OCEAN, C_LAND, C_BORDER = "#eaf6fb", "#dcdcdc", "#ffffff"
C_ROUTE, C_FEEDER, C_PORT = "#b55f2e", "#3d5f87", "#3d5f87"
C_DELIV = "#8c8c8c"
C_TEXT, C_SUB, C_FAINT = "#323232", "#585858", "#a5a5a5"

AROUND = [(13, 3, "start"), (13, -12, "start"), (13, 18, "start"),
          (-13, 3, "end"), (-13, -12, "end"), (-13, 18, "end"),
          (0, -16, "middle"), (0, 26, "middle"), (24, -24, "start"), (-24, -24, "end"),
          (24, 30, "start"), (-24, 30, "end"),
          (40, -30, "start"), (-40, -30, "end"), (40, 40, "start"), (-40, 40, "end"),
          (0, -40, "middle"), (0, 50, "middle"), (60, -50, "start"), (-60, -50, "end")]

CASES = {
    "mainline_feeders": {
        "window": (-36.0, 132.0, -6.0, 66.0),
        "legend_top": True,
        "aria": "Map of example 1: container mainline ships from Singapore to Rotterdam "
                "via Suez, feeders from Rotterdam to Hamburg and Aalborg, and a European "
                "bio-methanol plant delivering to every port but Aalborg",
        "ports": [(103.85, 1.26, "Singapore", "fuel oil · bio-methanol"),
                  (4.05, 51.95, "Rotterdam", "fuel oil · bio-methanol"),
                  (9.97, 53.55, "Hamburg", "fuel oil · bio-methanol"),
                  (9.92, 57.05, "Aalborg", "fuel oil only")],
        "routes": [
            ("mainline", C_ROUTE, 2.8, [
                (103.85, 1.26), (101.0, 2.9), (98.0, 5.2), (95.0, 6.3), (88.0, 5.8),
                (80.6, 5.3), (72.0, 9.0), (60.0, 13.5), (51.5, 12.6), (43.4, 12.5),
                (41.4, 15.0), (38.5, 20.0), (35.3, 25.5), (33.6, 27.7), (32.55, 29.9),
                (32.3, 31.5), (28.0, 33.5), (20.0, 35.0), (11.6, 37.4), (8.0, 37.6),
                (2.0, 37.0), (-2.0, 36.2), (-5.6, 35.95), (-9.6, 36.9), (-10.0, 43.0),
                (-6.0, 48.4), (-1.5, 50.0), (1.5, 51.0), (3.4, 51.9), (4.05, 51.95)],
             [5, 13]),
            ("feeders", C_FEEDER, 2.0, [
                (4.05, 51.95), (3.7, 52.3), (4.3, 53.3), (6.5, 53.85), (8.3, 54.05), (9.97, 53.55),
                (8.3, 54.2), (7.4, 55.6), (7.8, 57.2), (10.6, 57.9), (10.6, 57.2),
                (9.92, 57.05)],
             []),
        ],
        "sea_exempt": [(32.0, 27.5, 34.0, 31.6),     # the Gulf of Suez and the canal, land at 1:110m
                       (8.5, 53.3, 10.2, 54.1),      # the Elbe to Hamburg
                       (9.6, 56.8, 11.0, 57.3),      # the Limfjord to Aalborg
                       (3.4, 51.6, 4.3, 52.2),       # Rotterdam
                       (101.0, 1.0, 104.2, 3.2)],    # Singapore, the Strait
        "plants": [(14.0, 47.0, "Bio-methanol plant", "Europe region · 1,000 nm to every port",
                    ["methanol_bio"])],
        "delivery": [[(14.0, 47.0), (9.97, 53.55)], [(14.0, 47.0), (4.05, 51.95)]],
        "notes": [((62.0, 22.0), "about 8,300 nm each way", "laden west, nearly empty east",
                   C_ROUTE, "600"),
                  ((-34.0, 63.0), "feeders: Rotterdam, Hamburg, Aalborg", "270, 400 and 800 nm legs",
                   C_FEEDER, "600"),
                  ((52.0, 44.0), "EU ETS and FuelEU: Rotterdam, Hamburg, Aalborg",
                   "CII and a net-zero framework: all four ports", C_SUB, "400")],
        "legend": [("port", "bunker port"), ("plant", "bio-methanol plant", "methanol_bio"),
                   ("line", C_ROUTE, "mainline, 15,000 TEU"), ("line", C_FEEDER, "feeders, 1,500 TEU"),
                   ("dash", "fuel delivery")],
    },
    "south_pacific": {
        "window": (138.0, 196.0, -48.0, -6.0),
        "aria": "Map of example 2: Handysize bulk carriers on regional trips between "
                "Australia, New Zealand, Fiji, Samoa and Tonga, with FAME from Europe "
                "bunkered in Australia and New Zealand only",
        "ports": [(153.1, -27.4, "Australia", "fuel oil · FAME"),
                  (174.8, -36.8, "New Zealand", "fuel oil · FAME"),
                  (178.4, -18.1, "Fiji", "fuel oil only"),
                  (-171.8, -13.8, "Samoa", "fuel oil only"),
                  (-175.2, -21.1, "Tonga", "fuel oil only")],
        "routes": [
            ("pacific_trade", C_ROUTE, 2.6, [
                (153.1, -27.4), (156.0, -31.0), (163.0, -35.0), (172.0, -35.2),
                (174.8, -36.8), (178.0, -34.0), (-176.0, -27.0), (-175.2, -21.1),
                (-172.5, -16.5), (-171.8, -13.8), (-174.5, -15.0), (179.6, -17.0),
                (178.4, -18.1), (172.0, -20.0), (168.5, -23.8), (162.0, -25.0), (155.5, -26.5),
                (153.1, -27.4)],
             [1, 11]),
        ],
        "sea_exempt": [(152.5, -28.0, 154.2, -26.8), (174.0, -37.4, 175.4, -36.0),
                       (177.6, -18.8, 179.9, -17.4), (-180.0, -18.8, -179.0, -17.4),
                       (-172.6, -14.4, -171.2, -13.4), (-175.8, -21.6, -174.6, -20.6)],
        "plants": [],
        "delivery": [[(140.0, -40.0), (151.5, -30.5), (153.1, -27.4)],
                     [(140.0, -40.0), (160.0, -42.5), (174.8, -36.8)]],
        "notes": [((141.0, -44.5), "FAME made in Europe", "11,000 nm to Australia, 12,200 to New Zealand",
                   C_SUB, "600"),
                  ((160.0, -11.0), "regional trips between the five ports",
                   "no fixed order: 36 port calls shared between them", C_ROUTE, "600"),
                  ((160.0, -45.0), "CII and a net-zero framework at every port",
                   "no EU policy", C_SUB, "400")],
        "legend": [("port", "bunker port"), ("line", C_ROUTE, "Handysize bulk carriers"),
                   ("dash", "FAME delivery from Europe")],
    },
    "baltic": {
        "window": (9.0, 33.0, 52.6, 62.4),
        "aria": "Map of example 3: two groups of owners with the same product tankers, "
                "mid-range tankers between Helsinki, Stockholm and Gdansk, coastal "
                "tankers between Helsinki, Tallinn and Stockholm, and a European "
                "e-ammonia plant delivering to Helsinki and Stockholm",
        "ports": [(24.95, 60.16, "Helsinki", "fuel oil · e-ammonia"),
                  (18.07, 59.33, "Stockholm", "fuel oil · e-ammonia"),
                  (24.75, 59.44, "Tallinn", "fuel oil only"),
                  (18.65, 54.40, "Gdansk", "fuel oil only")],
        "routes": [
            ("mid_range_route", C_ROUTE, 2.6, [
                (24.95, 60.16), (22.5, 59.7), (20.5, 59.3), (19.2, 59.2), (18.07, 59.33),
                (18.9, 58.6), (19.6, 57.0), (19.4, 55.5), (18.65, 54.40),
                (19.6, 55.2), (20.6, 57.0), (21.3, 58.6), (22.8, 59.5), (24.95, 60.16)],
             [3, 7]),
            ("coastal_route", C_FEEDER, 2.0, [
                (24.75, 59.44), (24.85, 59.8), (24.95, 60.16), (24.4, 59.82), (23.0, 59.62), (20.8, 59.58),
                (19.3, 59.45), (18.07, 59.33), (19.5, 59.1), (21.5, 59.25), (23.3, 59.35),
                (24.75, 59.44)],
             [8]),
        ],
        "sea_exempt": [(17.8, 58.9, 19.6, 59.6),     # Stockholm and its archipelago
                       (18.3, 54.2, 19.0, 54.7),     # Gdansk
                       (24.2, 59.3, 25.2, 60.3)],    # Tallinn and Helsinki
        "plants": [(13.5, 56.6, "E-ammonia plant", "Europe region · 1,000 nm to every port",
                    ["ammonia_electro"])],
        "delivery": [[(13.5, 56.6), (15.5, 58.6), (18.07, 59.33)],
                     [(13.5, 56.6), (17.5, 57.5), (21.0, 58.6), (24.95, 60.16)]],
        "notes": [((10.0, 61.8), "two groups of owners, the same ships",
                   "one fits eight efficiency measures, one none", C_SUB, "600"),
                  ((26.5, 56.5), "EU ETS, FuelEU, CII and a",
                   "net-zero framework at every port", C_SUB, "400")],
        "legend": [("port", "bunker port"), ("plant", "e-ammonia plant", "ammonia_electro"),
                   ("line", C_ROUTE, "mid-range tankers, 47,000 DWT"),
                   ("line", C_FEEDER, "coastal tankers, 7,500 DWT"),
                   ("dash", "fuel delivery")],
    },
}


def run(name):
    case = CASES[name]
    lon0, lon1, lat0, lat1 = case["window"]
    W = 940.0
    sx = W / (lon1 - lon0)
    sy = sx / math.cos(math.radians((lat0 + lat1) / 2.0))
    H = round((lat1 - lat0) * sy)

    def east(lon):
        return lon0 + (lon - lon0) % 360.0

    def xy(lon, lat):
        return (east(lon) - lon0) * sx, (lat1 - lat) * sy

    g.xy, g.W, g.H = xy, W, H

    here = pathlib.Path(__file__).parent
    gj = json.loads((here / "ne_110m_countries.geojson").read_text(encoding="utf-8"))
    rings = g.rings_of(gj)

    # land in the window's own longitudes, so a route can cross 180: each ring
    # moves by a whole turn, whichever puts it in the window
    def shifted(ring):
        lons = [p[0] for p in ring]
        for d in (0.0, 360.0, -360.0):
            if min(lons) + d <= lon1 and max(lons) + d >= lon0:
                return [(lo + d, la) for lo, la in ring]
        return ring

    rings = [shifted(r) for r in rings]
    on_land = g.make_land_test(rings)
    exempt = [(east(x0), y0, east(x0) + (x1 - x0), y1) for x0, y0, x1, y1 in case["sea_exempt"]]
    for rname, _, _, pts, _ in case["routes"]:
        bad = g.verify_route([(east(lo), la) for lo, la in pts], on_land, exempt)
        assert not bad, f"{rname} crosses land at {bad[:10]} ({len(bad)} points)"

    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:940px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="{case["aria"]}">')
    add('<defs>'
        + "".join(f'<marker id="{name}{k}" viewBox="0 0 10 10" refX="8.5" refY="5" '
                  f'markerWidth="5" markerHeight="5" orient="auto-start-reverse">'
                  f'<path d="M0 0 L10 5 L0 10 z" fill="{c}"/></marker>'
                  for k, c in enumerate([C_ROUTE, C_FEEDER, C_DELIV]))
        + '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')

    paths = []
    for ring in rings:
        pts = g.simplify(g.clip_rect([((lo - lon0) * sx, (lat1 - la) * sy) for lo, la in ring],
                                     0, 0, W, H), tol=0.6)
        if len(pts) >= 3:
            paths.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
    add(f'<path d="{"".join(paths)}" fill="{C_LAND}" stroke="{C_BORDER}" '
        f'stroke-width="0.8" stroke-linejoin="round" fill-rule="evenodd"/>')

    lay = g.Layout()

    def reserve_polyline(points, half=3.0, step=7.0):
        for a, b in zip(points, points[1:]):
            n = max(1, int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) / step))
            for k in range(n + 1):
                f = k / n
                cx, cy = a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])
                lay.reserve([cx - half, cy - half, cx + half, cy + half])

    legend_h = 22 + 17 * len(case["legend"])
    if case.get("legend_top"):
        legend_box = [W - 232, 8, W - 10, 8 + legend_h]
    else:
        legend_box = [W - 232, H - legend_h - 28, W - 10, H - 26]
    lay.reserve(legend_box)
    lay.reserve([W - 262, H - 22, W - 6, H - 4])

    def line(pts, colour, width, dash=None, marker=None):
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        extra = (f' stroke-dasharray="{dash}"' if dash else "") + (f' marker-end="url(#{marker})"' if marker else "")
        add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" '
            f'stroke-linecap="round" stroke-linejoin="round"{extra}/>')

    for pts in case["delivery"]:
        p = g.straighten_tail(g.trim_end([xy(*c) for c in pts], 10.0), 14.0)
        reserve_polyline(p, half=2.0)
        line(p, C_DELIV, 1.5, "7 5", f"{name}2")

    ships = []
    for k, (_, colour, width, pts, segs) in enumerate(case["routes"]):
        p = [xy(*c) for c in pts]
        reserve_polyline(p)
        line(p, colour, width)
        ships += [g.ship_on_route(pts, s, 1.5) for s in segs]
    for svg, box in ships:
        lay.reserve(box)
        add(svg)

    def txt(x, y, s, fs, anchor, fill, weight="400"):
        wt = f' font-weight="{weight}"' if weight != "400" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
                f'text-anchor="{anchor}"{wt}>{s}</text>')

    labels = []
    for lon, lat, *_ in case["ports"]:
        x, y = xy(lon, lat)
        lay.reserve([x - 7, y - 7, x + 7, y + 7])
    for lon, lat, pname, sub, fuels in case["plants"]:
        x, y = xy(lon, lat)
        lay.reserve([x - 11, y - 10, x + 11, y + 10])
        for f in fuels:
            add(g.factory(x, y, fuel_colour(f)))
        bx, by, anchor = lay.pair(x, y, pname, sub, 11.5, 9.5, AROUND)
        labels += [txt(bx, by, pname, 11.5, anchor, C_TEXT, "600"),
                   txt(bx, by + 11.5, sub, 9.5, anchor, C_SUB)]
    for lon, lat, pname, sub in case["ports"]:
        x, y = xy(lon, lat)
        bx, by, anchor = lay.pair(x, y, pname, sub, 12.5, 9.5, AROUND)
        labels += [txt(bx, by, pname, 12.5, anchor, C_TEXT, "600"),
                   txt(bx, by + 12, sub, 9.5, anchor, C_SUB)]
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{C_PORT}" stroke="#ffffff" stroke-width="1.5"/>')

    spread = [(dx, dy, "start") for dx, dy in
              [(0, 0), (0, -17), (0, 19), (0, -34), (0, 36), (30, 0), (-30, 0), (0, -52), (0, 54)]]
    for at, top, bot, colour, weight in case["notes"]:
        x, y = xy(*at)
        bx, by, anchor = lay.pair(x, y, top, bot, 11.5, 10, spread)
        labels += [txt(bx, by, top, 11.5, anchor, colour, weight),
                   txt(bx, by + 12.5, bot, 10, anchor, colour)]
    out.extend(labels)
    add(txt(W - 10, H - 8, "Basemap: Natural Earth 1:110m (public domain)", 8.5, "end", C_FAINT))

    lgx, lgy = legend_box[0] + 2, legend_box[1] + 2
    add(f'<rect x="{lgx}" y="{lgy}" width="216" height="{legend_h - 4}" rx="5" fill="#ffffff" '
        f'fill-opacity="0.9" stroke="#bebebe" stroke-width="0.8"/>')
    row = lgy + 19
    for item in case["legend"]:
        if item[0] == "port":
            add(f'<circle cx="{lgx + 17}" cy="{row - 3}" r="5" fill="{C_PORT}"/>')
        elif item[0] == "plant":
            add(g.factory(lgx + 17, row - 3, fuel_colour(item[2]), scale=0.85))
        elif item[0] == "line":
            add(f'<line x1="{lgx + 10}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
                f'stroke="{item[1]}" stroke-width="2.6"/>')
        else:
            add(f'<line x1="{lgx + 10}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
                f'stroke="{C_DELIV}" stroke-width="1.5" stroke-dasharray="5 3"/>')
        add(txt(lgx + 32, row, item[-1] if item[0] != "plant" else item[1], 10, "start", C_TEXT))
        row += 17
    add('</svg>')

    bs = lay.text_boxes
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            gap = max(max(a[0] - b[2], b[0] - a[2]), max(a[1] - b[3], b[1] - a[3]))
            assert gap > 0, f"text boxes {i} and {j} overlap"

    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n\n"
           "Basemap geometry derived from Natural Earth 1:110m Admin 0 countries,\n"
           "which is in the public domain (naturalearthdata.com).\n-->\n")
    dest = here.parent / "_static" / "examples" / f"{name}_map.svg"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(hdr + "\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {dest.name}: {W:.0f}x{H}, {len(bs)} labels")


if __name__ == "__main__":
    for n in sys.argv[1:] or list(CASES):
        run(n)
