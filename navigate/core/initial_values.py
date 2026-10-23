# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The sentinel array an expectation holds before `initialize` sizes its arrays."""

from __future__ import annotations

import numpy as np

# safe to share: a zero-length array cannot be mutated in place
EMPTY_FLOAT = np.zeros(0)
