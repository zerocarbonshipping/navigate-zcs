# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Rendering configuration for the plots: matplotlib setup, fonts, and shared
save/legend options.

Domain-entity display labels and colour palettes live in
:mod:`navigate.output.plots._labels`. The catalogue of selectable plot
labels is derived from :mod:`navigate.output.plots._registry`.
"""

import matplotlib as mpl

from navigate.output.plots._fonts import setup_font

_initialized = False


def initialize_matplotlib():
    """Set up matplotlib backend and custom fonts. Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    # necessary for memory reasons when plotting multiple scenarios
    mpl.use('Agg')
    setup_font()
    _initialized = True


FONT_SIZE_SMALL = 15
FONT_SIZE_LARGE = 20
FONT_SIZE_LEGEND = 20

LEGEND_OPTIONS = {'fontsize': FONT_SIZE_LEGEND, 'framealpha': 1}
SAVE_OPTIONS = {'transparent': False}
