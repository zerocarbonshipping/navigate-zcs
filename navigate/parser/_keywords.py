# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The DSL keywords: each node type's class, registry group and allowed sections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import SectionID
from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition
from navigate.core.node_type import (
    BUNKER_OPTIONS,
    CONVERTER,
    CURVE,
    EMISSION,
    FEEDSTOCK,
    FLEET,
    FORECAST,
    FUEL,
    LEVY,
    MODEL_DEFINITION,
    PLANT,
    PLOT,
    PORT,
    POWER_SYSTEM,
    PROCESS,
    PRODUCER,
    REGION,
    REGULATION,
    REPORT,
    ROUTE,
    SOURCE,
    SURFACE,
    TANK,
    TECHNOLOGY,
    TIMETABLE,
    TRANSPORT,
    VARIABLE,
    VESSEL,
)
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.feedstock import Feedstock
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.levy import Levy
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.plot import Plot
from navigate.core.nodes.port import Port
from navigate.core.nodes.power_system import PowerSystem
from navigate.core.nodes.process import Process
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.region import Region
from navigate.core.nodes.regulation import Regulation
from navigate.core.nodes.report import Report
from navigate.core.nodes.route import Route
from navigate.core.nodes.source import Source
from navigate.core.nodes.surface import Surface
from navigate.core.nodes.tank import Tank
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.timetable import Timetable
from navigate.core.nodes.transport import Transport
from navigate.core.nodes.variable import Variable
from navigate.core.nodes.vessel import Vessel

if TYPE_CHECKING:
    from collections.abc import Callable

    from navigate.core.general_nodes._general_node import _GeneralNode
    from navigate.core.node import Node
    from navigate.core.node_registry import Nodes

# event-timeline keywords; the values mirror the literals in grammar.lark
DATE = "Date"
END = "End"
START = "Start"

type AllowedSections = tuple[SectionID, ...]

SECTION_DEFINE: AllowedSections = (SectionID.DEFINE,)
SECTION_EVENTS: AllowedSections = (SectionID.EVENTS,)
SECTION_BOTH: AllowedSections = (SectionID.DEFINE, SectionID.EVENTS)

NODE_CLASS: dict[str, Callable[[str], Node]] = {
    CONVERTER: Converter,
    CURVE: Curve,
    EMISSION: Emission,
    FEEDSTOCK: Feedstock,
    FLEET: Fleet,
    FORECAST: Forecast,
    FUEL: Fuel,
    LEVY: Levy,
    PLANT: Plant,
    PLOT: Plot,
    PORT: Port,
    POWER_SYSTEM: PowerSystem,
    PROCESS: Process,
    PRODUCER: Producer,
    REGION: Region,
    REGULATION: Regulation,
    REPORT: Report,
    ROUTE: Route,
    SOURCE: Source,
    SURFACE: Surface,
    TANK: Tank,
    TECHNOLOGY: Technology,
    TIMETABLE: Timetable,
    TRANSPORT: Transport,
    VARIABLE: Variable,
    VESSEL: Vessel,
}

GENERAL_NODE_CLASS: dict[str, type[_GeneralNode]] = {
    BUNKER_OPTIONS: BunkerOptions,
    MODEL_DEFINITION: ModelDefinition,
}

NODE_GROUP: dict[str, str] = {
    CONVERTER: "converters",
    CURVE: "curves",
    EMISSION: "emissions",
    FEEDSTOCK: "feedstocks",
    FLEET: "fleets",
    FORECAST: "forecasts",
    FUEL: "fuels",
    LEVY: "levies",
    PLANT: "plants",
    PLOT: "plots",
    PORT: "ports",
    POWER_SYSTEM: "power_systems",
    PROCESS: "processes",
    PRODUCER: "producers",
    REGION: "regions",
    REGULATION: "regulations",
    REPORT: "reports",
    ROUTE: "routes",
    SOURCE: "sources",
    SURFACE: "surfaces",
    TANK: "tanks",
    TECHNOLOGY: "technologies",
    TIMETABLE: "timetables",
    TRANSPORT: "transports",
    VARIABLE: "variables",
    VESSEL: "vessels",
}

GENERAL_NODE_GROUP: dict[str, str] = {
    BUNKER_OPTIONS: "bunker_options",
    MODEL_DEFINITION: "model_definition",
}

KEYWORD_SECTIONS: dict[str, AllowedSections] = {
    CONVERTER: SECTION_BOTH,
    CURVE: SECTION_BOTH,
    EMISSION: SECTION_DEFINE,
    FEEDSTOCK: SECTION_DEFINE,
    FLEET: SECTION_BOTH,
    FORECAST: SECTION_BOTH,
    FUEL: SECTION_DEFINE,
    LEVY: SECTION_BOTH,
    PLANT: SECTION_BOTH,
    PLOT: SECTION_DEFINE,
    PORT: SECTION_BOTH,
    POWER_SYSTEM: SECTION_BOTH,
    PROCESS: SECTION_BOTH,
    PRODUCER: SECTION_BOTH,
    REGION: SECTION_BOTH,
    REGULATION: SECTION_BOTH,
    REPORT: SECTION_DEFINE,
    ROUTE: SECTION_BOTH,
    SOURCE: SECTION_DEFINE,
    SURFACE: SECTION_BOTH,
    TANK: SECTION_BOTH,
    TECHNOLOGY: SECTION_BOTH,
    TIMETABLE: SECTION_BOTH,
    TRANSPORT: SECTION_BOTH,
    VARIABLE: SECTION_BOTH,
    VESSEL: SECTION_BOTH,
    # general nodes ----------------
    BUNKER_OPTIONS: SECTION_DEFINE,
    MODEL_DEFINITION: SECTION_DEFINE,
    # miscellaneous ----------------
    START: SECTION_EVENTS,
    DATE: SECTION_EVENTS,
    END: SECTION_EVENTS,
}

SECTION_NAME: dict[SectionID, str] = {
    SectionID.DEFINE: "DEFINE",
    SectionID.EVENTS: "EVENTS",
}


# methods ------------------------------------------------------------------------------
def define_new_node(node_type: str, name: str) -> Node:
    """
    Construct a node of a node type.

    Parameters
    ----------
    node_type
        The node type keyword.
    name
        The node name.

    Returns
    -------
    Node
        The new node, with no attribute assigned.
    """
    return NODE_CLASS[node_type](name)


def define_new_general_node(type_: str) -> _GeneralNode:
    """
    Construct a general node of a general node type.

    Parameters
    ----------
    type_
        The general node type keyword.

    Returns
    -------
    _GeneralNode
        The new general node, with no attribute assigned.
    """
    return GENERAL_NODE_CLASS[type_]()


def node_group(nodes: Nodes, node_type: str) -> dict[str, Node]:
    """
    Look up the registry group holding the nodes of a node type.

    Parameters
    ----------
    nodes
        The node registry.
    node_type
        The node type keyword.

    Returns
    -------
    dict[str, Node]
        The group, keyed by node name; the registry's own dict, so writes to
        it change the registry.
    """
    group: dict[str, Node] = getattr(nodes, NODE_GROUP[node_type])
    return group
