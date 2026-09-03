# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Fuel node."""
import pytest

from navigate.core.nodes.fuel import Fuel


class TestLiquidMarket:

    def test_defaults_to_false(self):
        assert Fuel('oil').liquid_market is False

    def test_set_true(self):
        fuel = Fuel('oil')
        fuel.set_liquid_market('TRUE')
        assert fuel.liquid_market is True

    def test_set_false(self):
        fuel = Fuel('oil')
        fuel.set_liquid_market('FALSE')
        assert fuel.liquid_market is False

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            Fuel('oil').set_liquid_market('MAYBE')
