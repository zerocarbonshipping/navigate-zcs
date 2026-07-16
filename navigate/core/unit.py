# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

# time
YEAR_TO_DAYS = 365.25
DAY_TO_YEARS = 1. / YEAR_TO_DAYS
DAY_TO_HOURS = 24.
HOUR_TO_DAYS = 1. / DAY_TO_HOURS

# mass
TON_TO_GRAM = 1e6
TON_TO_KG = 1e3

# energy
GJ_TO_MJ = 1e3
MJ_TO_GJ = 1e-3
MWH_TO_MJ = 3600.                       # mega watt hours to mega joule
MWH_TO_GJ = MWH_TO_MJ * MJ_TO_GJ        # mega watt hours to giga joule
MWD_TO_MJ = MWH_TO_MJ * DAY_TO_HOURS    # mega watt days to mega joule
MWD_TO_GJ = MWD_TO_MJ * MJ_TO_GJ        # mega watt days to giga joule

# multiples
TON_PER_GJ_TO_GRAM_PR_MJ = TON_TO_GRAM / GJ_TO_MJ
