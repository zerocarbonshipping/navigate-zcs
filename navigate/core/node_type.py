# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Node-type names: the DSL keywords that declare nodes in `.nav`/`.inc` files.
For regular nodes the name is also the value stored in the node's `type`
attribute (via `TypeCheckMixin`), so the `is_*` type guards and the parser's
per-type tables share a single vocabulary; general nodes carry no `type` and
use theirs only as parser dispatch keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeIs

if TYPE_CHECKING:
    from navigate.core.node import Node
    from navigate.core.nodes.curve import Curve
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.forecast import Forecast
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.surface import Surface
    from navigate.core.nodes.timetable import Timetable
    from navigate.core.nodes.variable import Variable

CONVERTER = "Converter"
CURVE = "Curve"
EMISSION = "Emission"
FEEDSTOCK = "Feedstock"
FLEET = "Fleet"
FORECAST = "Forecast"
FUEL = "Fuel"
LEVY = "Levy"
PLANT = "Plant"
PLOT = "Plot"
PORT = "Port"
POWER_SYSTEM = "PowerSystem"
PROCESS = "Process"
PRODUCER = "Producer"
REGION = "Region"
REGULATION = "Regulation"
REPORT = "Report"
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


_CALCULATOR_TYPES = (CURVE, FORECAST, SURFACE, TIMETABLE, VARIABLE)

# the node type(s) an attribute accepts; None where it accepts no reference
type AcceptedTypes = str | tuple[str, ...] | None


class TypeCheckMixin:
    """Stores a node's type tag."""

    def __init__(self, type_: str) -> None:
        self.type = type_  # node-type name (DSL keyword)

    def is_type(self, type_: str) -> bool:
        """Check whether the type tag equals ``type_``."""
        return self.type == type_


def is_calculator(
    node: Node,
) -> TypeIs[Curve | Forecast | Surface | Timetable | Variable]:
    """Check whether the node is a calculator, narrowing its static type."""
    return node.type in _CALCULATOR_TYPES


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
