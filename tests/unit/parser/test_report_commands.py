# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A Report property its command does not report stops the parse at its deck line.

The Report node is a root, so the prune keeps it without a referencing node.
"""

from __future__ import annotations

import pytest

from navigate.exceptions import CommandError


def _report(*commands):
    return 'Report "r" {\n' + "".join(f"    {c}\n" for c in commands) + "}\n"


@pytest.mark.parametrize(
    ("call", "reports", "key", "getter"),
    [
        ("add_property(ConsumedEnergy)", "manager", "global", "get_consumed_energy"),
        ('add_fleet_property("f", CargoMiles)', "fleet", "f", "get_cargo_miles"),
        ('add_levy_property("l", Collected)', "levy", "l", "get_collected"),
        (
            'add_plant_property("p", InstantaneousCost)',
            "plant",
            "p",
            "get_instantaneous_cost",
        ),
        ('add_port_property("p", BunkerPrice)', "port", "p", "get_bunker_price"),
        (
            'add_producer_property("p", Development)',
            "producer",
            "p",
            "get_development",
        ),
        (
            'add_regulation_property("r", RemedialUnits)',
            "regulation",
            "r",
            "get_remedial_units",
        ),
        (
            'add_vessel_property("v", AssetCharterRate)',
            "vessel",
            "v",
            "get_asset_charter_rate",
        ),
    ],
    ids=[
        "add_property",
        "add_fleet_property",
        "add_levy_property",
        "add_plant_property",
        "add_port_property",
        "add_producer_property",
        "add_regulation_property",
        "add_vessel_property",
    ],
)
def test_a_reported_property_parses(read_deck, call, reports, key, getter):
    parser = read_deck(_report(call))

    report = getattr(parser.nodes.reports["r"], f"{reports}_reports")
    assert report[key].getters == [getter]


@pytest.mark.parametrize(
    ("command", "token"),
    [
        ("add_fleet_property", "CargoMils"),
        # BunkerPrice is reported for ports only
        ("add_vessel_property", "BunkerPrice"),
    ],
    ids=["unknown_token", "token_of_another_command"],
)
def test_an_unreported_property_is_a_command_error_at_its_line(
    read_deck, command, token
):
    # define.inc opens with a blank line and the three lines of ModelDefinition,
    # then the Report header and the valid command
    deck = _report('add_fleet_property("*", CargoMiles)', f'{command}("*", {token})')

    with pytest.raises(
        CommandError, match=rf"define\.inc', line 7: '{command}' .*'{token}'"
    ):
        read_deck(deck)


def test_a_missing_argument_is_still_an_arity_error(read_deck):
    with pytest.raises(CommandError, match="'add_fleet_property' requires 2 inputs"):
        read_deck(_report("add_fleet_property(CargoMiles)"))
