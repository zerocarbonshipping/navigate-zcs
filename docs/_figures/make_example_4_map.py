"""Generate the example_4 case map as a standalone SVG.

Run from anywhere:  python docs/_figures/make_example_4_map.py

Writes docs/_static/example_4_map.svg, which is the source of truth for the map
at the top of docs/workshop/02-vessel-case-study.ipynb. The notebook itself
carries a base64 PNG rather than this SVG, because Jupyter's and Colab's trust
models strip SVG from untrusted notebooks. To push a change all the way through:

    python docs/_figures/make_example_4_map.py     # SVG
    python docs/_figures/render_map_png.py         # SVG -> PNG (headless Chrome)
    python docs/_figures/map_to_notebook.py        # PNG -> notebook cell 2

Basemap: Natural Earth 1:110m Admin 0 countries (public domain), projected
equirectangular and clipped to the Atlantic window. The geojson sits next to
this script; it is public domain and kept in the repo so the map is
reproducible without a download.

Two things are verified rather than eyeballed, because the author cannot see the
render:

1. LABELS. Every box is measured with real font metrics (matplotlib's DejaVu
   Sans, slightly wider than the UI sans the SVG requests, so boxes are
   conservative), padded, and required to clear every other box by MIN_GAP.
   Two-line labels reserve the union of both lines. The script asserts that no
   two text boxes touch.

2. THE ROUTE. Every waypoint and a dense sample along every leg is tested
   against the country polygons with a ray-cast point-in-polygon check. The
   script asserts the voyage stays at sea, except at the Panama Canal, which is
   a canal.

Fuel-delivery legs are exempt from the sea test: those move fuel overland from
plant to quayside.
"""
import json
import math
import pathlib

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

# ----------------------------------------------------------------- projection
W, H = 940.0, 470.0
LON0, LON1 = -132.0, 42.0
LAT0, LAT1 = -60.0, 70.0
SX, SY = W / (LON1 - LON0), H / (LAT1 - LAT0)


def xy(lon, lat):
    return (lon - LON0) * SX, (LAT1 - lat) * SY


# --------------------------------------------------------------- case content
PORTS = [(-71.6, -33.6, "San Antonio", "Chile \u00b7 bunker port"),
         (4.5, 51.9, "Rotterdam", "EU \u00b7 bunker port")]

# One icon per fuel produced at the site, coloured by fuel.
FUEL_COLOURS = {"e-methanol": "#1f8a70",      # teal
                "e-ammonia": "#6b3f9e",       # purple
                "bio-methanol": "#4e7a24"}    # green

# Sites sit where the deck's logistics distances put them, and each icon is
# placed at the origin of its own delivery leg in DELIVERY below:
#   - Magallanes (Punta Arenas), the Chilean wind resource. 1,250 nm up the
#     coast to San Antonio, 7,600 nm to Rotterdam.
#   - Gothenburg, the Swedish site: biomass for bio-methanol, and wind for an
#     e-methanol and an e-ammonia plant of its own. 540 nm to Rotterdam.
# See bunker_logistics.inc. Do not move an icon without moving its delivery leg
# and re-checking the distance it is labelled with.
PLANTS = [(-70.9, -53.2, "Chilean e-fuels", "Patagonia wind \u2192 e-fuels",
           ["e-methanol", "e-ammonia"]),
          (11.9, 57.7, "European fuels", "biomass + wind → three fuels",
           ["e-methanol", "e-ammonia", "bio-methanol"])]

# San Antonio -> Panama Canal -> east of the Antilles -> North Atlantic ->
# English Channel -> Rotterdam. Waypoints are held well offshore; the legs are
# sampled and tested against the land polygons in verify_route() below.
ROUTE = [(-71.6, -33.6), (-73.5, -31.0), (-77.0, -24.0), (-80.0, -16.0),
         (-82.5, -8.0), (-82.5, -2.0), (-81.0, 4.0), (-79.6, 9.0),
         (-77.5, 12.5), (-72.5, 15.2), (-68.0, 16.6), (-64.5, 17.2),
         (-61.5, 20.0), (-58.5, 24.0), (-52.0, 28.5), (-42.0, 34.0),
         (-32.0, 39.0), (-22.0, 44.0), (-13.0, 47.0), (-6.0, 49.0),
         (0.0, 50.4), (2.0, 51.2), (3.8, 51.9), (4.5, 51.9)]

# Places where a 1:110m basemap cannot resolve navigable water, so a sampled
# point legitimately lands on "land". These are exemptions for the *check*, not
# licence for the route to cut a corner.
#   - the Panama Canal is a canal
#   - the English Channel and the Dover Strait are narrower than the data
#   - the two ports are on the coast by definition
SEA_EXEMPT_BOXES = [(-81.0, 7.5, -78.0, 10.5),      # Panama Canal
                    (-5.5, 48.8, 5.5, 53.0),        # Channel, Dover Strait
                    (-72.5, -34.5, -70.5, -32.5),   # San Antonio
                    (3.5, 51.3, 5.5, 52.5),         # Rotterdam
                    (-76.0, -54.6, -67.5, -51.6),   # Strait of Magellan
                    (10.5, 56.8, 13.0, 58.6)]       # Gothenburg, Kattegat

# Fuel moves by ship, so the delivery legs follow the coast too. They are
# verified against the land polygons exactly like the voyage.
DELIVERY = [
    # Magallanes -> San Antonio, up the Chilean coast
    # out through the Strait of Magellan, then well offshore of the Patagonian
    # fjords - the inshore channels are real but far finer than this basemap
    ("chile_local", [(-70.9, -53.2), (-72.5, -53.6), (-74.8, -53.4), (-77.5, -52.0),
                     (-78.0, -48.0), (-77.0, -43.0), (-75.0, -38.0),
                     (-73.0, -34.5), (-71.6, -33.6)]),
    # Sweden -> Rotterdam, through the Kattegat and the North Sea
    ("europe_local", [(11.9, 57.7), (11.4, 58.2), (9.4, 57.9), (6.5, 57.0),
                      (4.6, 55.0), (3.9, 53.2), (4.1, 52.2), (4.5, 51.9)]),
    # Magallanes -> Rotterdam, the long way: out through the Strait of Magellan
    # and up the South Atlantic
    ("chile_far", [(-70.9, -53.2), (-69.5, -52.6), (-66.0, -51.0), (-60.0, -47.0),
                   (-52.0, -40.0), (-44.0, -31.0), (-36.0, -20.0), (-31.0, -8.0),
                   (-29.0, 4.0), (-28.0, 16.0), (-24.0, 28.0), (-18.0, 38.0),
                   (-12.0, 45.0), (-6.0, 49.0), (0.0, 50.4), (3.8, 51.9),
                   (4.5, 51.9)]),
]

C_OCEAN, C_LAND, C_BORDER = "#e7eef3", "#dcded8", "#ffffff"
C_ROUTE, C_PORT = "#b3731d", "#2f6f9f"
C_DELIV = "#7d8b97"           # fuel delivery: neutral, so colour means fuel
C_TEXT, C_SUB = "#17242e", "#5a6a75"

FACTORY = "M2 13H14V6H11V1H9V6H6V3H4V6H2Z"   # body with two chimneys, 12x12 box

# Side profile in a 16x14 box: hull, deckhouse, funnel. Drawn on the voyage line
# and rotated to the local heading, so it reads as sailing rather than parked.
SHIP = "M0 9H16L13.5 13.5H2.5ZM5 4.5H9V9H5ZM10.5 5.5H12V9H10.5Z"

# Which route segments carry a ship icon, as indices into ROUTE (segment i spans
# ROUTE[i] -> ROUTE[i+1]).
#
# The case is a fleet of 300 ships, not one, and a single icon made the map say
# otherwise. These are a handful of hulls spread along the leg - illustrative,
# not a count - so the picture reads as a line being worked continuously.
#
# Chosen for open water: clear of both coastlines, of the Panama Canal marker
# and its label, and of the Channel approach where the waypoints bunch up. Each
# icon's swept circle is reserved in the layout, so adding one here pushes the
# text labels around; if the label solver runs out of room it raises rather than
# overlapping, and the fix is to drop or move a segment.
SHIP_SEGMENTS = [2, 5, 10, 15, 18]

# Smaller than the 1.8 a lone icon used: five hulls at that size crowded the
# North Atlantic and fought with the "7,600 nm each way" label.
SHIP_SCALE = 1.5

# How far short of the port each drawn line stops, in px. The port dot is r=5.2
# with a 1.6 white stroke, so a tip needs ~7 px of clearance; the values also
# stagger the three heads that arrive at Rotterdam so they do not overlap.
TRIM = {"route": 11.0, "chile_local": 10.0, "europe_local": 17.0, "chile_far": 30.0}
MIN_TAIL = {"route": 26.0, "chile_local": 18.0, "europe_local": 18.0, "chile_far": 22.0}


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


POINT_CANDS = [(13, 3, "start"), (-13, 3, "end"), (13, -15, "start"),
               (-13, -15, "end"), (13, 20, "start"), (-13, 20, "end"),
               (0, -24, "middle"), (0, 34, "middle"),
               (46, 3, "start"), (-46, 3, "end"), (46, -30, "start"),
               (-46, -30, "end"), (0, -48, "middle"), (0, 56, "middle"),
               (74, 14, "start"), (-74, 14, "end")]


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
        b = verify_route(pts, on_land, SEA_EXEMPT_BOXES)
        if b:
            delivery_bad[name] = b
    assert not delivery_bad, f"delivery legs cross land: {delivery_bad}"

    out = []
    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:940px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="Map of the Chile to Rotterdam copper trade: two bunker ports, '
        f'a fleet of ships on the voyage via the Panama Canal, and the fuel '
        f'production sites in Chile and northern Europe">')
    add('<defs>'
        f'<marker id="m4arw" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_ROUTE}"/></marker>'
        f'<marker id="m4sup" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="4.5" '
        f'markerHeight="4.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_DELIV}"/></marker>'
        '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')

    for lon in range(-120, int(LON1) + 1, 30):
        x, _ = xy(lon, 0)
        add(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H:.0f}" stroke="#d3dde4" stroke-width="0.6"/>')
    for lat in range(-60, int(LAT1) + 1, 30):
        _, y = xy(0, lat)
        add(f'<line x1="0" y1="{y:.0f}" x2="{W:.0f}" y2="{y:.0f}" stroke="#d3dde4" stroke-width="0.6"/>')

    paths = []
    for ring in rings:
        pts = simplify(clip_rect([xy(*p) for p in ring], 0, 0, W, H))
        if len(pts) >= 3:
            paths.append("M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + "Z")
    add(f'<path d="{"".join(paths)}" fill="{C_LAND}" stroke="{C_BORDER}" '
        f'stroke-width="0.7" stroke-linejoin="round" fill-rule="evenodd"/>')

    _, yeq = xy(0, 0)
    add(f'<line x1="0" y1="{yeq:.0f}" x2="{W:.0f}" y2="{yeq:.0f}" stroke="#9db3c1" '
        f'stroke-width="0.9" stroke-dasharray="5 4"/>')

    lay = Layout()
    lay.reserve([10, 12, 222, 152])                       # legend
    lay.reserve([W - 262, H - 60, W - 6, H - 26])         # IMO note
    lay.reserve([W - 252, H - 22, W - 6, H - 4])          # attribution

    # Reserve a thin corridor along the drawn lines so no label is printed on
    # top of one. Labels *about* a line then sit beside it, which is what we
    # want; the generous candidate offsets give the solver room to do that.
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

    # The ship icons are drawn later, on top of the route, but their boxes have
    # to be reserved now so the label solver treats them as occupied space.
    ships = [ship_on_route(ROUTE, seg, SHIP_SCALE) for seg in SHIP_SEGMENTS]
    for _, ship_box in ships:
        lay.reserve(ship_box)
    for name, pts in DELIVERY:
        reserve_polyline([xy(*c) for c in pts], half=2.0 if name.endswith("far") else 3.0)

    ex, ey = xy(4.5, 51.9)
    add(f'<circle cx="{ex:.0f}" cy="{ey:.0f}" r="30" fill="{C_PORT}" fill-opacity="0.10" '
        f'stroke="{C_PORT}" stroke-width="1.1" stroke-dasharray="4 3"/>')

    rp = straighten_tail(trim_end([xy(*c) for c in ROUTE], TRIM["route"]),
                         MIN_TAIL["route"])
    add(f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in rp)}" fill="none" '
        f'stroke="{C_ROUTE}" stroke-width="2.8" stroke-linecap="round" '
        f'stroke-linejoin="round" marker-end="url(#m4arw)"/>')
    tips = {"route": marker_tip(rp, 5.5, 2.8)}

    # fuel delivery, all as coastal sea routes
    for name, pts in DELIVERY:
        far = name.endswith("far")
        sw = 1.5 if far else 1.8
        dp = straighten_tail(trim_end([xy(*c) for c in pts], TRIM[name]),
                             MIN_TAIL[name])
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in dp)
        add(f'<path d="{d}" fill="none" stroke="{C_DELIV}" '
            f'stroke-width="{sw}" '
            f'stroke-dasharray="{"7 5" if far else "3.5 2.5"}" '
            f'opacity="{0.8 if far else 1.0}" marker-end="url(#m4sup)"/>')
        tips[name] = marker_tip(dp, 4.5, sw)

    for ship_svg, _ in ships:
        add(ship_svg)

    px, py = xy(-79.6, 9.0)
    add(f'<circle cx="{px:.0f}" cy="{py:.0f}" r="3.4" fill="none" stroke="{C_ROUTE}" stroke-width="1.7"/>')

    def txt(x, y, s, fs, anchor, fill, weight="400"):
        wt = f' font-weight="{weight}"' if weight != "400" else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
                f'text-anchor="{anchor}"{wt}>{s}</text>')

    labels = []

    lx, ly = lay.one(px, py, "Panama Canal", 10, "end", "normal",
                     [(-9, -9), (-9, 17), (-9, -25), (17, -9), (17, 17), (-9, 32)])
    labels.append(txt(lx, ly, "Panama Canal", 10, "end", C_ROUTE))

    for lon, lat, name, sub in PORTS:
        x, y = xy(lon, lat)
        bx, by, anchor = lay.pair(x, y, name, sub, 12.5, 9.5, POINT_CANDS)
        labels.append(txt(bx, by, name, 12.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 12, sub, 9.5, anchor, C_SUB))
        add(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5.2" fill="{C_PORT}" '
            f'stroke="#ffffff" stroke-width="1.6"/>')

    for lon, lat, name, sub, fuels in PLANTS:
        x, y = xy(lon, lat)
        span = 13.0 * (len(fuels) - 1)
        for k, fuel in enumerate(fuels):
            add(factory(x - span / 2 + k * 13.0, y, FUEL_COLOURS[fuel]))
        lay.reserve([x - span / 2 - 10, y - 10, x + span / 2 + 10, y + 10])
        # Both sites are now near an edge of the window (Magallanes at the
        # bottom, Gothenburg at the top right), so the solver needs somewhere
        # to go besides the eight compass points: these push the label further
        # out over open water.
        extra = [(-13, 40, "end"), (13, 40, "start"), (0, 52, "middle"),
                 (-13, 62, "end"), (13, 62, "start"), (0, 76, "middle"),
                 (-96, 24, "end"), (96, 24, "start"),
                 (-70, 62, "end"), (70, 62, "start"),
                 (-96, -20, "end"), (96, -20, "start")]
        cands = [(dx + (span / 2 if dx > 0 else -span / 2), dy, a)
                 for dx, dy, a in POINT_CANDS + extra]
        bx, by, anchor = lay.pair(x, y, name, sub, 11.5, 9.5, cands)
        labels.append(txt(bx, by, name, 11.5, anchor, C_TEXT, "600"))
        labels.append(txt(bx, by + 11.5, sub, 9.5, anchor, C_SUB))

    lay.reserve([ex - 30, ey - 30, ex + 30, ey + 30])

    eux, euy, euanchor = lay.pair(
        ex, ey, "EU ETS + FuelEU", "50% of this voyage", 10, 9.5,
        [(0, -44, "middle"), (-48, -34, "end"), (48, -34, "start"),
         (-48, 48, "end"), (0, 64, "middle"), (48, 48, "start"),
         (-60, 8, "end"), (0, -64, "middle"), (60, 8, "start")])
    labels.append(txt(eux, euy, "EU ETS + FuelEU", 10, euanchor, C_PORT, "600"))
    labels.append(txt(eux, euy + 11.5, "50% of this voyage", 9.5, euanchor, C_PORT))

    SPREAD = [(0, 0), (0, -17), (0, 19), (0, -34), (0, 36), (36, 0), (-36, 0),
              (0, -52), (0, 54), (64, 10), (-64, 10), (0, -70), (0, 72),
              (-40, -34), (40, -34), (-40, 36), (40, 36), (0, -88), (0, 90),
              (-90, 0), (90, 0), (-70, -50), (70, -50), (-70, 50), (70, 50)]
    ann = [
        (xy(-46, 38), "7,600 nm each way", 11.5, "middle", C_ROUTE, "600"),
        (xy(-88, -44), "1,250 nm · +25 USD/t", 9.5, "start", C_DELIV, "400"),
        (xy(-30, -26), "7,600 nm · +152 USD/t to Rotterdam", 9.5, "middle", C_DELIV, "400"),
        (xy(18, 47), "540 nm · +11 USD/t", 9.5, "start", C_DELIV, "400"),
    ]
    for (x, y), s, fs, anchor, fill, weight in ann:
        lx, ly = lay.one(x, y, s, fs, anchor,
                         "bold" if weight == "600" else "normal", SPREAD)
        labels.append(txt(lx, ly, s, fs, anchor, fill, weight))

    out.extend(labels)

    # The IMO Net-Zero Framework and CII note that used to sit here is gone: the
    # deck carries only the EU ETS and FuelEU. Its reserved box above is kept on
    # purpose, so removing the text does not let the label solver reflow
    # everything else into the corner it used to occupy.
    add(txt(W - 10, H - 8, "Basemap: Natural Earth 1:110m (public domain)", 8.5, "end", "#9aa8b2"))

    lgx, lgy = 12, 14
    add(f'<rect x="{lgx}" y="{lgy}" width="206" height="134" rx="5" fill="#ffffff" '
        f'fill-opacity="0.90" stroke="#c3ccd3" stroke-width="0.8"/>')
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
    PORT_PX = {"san_antonio": xy(-71.6, -33.6), "rotterdam": xy(4.5, 51.9)}
    TARGET = {"route": "rotterdam", "chile_local": "san_antonio",
              "europe_local": "rotterdam", "chile_far": "rotterdam"}
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
    out_svg = here.parent / "_static" / "example_4_map.svg"
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
