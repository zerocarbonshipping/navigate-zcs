# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Rasterise a map SVG from docs/_static/ to a PNG with headless Chrome.

Run from anywhere:

    python docs/_figures/render_map_png.py                     # example_4
    python docs/_figures/render_map_png.py reference_scenario

Why a PNG at all: an uploaded notebook is untrusted, and Jupyter's trust model
strips SVG and HTML *outputs* of untrusted notebooks until the cell is run.
Colab does the same. Markdown images and PNGs are exempt, so a map travels in
the notebook as a base64 PNG in a markdown cell: nothing to run, nothing to
trust.

Rendered 1:1 with the SVG's own viewBox. A markdown image displays at its
natural size and the viewBox width is what the map's type sizes were designed
for, so it lays out identically in Colab, JupyterLab and the docs site. The
size is READ FROM THE FILE rather than hardcoded: the two maps are different
heights, and a wrong constant silently rescales or crops the raster.
"""

import argparse
import pathlib
import re
import struct
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
STATIC = HERE.parent / "_static"

# The maps this script knows about. The value is the shared stem: the SVG is
# docs/_static/<stem>.svg and the PNG is written to docs/_figures/<stem>.png.
MAPS = {
    "example_4": "example_4_map",
    "reference_scenario": "reference_scenario_map",
}

CHROME_CANDIDATES = [
    pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    pathlib.Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    pathlib.Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    pathlib.Path("/usr/bin/google-chrome"),
    pathlib.Path("/usr/bin/chromium"),
    pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def find_chrome():
    for p in CHROME_CANDIDATES:
        if p.exists():
            return p
    sys.exit("no Chrome/Chromium found; add its path to CHROME_CANDIDATES")


def viewbox_size(svg_text):
    """The SVG's own pixel size, so the raster cannot drift from its source."""
    match = re.search(r'viewBox="\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*"', svg_text)
    if not match:
        sys.exit("no 0-origin viewBox in the SVG; cannot size the raster")
    return int(round(float(match.group(1)))), int(round(float(match.group(2))))


def render(stem):
    """Rasterise docs/_static/<stem>.svg to docs/_figures/<stem>.png."""
    svg_path = STATIC / f"{stem}.svg"
    out = HERE / f"{stem}.png"
    if not svg_path.exists():
        sys.exit(f"no such SVG: {svg_path}")

    chrome = find_chrome()
    svg = svg_path.read_text(encoding="utf-8").strip()
    width, height = viewbox_size(svg)

    # The SVG asks for width="100%" and max-width in a style attribute, so the
    # wrapper has to override both. CSS beats a presentation attribute but not
    # an inline style, hence !important.
    wrapper = HERE / "_render_wrapper.html"
    wrapper.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "html,body{margin:0;padding:0;background:#e7eef3;overflow:hidden}"
        f"svg{{display:block;width:{width}px!important;height:{height}px!important;"
        "max-width:none!important}"
        "</style></head><body>" + svg + "</body></html>",
        encoding="utf-8")

    try:
        subprocess.run([str(chrome), "--headless", "--disable-gpu",
                        "--hide-scrollbars", f"--screenshot={out}",
                        f"--window-size={width},{height}",
                        "--force-device-scale-factor=1", wrapper.as_uri()],
                       check=True, capture_output=True)
    finally:
        wrapper.unlink(missing_ok=True)

    data = out.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    got = struct.unpack(">II", data[16:24])
    assert got == (width, height), f"unexpected raster size {got[0]}x{got[1]}"
    print(f"{svg_path.name} -> {out.name}: "
          f"{got[0]}x{got[1]} px, {len(data) / 1024:.0f} KB")
    print(f"wrote {out}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("map", nargs="?", default="example_4", choices=sorted(MAPS),
                        help="which map to rasterise (default: example_4)")
    args = parser.parse_args()
    render(MAPS[args.map])


if __name__ == "__main__":
    main()
