# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The calculator types, accepted node types and type guards over node types.

A node type is a `NodeTypeID` member; each node class, general nodes included,
carries its own as its `type` class attribute.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeIs

from navigate.core.enum_ import NodeTypeID

if TYPE_CHECKING:
    from navigate.core.node import Node
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.variable import Variable
    from navigate.core.types_ import Calculator

CALCULATOR_TYPES = (
    NodeTypeID.CURVE,
    NodeTypeID.FORECAST,
    NodeTypeID.SURFACE,
    NodeTypeID.TIMETABLE,
    NodeTypeID.VARIABLE,
)

# the node type(s) an attribute accepts
type AcceptedNodeTypes = NodeTypeID | tuple[NodeTypeID, ...]


def accepts_type(accepted: AcceptedNodeTypes | None, node_type: NodeTypeID) -> bool:
    """
    Check whether an attribute accepting the given node types accepts a node type.

    Parameters
    ----------
    accepted
        The node type(s) the attribute accepts; None where it accepts none.
    node_type
        The node type checked.

    Returns
    -------
    bool
        Whether the node type is among the accepted ones.
    """
    if accepted is None:
        return False

    if isinstance(accepted, NodeTypeID):
        return node_type == accepted

    return node_type in accepted


def is_calculator(node: Node) -> TypeIs[Calculator]:
    """Check whether the node is a calculator, narrowing its static type."""
    return node.type in CALCULATOR_TYPES


def is_feedstock(node: Node) -> TypeIs[Feedstock]:
    """Check whether the node is a Feedstock, narrowing its static type."""
    return node.type == NodeTypeID.FEEDSTOCK


def is_process(node: Node) -> TypeIs[Process]:
    """Check whether the node is a Process, narrowing its static type."""
    return node.type == NodeTypeID.PROCESS


def is_surface(node: Node) -> TypeIs[Surface]:
    """Check whether the node is a Surface, narrowing its static type."""
    return node.type == NodeTypeID.SURFACE


def is_variable(node: Node) -> TypeIs[Variable]:
    """Check whether the node is a Variable, narrowing its static type."""
    return node.type == NodeTypeID.VARIABLE
