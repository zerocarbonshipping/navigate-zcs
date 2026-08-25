# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import numpy as np

# Zero-length sentinel arrays used as __init__ defaults before initialize() is called.
# Safe to share: zero-length arrays cannot be mutated in-place.
EMPTY_FLOAT = np.zeros(0, dtype=float)
EMPTY_NAN = np.full(0, np.nan)
EMPTY_BOOL = np.zeros(0, dtype=bool)
