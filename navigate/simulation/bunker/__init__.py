# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The bunkering LP: the algorithm class and the fair-share supply estimate."""

from __future__ import annotations

from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm
from navigate.simulation.bunker.supply_allocation import (
    calculate_fair_share_fuel_supply,
)
