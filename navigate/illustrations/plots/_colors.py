# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Colour palettes and per-series colour assignment for the plots.

Holds the raw palettes (Center-brand scales, the shore-power accent, the
Matlab/Matplotlib default scheme) together with the logic that assigns a colour
to each plotted entity: preferring the caller-supplied domain defaults, then the
generic scheme, then generated fallback colours.
"""

import math

import numpy as np

# ----------------------------------------------------------------------------------------------------------------------
# Default colouring scheme - first 7 from Matlab default, next 10 from Matplotlib default
DEFAULT_COLOURS = [
    np.array([0.,   114., 189.]) / 255.,
    np.array([217., 83.,   25.]) / 255.,
    np.array([237., 177.,  32.]) / 255.,
    np.array([126., 47.,  142.]) / 255.,
    np.array([119., 172.,  48.]) / 255.,
    np.array([77.,  190., 238.]) / 255.,
    np.array([162., 20.,   47.]) / 255.,
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f',
    '#bcbd22',
    '#17becf'
]


CENTER_COLORS_BLUE = [
    np.array([232., 248., 252.]) / 255.,
    np.array([212., 238., 250.]) / 255.,
    np.array([184., 228., 244.]) / 255.,
    np.array([150., 200., 228.]) / 255.,
    np.array([104., 164., 194.]) / 255.,
    np.array([60., 94., 134.]) / 255.,
    np.array([44., 64., 104.]) / 255.
]


CENTER_COLORS_GREEN = [
    np.array([238., 250., 232.]) / 255.,
    np.array([220., 240., 214.]) / 255.,
    np.array([184., 224., 194.]) / 255.,
    np.array([110., 164., 154.]) / 255.,
    np.array([68., 122., 122.]) / 255.,
    np.array([40., 100., 100.]) / 255.,
    np.array([35., 70., 75.]) / 255.
]


CENTER_COLORS_GREY = [
    np.array([242., 242., 242.]) / 255.,
    np.array([220., 220., 220.]) / 255.,
    np.array([190., 190., 190.]) / 255.,
    np.array([140., 140., 140.]) / 255.,
    np.array([88., 88., 88.]) / 255.,
    np.array([65., 65., 65.]) / 255.,
    np.array([50., 50., 50.]) / 255.
]


CENTER_COLORS_RED = [
    np.array([254., 238., 234.]) / 255.,
    np.array([250., 224., 218.]) / 255.,
    np.array([250., 200., 194.]) / 255.,
    np.array([224., 164., 164.]) / 255.,
    np.array([194., 128., 128.]) / 255.,
    np.array([158., 88., 88.]) / 255.,
    np.array([128., 64., 64.]) / 255.
]


CENTER_COLORS_YELLOW = [
    np.array([252., 248., 228.]) / 255.,
    np.array([252., 238., 200.]) / 255.,
    np.array([250., 230., 170.]) / 255.,
    np.array([250., 214., 144.]) / 255.,
    np.array([232., 194., 124.]) / 255.,
    np.array([188., 142., 84.]) / 255.,
    np.array([162., 112., 60.]) / 255.
]


SHORE_POWER_COLOR = np.array([250., 230., 170.]) / 255.  # #fae6aa


GENERIC_COLOR_SCHEME = [
    *CENTER_COLORS_BLUE,
    *CENTER_COLORS_GREEN,
    *CENTER_COLORS_GREY,
    *CENTER_COLORS_RED,
    *CENTER_COLORS_YELLOW
]


def default_color(i):
    return DEFAULT_COLOURS[i % len(DEFAULT_COLOURS)]


def center_color_saturation(n, shift=False):

    n_max = 35  # number of colors in Center color scale

    if n > n_max:
        raise ValueError("The maximum number of colors is {}, you requested {}.".format(n_max, n))

    initial = 0
    step = 1
    color_types = [CENTER_COLORS_GREEN, CENTER_COLORS_YELLOW, CENTER_COLORS_RED, CENTER_COLORS_BLUE, CENTER_COLORS_GREY]

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

    elif 20 <= n < 25:
        initial = 1
        step = 1

    elif 25 <= n < 30:
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
        nodes = {node.get_name(): node for node in nodes}

    out_dict = {key: None for key in nodes}
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
