# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.parser._commands — command validation logic."""
import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import CommandError
from navigate.parser._commands import CommandReference, check_node_command_is_allowed
from navigate.parser._lark_parser import Command, GeneralNodeDeclaration, SourceLocation
from navigate.parser.parser import Parser


class TestCheckNodeCommandIsAllowed:

    def test_valid_command_both_sections(self):
        """set_bunkering_allowed is BOTH for Port."""
        assert check_node_command_is_allowed("Port", "set_bunkering_allowed", SimulationSectionID.DEFINE)
        assert check_node_command_is_allowed("Port", "set_bunkering_allowed", SimulationSectionID.EVENTS)

    def test_define_only_command_in_events_raises(self):
        """set_ttw is DEFINE-only for Fuel."""
        assert check_node_command_is_allowed("Fuel", "set_ttw", SimulationSectionID.DEFINE)
        with pytest.raises(CommandError, match="does not allow use of command"):
            check_node_command_is_allowed("Fuel", "set_ttw", SimulationSectionID.EVENTS)

    def test_unknown_command_raises(self):
        with pytest.raises(CommandError, match="has no command"):
            check_node_command_is_allowed("Port", "nonexistent_command", SimulationSectionID.DEFINE)


class TestGeneralNodeCommands:

    def test_command_on_general_node_raises(self):
        parser = Parser()
        parser._current_section = SimulationSectionID.DEFINE
        declaration = GeneralNodeDeclaration(
            node_type="BunkerOptions",
            body=[Command(name="set_solver", args=["GUROBI"], source=SourceLocation("file.nav", 5))],
        )

        with pytest.raises(CommandError, match="does not support commands"):
            parser._process_general_node_declaration(declaration)


class _DummyNode:
    def __str__(self):
        return "DummyNode"

    def two_required(self, a, b):
        pass

    def one_required(self, a):
        pass


class TestCommandReference:

    @pytest.mark.parametrize("command, inputs, match", [
        ("two_required", [1], "requires 2 inputs"),
        ("one_required", [1, 2, 3], "takes up to 1 inputs"),
    ], ids=["too_few", "too_many"])
    def test_check_command_arity_mismatch(self, command, inputs, match):
        """CommandReference._check_command should raise on an arity mismatch."""
        ref = CommandReference(command, inputs, source=SourceLocation("file.nav", 5), deck_line=10)

        with pytest.raises(CommandError, match=match):
            ref.execute(_DummyNode())
