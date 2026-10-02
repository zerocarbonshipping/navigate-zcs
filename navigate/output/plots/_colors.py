# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Color palettes and per-series color assignment for the plots.

Holds the raw palettes (Center-brand scales, the shore-power accent, the
Matlab/Matplotlib default scheme) together with the logic that assigns a color
to each plotted entity: preferring the caller-supplied domain defaults, then the
generic scheme, then generated fallback colors.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping

    from matplotlib.typing import ColorType


def rgb(red: float, green: float, blue: float) -> tuple[float, float, float]:
    """Scale 0-255 color channels to the unit interval matplotlib reads."""
    return red / 255.0, green / 255.0, blue / 255.0


# first 7 from the Matlab default scheme, next 10 from the Matplotlib default
_FALLBACK_COLORS: list[ColorType] = [
    rgb(0.0, 114.0, 189.0),
    rgb(217.0, 83.0, 25.0),
    rgb(237.0, 177.0, 32.0),
    rgb(126.0, 47.0, 142.0),
    rgb(119.0, 172.0, 48.0),
    rgb(77.0, 190.0, 238.0),
    rgb(162.0, 20.0, 47.0),
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


CENTER_COLORS_BLUE = [
    rgb(232.0, 248.0, 252.0),
    rgb(212.0, 238.0, 250.0),
    rgb(184.0, 228.0, 244.0),
    rgb(150.0, 200.0, 228.0),
    rgb(104.0, 164.0, 194.0),
    rgb(60.0, 94.0, 134.0),
    rgb(44.0, 64.0, 104.0),
]


CENTER_COLORS_GREEN = [
    rgb(238.0, 250.0, 232.0),
    rgb(220.0, 240.0, 214.0),
    rgb(184.0, 224.0, 194.0),
    rgb(110.0, 164.0, 154.0),
    rgb(68.0, 122.0, 122.0),
    rgb(40.0, 100.0, 100.0),
    rgb(35.0, 70.0, 75.0),
]


CENTER_COLORS_GREY = [
    rgb(242.0, 242.0, 242.0),
    rgb(220.0, 220.0, 220.0),
    rgb(190.0, 190.0, 190.0),
    rgb(140.0, 140.0, 140.0),
    rgb(88.0, 88.0, 88.0),
    rgb(65.0, 65.0, 65.0),
    rgb(50.0, 50.0, 50.0),
]


CENTER_COLORS_RED = [
    rgb(254.0, 238.0, 234.0),
    rgb(250.0, 224.0, 218.0),
    rgb(250.0, 200.0, 194.0),
    rgb(224.0, 164.0, 164.0),
    rgb(194.0, 128.0, 128.0),
    rgb(158.0, 88.0, 88.0),
    rgb(128.0, 64.0, 64.0),
]


CENTER_COLORS_YELLOW = [
    rgb(252.0, 248.0, 228.0),
    rgb(252.0, 238.0, 200.0),
    rgb(250.0, 230.0, 170.0),
    rgb(250.0, 214.0, 144.0),
    rgb(232.0, 194.0, 124.0),
    rgb(188.0, 142.0, 84.0),
    rgb(162.0, 112.0, 60.0),
]


SHORE_POWER_COLOR = rgb(250.0, 230.0, 170.0)  # #fae6aa


_GENERIC_COLOR_SCHEME = [
    *CENTER_COLORS_BLUE,
    *CENTER_COLORS_GREEN,
    *CENTER_COLORS_GREY,
    *CENTER_COLORS_RED,
    *CENTER_COLORS_YELLOW,
]


def _fallback_color(index: int) -> ColorType:
    return _FALLBACK_COLORS[index % len(_FALLBACK_COLORS)]


def center_color_saturation(count: int) -> list[tuple[float, float, float]]:
    count_max = 35

    if count > count_max:
        raise ValueError(
            f"The maximum number of colors is {count_max}, you requested {count}."
        )

    initial = 0
    step = 1
    color_types = [
        CENTER_COLORS_GREEN,
        CENTER_COLORS_YELLOW,
        CENTER_COLORS_RED,
        CENTER_COLORS_BLUE,
        CENTER_COLORS_GREY,
    ]

    if count < 10:
        initial = 2
        step = 3

        if count < 5:
            color_types = color_types[:count]

    elif 10 <= count < 15:
        initial = 1
        step = 2

    elif 15 <= count < 20:
        initial = 0
        step = 2

    elif 20 <= count < 30:
        initial = 1
        step = 1

    shade = initial
    i = 0
    colors = []

    while i < count:
        j = 0
        while (j < len(color_types)) and (i + j < count):
            colors.append(color_types[j][shade])
            j += 1

        i += j
        shade += step

    return colors


def generate_color_dict(
    names: Collection[str], default_dict: Mapping[str, ColorType]
) -> dict[str, ColorType]:
    """Color each name by its default, else by the next unused generic color."""
    chosen: dict[str, ColorType] = {}
    colors_used: list[ColorType] = []

    for name in names:
        if name in default_dict:
            chosen[name] = default_dict[name]
            colors_used.append(default_dict[name])

    # start in the middle of the scheme and move down, then up, so the most
    # appropriate colors are used first
    scheme_size = len(_GENERIC_COLOR_SCHEME)
    order = [
        *range(math.floor(scheme_size / 2), 0, -1),
        *range(math.ceil(scheme_size / 2), scheme_size, 1),
    ]

    fallback_count = 0
    for name in names:
        if name in default_dict:
            continue

        color_chosen: ColorType | None = None
        for i in order:
            color = _GENERIC_COLOR_SCHEME[i]

            if _color_is_used(color, colors_used):
                continue

            color_chosen = color
            break

        if color_chosen is None:
            color_chosen = _fallback_color(fallback_count)
            fallback_count += 1

        chosen[name] = color_chosen
        colors_used.append(color_chosen)

    # callers read the colors positionally, so they follow the order of names
    return {name: chosen[name] for name in names}


def _color_is_used(color: ColorType, colors: list[ColorType]) -> bool:
    if not colors:
        return False

    return bool(np.any(np.all(np.asarray(color) == np.asarray(colors), axis=1)))
