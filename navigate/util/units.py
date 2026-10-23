# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The unit conversion factors the model calculates with."""

from __future__ import annotations

# time
DAY_TO_HOURS = 24.0
HOUR_TO_DAYS = 1.0 / DAY_TO_HOURS

# mass
TON_TO_GRAM = 1e6
TON_TO_KG = 1e3

# energy
GJ_TO_MJ = 1e3
MWH_TO_GJ = 3.6
MWD_TO_GJ = MWH_TO_GJ * DAY_TO_HOURS

# intensity
TON_PER_GJ_TO_GRAM_PER_MJ = TON_TO_GRAM / GJ_TO_MJ
