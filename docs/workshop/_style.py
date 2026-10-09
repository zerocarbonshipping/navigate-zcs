# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""One colour system for the workshop notebooks.

Every colour the notebooks draw is a swatch of the Center's palette: nine
hues, levels 0 to 8, in PALETTE below. Level 0 does not show on large screens
and projectors, so figures use levels 1 to 8 only.

The roles (fuels, accents, greys) start from Navigate's own palette
(`navigate/illustrations/plots/_colors.py` and `_labels.py`) and are snapped to
the nearest swatch, so a fuel keeps its hue and its step while the hex is the
Center's. The PNGs notebook 4 displays straight from a run's output folder are
drawn by Navigate itself and keep the library's colours.

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
# The Center's palette
# ---------------------------------------------------------------------------
PALETTE = {
    "black":  ["#f2f2f2", "#dcdcdc", "#bebebe", "#a5a5a5", "#8c8c8c",
               "#585858", "#4c4c4c", "#414141", "#323232"],
    "red":    ["#f2e1dc", "#e6bfb4", "#da9b8a", "#ca6b5b", "#b95747",
               "#a6473b", "#8e3b32", "#78312b", "#612825"],
    "orange": ["#f5e6d6", "#f3e0c5", "#f0caa4", "#e2af7c", "#d79056",
               "#c9753e", "#b55f2e", "#9b4d26", "#824023"],
    "peach":  ["#feeeeb", "#fae0da", "#fbc8c3", "#edb6b3", "#e1a5a5",
               "#c28080", "#b16d6d", "#9f5959", "#814141"],
    "yellow": ["#fcf6de", "#fdf0ca", "#fae6a9", "#fbdf9d", "#fbd790",
               "#e8c17b", "#d2a968", "#bc8e53", "#a2713c"],
    "green":  ["#eff6e8", "#dcedd6", "#badfc2", "#94c2ae", "#6fa59b",
               "#457b7b", "#377070", "#296565", "#25474c"],
    "blue":   ["#eaf6fb", "#d5effb", "#b9e5f5", "#a9d7ec", "#97c8e4",
               "#68a4c2", "#5382a5", "#3d5f87", "#2c4169"],
    "purple": ["#e8e4ef", "#d7d3e1", "#c6c1d1", "#b5b0c3", "#a39eb3",
               "#938ea4", "#827c95", "#716b86", "#5f5775"],
}


def swatch(hue, level):
    """One colour of the palette, e.g. swatch("green", 6)."""
    return PALETTE[hue][level]


def nearest(colour, taken=(), levels=range(1, 9)):
    """The swatch closest to `colour` (hex or RGB in 0-1) among `levels`, skipping `taken`."""
    rgb = _to_rgb(colour) if isinstance(colour, str) else [float(c) for c in colour[:3]]
    best = min((sum((a - b) ** 2 for a, b in zip(rgb, _to_rgb(ramp[level]))), ramp[level])
               for ramp in PALETTE.values() for level in levels
               if ramp[level] not in taken)
    return best[1]


def _to_rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return [int(h[i:i + 2], 16) / 255. for i in (0, 2, 4)]


# ---------------------------------------------------------------------------
# Chrome and accents
# ---------------------------------------------------------------------------
# The ramps are sequential by design, so these are the steps that stay furthest
# apart when used as categorical slots.
BLUE = swatch("blue", 8)            # #2c4169
ORANGE = swatch("yellow", 8)        # #a2713c
GREEN = swatch("green", 7)          # #296565

GRID = swatch("black", 1)           # #dcdcdc  gridlines
AXIS = swatch("black", 2)           # #bebebe  spines, zero lines
TICK = swatch("black", 4)           # #8c8c8c  tick labels
SUBINK = swatch("black", 5)         # #585858  axis labels, legends
INK = swatch("black", 8)            # #323232  titles

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
          swatch("peach", 7),
          swatch("black", 5),
          swatch("blue", 5),
          swatch("yellow", 5),
          swatch("green", 4),
          swatch("peach", 4),
          swatch("black", 2)]


# Compliance status: under a regulatory threshold, or over it. Taken from the
# same ramps Navigate's own regulation_compliance plot uses, so the workshop and
# the library shade a breach the same way. These are STATUS colours - they never
# name a fuel, and never share a figure with a fuel series.
COMPLIANT = nearest(CENTER_COLORS_GREEN[3])
BREACH = nearest(CENTER_COLORS_RED[3])


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

_BASE = {name: nearest(rgb) for name, rgb in _FUEL_RGB.items()}
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
        # levels 3-7 only: a pale swatch vanishes as a line on white
        _EXTRA[name] = nearest(assigned[name], levels=range(3, 8),
                               taken={*_BASE.values(), *_EXTRA.values()})


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
SCEN_COLOUR = {"basecase_no_regulation": swatch("black", 5),
               "basecase_mid_regulation": swatch("blue", 7),
               "basecase_strong_regulation": swatch("blue", 8),
               # notebooks 1-3: the deck as shipped against the reader's version of it
               "reference": swatch("black", 4),
               "your scenario": swatch("blue", 8)}


def scen_colour(name):
    return SCEN_COLOUR.get(name, SUBINK)
