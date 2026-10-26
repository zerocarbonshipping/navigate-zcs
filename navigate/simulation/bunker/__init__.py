# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The bunkering LP: its algorithm class, solver backend and fair-share supply."""

from __future__ import annotations

from navigate.simulation.bunker.bunker_algorithm import BunkerAlgorithm
from navigate.simulation.bunker.fair_share_supply import (
    calculate_fair_share_fuel_supply,
)
from navigate.simulation.bunker.solver_backend import select_backend
