# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Generate the "Two fleets, one market" schematic as a standalone SVG.

Run from anywhere:  python docs/_figures/make_two_fleets_schematic.py

Writes docs/_static/two_fleets_schematic.svg; rasterise it with

    python docs/_figures/render_map_png.py two_fleets

A schematic, not a map: there is no basemap, because the reader picks the two
ports. It borrows the workshop maps' palette, port dots, voyage line, ship icon
and legend box from make_example_4_map.py so it reads as one of the family.

Every text box is measured with real font metrics (DejaVu Sans, slightly wider
than the UI sans the SVG requests, so the boxes are conservative) and the
script asserts that no text box touches another text box or an icon.
"""
import pathlib

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

W, H = 940.0, 320.0

# The maps' palette.
C_OCEAN, C_GRID = "#eaf6fb", "#d5effb"
C_ROUTE, C_PORT = "#b55f2e", "#3d5f87"
C_TEXT, C_SUB = "#323232", "#585858"
C_FAINT = "#a5a5a5"
C_FLEET_A = "#4c4c4c"        # Black-6
C_FLEET_B = "#377070"        # Green-6

# The maps' ship glyph (16 x 14 box) and, for Fleet B, two rotor sails on deck.
SHIP = "M0 9H16L13.5 13.5H2.5ZM5 4.5H9V9H5ZM10.5 5.5H12V9H10.5Z"
ROTORS = "M1.6 2.5H3.4V9H1.6ZM13.0 2.5H14.8V9H13.0Z"
SHIP_SCALE = 1.9

PORT_Y = 150.0
PORTS = [(150.0, "[ORIGIN]", "bunker port", "end"),
         (790.0, "[DESTINATION]", "bunker port", "start")]

SHIP_X = [290.0, 370.0, 570.0, 650.0]   # a gap mid-route for its label
ROW_A_Y, ROW_B_Y = 110.0, 190.0      # ship centres, either side of the line

MEASURES = ["hull coating", "propeller devices", "Flettner rotors",
            "air lubrication"]

PAD_X, PAD_Y = 3.0, 2.0
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


def gap(a, b):
    return max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3])


class Layout:
    """Text boxes must clear each other and every icon; icons may abut."""

    def __init__(self):
        self.text, self.icons = [], []

    def icon(self, name, b):
        self.icons.append((name, b))

    def label(self, name, b):
        assert b[0] >= 3 and b[1] >= 3 and b[2] <= W - 3 and b[3] <= H - 3, \
            f"{name!r} is cut off: {b}"
        for other, o in self.text + self.icons:
            assert gap(b, o) > 0, f"{name!r} touches {other!r} by {-gap(b, o):.1f} px"
        self.text.append((name, b))


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fs, anchor, fill, weight="400"):
    wt = f' font-weight="{weight}"' if weight != "400" else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
            f'text-anchor="{anchor}"{wt}>{esc(s)}</text>')


def ship(cx, cy, colour, rotors=False, scale=SHIP_SCALE):
    w, h = 16.0 * scale, 14.0 * scale
    extra = (f'<path d="{ROTORS}" fill="{colour}" stroke="#ffffff" '
             f'stroke-width="1.2" stroke-linejoin="round"/>') if rotors else ""
    return (f'<g transform="translate({cx - w / 2:.1f} {cy - h / 2:.1f}) scale({scale})">'
            f'{extra}<path d="{SHIP}" fill="{colour}" stroke="#ffffff" '
            f'stroke-width="1.3" stroke-linejoin="round"/></g>',
            [cx - w / 2 - 1, cy - h / 2 - 1, cx + w / 2 + 1, cy + h / 2 + 1])


def main():
    here = pathlib.Path(__file__).parent
    lay = Layout()
    out = []
    add = out.append

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="100%" style="max-width:{W:.0f}px;height:auto;'
        f'font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif" role="img" '
        f'aria-label="Schematic of two fleets of the same vessel class sailing one '
        f'route between two bunker ports the reader chooses: Fleet A fits no '
        f'efficiency measure, Fleet B fits the efficiency technologies the library '
        f'offers, such as hull coating, propeller devices, Flettner rotors and air '
        f'lubrication">')
    add('<defs>'
        '<marker id="tfarw" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="5.5" '
        'markerHeight="5.5" orient="auto-start-reverse">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="{C_ROUTE}"/></marker>'
        '</defs>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="{C_OCEAN}"/>')
    for x in range(70, int(W), 160):
        add(f'<line x1="{x}" y1="0" x2="{x}" y2="{H:.0f}" stroke="{C_GRID}" stroke-width="0.6"/>')
    for y in range(30, int(H), 110):
        add(f'<line x1="0" y1="{y}" x2="{W:.0f}" y2="{y}" stroke="{C_GRID}" stroke-width="0.6"/>')

    # Legend, in the maps' box style.
    lgx, lgy, lgw, lgh = 12, 14, 170, 88
    lay.icon("legend", [lgx, lgy, lgx + lgw, lgy + lgh])
    add(f'<rect x="{lgx}" y="{lgy}" width="{lgw}" height="{lgh}" rx="5" fill="#ffffff" '
        f'fill-opacity="0.90" stroke="#bebebe" stroke-width="0.8"/>')
    row = lgy + 19
    add(f'<circle cx="{lgx + 17}" cy="{row - 3}" r="5.2" fill="{C_PORT}"/>')
    add(txt(lgx + 32, row, "bunker port", 10, "start", C_TEXT))
    row += 18
    add(f'<line x1="{lgx + 10}" y1="{row - 3}" x2="{lgx + 24}" y2="{row - 3}" '
        f'stroke="{C_ROUTE}" stroke-width="2.8"/>')
    add(txt(lgx + 32, row, "the voyage", 10, "start", C_TEXT))
    row += 18
    add(ship(lgx + 17, row - 4, C_FLEET_A, scale=1.2)[0])
    add(txt(lgx + 32, row, "ship of Fleet A", 10, "start", C_TEXT))
    row += 18
    add(ship(lgx + 17, row - 4, C_FLEET_B, rotors=True, scale=1.2)[0])
    add(txt(lgx + 32, row, "ship of Fleet B", 10, "start", C_TEXT))

    # The voyage: one straight line, both ways, trimmed clear of the port dots.
    (x0, _, _, _), (x1, _, _, _) = PORTS
    trim = 11.0
    add(f'<path d="M{x0 + trim:.1f} {PORT_Y:.1f}L{x1 - trim:.1f} {PORT_Y:.1f}" '
        f'fill="none" stroke="{C_ROUTE}" stroke-width="2.8" stroke-linecap="round" '
        f'marker-start="url(#tfarw)" marker-end="url(#tfarw)"/>')
    # Its label sits in a break in the line, in the gap between the ships, so
    # the line is reserved as two pieces either side of the break.
    s = "one route, both fleets"
    b = box_of(W / 2, PORT_Y + 4, s, 11.5, "middle", "bold")
    gx0, gx1 = b[0] + 4, b[2] - 4     # DejaVu boxes run wide of the UI sans
    add(f'<rect x="{gx0:.1f}" y="{PORT_Y - 4:.1f}" width="{gx1 - gx0:.1f}" height="8" '
        f'fill="{C_OCEAN}"/>')
    lay.icon("voyage west", [x0, PORT_Y - 5, b[0] - 0.5, PORT_Y + 5])
    lay.icon("voyage east", [b[2] + 0.5, PORT_Y - 5, x1, PORT_Y + 5])
    lay.label(s, b)
    add(txt(W / 2, PORT_Y + 4, s, 11.5, "middle", C_ROUTE, "600"))

    for x, name, sub, anchor in PORTS:
        lay.icon(f"dot {name}", [x - 6, PORT_Y - 6, x + 6, PORT_Y + 6])
        dx = -13 if anchor == "end" else 13
        b1 = box_of(x + dx, PORT_Y + 3, name, 12.5, anchor, "bold")
        b2 = box_of(x + dx, PORT_Y + 15, sub, 9.5, anchor, "normal")
        # A two-line label reserves the union of both lines, as on the maps.
        lay.label(name, [min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3]])
        add(txt(x + dx, PORT_Y + 3, name, 12.5, anchor, C_TEXT, "600"))
        add(txt(x + dx, PORT_Y + 15, sub, 9.5, anchor, C_SUB))
        add(f'<circle cx="{x:.0f}" cy="{PORT_Y:.0f}" r="5.2" fill="{C_PORT}" '
            f'stroke="#ffffff" stroke-width="1.6"/>')

    # Fleet A above the line, Fleet B below: same hulls, same positions.
    for i, x in enumerate(SHIP_X):
        svg, b = ship(x, ROW_A_Y, C_FLEET_A)
        lay.icon(f"ship A{i}", b)
        add(svg)
        svg, b = ship(x, ROW_B_Y, C_FLEET_B, rotors=True)
        lay.icon(f"ship B{i}", b)
        add(svg)

    s = "Fleet A · fits nothing"
    ya = ROW_A_Y - 24
    lay.label(s, box_of(W / 2, ya, s, 12.5, "middle", "bold"))
    add(txt(W / 2, ya, s, 12.5, "middle", C_FLEET_A, "600"))

    s = "Fleet B · fits efficiency measures"
    yb = ROW_B_Y + 34
    lay.label(s, box_of(W / 2, yb, s, 12.5, "middle", "bold"))
    add(txt(W / 2, yb, s, 12.5, "middle", C_FLEET_B, "600"))

    # The measures as pills, centred under the Fleet B label.
    fs, pad, sep, ph = 10, 8.0, 8.0, 18.0
    eg = "e.g."
    eg_w = text_width(eg, 9.5, "normal")
    widths = [text_width(m, fs, "normal") + 2 * pad for m in MEASURES]
    total = eg_w + 8.0 + sum(widths) + sep * (len(widths) - 1)
    px = W / 2 - total / 2
    py = yb + 14
    lay.label(eg, box_of(px, py + 13, eg, 9.5, "start", "normal"))
    add(txt(px, py + 13, eg, 9.5, "start", C_SUB))
    px += eg_w + 8.0 + PAD_X
    for m, w in zip(MEASURES, widths):
        add(f'<rect x="{px:.1f}" y="{py:.1f}" width="{w:.1f}" height="{ph:.0f}" rx="9" '
            f'fill="#ffffff" fill-opacity="0.9" stroke="{C_FLEET_B}" stroke-width="1"/>')
        lay.label(m, [px, py, px + w, py + ph])
        add(txt(px + w / 2, py + 12.8, m, fs, "middle", C_FLEET_B))
        px += w + sep

    s = ("same class, same costs, same route, same regulation – "
         "only the owners’ choices differ")
    lay.label(s, box_of(W / 2, H - 16, s, 10.5, "middle", "normal"))
    add(txt(W / 2, H - 16, s, 10.5, "middle", C_SUB))

    add('</svg>')
    svg = "\n".join(out)

    worst = min(gap(a, b) for i, (_, a) in enumerate(lay.text)
                for _, b in lay.text[i + 1:] + lay.icons)
    hdr = ("<!--\nSPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center "
           "for Zero Carbon Shipping\nSPDX-License-Identifier: CC-BY-4.0\n-->\n")
    out_svg = here.parent / "_static" / "two_fleets_schematic.svg"
    out_svg.write_text(hdr + svg + "\n", encoding="utf-8")
    print(f"text labels        : {len(lay.text)}")
    print(f"tightest text gap  : {worst:.1f} px")
    print(f"wrote              : {out_svg}")


if __name__ == "__main__":
    main()
