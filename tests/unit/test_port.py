# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Port command defaults: which fuels keep the bottom-up bunker price and WTT."""

from __future__ import annotations

from navigate.core.nodes.emission import Emission
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.port import Port


def _fuel(name, *, liquid_market):
    fuel = Fuel(name)
    fuel.liquid_market = liquid_market
    return fuel


def test_only_an_unpriced_liquid_market_fuel_is_filled_with_zero():
    # a liquid-market fuel has no production chain to price it, so an unset
    # overwrite becomes 0; a bottom-up fuel keeps None, which selects the
    # bottom-up calculation, and an assigned overwrite is never replaced
    fuels = {
        "oil": _fuel("oil", liquid_market=True),
        "lng": _fuel("lng", liquid_market=True),
        "ammonia": _fuel("ammonia", liquid_market=False),
    }
    port = Port("port")
    port.initialize_dependencies({"co2": Emission("co2")}, fuels)
    port.set_bunker_price_overwrite("lng", 500.0)
    port.initialize()

    assert port.bunker_price_overwrite["oil"].get() == 0.0
    assert port.bunker_wtt_overwrite[("oil", "co2")].get() == 0.0
    assert port.bunker_price_overwrite["lng"].get() == 500.0
    assert port.bunker_price_overwrite["ammonia"] is None
    assert port.bunker_wtt_overwrite[("ammonia", "co2")] is None
