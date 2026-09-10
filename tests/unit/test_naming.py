# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the deck-token to method-name mapping in navigate.util.naming."""
import pytest

from navigate.util import attribute_to_instance_name, attribute_to_setter


@pytest.mark.parametrize("attribute, expected", [
    ("Extrapolate", "set_extrapolate"),
    ("LowerHeatingValue", "set_lower_heating_value"),
    ("Capex", "set_capex"),
    ("Opex", "set_opex"),
])
def test_attribute_to_setter(attribute, expected):
    assert attribute_to_setter(attribute) == expected


@pytest.mark.parametrize("attribute, expected", [
    ("TotalEquivalentWtt", "get_total_equivalent_wtt"),
    ("CumulativeEquivalentTtw", "get_cumulative_equivalent_ttw"),
    ("BunkerIntensityTotalEquivalentWtw", "get_bunker_intensity_total_equivalent_wtw"),
])
def test_attribute_to_getter(attribute, expected):
    assert attribute_to_setter(attribute, method="get") == expected


@pytest.mark.parametrize("attribute, expected", [
    ("EmissionFactors", "emission_factors"),
    ("Jurisdiction", "jurisdiction"),
    ("BunkerWttOverwrite", "bunker_wtt_overwrite"),
])
def test_attribute_to_instance_name(attribute, expected):
    assert attribute_to_instance_name(attribute) == expected
