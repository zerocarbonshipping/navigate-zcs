# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for PowerSystem converter-uniqueness validation."""
from unittest.mock import MagicMock

import pytest

from navigate.core.nodes.power_system import PowerSystem


def _mock_converter(name):
    converter = MagicMock()
    converter.get_name.return_value = name
    return converter


def _make_power_system(propulsion='main_engine', electrical='auxiliary_engine', heat='boiler'):
    power_system = PowerSystem('ps')
    power_system.propulsion = _mock_converter(propulsion)
    power_system.electrical = _mock_converter(electrical)
    power_system.heat = _mock_converter(heat)
    return power_system


def test_initialize_succeeds_with_distinct_converters():
    _make_power_system().initialize()


def test_initialize_raises_for_shared_converter():
    power_system = _make_power_system(electrical='shared', heat='shared')

    with pytest.raises(ValueError, match='distinct'):
        power_system.initialize()
