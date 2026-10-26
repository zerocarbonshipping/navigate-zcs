# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Internal type vocabulary: numpy array aliases and the unions over them.

Dependency-free; ``navigate/core/types_.py`` holds the aliases built over
core classes.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

type BoolArray = npt.NDArray[np.bool_]
type DateArray = npt.NDArray[np.datetime64]
type FloatArray = npt.NDArray[np.float64]
type TimedeltaArray = npt.NDArray[np.timedelta64]

type FloatLike = float | FloatArray

# index-producing numpy operations (searchsorted and friends) reveal
# width-parametrized signed integers, which only the unparametrized
# signedinteger accepts
type IntArray = npt.NDArray[np.signedinteger]

# a time index selects one time-step or several
type Step = int | np.signedinteger
type Steps = slice | IntArray
type Index = Step | Steps
