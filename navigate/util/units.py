# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit conversion factors, and the conversion between power and energy over time."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

from navigate.util.numeric import divide_nonzero

if TYPE_CHECKING:
    from navigate.util.types_ import FloatArray, FloatLike

# time
DAY_TO_HOUR = 24.0
HOUR_TO_DAY = 1.0 / DAY_TO_HOUR

# mass
TON_TO_GRAM = 1e6
TON_TO_KG = 1e3

# energy
GJ_TO_MJ = 1e3
MWH_TO_GJ = 3.6
MWD_TO_GJ = MWH_TO_GJ * DAY_TO_HOUR

# intensity
TON_PER_GJ_TO_GRAM_PER_MJ = TON_TO_GRAM / GJ_TO_MJ


@overload
def power_to_energy(power: float, duration: float) -> float: ...


@overload
def power_to_energy(power: FloatLike, duration: FloatArray) -> FloatArray: ...


@overload
def power_to_energy(power: FloatArray, duration: FloatLike) -> FloatArray: ...


def power_to_energy(power: FloatLike, duration: FloatLike) -> FloatLike:
    """
    Convert a power held over a duration to energy.

    Parameters
    ----------
    power
        Power, in MW.
    duration
        Time the power is held, in days.

    Returns
    -------
    FloatLike
        Energy, in GJ.
    """
    return power * duration * MWD_TO_GJ


def energy_to_power(energy: FloatLike, duration: FloatLike) -> FloatArray:
    """
    Convert an energy spread over a duration to power, zero without time.

    Parameters
    ----------
    energy
        Energy, in GJ.
    duration
        Time the energy is spread over, in days.

    Returns
    -------
    FloatArray
        Power, in MW; 0-d for scalar inputs.
    """
    return divide_nonzero(energy, duration * MWD_TO_GJ)
