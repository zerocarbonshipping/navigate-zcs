# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The processes of a plant's process tree that its region leaves unpriced."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.node_type import is_process

if TYPE_CHECKING:
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.region import Region


def find_unpriced_processes(region: Region, process: Process) -> list[Process]:
    """
    Return the processes of a tree to which a region assigns no rate.

    A process is unpriced where the region assigns none of its CAPEX, OPEX and
    energy demand, so that it costs nothing and uses no energy.

    Parameters
    ----------
    region
        Region whose process rates are read.
    process
        Process at the root of the tree.

    Returns
    -------
    list[Process]
        The unpriced processes, each once, in the order the tree is walked.
    """
    return [node for node in _process_tree(process) if _is_unpriced(region, node)]


def _process_tree(process: Process) -> list[Process]:
    """Return a process and every process feeding it, directly or not, each once."""
    tree = [process]

    # the loop reaches each feed appended to the tree while it walks it
    for node in tree:
        for feed in node.feeds:
            if is_process(feed) and feed not in tree:
                tree.append(feed)

    return tree


def _is_unpriced(region: Region, process: Process) -> bool:
    """Check whether a region assigns none of a process's CAPEX, OPEX and energy."""
    name = process.name

    return (
        region.process_capex[name] is None
        and region.process_opex[name] is None
        and region.process_energy[name] is None
    )
