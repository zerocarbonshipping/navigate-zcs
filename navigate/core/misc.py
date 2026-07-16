# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

from navigate.core.enum_ import SimulationSectionID

# Zero-length sentinel arrays used as __init__ defaults before initialize() is called.
# Safe to share: zero-length arrays cannot be mutated in-place.
EMPTY_FLOAT = np.zeros(0, dtype=float)
EMPTY_NAN = np.full(0, np.nan)
EMPTY_BOOL = np.zeros(0, dtype=bool)

ROUND_OFF = 5   # decimals
TOLERANCE = 10 ** (-ROUND_OFF)


BOOL_ID = {'FALSE': False,
           'TRUE': True}


BOUNDS_MAP = {'-INF': -np.inf,
              'INF': np.inf}

DAY = 1.
MONTH = 30.4375   # equivalent to 365.25/12 = 30.4375 days
YEAR = 365.25    # equivalent to 365.25 days


SECTION_DEFINE = [SimulationSectionID.DEFINE]
SECTION_EVENTS = [SimulationSectionID.EVENTS]
SECTION_BOTH = [SimulationSectionID.DEFINE, SimulationSectionID.EVENTS]
