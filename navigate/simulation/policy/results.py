# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The results of the regulation profiles that combine their written ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.profiles import RegulationProfile


def complete_regulation_profile(profile: RegulationProfile) -> None:
    """
    Write the results of a regulation profile that total its written ones.

    Parameters
    ----------
    profile
        Regulation profile, written for the whole run.
    """
    profile.non_compliance_units = profile.flexibility_units + profile.remedial_units
