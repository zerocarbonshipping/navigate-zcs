# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Look up the time-steps that index the bunkering LP."""

from __future__ import annotations

import numpy as np

from navigate.core.enum_ import BunkerScopeID

# the time-steps a bunkering scope reads: one, or every one from a time-step on
type ScopeSteps = int | slice


def get_scope_steps(idx: int, scope: BunkerScopeID) -> ScopeSteps:
    """
    Return the time-steps a bunkering scope reads.

    Parameters
    ----------
    idx
        Time-step index at which the bunkering is initiated.
    scope
        Whether the steps are read for existing or for expected bunkering.

    Returns
    -------
    ScopeSteps
        The time-step itself if existing, or every step from it if expected.
    """
    return idx if scope == BunkerScopeID.EXISTING else np.s_[idx:]
