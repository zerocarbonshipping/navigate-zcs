# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the deck-token to method-name mapping in navigate.util.naming."""
import pytest

from navigate.util import attribute_to_setter


@pytest.mark.parametrize("attribute, expected", [
    ("Extrapolate", "set_extrapolate"),
    ("LowerHeatingValue", "set_lower_heating_value"),
    ("CAPEX", "set_capex"),
    ("OPEX", "set_opex"),
    ("BunkerWTTOverwrite", "set_bunker_wtt_overwrite"),
])
def test_attribute_to_setter(attribute, expected):
    assert attribute_to_setter(attribute) == expected


@pytest.mark.parametrize("attribute, expected", [
    ("TotalEquivalentWTT", "get_total_equivalent_wtt"),
    ("CumulativeEquivalentTTW", "get_cumulative_equivalent_ttw"),
    ("BunkerIntensityTotalEquivalentWTW", "get_bunker_intensity_total_equivalent_wtw"),
])
def test_attribute_to_getter(attribute, expected):
    assert attribute_to_setter(attribute, method="get") == expected


def test_attribute_to_file_name():
    assert attribute_to_setter("EmissionFactors", method="")[1:] == "emission_factors"
