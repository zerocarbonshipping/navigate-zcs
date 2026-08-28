# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Converter node."""
from navigate.core.enum_ import FuelTypeID
from navigate.core.nodes.converter import Converter


def _make_converter() -> Converter:
    converter = Converter('main_engine')
    converter.set_power_capacity(10.)
    converter.set_main_fuel_types(['OIL', 'AMMONIA'])
    converter.set_efficiency(0.5)
    return converter


class TestSlipFractionDefaults:
    """slip_fraction must index for every fuel type after node setup: the
    parser seeds the dict in initialize_dependencies before deck commands
    assign values, and initialize defaults unassigned entries to zero."""

    def test_partial_assignment_defaults_other_fuel_types(self):
        converter = _make_converter()

        converter.initialize_dependencies({})
        converter.set_slip_fraction('AMMONIA', 0.03)
        converter.initialize()

        assert converter.slip_fraction[FuelTypeID.AMMONIA].get() == 0.03
        assert converter.slip_fraction[FuelTypeID.OIL].get() == 0.

    def test_no_assignment_defaults_all_fuel_types(self):
        converter = _make_converter()

        converter.initialize_dependencies({})
        converter.initialize()

        assert converter.slip_fraction[FuelTypeID.OIL].get() == 0.
        assert converter.slip_fraction[FuelTypeID.AMMONIA].get() == 0.
