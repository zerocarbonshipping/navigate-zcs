# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Look up the port converters and the time-steps that index the bunkering LP."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.enum_ import PORT_ENERGY_DEMANDS, BunkerScopeID

if TYPE_CHECKING:
    from navigate.core.nodes.vessel import Vessel

# the time-steps a bunkering scope reads: one, or every one from a time-step on
type ScopeSteps = int | slice


def get_port_converters(vessel: Vessel) -> list[str]:
    """
    Return the names of the converters serving port energy demands.

    Parameters
    ----------
    vessel
        Vessel whose port converters are named.

    Returns
    -------
    list[str]
        The electrical and heat converter names.
    """
    converters = map(vessel.get_converter, PORT_ENERGY_DEMANDS)
    return [converter.name for converter in converters]


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
