# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for navigate.parser._commands — command validation logic."""
import pytest

from navigate.core.enum_ import SimulationSectionID
from navigate.exceptions import CommandError
from navigate.parser._commands import (
    NODE_COMMAND_SECTIONS,
    CommandReference,
    check_general_node_command_is_allowed,
    check_node_command_is_allowed,
)
from navigate.parser._lark_parser import SourceLoc


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

    @pytest.mark.parametrize("node_type", list(NODE_COMMAND_SECTIONS.keys()))
    def test_all_node_types_have_dict(self, node_type):
        assert isinstance(NODE_COMMAND_SECTIONS[node_type], dict)


class TestCheckGeneralNodeCommandIsAllowed:

    def test_bunker_logistics_set_distance(self):
        assert check_general_node_command_is_allowed("BunkerLogistics", "set_distance", SimulationSectionID.DEFINE)

    def test_bunker_logistics_set_distance_in_events_raises(self):
        with pytest.raises(CommandError, match="does not allow use of command"):
            check_general_node_command_is_allowed("BunkerLogistics", "set_distance", SimulationSectionID.EVENTS)

    def test_unknown_general_node_command_raises(self):
        with pytest.raises(CommandError, match="has no command"):
            check_general_node_command_is_allowed("BunkerLogistics", "fake_cmd", SimulationSectionID.DEFINE)


class TestCommandReference:

    def test_check_command_too_few_args(self):
        """CommandReference._check_command should raise when too few inputs are provided."""

        class DummyNode:
            def my_method(self, a, b):
                pass

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference("my_method", [1], source=SourceLoc("file.nav", 5), deck_line=10)

        with pytest.raises(CommandError, match="requires 2 inputs"):
            ref.execute(node)

    def test_check_command_too_many_args(self):
        """CommandReference._check_command should raise when too many inputs are provided."""

        class DummyNode:
            def my_method(self, a):
                pass

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference("my_method", [1, 2, 3], source=SourceLoc("file.nav", 5), deck_line=10)

        with pytest.raises(CommandError, match="takes up to 1 inputs"):
            ref.execute(node)

    def test_execute_success(self):
        """CommandReference.execute should call the method with correct inputs."""
        call_log = []

        class DummyNode:
            def my_method(self, a, b):
                call_log.append((a, b))

            def __str__(self):
                return "DummyNode"

        node = DummyNode()
        ref = CommandReference("my_method", [1, 2], source=SourceLoc("file.nav", 5), deck_line=10)
        ref.execute(node)
        assert call_log == [(1, 2)]
