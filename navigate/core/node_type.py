# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Node-type names: the DSL keywords that declare nodes in `.nav`/`.inc` files.

Each node class, general nodes included, carries its keyword as its `type`
class attribute, so the `is_*` type guards and the parser's per-type tables
share a single vocabulary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeIs

if TYPE_CHECKING:
    from navigate.core.node import Node
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.variable import Variable
    from navigate.core.types_ import Calculator

CONVERTER = "Converter"
CURVE = "Curve"
EMISSION = "Emission"
FEEDSTOCK = "Feedstock"
FLEET = "Fleet"
FORECAST = "Forecast"
FUEL = "Fuel"
LEVY = "Levy"
PLANT = "Plant"
PORT = "Port"
PROCESS = "Process"
PRODUCER = "Producer"
REGION = "Region"
REGULATION = "Regulation"
ROUTE = "Route"
SOURCE = "Source"
SURFACE = "Surface"
TANK = "Tank"
TECHNOLOGY = "Technology"
TIMETABLE = "Timetable"
TRANSPORT = "Transport"
VARIABLE = "Variable"
VESSEL = "Vessel"

# general nodes
BUNKER_OPTIONS = "BunkerOptions"
MODEL_DEFINITION = "ModelDefinition"

CALCULATOR_TYPES = (CURVE, FORECAST, SURFACE, TIMETABLE, VARIABLE)

# the node type(s) an attribute accepts
type AcceptedNodeTypes = str | tuple[str, ...]


def accepts_type(accepted: AcceptedNodeTypes | None, node_type: str) -> bool:
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

    if isinstance(accepted, str):
        return node_type == accepted

    return node_type in accepted


def is_calculator(node: Node) -> TypeIs[Calculator]:
    """Check whether the node is a calculator, narrowing its static type."""
    return node.type in CALCULATOR_TYPES


def is_feedstock(node: Node) -> TypeIs[Feedstock]:
    """Check whether the node is a Feedstock, narrowing its static type."""
    return node.type == FEEDSTOCK


def is_process(node: Node) -> TypeIs[Process]:
    """Check whether the node is a Process, narrowing its static type."""
    return node.type == PROCESS


def is_surface(node: Node) -> TypeIs[Surface]:
    """Check whether the node is a Surface, narrowing its static type."""
    return node.type == SURFACE


def is_variable(node: Node) -> TypeIs[Variable]:
    """Check whether the node is a Variable, narrowing its static type."""
    return node.type == VARIABLE
