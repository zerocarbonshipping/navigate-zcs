# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The sweeps over the node registry that bring every node to a usable state.

The parser runs them once the DEFINE block is built and again after every
event read: seed the command-written dictionaries, run the default hooks of
`Node`, then validate every node. They are the one place that knows which
registries a node type's dependencies are seeded from.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.node_registry import Nodes


def seed_dependencies(nodes: Nodes) -> None:
    """
    Seed the dictionaries the DSL commands write, on every node that has them.

    Runs before the commands on every pass, so a node seeds with ``setdefault``
    and recomputes what it derives.

    Parameters
    ----------
    nodes
        The node registry.
    """
    for converter in nodes.converters.values():
        converter.initialize_dependencies(nodes.emissions)

    for fleet in nodes.fleets.values():
        fleet.initialize_dependencies()

    for fuel in nodes.fuels.values():
        fuel.initialize_dependencies(nodes.emissions)

    for levy in nodes.levies.values():
        levy.initialize_dependencies(nodes.vessels)

    for plant in nodes.plants.values():
        plant.initialize_dependencies(nodes.feedstocks, nodes.ports, nodes.processes)

    for port in nodes.ports.values():
        port.initialize_dependencies(nodes.emissions, nodes.fuels)

    for producer in nodes.producers.values():
        producer.initialize_dependencies(nodes.feedstocks, nodes.ports, nodes.processes)

    for region in nodes.regions.values():
        region.initialize_dependencies(
            nodes.emissions,
            nodes.feedstocks,
            nodes.processes,
            nodes.sources,
            nodes.transports,
        )

    for regulation in nodes.regulations.values():
        regulation.initialize_dependencies(nodes.vessels)

    for route in nodes.routes.values():
        route.initialize_dependencies()


def initialize(nodes: Nodes) -> None:
    """
    Run the first-pass lifecycle hooks over every node.

    Parameters
    ----------
    nodes
        The node registry.
    """
    for node in nodes.all_nodes():
        node.initialize()


def reinitialize(nodes: Nodes) -> None:
    """
    Re-run the hooks an event read can invalidate, over every node.

    Parameters
    ----------
    nodes
        The node registry.
    """
    for node in nodes.all_nodes():
        node.reinitialize()


def validate(nodes: Nodes) -> None:
    """
    Run every node's requirement and consistency checks after its defaults.

    Parameters
    ----------
    nodes
        The node registry.
    """
    for node in nodes.all_nodes():
        node.check_requirements()
        node.check_consistency()
