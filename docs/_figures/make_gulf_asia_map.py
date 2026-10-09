"""Generate the Gulf-to-Asia tanker case map as a standalone SVG.

Run from anywhere:  python docs/_figures/make_gulf_asia_map.py

Writes docs/_static/gulf_asia_tanker_map.svg, the map for the workshop prompt
"One trade, two ports": a tanker trade from Ras Tanura to Ningbo with a bunker
port at each end and one Middle East e-fuel site. To rasterise it:

    python docs/_figures/make_gulf_asia_map.py                 # SVG
    python docs/_figures/render_map_png.py gulf_asia_tanker    # SVG -> PNG

Adapted from make_example_4_map.py, same palette, icons and checks.

Basemap: Natural Earth 1:110m Admin 0 countries (public domain), projected
equirectangular and clipped to the Indian Ocean / western Pacific window.

Two things are verified rather than eyeballed:

1. LABELS. Every box is measured with real font metrics (matplotlib's DejaVu
   Sans, slightly wider than the UI sans the SVG requests, so boxes are
   conservative), padded, and required to clear every other box by MIN_GAP.
   Two-line labels reserve the union of both lines. The script asserts that no
   two text boxes touch.

2. THE ROUTE. Every waypoint and a dense sample along every leg is tested
   against the country polygons with a ray-cast point-in-polygon check. The
   script asserts the voyage stays at sea, except in the narrow water listed in
   SEA_EXEMPT_BOXES.

The short leg from the plant to Ras Tanura is overland (the site is drawn
inland so its icons clear the port dot) and is the one leg exempt from the sea
test; see OVERLAND.
"""
import json
import math
import pathlib

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

# ----------------------------------------------------------------- projection
W, H = 940.0, 500.0
LON0, LON1 = 37.0, 133.0
LAT0, LAT1 = -12.0, 46.0
SX, SY = W / (LON1 - LON0), H / (LAT1 - LAT0)


def xy(lon, lat):
    return (lon - LON0) * SX, (LAT1 - lat) * SY


# --------------------------------------------------------------- case content
RAS_TANURA, NINGBO = (50.2, 26.6), (121.9, 29.9)
PORTS = [(*RAS_TANURA, "Ras Tanura", "Saudi Arabia \u00b7 bunker port"),
         (*NINGBO, "Ningbo", "China \u00b7 bunker port")]

# One icon per fuel produced at the site, coloured by fuel.
FUEL_COLOURS = {"e-methanol": "#457b7b",      # Green-5, as methanol_electro in the charts
                "e-ammonia": "#6fa59b"}       # Green-4, as ammonia_electro

# One site on the Saudi Gulf coast near Jubail. It is drawn about 300 km inland
# of Jubail, because at this scale Jubail is two pixels from Ras Tanura: the
# icon pair would sit on the port dot and the delivery leg to it would vanish.
# The icon pair sits at the origin of both delivery legs in DELIVERY below.
PLANT = (46.9, 27.3)
PLANTS = [(*PLANT, "Middle East e-fuels", "solar + wind \u2192 e-ammonia, e-methanol",
           ["e-methanol", "e-ammonia"])]

# Ras Tanura -> north of Qatar -> Strait of Hormuz -> Gulf of Oman -> Arabian
# Sea -> south of Sri Lanka -> north of Sumatra -> Strait of Malacca ->
# Singapore Strait -> South China Sea -> Taiwan Strait -> Ningbo. Waypoints
# are held offshore and mid-channel; the legs are sampled and tested against
# the land polygons in verify_route() below.
ROUTE = [RAS_TANURA, (51.2, 27.0), (52.6, 26.6), (54.4, 26.0), (55.6, 26.0),
         (56.3, 26.4), (56.8, 26.1), (57.4, 25.3), (58.8, 24.4), (60.4, 23.0),
         (61.8, 21.0), (66.0, 16.5), (72.0, 10.8), (77.0, 6.8), (80.6, 5.2),
         (84.5, 5.4), (90.0, 6.0), (94.8, 6.3), (97.0, 5.9), (98.6, 4.6),
         (100.2, 3.2), (101.6, 2.2), (102.8, 1.5), (103.8, 1.15), (104.6, 1.4),
         (106.0, 3.0), (108.0, 6.0), (110.0, 9.5), (111.6, 13.5),
         (113.8, 18.0), (116.6, 21.4), (118.9, 23.4), (120.2, 25.1),
         (121.3, 26.9), (122.3, 28.5), (122.4, 29.6), NINGBO]

# Places where a 1:110m basemap cannot resolve navigable water, so a sampled
# point legitimately lands on "land". These are exemptions for the *check*, not
# licence for the route to cut a corner. Only the two ports are exempt: they
# are on the coast by definition. The Strait of Hormuz, the Strait of Malacca,
# the Singapore Strait, the Sunda Strait and the Taiwan Strait all pass the
# check with mid-channel waypoints, though Malacca at 1:110m is only ~0.2
# degrees wide near 102E, so a waypoint moved there may need a box of its own.
SEA_EXEMPT_BOXES = [(49.7, 26.1, 50.7, 27.1),       # Ras Tanura
                    (121.3, 29.4, 122.3, 30.4)]     # Ningbo

# The plant-to-Ras-Tanura leg is an overland move (pipeline or truck) from the
# inland site; it is the one leg not tested for sea.
OVERLAND = {"gulf_local"}

# Fuel moves by ship to Ningbo, so that leg is verified against the land
# polygons exactly like the voyage. It is drawn on its own track, south of the
# voyage across the Indian Ocean and east of Taiwan, so the two do not merge.
DELIVERY = [
    ("gulf_local", [PLANT, (48.6, 27.1), RAS_TANURA]),
    # Plant -> Ningbo: north side of the Gulf and Hormuz, then south of the
    # voyage across the Indian Ocean, through the Sunda Strait and the Java
    # Sea, up the eastern South China Sea and east of Taiwan.
    ("gulf_far", [PLANT, (49.8, 27.7), (51.0, 27.6), (52.4, 27.0), (53.6, 26.6),
                  (54.8, 26.35), (55.8, 26.55), (56.3, 26.75), (56.9, 26.45),
                  (57.6, 25.6), (58.4, 25.0), (59.8, 24.3), (61.4, 22.6),
                  (64.0, 17.0), (69.0, 9.0), (76.0, 3.5), (84.0, 1.0),
                  (92.0, -1.5), (98.0, -4.0), (102.0, -6.0), (104.4, -6.6),
                  (105.5, -6.15), (105.95, -5.85), (106.6, -5.0), (108.0, -3.2),
                  (108.6, -1.5), (108.6, 0.5), (109.6, 4.0), (113.0, 10.0),
                  (117.0, 15.5), (120.0, 19.8), (122.2, 21.6), (123.4, 24.2),
                  (124.0, 27.0), (123.6, 29.6), (122.8, 30.3), NINGBO]),
]

C_OCEAN, C_LAND, C_BORDER = "#eaf6fb", "#dcdcdc", "#ffffff"
C_ROUTE, C_PORT = "#b55f2e", "#3d5f87"
C_DELIV = "#8c8c8c"           # fuel delivery: neutral, so colour means fuel
C_TEXT, C_SUB = "#323232", "#585858"

FACTORY = "M2 13H14V6H11V1H9V6H6V3H4V6H2Z"   # body with two chimneys, 12x12 box

# Side profile in a 16x14 box: hull, deckhouse, funnel. Drawn on the voyage line
# and rotated to the local heading, so it reads as sailing rather than parked.
SHIP = "M0 9H16L13.5 13.5H2.5ZM5 4.5H9V9H5ZM10.5 5.5H12V9H10.5Z"

# Which route segments carry a ship icon, as indices into ROUTE (segment i spans
# ROUTE[i] -> ROUTE[i+1]). Illustrative hulls in open water, clear of the
# straits; each icon's swept circle is reserved in the layout.
SHIP_SEGMENTS = [11, 15, 28]
SHIP_SCALE = 1.5

# How far short of the port each drawn line stops, in px (see example_4).
TRIM = {"route": 11.0, "gulf_local": 9.0, "gulf_far": 22.0}
MIN_TAIL = {"route": 22.0, "gulf_local": 8.0, "gulf_far": 18.0}

# The Ningbo delivery leaves the inland site overland before reaching the Gulf
# coast; that first stretch is exempt from the sea test, the rest is not.
PLANT_EXEMPT = (46.4, 26.9, 50.0, 28.4)

# Legend in the bottom-left corner, over the Somali coast and open ocean: the
# top-left corner is where the Gulf and its labels are.
LEGEND_BOX = [10, H - 136, 222, H - 14]

# Where the solver starts looking for the two free-floating notes.
ROUTE_LABEL_AT = (86.0, 9.0)
NOTE_AT = (89.0, 15.5)

# Label candidates, in order of preference. Ras Tanura's goes south over Saudi
# Arabia (the port is too near the left edge for an end-anchored label), the
# plant's north over Iraq and Iran; Ningbo's sits inland of the port, since the
# East China Sea side runs off the window.
PORT_CANDS = [
    [(0, 26, "middle"), (-20, 24, "start"), (-40, 26, "start"), (10, 24, "start"),
     (0, 40, "middle"), (-30, 40, "start"), (10, 40, "start")],
    [(-13, 3, "end"), (-13, -15, "end"), (-13, 20, "end"), (0, -24, "middle"),
     (-30, 30, "end")],
]
PLANT_CANDS = [(0, -30, "middle"), (-30, -30, "start"), (-20, -30, "start"), (0, -24, "middle"), (-13, -15, "end"), (13, -15, "start"),
               (0, -40, "middle"), (-13, -30, "end"), (13, -30, "start"),
               (-13, 3, "end"), (-40, -15, "end")]

# ------------------------------------------------------------------- geometry
def _clip_edge(pts, inside, isect):
    out = []
    if not pts:
        return out
    prev = pts[-1]
    for cur in pts:
        if inside(cur):
            if not inside(prev):
                out.append(isect(prev, cur))
            out.append(cur)
        elif inside(prev):
            out.append(isect(prev, cur))
        prev = cur
    return out


def clip_rect(pts, x0, y0, x1, y1):
    def ix(p, q, x):
        t = (x - p[0]) / (q[0] - p[0])
        return (x, p[1] + t * (q[1] - p[1]))

    def iy(p, q, y):
        t = (y - p[1]) / (q[1] - p[1])
        return (p[0] + t * (q[0] - p[0]), y)

    pts = _clip_edge(pts, lambda p: p[0] >= x0, lambda p, q: ix(p, q, x0))
    pts = _clip_edge(pts, lambda p: p[0] <= x1, lambda p, q: ix(p, q, x1))
    pts = _clip_edge(pts, lambda p: p[1] >= y0, lambda p, q: iy(p, q, y0))
    pts = _clip_edge(pts, lambda p: p[1] <= y1, lambda p, q: iy(p, q, y1))
    return pts


def simplify(pts, tol=1.25):
    if not pts:
        return pts
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) >= tol:
            out.append(p)
    return out


def rings_of(geojson):
    """All exterior/interior rings as lon/lat point lists."""
    rings = []
    for feat in geojson["features"]:
        geom = feat["geometry"]
        if geom is None:
            continue
        polys = (geom["coordinates"] if geom["type"] == "MultiPolygon"
                 else [geom["coordinates"]])
        for poly in polys:
            for ring in poly:
                rings.append([(c[0], c[1]) for c in ring])
    return rings


def ring_bbox(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def in_ring(lon, lat, ring):
    """Ray-cast point-in-polygon."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            if lon < xi + (lat - yi) * (xj - xi) / (yj - yi):
                inside = not inside
        j = i
    return inside


def make_land_test(rings):
    boxed = [(ring_bbox(r), r) for r in rings if len(r) > 3]

    def on_land(lon, lat):
        for (x0, y0, x1, y1), ring in boxed:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and in_ring(lon, lat, ring):
                return True
        return False

    return on_land


def verify_route(route, on_land, exempt_boxes, step=0.3):
    """Sample every leg densely; report sampled points on land outside the
    exempt boxes."""
    def exempt(lon, lat):
        return any(x0 <= lon <= x1 and y0 <= lat <= y1
                   for x0, y0, x1, y1 in exempt_boxes)

    bad = []
    for (a, b) in zip(route, route[1:]):
        span = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        n = max(2, int(span / step))
        for k in range(n + 1):
            f = k / n
            lon = a[0] + f * (b[0] - a[0])
            lat = a[1] + f * (b[1] - a[1])
            if not exempt(lon, lat) and on_land(lon, lat):
                bad.append((round(lon, 2), round(lat, 2)))
    return bad


# ------------------------------------------------------------------- metrics
PAD_X, PAD_Y, MIN_GAP = 3.0, 2.0, 2.5
_W_CACHE = {}


def text_width(s, fs, weight):
    key = (s, fs, weight)
    if key not in _W_CACHE:
        fp = FontProperties(family="DejaVu Sans", weight=weight, size=fs)
        _W_CACHE[key] = TextPath((0, 0), s, prop=fp).get_extents().width
    return _W_CACHE[key]


def box_of(x, y, s, fs, anchor, weight):
    w = text_width(s, fs, weight)
    x0 = {"start": x, "middle": x - w / 2.0, "end": x - w}[anchor]
    return [x0 - PAD_X, y - fs * 0.95 - PAD_Y, x0 + w + PAD_X, y + fs * 0.32 + PAD_Y]


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


class Layout:
    """Reserved rectangles. Non-text zones block new labels but may sit under an
    existing one (the jurisdiction halo is a translucent circle, not type), so
    only text-vs-text overlap is an error."""

    def __init__(self):
        self.boxes = []
        self.text_boxes = []

    def free(self, b):
        if b[0] < 3 or b[2] > W - 3 or b[1] < 3 or b[3] > H - 3:
            return False
        g = MIN_GAP
        for o in self.boxes:
            if not (b[2] + g <= o[0] or b[0] - g >= o[2]
                    or b[3] + g <= o[1] or b[1] - g >= o[3]):
                return False
        return True

    def reserve(self, b, text=False):
        self.boxes.append(b)
        if text:
            self.text_boxes.append(b)

    def one(self, x, y, s, fs, anchor, weight, candidates):
        for dx, dy in candidates:
            b = box_of(x + dx, y + dy, s, fs, anchor, weight)
            if self.free(b):
                self.reserve(b, text=True)
                return x + dx, y + dy
        raise RuntimeError(f"no free position for {s!r}")

    def pair(self, x, y, top, bot, fs_t, fs_b, candidates):
        for dx, dy, anchor in candidates:
            b1 = box_of(x + dx, y + dy, top, fs_t, anchor, "bold")
            b2 = box_of(x + dx, y + dy + fs_b + 2.5, bot, fs_b, anchor, "normal")
            u = union(b1, b2)
            if self.free(u):
                self.reserve(u, text=True)
                return x + dx, y + dy, anchor
        raise RuntimeError(f"no free position for pair {top!r}")


def _seg_len(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def trim_end(pts, dist):
    """Same polyline, stopping `dist` px short of its own end.

    An arrowhead is placed at the path end, so a line that ends exactly on a
    port marker puts its head under the dot. Trimming gives the head clear
    water and lets several lines arriving at one port keep their heads apart.
    """
    out = list(pts)
    left = dist
    while len(out) >= 2:
        a, b = out[-2], out[-1]
        seg = _seg_len(a, b)
        if seg > left:
            f = (seg - left) / seg
            out[-1] = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
            return out
        left -= seg
        out.pop()
    return out


def straighten_tail(pts, min_len):
    """Guarantee a straight final segment of at least `min_len` px.

    The Channel approach is a cluster of waypoints a few px apart, shorter than
    the arrowhead itself, so the head ends up spanning a bend and looks broken
    off. This replaces that cluster with one straight run into the endpoint.
    """
    if len(pts) < 2 or _seg_len(pts[-2], pts[-1]) >= min_len:
        return pts
    end = pts[-1]
    acc, i = 0.0, len(pts) - 1
    while i > 0:
        acc += _seg_len(pts[i - 1], pts[i])
        i -= 1
        if acc >= min_len:
            break
    a = pts[i]
    seg = _seg_len(a, end)
    if seg == 0:
        return pts
    f = min_len / seg
    start = (end[0] - f * (end[0] - a[0]), end[1] - f * (end[1] - a[1]))
    return pts[:i + 1] + [start, end]


def marker_tip(pts, marker_width, stroke_width, view_w=10.0, ref_x=8.5):
    """Where the arrow tip actually lands, in px, given markerUnits=strokeWidth."""
    length = marker_width * stroke_width
    over = (view_w - ref_x) / view_w * length
    a, b = pts[-2], pts[-1]
    seg = _seg_len(a, b)
    ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
    return (b[0] + over * ux, b[1] + over * uy), length


def ship_on_route(route, seg, scale=1.8):
    """Ship glyph at the midpoint of a route segment, turned to its heading.

    Returns (svg, box) so the caller can reserve the box before the labels are
    placed; otherwise a label lands on top of the icon.
    """
    (x0, y0), (x1, y1) = xy(*route[seg]), xy(*route[seg + 1])
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
    w, h = 16.0 * scale, 14.0 * scale
    svg = (f'<g transform="translate({cx:.1f} {cy:.1f}) rotate({angle:.1f}) '
           f'translate({-w / 2:.1f} {-h / 2:.1f}) scale({scale})">'
           f'<path d="{SHIP}" fill="{C_TEXT}" stroke="#ffffff" stroke-width="1.4" '
           f'stroke-linejoin="round"/></g>')
    r = max(w, h) / 2.0 + 2.0          # rotation-proof: reserve the swept circle
    return svg, [cx - r, cy - r, cx + r, cy + r]


def factory(cx, cy, colour, scale=0.92):
    return (f'<g transform="translate({cx - 8 * scale:.1f} {cy - 7 * scale:.1f}) '
            f'scale({scale})"><path d="{FACTORY}" fill="{colour}" stroke="#ffffff" '
            f'stroke-width="1.3" stroke-linejoin="round"/></g>')


def main():
    here = pathlib.Path(__file__).parent
    gj = json.loads((here / "ne_110m_countries.geojson").read_text(encoding="utf-8"))
    rings = rings_of(gj)
    on_land = make_land_test(rings)

    # ---- verify the voyage stays at sea before drawing anything ----------
    bad = verify_route(ROUTE, on_land, SEA_EXEMPT_BOXES)
    assert not bad, f"voyage crosses land at {bad[:12]} ({len(bad)} sampled points)"

    delivery_bad = {}
    for name, pts in DELIVERY:
        if name in OVERLAND:
            continue
        b = verify_route(pts, on_land, SEA_EXEMPT_BOXES + [PLANT_EXEMPT])
        if b:
            delivery_bad[name] = b
    assert not delivery_bad, f"delivery legs cross land: {delivery_bad}"

    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:940px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="Map of a tanker trade from Ras Tanura in Saudi Arabia to '
        f'Ningbo in China: two bunker ports, ships on the voyage via the Strait of '
        f'Hormuz, the Strait of Malacca and the Taiwan Strait, and one e-fuel '
        f'production site on the Saudi Gulf coast">')
    add('<defs>'
        f'<marker id="gaarw" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_ROUTE}"/></marker>'
        f'<marker id="gasup" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="4.5" '
        f'markerHeight="4.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_DELIV}"/></marker>'
        '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')

    for lon in range(60, int(LON1) + 1, 30):
        x, _ = xy(lon, 0)
        add(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H:.0f}" stroke="#d5effb" stroke-width="0.6"/>')
    for lat in range(30, int(LAT1) + 1, 30):
        _, y = xy(0, lat)
        add(f'<line x1="0" y1="{y:.0f}" x2="{W:.0f}" y2="{y:.0f}" stroke="#d5effb" stroke-width="0.6"/>')

    paths = []
    for ring in rings:
        pts = simplify(clip_rect([xy(*p) for p in ring], 0, 0, W, H))
        if len(pts) >= 3:
            paths.append("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + "Z")
    add(f'<path d="{"".join(paths)}" fill="{C_LAND}" stroke="{C_BORDER}" '
        f'stroke-width="0.7" stroke-linejoin="round" fill-rule="evenodd"/>')

    _, yeq = xy(0, 0)
    add(f'<line x1="0" y1="{yeq:.0f}" x2="{W:.0f}" y2="{yeq:.0f}" stroke="#a9d7ec" '
        f'stroke-width="0.9" stroke-dasharray="5 4"/>')

    lay = Layout()
    lay.reserve(LEGEND_BOX)                                # legend
    lay.reserve([W - 252, H - 22, W - 6, H - 4])          # attribution

    # Reserve a thin corridor along the drawn lines so no label is printed on
    # top of one.
    def reserve_polyline(points, half=4.0, step=7.0):
        for a, b in zip(points, points[1:]):
            seg = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
            n = max(1, int(seg / step))
            for k in range(n + 1):
                f = k / n
                cx = a[0] + f * (b[0] - a[0])
                cy = a[1] + f * (b[1] - a[1])
                lay.reserve([cx - half, cy - half, cx + half, cy + half])

    reserve_polyline([xy(*c) for c in ROUTE])

    ships = [ship_on_route(ROUTE, seg, SHIP_SCALE) for seg in SHIP_SEGMENTS]
    for _, ship_box in ships:
        lay.reserve(ship_box)
    for name, pts in DELIVERY:
        reserve_polyline([xy(*c) for c in pts], half=2.0 if name.endswith("far") else 3.0)

    rp = straighten_tail(trim_end([xy(*c) for c in ROUTE], TRIM["route"]),
                         MIN_TAIL["route"])
    add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in rp)}" fill="none" '
        f'stroke="{C_ROUTE}" stroke-width="2.8" stroke-linecap="round" '
        f'stroke-linejoin="round" marker-end="url(#gaarw)"/>')
    tips = {"route": marker_tip(rp, 5.5, 2.8)}

    for name, pts in DELIVERY:
        far = name.endswith("far")
        sw = 1.5 if far else 1.8
        dp = straighten_tail(trim_end([xy(*c) for c in pts], TRIM[name]),
                             MIN_TAIL[name])
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in dp)
        add(f'<path d="{d}" fill="none" stroke="{C_DELIV}" '
            f'stroke-width="{sw}" '
            f'stroke-dasharray="{"7 5" if far else "3.5 2.5"}" '
            f'opacity="{0.8 if far else 1.0}" marker-end="url(#gasup)"/>')
        tips[name] = marker_tip(dp, 4.5, sw)

    for ship_svg, _ in ships:
        add(ship_svg)

    def txt(x, y, s, fs, anchor, fill, weight="400"):
        wt = f' font-weight="{weight}"' if weight != "400" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
                f'text-anchor="{anchor}"{wt}>{s}</text>')

    labels = []

    # The port dots and the plant icons are reserved before any label, so
    # neither label can land on the other's marker.
    for lon, lat, _, _ in PORTS:
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
            add(factory(x - span / 2 + k * 13.0, y, FUEL_COLOURS[fuel]))
        cands = [(dx + (span / 2 if dx > 0 else -span / 2 if dx < 0 else 0), dy, a)
                 for dx, dy, a in PLANT_CANDS]
        bx, by, anchor = lay.pair(x, y, name, sub, 11.5, 9.5, cands)
        labels.append(txt(bx, by, name, 11.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 11.5, sub, 9.5, anchor, C_SUB))

    for (lon, lat, name, sub), cands in zip(PORTS, PORT_CANDS):
        x, y = xy(lon, lat)
        bx, by, anchor = lay.pair(x, y, name, sub, 12.5, 9.5, cands)
        labels.append(txt(bx, by, name, 12.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 12, sub, 9.5, anchor, C_SUB))
        add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5.2" fill="{C_PORT}" '
            f'stroke="#ffffff" stroke-width="1.6"/>')

    SPREAD = [(0, 0), (0, -17), (0, 19), (0, -34), (0, 36), (36, 0), (-36, 0),
              (0, -52), (0, 54), (64, 10), (-64, 10), (0, -70), (0, 72),
              (-40, -34), (40, -34), (-40, 36), (40, 36), (0, -88), (0, 90),
              (-90, 0), (90, 0), (-70, -50), (70, -50), (-70, 50), (70, 50)]
    ann = [
        (xy(*ROUTE_LABEL_AT), "about 5,900 nm each way · laden out, ballast home",
         11.5, "middle", C_ROUTE, "600"),
        # Where example_4 shows its EU ETS badge: this trade has none.
        (xy(*NOTE_AT), "No regulation on this trade", 10, "middle", C_SUB, "400"),
    ]
    for (x, y), s, fs, anchor, fill, weight in ann:
        lx, ly = lay.one(x, y, s, fs, anchor,
                         "bold" if weight == "600" else "normal", SPREAD)
        labels.append(txt(lx, ly, s, fs, anchor, fill, weight))

    out.extend(labels)

    add(txt(W - 10, H - 8, "Basemap: Natural Earth 1:110m (public domain)", 8.5, "end", "#a5a5a5"))

    lgx, lgy = LEGEND_BOX[0] + 2, LEGEND_BOX[1] + 2
    add(f'<rect x="{lgx}" y="{lgy}" width="206" height="117" rx="5" fill="#ffffff" '
        f'fill-opacity="0.90" stroke="#bebebe" stroke-width="0.8"/>')
    row = lgy + 19
    add(f'<circle cx="{lgx + 17}" cy="{row - 3}" r="5.2" fill="{C_PORT}"/>')
    add(txt(lgx + 32, row, "bunker port", 10, "start", C_TEXT))
    row += 18
    add(txt(lgx + 10, row, "fuel plant, by fuel made:", 9.5, "start", C_SUB))
    for fuel, colour in FUEL_COLOURS.items():
        row += 17
        add(factory(lgx + 17, row - 3, colour, scale=0.85))
        add(txt(lgx + 32, row, fuel, 10, "start", C_TEXT))
    row += 19
    add(f'<line x1="{lgx + 11}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_ROUTE}" stroke-width="2.8"/>')
    add(txt(lgx + 32, row, "the voyage", 10, "start", C_TEXT))
    row += 15
    add(f'<line x1="{lgx + 11}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_DELIV}" stroke-width="1.8" stroke-dasharray="3.5 2.5"/>')
    add(txt(lgx + 32, row, "fuel delivery", 10, "start", C_TEXT))

    add('</svg>')
    svg = "\n".join(out)

    # ---- verify the arrowheads: clear of the port dots, clear of each other --
    PORT_PX = {"ras_tanura": xy(*RAS_TANURA), "ningbo": xy(*NINGBO)}
    TARGET = {"route": "ningbo", "gulf_local": "ras_tanura", "gulf_far": "ningbo"}
    DOT_R = 5.2 + 1.6 / 2 + 1.0
    print("arrowheads:")
    for name, ((tx, ty), length) in tips.items():
        px_, py_ = PORT_PX[TARGET[name]]
        gap = math.hypot(tx - px_, ty - py_)
        assert gap >= DOT_R, f"{name} tip sits on the {TARGET[name]} dot ({gap:.1f} px)"
        print(f"  {name:14} tip {gap:5.1f} px from the port dot, head {length:4.1f} px long")
    names = list(tips)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if TARGET[names[i]] != TARGET[names[j]]:
                continue
            (ax, ay), _ = tips[names[i]]
            (bx, by), _ = tips[names[j]]
            sep = math.hypot(ax - bx, ay - by)
            assert sep >= 8.0, f"{names[i]} and {names[j]} heads overlap ({sep:.1f} px)"
            print(f"  {names[i]:14} vs {names[j]:14} heads {sep:5.1f} px apart")

    bs = lay.text_boxes
    worst = None
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, b = bs[i], bs[j]
            gap = max(max(a[0] - b[2], b[0] - a[2]), max(a[1] - b[3], b[1] - a[3]))
            if worst is None or gap < worst[0]:
                worst = (gap, i, j)
            assert gap > 0, f"text boxes {i} and {j} overlap by {-gap:.1f} px"

    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n\n"
           "Basemap geometry derived from Natural Earth 1:110m Admin 0 countries,\n"
           "which is in the public domain (naturalearthdata.com).\n-->\n")
    out_svg = here.parent / "_static" / "gulf_asia_tanker_map.svg"
    out_svg.write_text(hdr + svg + "\n", encoding="utf-8")

    print(f"country rings      : {len(paths)}")
    print(f"route legs verified: {len(ROUTE) - 1}, sampled points on land: {len(bad)}")
    print(f"ship icons         : {len(ships)} at segments {SHIP_SEGMENTS}, scale {SHIP_SCALE}")
    print(f"text labels        : {len(bs)}")
    print(f"tightest text gap  : {worst[0]:.1f} px")
    print(f"svg size           : {len(svg) / 1024:.1f} KB")
    print(f"wrote              : {out_svg}")


if __name__ == "__main__":
    main()
