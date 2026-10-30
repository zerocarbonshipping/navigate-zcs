"""Generate the Rhine inland case map as a standalone SVG.

Run from anywhere:  python docs/_figures/make_rhine_map.py

Writes docs/_static/rhine_inland_map.svg, the map for the workshop prompt
"Inland waterways in Germany": Rhine motor cargo vessels from Duisburg up to
Mannheim, calling at Cologne, Koblenz and Mainz, with the new fuels bunkered at
the two ends only, and the European fuel production that supplies them. To rasterise it:

    python docs/_figures/make_rhine_map.py                 # SVG
    python docs/_figures/render_map_png.py rhine_inland    # SVG -> PNG

The geometry, label solver and checks are make_gulf_asia_map.py's, imported
from it. Two things differ:

- The projection scales longitude by cos(latitude) at the window's centre: at
  50 degrees north a plain equirectangular map stretches Germany sideways.
- The voyage is on a river, so there is no sea test. The Rhine is drawn from
  approximate coordinates of the towns on its banks (RHINE below); at 1:110m
  the basemap has no rivers.

The plants are drawn at one place in the west for legibility only: the deck's
plants are the library's Europe region, which has no location, and their
delivery legs carry the deck's INVENTED 400 nm.
"""
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_gulf_asia_map as g  # noqa: E402

# ----------------------------------------------------------------- projection
W, H = 940.0, 500.0
LAT0, LAT1 = 47.2, 53.6
SY = H / (LAT1 - LAT0)
SX = SY * math.cos(math.radians((LAT0 + LAT1) / 2.0))
LON0 = 9.0 - W / SX / 2.0      # centred on the Rhine
LON1 = LON0 + W / SX


def xy(lon, lat):
    return (lon - LON0) * SX, (LAT1 - lat) * SY


# The helpers in make_gulf_asia_map read its own projection and canvas size.
g.xy, g.W, g.H = xy, W, H

# --------------------------------------------------------------- case content
DUISBURG, MANNHEIM = (6.76, 51.43), (8.47, 49.49)
COLOGNE, KOBLENZ, MAINZ = (6.96, 50.94), (7.60, 50.36), (8.27, 50.00)
# (lon, lat, name, what it sells, sells every fuel)
PORTS = [(*DUISBURG, "Duisburg", "every fuel", True),
         (*COLOGNE, "Cologne", "fuel oil only", False),
         (*KOBLENZ, "Koblenz", "fuel oil only", False),
         (*MAINZ, "Mainz", "fuel oil only", False),
         (*MANNHEIM, "Mannheim", "every fuel", True)]

# Colours as in the charts: oil_bio, diesel_electro, methanol_electro.
FUEL_COLOURS = {"FAME": "#9f5959",
                "e-diesel": "#296565",
                "e-methanol": "#457b7b"}

PLANT = (3.4, 50.0)
PLANTS = [(*PLANT, "European fuel production",
           "Europe region · 400 nm to each end",
           list(FUEL_COLOURS))]

# The Rhine from Lake Constance to the North Sea, through the towns on its
# banks: Schaffhausen, Basel, Strasbourg, Karlsruhe, Speyer, Mannheim, Worms,
# Mainz, Bingen, Koblenz, Bonn, Cologne, Dusseldorf, Duisburg, Wesel, Emmerich,
# then the Waal past Nijmegen to Rotterdam.
RHINE = [(9.40, 47.62), (8.63, 47.70), (8.20, 47.60), (7.59, 47.56),
         (7.55, 47.95), (7.80, 48.58), (8.10, 48.85), (8.30, 49.03),
         (8.45, 49.32), MANNHEIM, (8.37, 49.63), (8.40, 49.85), (8.27, 50.00),
         (7.90, 49.97), (7.72, 50.14), (7.60, 50.36), (7.30, 50.55),
         (7.10, 50.73), (6.96, 50.94), (6.77, 51.23), DUISBURG, (6.62, 51.66),
         (6.25, 51.84), (5.85, 51.85), (5.20, 51.82), (4.40, 51.90),
         (4.00, 51.98)]

# The voyage is the Duisburg-Mannheim stretch, sailed upstream with a call at
# each port: the arrowhead is at Mannheim.
i0, i1 = RHINE.index(DUISBURG), RHINE.index(MANNHEIM)
ROUTE = RHINE[i0:i1 - 1:-1]

DELIVERY = [("to_duisburg", [PLANT, (4.6, 50.9), (5.8, 51.3), DUISBURG]),
            ("to_mannheim", [PLANT, (5.0, 50.1), (6.9, 49.8), (7.6, 49.38), MANNHEIM])]

C_OCEAN, C_LAND, C_BORDER = "#eaf6fb", "#dcdcdc", "#ffffff"
C_GERMANY = "#cfcfcf"
C_RIVER = "#97c8e4"
C_ROUTE, C_PORT = "#b55f2e", "#3d5f87"
C_DELIV = "#8c8c8c"
C_TEXT, C_SUB = "#323232", "#585858"

SHIP_SEGMENTS = [2, 6]     # Cologne-Bonn and Koblenz-Bingen
SHIP_SCALE = 1.2

TRIM = {"route": 10.0, "to_duisburg": 10.0, "to_mannheim": 10.0}
MIN_TAIL = {"route": 18.0, "to_duisburg": 16.0, "to_mannheim": 16.0}

LEGEND_BOX = [W - 222, H - 208, W - 10, H - 30]

ROUTE_LABEL_AT = (8.0, 50.5)
NOTE_AT = (11.6, 49.4)
GERMANY_AT = (10.6, 52.3)

PORT_CANDS = [
    [(13, 3, "start"), (13, -12, "start"), (13, 18, "start"), (0, -16, "middle")],
    [(13, 3, "start"), (13, 12, "start"), (13, -8, "start"), (-13, 3, "end"),
     (-13, 16, "end"), (-13, -10, "end"), (-20, 24, "end"), (20, 20, "start")],
    [(13, 3, "start"), (13, 12, "start"), (13, -8, "start"), (-13, 3, "end"),
     (-13, 16, "end"), (-13, -10, "end"), (-20, 24, "end"), (20, 20, "start")],
    [(13, -8, "start"), (13, 3, "start"), (13, -20, "start"), (-13, -8, "end"),
     (-13, -20, "end"), (16, 14, "start"), (24, -2, "start"), (24, 10, "start"),
     (30, -16, "start"), (-16, 18, "end"), (-24, 28, "end"), (0, -26, "middle")],
    [(13, 3, "start"), (13, 18, "start"), (13, -12, "start"), (0, 26, "middle")],
]
PLANT_CANDS = [(-44, 26, "start"), (-24, -30, "start"), (-24, 26, "start"), (0, -30, "middle"), (0, 26, "middle"),
               (13, -30, "start")]


def main():
    here = pathlib.Path(__file__).parent
    gj = json.loads((here / "ne_110m_countries.geojson").read_text(encoding="utf-8"))
    rings = g.rings_of(gj)
    germany = g.rings_of({"features": [f for f in gj["features"]
                                       if f["properties"].get("ADM0_A3") == "DEU"]})
    assert germany, "Germany not found in the basemap"

    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:940px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="Map of an inland trade on the Rhine in Germany from Duisburg '
        f'upstream to Mannheim, calling at Cologne, Koblenz and Mainz: every fuel at '
        f'Duisburg and Mannheim, fuel oil only at the three ports between, and '
        f'European fuel production delivering FAME, e-diesel and e-methanol to the two '
        f'ends">')
    add('<defs>'
        f'<marker id="rharw" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_ROUTE}"/></marker>'
        f'<marker id="rhsup" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="4.5" '
        f'markerHeight="4.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_DELIV}"/></marker>'
        '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')

    def land(rs, fill):
        paths = []
        for ring in rs:
            pts = g.simplify(g.clip_rect([xy(*p) for p in ring], 0, 0, W, H), tol=0.6)
            if len(pts) >= 3:
                paths.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z")
        add(f'<path d="{"".join(paths)}" fill="{fill}" stroke="{C_BORDER}" '
            f'stroke-width="1.0" stroke-linejoin="round" fill-rule="evenodd"/>')
        return len(paths)

    n_rings = land(rings, C_LAND)
    land(germany, C_GERMANY)

    river = [xy(*c) for c in RHINE]
    add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in river)}" fill="none" '
        f'stroke="{C_RIVER}" stroke-width="3.2" stroke-linecap="round" '
        f'stroke-linejoin="round"/>')

    lay = g.Layout()
    lay.reserve(LEGEND_BOX)
    lay.reserve([W - 252, H - 22, W - 6, H - 4])

    def reserve_polyline(points, half=4.0, step=7.0):
        for a, b in zip(points, points[1:]):
            seg = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            n = max(1, int(seg / step))
            for k in range(n + 1):
                f = k / n
                cx = a[0] + f * (b[0] - a[0])
                cy = a[1] + f * (b[1] - a[1])
                lay.reserve([cx - half, cy - half, cx + half, cy + half])

    reserve_polyline(river, half=3.0)
    ships = [g.ship_on_route(ROUTE, seg, SHIP_SCALE) for seg in SHIP_SEGMENTS]
    for _, ship_box in ships:
        lay.reserve(ship_box)
    for _, pts in DELIVERY:
        reserve_polyline([xy(*c) for c in pts], half=2.5)

    rp = g.straighten_tail(g.trim_end([xy(*c) for c in ROUTE], TRIM["route"]),
                           MIN_TAIL["route"])
    add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in rp)}" fill="none" '
        f'stroke="{C_ROUTE}" stroke-width="2.8" stroke-linecap="round" '
        f'stroke-linejoin="round" marker-end="url(#rharw)"/>')
    tips = {"route": g.marker_tip(rp, 5.5, 2.8)}

    for name, pts in DELIVERY:
        dp = g.straighten_tail(g.trim_end([xy(*c) for c in pts], TRIM[name]),
                               MIN_TAIL[name])
        add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in dp)}" fill="none" '
            f'stroke="{C_DELIV}" stroke-width="1.6" stroke-dasharray="7 5" '
            f'marker-end="url(#rhsup)"/>')
        tips[name] = g.marker_tip(dp, 4.5, 1.6)

    for ship_svg, _ in ships:
        add(ship_svg)

    def port_dot(x, y, full):
        if full:
            return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.2" fill="{C_PORT}" '
                    f'stroke="#ffffff" stroke-width="1.6"/>')
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#ffffff" '
                f'stroke="{C_PORT}" stroke-width="2.0"/>')

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

    for lon, lat, name, sub, fuels in PLANTS:
        x, y = xy(lon, lat)
        span = 13.0 * (len(fuels) - 1)
        for k, fuel in enumerate(fuels):
            add(g.factory(x - span / 2 + k * 13.0, y, FUEL_COLOURS[fuel]))
        bx, by, anchor = lay.pair(x, y, name, sub, 11.5, 9.5, PLANT_CANDS)
        labels.append(txt(bx, by, name, 11.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 11.5, sub, 9.5, anchor, C_SUB))

    for (lon, lat, name, sub, full), cands in zip(PORTS, PORT_CANDS):
        x, y = xy(lon, lat)
        bx, by, anchor = lay.pair(x, y, name, sub, 12.5, 9.5, cands)
        labels.append(txt(bx, by, name, 12.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 12, sub, 9.5, anchor, C_SUB))
        add(port_dot(x, y, full))

    SPREAD = [(0, 0), (0, -17), (0, 19), (0, -34), (0, 36), (36, 0), (-36, 0),
              (0, -52), (0, 54), (64, 10), (-64, 10), (0, -70), (0, 72)]
    lx, ly = lay.one(*xy(*GERMANY_AT), "GERMANY", 13, "middle", "bold", SPREAD)
    labels.append(txt(lx, ly, "GERMANY", 13, "middle", "#a5a5a5", "600"))

    # Two-line notes: the second line sits under the first, placed together.
    PAIR_SPREAD = [(dx, dy, "start") for dx, dy in SPREAD]
    notes = [(ROUTE_LABEL_AT, "193 nm upstream, five calls", "cargo off at each call, ballast down",
              C_ROUTE, "600"),
             (NOTE_AT, "No EU ETS or FuelEU on inland waterways",
              "the second deck adds a national CO2 price", C_SUB, "400")]
    for at, top, bot, fill, weight in notes:
        x, y = xy(*at)
        bx, by, anchor = lay.pair(x, y, top, bot, 11.5, 10, PAIR_SPREAD)
        labels.append(txt(bx, by, top, 11.5, anchor, fill, weight))
        labels.append(txt(bx, by + 12.5, bot, 10, anchor, fill))

    out.extend(labels)
    add(txt(W - 10, H - 8, "Basemap: Natural Earth 1:110m (public domain)", 8.5, "end", "#a5a5a5"))

    lgx, lgy = LEGEND_BOX[0] + 2, LEGEND_BOX[1] + 2
    add(f'<rect x="{lgx}" y="{lgy}" width="206" height="169" rx="5" fill="#ffffff" '
        f'fill-opacity="0.90" stroke="#bebebe" stroke-width="0.8"/>')
    row = lgy + 19
    add(port_dot(lgx + 17, row - 3, True))
    add(txt(lgx + 32, row, "port, every fuel", 10, "start", C_TEXT))
    row += 17
    add(port_dot(lgx + 17, row - 3, False))
    add(txt(lgx + 32, row, "port, fuel oil only", 10, "start", C_TEXT))
    row += 18
    add(txt(lgx + 10, row, "fuel plant, by fuel made:", 9.5, "start", C_SUB))
    for fuel, colour in FUEL_COLOURS.items():
        row += 17
        add(g.factory(lgx + 17, row - 3, colour, scale=0.85))
        add(txt(lgx + 32, row, fuel, 10, "start", C_TEXT))
    row += 19
    add(f'<line x1="{lgx + 11}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_ROUTE}" stroke-width="2.8"/>')
    add(txt(lgx + 32, row, "the voyage", 10, "start", C_TEXT))
    row += 15
    add(f'<line x1="{lgx + 11}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_RIVER}" stroke-width="3.2"/>')
    add(txt(lgx + 32, row, "the Rhine", 10, "start", C_TEXT))
    row += 15
    add(f'<line x1="{lgx + 11}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_DELIV}" stroke-width="1.6" stroke-dasharray="7 5"/>')
    add(txt(lgx + 32, row, "fuel delivery", 10, "start", C_TEXT))

    add('</svg>')
    svg = "\n".join(out)

    PORT_PX = {"duisburg": xy(*DUISBURG), "mannheim": xy(*MANNHEIM)}
    TARGET = {"route": "mannheim", "to_duisburg": "duisburg", "to_mannheim": "mannheim"}
    DOT_R = 5.2 + 1.6 / 2 + 1.0
    print("arrowheads:")
    for name, ((tx, ty), length) in tips.items():
        px_, py_ = PORT_PX[TARGET[name]]
        gap = math.hypot(tx - px_, ty - py_)
        assert gap >= DOT_R, f"{name} tip sits on the {TARGET[name]} dot ({gap:.1f} px)"
        print(f"  {name:12} tip {gap:5.1f} px from the port dot")
    (ax, ay), _ = tips["route"]
    (bx, by), _ = tips["to_mannheim"]
    assert math.hypot(ax - bx, ay - by) >= 8.0, "heads at Mannheim overlap"

    bs = lay.text_boxes
    worst = None
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            gap = max(max(a[0] - b[2], b[0] - a[2]), max(a[1] - b[3], b[1] - a[3]))
            if worst is None or gap < worst:
                worst = gap
            assert gap > 0, f"text boxes {i} and {j} overlap by {-gap:.1f} px"

    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n\n"
           "Basemap geometry derived from Natural Earth 1:110m Admin 0 countries,\n"
           "which is in the public domain (naturalearthdata.com).\n-->\n")
    out_svg = here.parent / "_static" / "rhine_inland_map.svg"
    out_svg.write_text(hdr + svg + "\n", encoding="utf-8")

    print(f"window             : {LON0:.1f}-{LON1:.1f} E, {LAT0}-{LAT1} N")
    print(f"country rings      : {n_rings}")
    print(f"text labels        : {len(bs)}, tightest gap {worst:.1f} px")
    print(f"wrote              : {out_svg.name}")


if __name__ == "__main__":
    main()
