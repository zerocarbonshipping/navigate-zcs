# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Configure the matplotlib font family used for Center plots.

The preferred Aktiv Grotesk font is no longer shipped with the package. If it
is installed on the system we use it; otherwise we fall back to Calibri Light
and finally to matplotlib's generic sans-serif.
"""

import matplotlib as mpl
from matplotlib import font_manager

# preference order: Center font, Calibri Light, then the generic family
PREFERRED_FONTS: list[str] = ['Aktiv Grotesk Thin', 'Calibri Light']


def setup_font() -> None:
    """
    Set the matplotlib font family, preferring the Center font when available.

    The preferred fonts are used only if installed on the system; matplotlib
    falls back to the next entry and ultimately to a generic sans-serif.
    """

    installed = {font.name for font in font_manager.fontManager.ttflist}
    available = [name for name in PREFERRED_FONTS if name in installed]

    mpl.rcParams['font.family'] = 'sans-serif'
    mpl.rcParams['font.sans-serif'] = [*available, *mpl.rcParamsDefault['font.sans-serif']]
