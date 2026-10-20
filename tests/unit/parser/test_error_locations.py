# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every deck error names where it was written, and carries a class the CLI catches.

The prefix is `Error in deck file, line <deck line>, include file '<path>',
line <include line>`: the deck line is that of the Include directive (1 for
DEFINE, 2 for EVENTS in these decks), the include line that of the statement.
A setter's or command's `ValueError` is re-raised as a `DeckError` with that
prefix. A table rejected when it is built after the deck is read names its
node instead, and the run-level guards name what is missing.
"""

from __future__ import annotations

import pytest

from helpers.parser_decks import FLEET, FUEL, line_of
from navigate.exceptions import DeckError, NavigateError
from navigate.simulation.time_stepping import check_runnable

CO2 = 'Emission "co2" { GlobalWarmingPotential = 1.0 }\n'
LEVY = """
Levy "levy" {{
    Scheme = BOTH
    Emissions = [Emission("co2")]
    Fuels = [Fuel("oil")]
    Jurisdiction = [Port("port")]
    Level = 30
    {command}
}}
"""


def _prefix(tmp_path, file_name, needle, deck_line=1):
    line = line_of(tmp_path / file_name, needle)
    return (
        f"Error in deck file, line {deck_line}, include file "
        f"'{tmp_path / file_name}', line {line}: "
    )


# input:    | Emission "e" { GlobalWarmingPotential = -1 }   (define.inc, line 5)
# expected: -> DeckError "Error in deck file, line 1, include file
#              '.../define.inc', line 5: Emission("e") attribute
#              'GlobalWarmingPotential' must be >= 0.0, but got -1.0."
@pytest.mark.parametrize(
    ("define", "needle", "message"),
    [
        (
            'Emission "e" { Foo = 1 }\n',
            "Foo",
            "Nodes of type 'Emission' has no attribute 'Foo'.",
        ),
        (
            'Emission "e" { GlobalWarmingPotential = -1 }\n',
            "GlobalWarmingPotential",
            "Emission(\"e\") attribute 'GlobalWarmingPotential' must be ≥ 0.0, but "
            "got -1.0.",
        ),
        (
            'Emission "e" { foo(1) }\n',
            "foo",
            "Nodes of type 'Emission' has no command 'foo'.",
        ),
        (
            FLEET
            + FUEL
            + 'Fleet "fleet" { set_operational_saving_sea(PROPULSION, 2.0) }\n',
            "set_operational_saving_sea",
            "'set_operational_saving_sea' must be ≤ 1.0, but got 2.0.",
        ),
        (
            FLEET
            + FUEL
            + CO2
            + LEVY.format(command='set_include_vessel("nope", TRUE)'),
            "set_include_vessel",
            "'set_include_vessel' attempts to reference non-existing name(s) 'nope'.",
        ),
        (
            'Variable "z*" { Value = 1 }\n',
            "z*",
            "No node of type 'Variable' matches the wildcard expression 'z*'.",
        ),
        (
            'Emission "e" { GlobalWarmingPotential = Variable("v*") }\n'
            'Variable "w1" { Value = 1 }\n',
            "GlobalWarmingPotential",
            "Wildcard 'v*' did not match any Variable nodes.",
        ),
    ],
    ids=[
        "unknown_attribute",
        "setter_value",
        "unknown_command",
        "command_value",
        "command_key",
        "wildcard_name",
        "wildcard_value",
    ],
)
def test_a_define_error_names_its_deck_and_include_line(
    tmp_path, read_deck, define, needle, message
):
    with pytest.raises(DeckError) as raised:
        read_deck(define)

    assert isinstance(raised.value, NavigateError)
    assert str(raised.value) == _prefix(tmp_path, "define.inc", needle) + message


# input:    | EVENTS: Date "01-01-2027"
#           | Converter "propulsion" { Efficiency = -1 }
# expected: -> DeckError "Error in deck file, line 2, include file
#              '.../events.inc', line 2: Converter("propulsion") attribute
#              'Efficiency' must be ..." when the date is replayed
def test_an_events_error_names_the_events_deck_line(tmp_path, read_deck):
    events = 'Date "01-01-2027"\nConverter "propulsion" { Efficiency = -1 }\n'
    parser = read_deck(FLEET + FUEL, events=events)

    with pytest.raises(DeckError) as raised:
        parser.read_events(parser.dates[1])

    prefix = _prefix(tmp_path, "events.inc", "Efficiency", deck_line=2)
    assert str(raised.value).startswith(
        prefix + "Converter(\"propulsion\") attribute 'Efficiency' must be"
    )


# input:    | EVENTS: Start
#           | Date "01-01-2027"
#           | Foo "x" { A = 1 }
# expected: -> DeckError "... events.inc', line 3: 'Foo' is not a recognized
#              node type." while the deck is read
def test_an_unknown_node_type_in_events_is_rejected_when_read(tmp_path, read_deck):
    events = 'Start\nDate "01-01-2027"\nFoo "x" {\n    A = 1\n}\n'

    with pytest.raises(DeckError) as raised:
        read_deck(events=events)

    assert str(raised.value) == (
        _prefix(tmp_path, "events.inc", "Foo", deck_line=2)
        + "'Foo' is not a recognized node type."
    )


# input:    | Fuel "f" {
#           |     ...
#           |     set_ttw("co2")
#           | }
# expected: -> DeckError "Error in deck file, line 1, include file '.../define.inc',
#              line 9: 'set_ttw' missing a required argument: 'ttw'."
def test_a_wrong_number_of_command_arguments_is_located(tmp_path, read_deck):
    message = (
        f"Error in deck file, line 1, include file '{tmp_path / 'define.inc'}', "
        "line 9: 'set_ttw' missing a required argument: 'ttw'."
    )

    with pytest.raises(DeckError) as raised:
        read_deck(
            'Fuel "f" {\n    FuelType = OIL\n    LowerHeatingValue = 40\n'
            '    MassDensity = 900\n    set_ttw("co2")\n}\n'
        )

    assert str(raised.value) == message


class TestTableBuild:
    """A table is built once its node's whole definition is read."""

    TABLE = "    Table = [\n        0, 0;\n        2, 20;\n    ]\n"
    HOST = 'Emission "e" { GlobalWarmingPotential = Curve("c") }\n'

    # input:    | Curve "c" { Extrapolate = FLAT  Below = 5  Table = [0, 0; 2, 20] }
    #           | (settings before the table, after it, or in a later block)
    # expected: -> get(-1) = 5 (flat), not the linear extrapolation -10
    @pytest.mark.parametrize(
        "curve",
        [
            'Curve "c" {\n' + TABLE + "    Extrapolate = FLAT\n    Below = 5\n}\n",
            'Curve "c" {\n    Extrapolate = FLAT\n    Below = 5\n' + TABLE + "}\n",
            'Curve "c" {\n' + TABLE + '}\nCurve "c" {\n    Extrapolate = FLAT\n'
            "    Below = 5\n}\n",
        ],
        ids=["after_table", "before_table", "later_block"],
    )
    def test_settings_apply_wherever_the_definition_writes_them(self, read_deck, curve):
        parser = read_deck(self.HOST + curve)

        # the flat value 5 below the table, not the linear extrapolation -10
        assert parser.nodes.curves["c"].get(-1.0) == 5.0

    # input:    | Curve "c" { Table = [0, 0; 2, 20]  Interpolate = PREVIOUS }
    # expected: -> DeckError "Curve("c"): 'Extrapolate' must not be LINEAR when
    #              'Interpolate' is PREVIOUS."
    def test_a_refused_curve_is_reported_against_its_node(self, read_deck):
        curve = 'Curve "c" {\n' + self.TABLE + "    Interpolate = PREVIOUS\n}\n"

        with pytest.raises(
            DeckError,
            match=(
                r"^Curve\(\"c\"\): 'Extrapolate' must not be LINEAR when "
                r"'Interpolate' is PREVIOUS\."
            ),
        ):
            read_deck(self.HOST + curve)

    # input:    | Forecast "f" { Table = [2, 0; 1, 1] }   (held by Fleet TradeGrowth)
    # expected: -> DeckError "Forecast("f"): ... 'x' must be strictly increasing"
    def test_a_refused_dated_table_is_reported_against_its_node(self, read_deck):
        # a Forecast is rebased to the start date before it is checked
        define = (
            FLEET
            + FUEL
            + 'Fleet "fleet" { TradeGrowth = Forecast("f") }\n'
            + 'Forecast "f" {\n    Table = [\n        2, 0;\n        1, 1;\n    ]\n}\n'
        )

        with pytest.raises(
            DeckError, match=r"^Forecast\(\"f\"\): .*'x' must be strictly increasing"
        ):
            read_deck(define)


class TestReportProperty:
    """A Report property its command does not report stops the parse at its line."""

    @staticmethod
    def _report(*commands):
        return 'Report "r" {\n' + "".join(f"    {c}\n" for c in commands) + "}\n"

    # input:    | Report "r" { add_fleet_property("f", CargoMiles) }
    # expected: -> the fleet report "f" reads the result "cargo_miles"
    def test_a_reported_property_resolves_to_its_result(self, read_deck):
        parser = read_deck(self._report('add_fleet_property("f", CargoMiles)'))

        assert parser.nodes.reports["r"].fleet_reports["f"].results == ["cargo_miles"]

    # input:    | Report "r" { add_fleet_property("*", CargoMils) }
    # expected: -> DeckError at the command's define.inc line, naming
    #              'add_fleet_property' and 'CargoMils'
    @pytest.mark.parametrize(
        ("command", "token"),
        [
            ("add_fleet_property", "CargoMils"),
            # BunkerPrice is reported for ports only
            ("add_vessel_property", "BunkerPrice"),
        ],
        ids=["unknown_token", "token_of_another_command"],
    )
    def test_an_unreported_property_is_a_deck_error_at_its_line(
        self, tmp_path, read_deck, command, token
    ):
        with pytest.raises(DeckError) as raised:
            read_deck(self._report(f'{command}("*", {token})'))

        message = str(raised.value)
        assert message.startswith(_prefix(tmp_path, "define.inc", command))
        assert f"'{command}'" in message
        assert f"'{token}'" in message


# input:    | a deck with Fleet "fleet" but no Fuel
# expected: -> DeckError "Unable to run a simulation:
#              - No Fuels are defined."
@pytest.mark.parametrize(
    ("define", "missing"),
    [(FLEET, ["Fuels"]), (FUEL, ["Fleets"]), ("", ["Fleets", "Fuels"])],
    ids=["no_fuel", "no_fleet", "neither"],
)
def test_a_deck_without_a_fleet_or_a_fuel_cannot_run(read_deck, define, missing):
    parser = read_deck(define)

    with pytest.raises(DeckError) as raised:
        check_runnable(parser.nodes)

    assert str(raised.value) == "Unable to run a simulation:\n" + "".join(
        f"\t- No {label} are defined.\n" for label in missing
    )


# input:    | a deck with Fleet "fleet" and Fuel "oil" but no Emission
# expected: -> check_runnable raises nothing
def test_a_deck_with_a_fleet_and_a_fuel_but_no_emission_can_run(read_deck):
    check_runnable(read_deck(FLEET + FUEL).nodes)
