# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Colour palettes and per-series colour assignment for the plots.

Holds the raw palettes (Center-brand scales, the shore-power accent, the
Matlab/Matplotlib default scheme) together with the logic that assigns a colour
to each plotted entity: preferring the caller-supplied domain defaults, then the
generic scheme, then generated fallback colours.
"""

from __future__ import annotations

import math

import numpy as np

# ----------------------------------------------------------------------------------------------------------------------
# Default colouring scheme - first 7 from Matlab default, next 10 from Matplotlib default
DEFAULT_COLOURS = [
    np.array([0.0, 114.0, 189.0]) / 255.0,
    np.array([217.0, 83.0, 25.0]) / 255.0,
    np.array([237.0, 177.0, 32.0]) / 255.0,
    np.array([126.0, 47.0, 142.0]) / 255.0,
    np.array([119.0, 172.0, 48.0]) / 255.0,
    np.array([77.0, 190.0, 238.0]) / 255.0,
    np.array([162.0, 20.0, 47.0]) / 255.0,
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
    np.array([232.0, 248.0, 252.0]) / 255.0,
    np.array([212.0, 238.0, 250.0]) / 255.0,
    np.array([184.0, 228.0, 244.0]) / 255.0,
    np.array([150.0, 200.0, 228.0]) / 255.0,
    np.array([104.0, 164.0, 194.0]) / 255.0,
    np.array([60.0, 94.0, 134.0]) / 255.0,
    np.array([44.0, 64.0, 104.0]) / 255.0,
]


CENTER_COLORS_GREEN = [
    np.array([238.0, 250.0, 232.0]) / 255.0,
    np.array([220.0, 240.0, 214.0]) / 255.0,
    np.array([184.0, 224.0, 194.0]) / 255.0,
    np.array([110.0, 164.0, 154.0]) / 255.0,
    np.array([68.0, 122.0, 122.0]) / 255.0,
    np.array([40.0, 100.0, 100.0]) / 255.0,
    np.array([35.0, 70.0, 75.0]) / 255.0,
]


CENTER_COLORS_GREY = [
    np.array([242.0, 242.0, 242.0]) / 255.0,
    np.array([220.0, 220.0, 220.0]) / 255.0,
    np.array([190.0, 190.0, 190.0]) / 255.0,
    np.array([140.0, 140.0, 140.0]) / 255.0,
    np.array([88.0, 88.0, 88.0]) / 255.0,
    np.array([65.0, 65.0, 65.0]) / 255.0,
    np.array([50.0, 50.0, 50.0]) / 255.0,
]


CENTER_COLORS_RED = [
    np.array([254.0, 238.0, 234.0]) / 255.0,
    np.array([250.0, 224.0, 218.0]) / 255.0,
    np.array([250.0, 200.0, 194.0]) / 255.0,
    np.array([224.0, 164.0, 164.0]) / 255.0,
    np.array([194.0, 128.0, 128.0]) / 255.0,
    np.array([158.0, 88.0, 88.0]) / 255.0,
    np.array([128.0, 64.0, 64.0]) / 255.0,
]


CENTER_COLORS_YELLOW = [
    np.array([252.0, 248.0, 228.0]) / 255.0,
    np.array([252.0, 238.0, 200.0]) / 255.0,
    np.array([250.0, 230.0, 170.0]) / 255.0,
    np.array([250.0, 214.0, 144.0]) / 255.0,
    np.array([232.0, 194.0, 124.0]) / 255.0,
    np.array([188.0, 142.0, 84.0]) / 255.0,
    np.array([162.0, 112.0, 60.0]) / 255.0,
]


SHORE_POWER_COLOR = np.array([250.0, 230.0, 170.0]) / 255.0  # #fae6aa


GENERIC_COLOR_SCHEME = [
    *CENTER_COLORS_BLUE,
    *CENTER_COLORS_GREEN,
    *CENTER_COLORS_GREY,
    *CENTER_COLORS_RED,
    *CENTER_COLORS_YELLOW,
]


def default_color(i):
    return DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)]


def center_color_saturation(n, shift=False):

    n_max = 35  # number of colors in Center color scale

    if n > n_max:
        raise ValueError(f"The maximum number of colors is {n_max}, you requested {n}.")

    initial = 0
    step = 1
    color_types = [
        CENTER_COLORS_GREEN,
        CENTER_COLORS_YELLOW,
        CENTER_COLORS_RED,
        CENTER_COLORS_BLUE,
        CENTER_COLORS_GREY,
    ]

    if n < 10:
        if shift:
            initial = 3

        else:
            initial = 2

        step = 3

        if n < 5:
            color_types = color_types[:n]

    elif 10 <= n < 15:
        if shift:
            initial = 1 + shift
        else:
            initial = 1

        step = 2

    elif 15 <= n < 20:
        initial = 0
        step = 2

    elif 20 <= n < 25 or 25 <= n < 30:
        initial = 1
        step = 1

    else:
        pass

    idx = initial
    i = 0
    colors = []

    while i < n:
        j = 0
        while (j < len(color_types)) and (i + j < n):
            colors.append(color_types[j][idx])
            j += 1

        i += j
        idx += step

    return colors


def generate_color_dict(nodes, default_dict):

    if not isinstance(nodes, dict):
        nodes = {node.name: node for node in nodes}

    out_dict = dict.fromkeys(nodes)
    colors_used = []

    # use default values where applicable
    for key in nodes:
        if key in default_dict:
            out_dict[key] = default_dict[key]
            colors_used.append(default_dict[key])

    # for all which did not have an applicable default, assign the best alternative
    no_success_count = 0
    for key, _node in nodes.items():
        if key not in default_dict:
            scheme = GENERIC_COLOR_SCHEME

            # build a range that starts in the middle and
            # moves down, then upwards, in order to use
            # the most appropriate colors first
            n = len(scheme)
            order = [*range(math.floor(n / 2), 0, -1), *range(math.ceil(n / 2), n, 1)]

            color_chosen = None
            for i in order:
                color = scheme[i]

                if _color_is_used(color, colors_used):
                    continue

                color_chosen = color
                break

            # if all colors are already in use, pick a default color
            if color_chosen is None:
                color_chosen = default_color(no_success_count)
                no_success_count += 1

            out_dict[key] = color_chosen
            colors_used.append(color_chosen)

    return out_dict


def _color_is_used(color, colors):
    if not colors:
        return False

    return np.any(np.all(color == colors, axis=1))
