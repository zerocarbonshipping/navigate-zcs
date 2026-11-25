# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Rasterise the demo's illustrations, images/*.svg, to images/*.png.

The SVGs set their text in Aktiv Grotesk, the Center's typeface, which must be
installed where this runs; build_notebook.py embeds the PNGs in the notebook.
Needs cairosvg:

    python demo/leadership/make_images.py
"""

from __future__ import annotations

from pathlib import Path

import cairosvg

IMAGES = Path(__file__).resolve().parent / "images"

for svg in sorted(IMAGES.glob("*.svg")):
    png = svg.with_suffix(".png")
    cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=1600)
    print(f"{svg.name} -> {png.name}, {png.stat().st_size // 1024} KB")
