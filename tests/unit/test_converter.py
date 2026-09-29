# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the Converter node."""

from __future__ import annotations

import pytest

from navigate.core.enum_ import FuelTypeID
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.emission import Emission


def _make_converter() -> Converter:
    converter = Converter("main_engine")
    converter.set_power_capacity(10.0)
    converter.set_main_fuel_types(["OIL", "AMMONIA"])
    converter.set_efficiency(0.5)
    return converter


def _seeded_converter() -> Converter:
    converter = _make_converter()
    converter.initialize_dependencies(
        {name: Emission(name) for name in ("carbon_dioxide", "nitrous_oxide")}
    )
    return converter


class TestSlipFractionDefaults:
    """
    slip_fraction must index for every fuel type after node setup.

    The parser seeds the dict in initialize_dependencies before deck commands assign
    values, and initialize defaults unassigned entries to zero.
    """

    def test_partial_assignment_defaults_other_fuel_types(self):
        converter = _make_converter()

        converter.initialize_dependencies({})
        converter.set_slip_fraction("AMMONIA", 0.03)
        converter.initialize()

        assert converter.slip_fraction[FuelTypeID.AMMONIA].get() == 0.03
        assert converter.slip_fraction[FuelTypeID.OIL].get() == 0.0


class TestCommandValueValidatedBeforeKeyMatch:
    """
    Both commands validate the value before checking the fuel type they were given.

    'set_consumption_ttw' also guards the emission key, checked only once the fuel
    type is found, so a fuel type missing from the converter never gets that far
    either. A command wrong in both ways therefore reports the value error, not the
    fuel type or emission key error.
    """

    @pytest.mark.parametrize(
        ("setter_name", "args"),
        [
            ("set_slip_fraction", ("METHANE", -1.0)),
            ("set_consumption_ttw", ("METHANE", "carbon_dioxide", -1.0)),
        ],
        ids=["set_slip_fraction", "set_consumption_ttw"],
    )
    def test_invalid_value_on_an_unconfigured_fuel_type_reports_the_value_error(
        self, setter_name, args
    ):
        converter = _make_converter()

        with pytest.raises(ValueError, match=r"must be ≥ 0\.0"):
            getattr(converter, setter_name)(*args)


@pytest.mark.parametrize(
    ("setter_name", "args"),
    [
        ("set_slip_fraction", ("METHANE", 0.03)),
        ("set_consumption_ttw", ("METHANE", "carbon_dioxide", 0.001)),
    ],
    ids=["set_slip_fraction", "set_consumption_ttw"],
)
def test_a_fuel_type_the_converter_lacks_is_rejected_naming_the_declared_ones(
    setter_name, args
):
    converter = _seeded_converter()

    # the declared fuel types are listed in their MainFuelTypes order
    with pytest.raises(
        ValueError, match=r"only allows assignment of OIL, AMMONIA, but got METHANE$"
    ):
        getattr(converter, setter_name)(*args)


class TestConsumptionTtwEmissionName:
    """
    The emission name is matched against the emissions the deck defines.

    The parser seeds one entry per declared fuel type and defined emission
    before the deck's commands run, so a wildcard reaches every emission of
    the fuel type and a name matching none of them is refused.
    """

    def test_wildcard_assigns_every_emission_of_the_fuel_type(self):
        converter = _seeded_converter()

        converter.set_consumption_ttw("OIL", "*", 0.001)

        values = {key: value.get() for key, value in converter.consumption_ttw.items()}
        assert values == {
            (FuelTypeID.OIL, "carbon_dioxide"): 0.001,
            (FuelTypeID.OIL, "nitrous_oxide"): 0.001,
            (FuelTypeID.AMMONIA, "carbon_dioxide"): 0.0,
            (FuelTypeID.AMMONIA, "nitrous_oxide"): 0.0,
        }

    def test_unknown_emission_name_is_refused(self):
        converter = _seeded_converter()

        with pytest.raises(KeyError, match="sulphur_oxide"):
            converter.set_consumption_ttw("OIL", "sulphur_oxide", 0.001)
