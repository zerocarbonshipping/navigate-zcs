# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Internal type vocabulary: numpy array aliases."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

type BoolArray = npt.NDArray[np.bool_]
type DateArray = npt.NDArray[np.datetime64]
type FloatArray = npt.NDArray[np.float64]
type FloatLike = float | FloatArray
type Index = int | np.signedinteger | slice | IntArray
# index-producing numpy operations (searchsorted and friends) reveal
# width-parametrized signed integers, which only the unparametrized
# signedinteger accepts
type IntArray = npt.NDArray[np.signedinteger]
type TimedeltaArray = npt.NDArray[np.timedelta64]
