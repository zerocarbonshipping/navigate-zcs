# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The registries the parser fills with the nodes and general nodes of a deck."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING

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
    from collections.abc import Iterable, Mapping

    from navigate.core.general_nodes._general_node import _GeneralNode
    from navigate.core.node import Node


# the field metadata key naming the node class a field holds
CLASS = "class"


@dataclass
class Nodes:
    """The nodes a deck defines, grouped by node type and keyed by node name."""

    converters: dict[str, Converter] = field(
        default_factory=dict, metadata={CLASS: Converter}
    )
    curves: dict[str, Curve] = field(default_factory=dict, metadata={CLASS: Curve})
    emissions: dict[str, Emission] = field(
        default_factory=dict, metadata={CLASS: Emission}
    )
    feedstocks: dict[str, Feedstock] = field(
        default_factory=dict, metadata={CLASS: Feedstock}
    )
    fleets: dict[str, Fleet] = field(default_factory=dict, metadata={CLASS: Fleet})
    forecasts: dict[str, Forecast] = field(
        default_factory=dict, metadata={CLASS: Forecast}
    )
    fuels: dict[str, Fuel] = field(default_factory=dict, metadata={CLASS: Fuel})
    levies: dict[str, Levy] = field(default_factory=dict, metadata={CLASS: Levy})
    plants: dict[str, Plant] = field(default_factory=dict, metadata={CLASS: Plant})
    plots: dict[str, Plot] = field(default_factory=dict, metadata={CLASS: Plot})
    ports: dict[str, Port] = field(default_factory=dict, metadata={CLASS: Port})
    power_systems: dict[str, PowerSystem] = field(
        default_factory=dict, metadata={CLASS: PowerSystem}
    )
    processes: dict[str, Process] = field(
        default_factory=dict, metadata={CLASS: Process}
    )
    producers: dict[str, Producer] = field(
        default_factory=dict, metadata={CLASS: Producer}
    )
    regions: dict[str, Region] = field(default_factory=dict, metadata={CLASS: Region})
    regulations: dict[str, Regulation] = field(
        default_factory=dict, metadata={CLASS: Regulation}
    )
    reports: dict[str, Report] = field(default_factory=dict, metadata={CLASS: Report})
    routes: dict[str, Route] = field(default_factory=dict, metadata={CLASS: Route})
    sources: dict[str, Source] = field(default_factory=dict, metadata={CLASS: Source})
    surfaces: dict[str, Surface] = field(
        default_factory=dict, metadata={CLASS: Surface}
    )
    tanks: dict[str, Tank] = field(default_factory=dict, metadata={CLASS: Tank})
    technologies: dict[str, Technology] = field(
        default_factory=dict, metadata={CLASS: Technology}
    )
    timetables: dict[str, Timetable] = field(
        default_factory=dict, metadata={CLASS: Timetable}
    )
    transports: dict[str, Transport] = field(
        default_factory=dict, metadata={CLASS: Transport}
    )
    variables: dict[str, Variable] = field(
        default_factory=dict, metadata={CLASS: Variable}
    )
    vessels: dict[str, Vessel] = field(default_factory=dict, metadata={CLASS: Vessel})

    def _all_groups(self) -> tuple[Mapping[str, Node], ...]:
        """
        Collect the per-type groups in one tuple.

        Every field of ``Nodes`` is one of these groups, so deriving the
        tuple from the dataclass fields keeps it complete by construction:
        a group added to the dataclass can no longer be forgotten here. The
        order matches field declaration order, which callers such as
        ``all_nodes`` rely on to leak into results consistently.

        Returns
        -------
        tuple[Mapping[str, Node], ...]
            One group per node type, each keyed by node name, in field
            declaration order.
        """
        return tuple(getattr(self, f.name) for f in fields(self))

    def all_nodes(self) -> Iterable[Node]:
        """
        Walk every node the deck defines, group by group.

        Yields
        ------
        Node
            Each node of every group, in turn.
        """
        for group in self._all_groups():
            yield from group.values()

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

    def all_names(self) -> Iterable[str]:
        """
        Walk the name of every node the deck defines, group by group.

        Yields
        ------
        str
            The name of each node of every group, in turn.
        """
        for group in self._all_groups():
            yield from group.keys()


# the field of Nodes holding each node type, read off the field metadata
_GROUP_FIELD: dict[str, str] = {f.metadata[CLASS].type: f.name for f in fields(Nodes)}


@dataclass
class GeneralNodes:
    """The at-most-one-per-deck nodes, built once the DEFINE pass has checked them."""

    bunker_options: BunkerOptions = field(metadata={CLASS: BunkerOptions})
    model_definition: ModelDefinition = field(metadata={CLASS: ModelDefinition})


# the class of each node type and general node, read off the field metadata
NODE_CLASS: dict[str, type[Node]] = {
    f.metadata[CLASS].type: f.metadata[CLASS] for f in fields(Nodes)
}
GENERAL_NODE_CLASS: dict[str, type[_GeneralNode]] = {
    f.metadata[CLASS].type: f.metadata[CLASS] for f in fields(GeneralNodes)
}
