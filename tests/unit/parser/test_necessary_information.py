# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The parser refuses to run a deck that defines no Fleet or no Fuel.

A read deck always has a timeline, since the start date is on it, and a Fleet
cannot be read without vessels and ports, so Fleets and Fuels are what the
guard can find missing. The message names exactly the missing types, and no
Emission is required.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import DeckKeywordError

FUEL = """
Fuel "oil" {
    FuelType = OIL
    LowerHeatingValue = 41.2
    MassDensity = 0.9
}
"""

FLEET = """
Fleet "fleet" {
    Vessels = [Vessel("vessel")]
    InterFuelSensitivity = 0.5
    IntraFuelSensitivity = 0.5
    InitialVessels = 100
}

Vessel "vessel" {
    PowerSystem = PowerSystem("ps")
    Route = Route("route")
    NominalCapacity = 8000
    Tanks = [Tank("tank")]
    PropulsionLoad = 10
}

PowerSystem "ps" {
    Propulsion = Converter("conv")
    Electrical = Converter("conv_electrical")
    Heat = Converter("conv_heat")
}

Converter "conv" {
    PowerCapacity = 50
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Converter "conv_electrical" {
    PowerCapacity = 10
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Converter "conv_heat" {
    PowerCapacity = 5
    MainFuelTypes = OIL
    Efficiency = 0.5
}

Tank "tank" {
    FuelTypes = OIL
    Size = 9000
}

Route "route" {
    RouteType = REGIONAL_TRIP
    Ports = [Port("port")]
    TimeAtSea = 0.75
    ConditionDistribution = [1.0]
    Speeds = [10]
}

Port "port" {
}
"""


@pytest.mark.parametrize(
    ("define", "missing"),
    [
        pytest.param(FLEET, "Fuels", id="no-fuel"),
        pytest.param(FUEL, "Fleets", id="no-fleet"),
    ],
)
def test_a_deck_missing_a_required_type_is_refused(read_deck, define, missing):
    parser = read_deck(define)

    with pytest.raises(DeckKeywordError) as error:
        parser.includes_necessary_information()

    assert str(error.value) == (
        f"Unable to run a simulation:\n\t- No {missing} are defined.\n"
    )


def test_a_deck_with_a_fleet_and_a_fuel_but_no_emission_passes(read_deck):
    parser = read_deck(FLEET + FUEL)

    parser.includes_necessary_information()
