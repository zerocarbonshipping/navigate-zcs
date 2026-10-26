# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The registries the parser fills with the nodes and general nodes of a deck."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any

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
from navigate.core.nodes.plot import Plot
from navigate.core.nodes.port import Port
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
    from collections.abc import Iterable

    from navigate.core.general_nodes.general_node import GeneralNode
    from navigate.core.node import Node


# the field metadata key naming the node class a field holds
_CLASS = "class"


def _node_group(cls: type[Node]) -> Any:
    return field(default_factory=dict, metadata={_CLASS: cls})


@dataclass
class Nodes:
    """The nodes a deck defines, grouped by node type and keyed by node name."""

    converters: dict[str, Converter] = _node_group(Converter)
    curves: dict[str, Curve] = _node_group(Curve)
    emissions: dict[str, Emission] = _node_group(Emission)
    feedstocks: dict[str, Feedstock] = _node_group(Feedstock)
    fleets: dict[str, Fleet] = _node_group(Fleet)
    forecasts: dict[str, Forecast] = _node_group(Forecast)
    fuels: dict[str, Fuel] = _node_group(Fuel)
    levies: dict[str, Levy] = _node_group(Levy)
    plants: dict[str, Plant] = _node_group(Plant)
    plots: dict[str, Plot] = _node_group(Plot)
    ports: dict[str, Port] = _node_group(Port)
    processes: dict[str, Process] = _node_group(Process)
    producers: dict[str, Producer] = _node_group(Producer)
    regions: dict[str, Region] = _node_group(Region)
    regulations: dict[str, Regulation] = _node_group(Regulation)
    reports: dict[str, Report] = _node_group(Report)
    routes: dict[str, Route] = _node_group(Route)
    sources: dict[str, Source] = _node_group(Source)
    surfaces: dict[str, Surface] = _node_group(Surface)
    tanks: dict[str, Tank] = _node_group(Tank)
    technologies: dict[str, Technology] = _node_group(Technology)
    timetables: dict[str, Timetable] = _node_group(Timetable)
    transports: dict[str, Transport] = _node_group(Transport)
    variables: dict[str, Variable] = _node_group(Variable)
    vessels: dict[str, Vessel] = _node_group(Vessel)

    def all_nodes(self) -> Iterable[Node]:
        """
        Walk every node the deck defines, group by group.

        Yields
        ------
        Node
            Each node of every group, in turn.
        """
        for group_field in fields(self):
            yield from getattr(self, group_field.name).values()

    def group(self, node_type: str) -> dict[str, Node]:
        """
        Look up the group holding the nodes of a node type.

        Parameters
        ----------
        node_type
            The node type keyword.

        Returns
        -------
        dict[str, Node]
            The group, keyed by node name; the registry's own dict, so writes
            to it change the registry.
        """
        group: dict[str, Node] = getattr(self, _GROUP_FIELD[node_type])
        return group


# the field of Nodes holding each node type, read off the field metadata
_GROUP_FIELD: dict[str, str] = {f.metadata[_CLASS].type: f.name for f in fields(Nodes)}


@dataclass
class GeneralNodes:
    """The at-most-one-per-deck nodes, built once the DEFINE pass has checked them."""

    bunker_options: BunkerOptions = field(metadata={_CLASS: BunkerOptions})
    model_definition: ModelDefinition = field(metadata={_CLASS: ModelDefinition})


def _classes_by_type(registry: type[Nodes | GeneralNodes]) -> dict[str, Any]:
    classes = [f.metadata[_CLASS] for f in fields(registry)]
    return {cls.type: cls for cls in classes}


# the class of each node type and general node, read off the field metadata
NODE_CLASS: dict[str, type[Node]] = _classes_by_type(Nodes)
GENERAL_NODE_CLASS: dict[str, type[GeneralNode]] = _classes_by_type(GeneralNodes)
