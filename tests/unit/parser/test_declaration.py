# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A declaration registers its node before its body is read.

A body can reference the node it declares — a Process may feed on a Process —
and that reference must bind to the node being declared, not to a second one
no declaration ever fills.
"""

from __future__ import annotations

from navigate.core.enum_ import SimulationSectionID
from navigate.core.node_type import PROCESS
from navigate.parser._lark_parser import Assignment, NodeDeclaration
from navigate.parser._node_reference import NodeReference
from navigate.parser.parser import Parser


def test_a_body_reference_to_its_own_node_binds_to_it():
    parser = Parser()
    parser._current_section = SimulationSectionID.DEFINE
    body = [Assignment("Feeds", [NodeReference(PROCESS, "p")])]

    parser._process_node_declaration(NodeDeclaration(PROCESS, "p", body))

    process = parser.nodes.processes["p"]
    assert process.feeds == [process]
