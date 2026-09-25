# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One colour system for the workshop notebooks.

Everything here comes from Navigate's own palette
(`navigate/illustrations/plots/_colors.py` and `_labels.py`), so the figures the
notebooks draw match the plots the model itself generates -- including the PNGs
that notebooks 1 and 4 display straight from a run's output folder.

Why the two methanols are not the same colour
---------------------------------------------
`FUEL_COLOR` encodes the **production pathway in the hue** and the **molecule in
the step down that hue's ramp**:

    GREY  fossil        RED  bio        GREEN  electro        BLUE  blue

Bio-methanol is RED[4] and e-methanol is GREEN[4] -- the same step on two
different ramps. That is deliberate: in a decarbonisation model how a fuel was
made is the decision-relevant fact, and two fuels sharing a molecule can have
completely different well-to-tank emissions and cost drivers. The molecule is
carried by the label instead, via `fuel_label()`: "Bio-methanol" and
"e-methanol".

The rule this module follows
----------------------------
Colours must be distinct **within a figure**, not across the whole notebook. A
colour may mean different things in two unrelated figures -- Navigate's own plots
do this, and minting one colour per meaning would exhaust the palette. Chrome
(grid, axis, tick, ink) may share a hex with a series: a 0.8px spine and a filled
band with a legend entry are never confused.
"""

from matplotlib.colors import to_hex

from navigate.illustrations.plots._colors import (
    CENTER_COLORS_BLUE,
    CENTER_COLORS_GREEN,
    CENTER_COLORS_GREY,
    CENTER_COLORS_RED,
    CENTER_COLORS_YELLOW,
    generate_color_dict,
)
from navigate.illustrations.plots._labels import FUEL_COLOR, FUEL_LABEL, FUEL_ORDER

# ---------------------------------------------------------------------------
# Chrome and accents
# ---------------------------------------------------------------------------
# The ramps are sequential by design, so these are the steps that stay furthest
# apart when used as categorical slots.
BLUE = to_hex(CENTER_COLORS_BLUE[6])        # #2c4068
ORANGE = to_hex(CENTER_COLORS_YELLOW[6])    # #a2703c
GREEN = to_hex(CENTER_COLORS_GREEN[5])      # #286464

GRID = to_hex(CENTER_COLORS_GREY[1])        # #dcdcdc  gridlines
AXIS = to_hex(CENTER_COLORS_GREY[2])        # #bebebe  spines, zero lines
TICK = to_hex(CENTER_COLORS_GREY[3])        # #8c8c8c  tick labels
SUBINK = to_hex(CENTER_COLORS_GREY[4])      # #585858  axis labels, legends
INK = to_hex(CENTER_COLORS_GREY[6])         # #323232  titles

# Two more greys for "present but not the point": a pale band behind a series,
# and a muted mark for something already accounted for.
PALE = GRID
MUTED = AXIS

# A categorical ramp for series the palette has no opinion about -- technologies,
# fleet flows, cost parts. The first three ARE the house accents, so a two- or
# three-series chart matches every other figure; the rest step across the ramps
# at comparable darkness. Anything here beats matplotlib's default cycle, whose
# assignment silently shifts when the number of non-zero series changes.
SERIES = [BLUE, ORANGE, GREEN,
          to_hex(CENTER_COLORS_RED[5]),
          to_hex(CENTER_COLORS_GREY[4]),
          to_hex(CENTER_COLORS_BLUE[4]),
          to_hex(CENTER_COLORS_YELLOW[4]),
          to_hex(CENTER_COLORS_GREEN[3]),
          to_hex(CENTER_COLORS_RED[3]),
          to_hex(CENTER_COLORS_GREY[2])]


# Compliance status: under a regulatory threshold, or over it. Taken from the
# same ramps Navigate's own regulation_compliance plot uses, so the workshop and
# the library shade a breach the same way. These are STATUS colours - they never
# name a fuel, and never share a figure with a fuel series.
COMPLIANT = to_hex(CENTER_COLORS_GREEN[3])
BREACH = to_hex(CENTER_COLORS_RED[3])


def series_colours(how_many):
    """The first `how_many` categorical colours; also accepts the series itself."""
    count = how_many if isinstance(how_many, int) else len(list(how_many))
    if count > len(SERIES):
        raise ValueError(f"only {len(SERIES)} categorical colours, asked {count} "
                         "-- group the tail into 'other' rather than minting hues")
    return SERIES[:count]

# ---------------------------------------------------------------------------
# Fuels
# ---------------------------------------------------------------------------
# LNG ships as the palest grey on the Center ramp (#dcdcdc). That reads as a bar
# fill but disappears as a 2px line on white, so step it down the SAME ramp
# rather than inventing a colour. GREY[2] is the only step no fuel claims:
# GREY[1] is LNG itself and grey ammonia, GREY[3] is LPG, GREY[5] is fuel oil.
_FUEL_RGB = {**FUEL_COLOR, "liquefied_natural_gas": CENTER_COLORS_GREY[2]}

_BASE = {name: to_hex(rgb) for name, rgb in _FUEL_RGB.items()}
_EXTRA = {}     # fuels outside Navigate's palette, coloured on first sight


def fuel_colour(fuel_name):
    """Navigate's colour for a fuel.

    A fuel the library does not know about is given a colour distinct from every
    other fuel already in use, rather than a shared fallback grey.
    """
    if fuel_name in _BASE:
        return _BASE[fuel_name]
    if fuel_name not in _EXTRA:
        _assign([fuel_name])
    return _EXTRA[fuel_name]


def _assign(unknown):
    """Colour fuels the library has no entry for, avoiding what is taken.

    `generate_color_dict` is the same helper Navigate's own plots use: it keeps
    the supplied defaults and walks GENERIC_COLOR_SCHEME outwards from the middle
    for the rest, skipping any colour already spoken for. Passing the taken
    colours as RGB (not hex) is required -- it compares them componentwise.
    """
    if not unknown:
        return
    taken = {**_FUEL_RGB, **{n: _to_rgb(c) for n, c in _EXTRA.items()}}
    assigned = generate_color_dict({n: None for n in [*taken, *unknown]}, taken)
    for name in unknown:
        _EXTRA[name] = to_hex(assigned[name])


def _to_rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 255. for i in (0, 2, 4)]


def fuel_label(fuel_name):
    """The library's display name for a fuel: 'Bio-methanol', 'e-methanol', 'LNG'."""
    return FUEL_LABEL.get(fuel_name, fuel_name.replace("_", " "))


def fuel_sorted(fuel_names):
    """Fuels in Navigate's canonical stacking order: fossil, then bio, then electro."""
    rank = {name: i for i, name in enumerate(FUEL_ORDER)}
    return sorted(fuel_names, key=lambda n: (rank.get(n, len(rank)), n))


# ---------------------------------------------------------------------------
# Ship configurations
# ---------------------------------------------------------------------------
# A hull takes the colour of the fuel it is named for, so a configuration and
# what it burns read the same in every figure. Navigate also ships
# FUEL_TYPE_COLOR, keyed by fuel TYPE, but the two palettes disagree -- LNG is
# grey as a fuel and red as a type -- and putting both in one notebook is what
# made this confusing. Only FUEL_TYPE_ORDER is used, and only for ordering.
CONFIG_FUEL = {"ship_oil": "fossil_fuel_oil",
               "ship_lng": "liquefied_natural_gas",
               "ship_methanol": "methanol_bio",      # the methanol this deck burns
               "ship_ammonia": "ammonia_electro"}


def config_colour(config_name):
    """The colour of a ship configuration, taken from its fuel."""
    if config_name in CONFIG_FUEL:
        return fuel_colour(CONFIG_FUEL[config_name])
    return fuel_colour(config_name)     # already a fuel, or an unknown hull


def config_label(config_name):
    """A hull's name, as the deck spells it.

    Kept as a function rather than inlined: every ship legend in the workshop
    then reads the same, and if that convention is ever revised there is one
    place to revise it. Note it is NOT safe to prefix the result with "ship_"
    - it already carries it.
    """
    return config_name


# ---------------------------------------------------------------------------
# Cost categories
# ---------------------------------------------------------------------------
# Kept in one place so a label and its colour never come apart between figures.
# GREEN carries FuelEU in one chart and technology in another; they never share
# a figure, which the rule at the top of this file allows.
COST_COLOUR = {"fuel": BLUE,
               "compliance": ORANGE,
               "EU ETS": ORANGE,
               "FuelEU": GREEN,
               "technology": GREEN}


def cost_colour(part):
    """The colour of a cost category, matched on the leading word of its label."""
    if part in COST_COLOUR:
        return COST_COLOUR[part]
    for key, colour in COST_COLOUR.items():
        if part.lower().startswith(key.lower()):
            return colour
    return SUBINK


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------
# Ordered none < mid < strong, so an ordered ramp rather than three unrelated
# hues. Grey then two blues: none of the three is a fuel colour, which matters
# because the comparison figure puts scenario lines beside a fuel-mix stack.
SCEN_COLOUR = {"basecase_no_regulation": to_hex(CENTER_COLORS_GREY[4]),
               "basecase_mid_regulation": to_hex(CENTER_COLORS_BLUE[5]),
               "basecase_strong_regulation": to_hex(CENTER_COLORS_BLUE[6]),
               # notebooks 2 and 5: the deck as shipped against the reader's version of it
               "reference": to_hex(CENTER_COLORS_GREY[4]),
               "your scenario": to_hex(CENTER_COLORS_BLUE[6])}


def scen_colour(name):
    return SCEN_COLOUR.get(name, SUBINK)
