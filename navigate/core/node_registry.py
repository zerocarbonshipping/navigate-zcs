# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The registries the parser builds from the nodes and general nodes of a deck."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, get_args, get_type_hints

from navigate.core.general_nodes.bunker_options import BunkerOptions
from navigate.core.general_nodes.model_definition import ModelDefinition
from navigate.core.nodes.converter import Converter
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.feedstock import Feedstock
from navigate.core.nodes.fleet import Fleet
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.levy import Levy
from navigate.core.nodes.plant import Plant
from navigate.core.nodes.port import Port
from navigate.core.nodes.process import Process
from navigate.core.nodes.producer import Producer
from navigate.core.nodes.region import Region
from navigate.core.nodes.regulation import Regulation
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
    from collections.abc import Iterable

    from navigate.core.enum_ import NodeTypeID
    from navigate.core.general_nodes.general_node import GeneralNode
    from navigate.core.node import Node


class Nodes(NamedTuple):
    """The nodes a deck defines, grouped by node type and keyed by node name."""

    converters: dict[str, Converter]
    curves: dict[str, Curve]
    emissions: dict[str, Emission]
    feedstocks: dict[str, Feedstock]
    fleets: dict[str, Fleet]
    forecasts: dict[str, Forecast]
    fuels: dict[str, Fuel]
    levies: dict[str, Levy]
    plants: dict[str, Plant]
    ports: dict[str, Port]
    processes: dict[str, Process]
    producers: dict[str, Producer]
    regions: dict[str, Region]
    regulations: dict[str, Regulation]
    routes: dict[str, Route]
    sources: dict[str, Source]
    surfaces: dict[str, Surface]
    tanks: dict[str, Tank]
    technologies: dict[str, Technology]
    timetables: dict[str, Timetable]
    transports: dict[str, Transport]
    variables: dict[str, Variable]
    vessels: dict[str, Vessel]

    @classmethod
    def build(cls, nodes: Iterable[Node]) -> Nodes:
        """
        Sort nodes into the groups of their node types.

        Parameters
        ----------
        nodes
            The nodes, each group taking its nodes in this order.

        Returns
        -------
        Nodes
            The registry, with an empty group for a node type without nodes.
        """
        groups: dict[str, dict[str, Any]] = {name: {} for name in cls._fields}

        for node in nodes:
            groups[_GROUP_FIELD[node.type]][node.name] = node

        return cls(**groups)

    def all_nodes(self) -> Iterable[Node]:
        """
        Walk every node the deck defines, group by group.

        Yields
        ------
        Node
            Each node of every group, in turn.
        """
        for group in self:
            yield from group.values()


class GeneralNodes(NamedTuple):
    """The at-most-one-per-deck nodes, built once the DEFINE pass has checked them."""

    bunker_options: BunkerOptions
    model_definition: ModelDefinition


# the node class each field of Nodes holds, read off its annotation
_GROUP_CLASS: dict[str, type[Node]] = {
    name: get_args(hint)[1] for name, hint in get_type_hints(Nodes).items()
}

# the field of Nodes holding each node type
_GROUP_FIELD: dict[NodeTypeID, str] = {
    cls.type: name for name, cls in _GROUP_CLASS.items()
}

# the class of each node type and general node
NODE_CLASS: dict[NodeTypeID, type[Node]] = {
    cls.type: cls for cls in _GROUP_CLASS.values()
}
GENERAL_NODE_CLASS: dict[NodeTypeID, type[GeneralNode]] = {
    cls.type: cls for cls in get_type_hints(GeneralNodes).values()
}
