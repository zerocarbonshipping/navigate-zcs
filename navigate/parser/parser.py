# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The Parser: reads a deck and its include files into nodes and a timeline of events.

navigate.driver's run_deck builds one to read the deck, then applies the events of each
date in `dates` with `read_events`. Reading is four phases, each finished before the
next starts: collect the files, and the library files they reference, into
declarations and events; resolve each event to the declarations it targets; prune
to the declarations the simulation holds; build the nodes. The prune is the one
phase the others do not depend on: without it, every declaration is kept.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

from navigate.exceptions import DeckError
from navigate.parser._build import Builder
from navigate.parser._collect import Collector
from navigate.parser._library import Library
from navigate.parser._prune import prune
from navigate.parser._resolve import check_pinned_calculators, resolve

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from navigate.core.node_registry import GeneralNodes, Nodes
    from navigate.parser._resolve import BoundEvent
    from navigate.util.types_ import DateArray


class Parser:
    """Read and process Navigate input decks (.nav and .inc files)."""

    def __init__(self) -> None:
        self.nodes: Nodes
        self.general_nodes: GeneralNodes
        self.dates: DateArray

        self._builder: Builder
        self._events: dict[np.datetime64, list[BoundEvent]]

    def read_deck(
        self,
        path: Path,
        data_dir: Path | None = None,
        params: Mapping[str, str] | None = None,
    ) -> None:
        """
        Read and process the main .nav deck file.

        Parameters
        ----------
        path
            Full or relative path to the input deck file.
        data_dir
            Assumptions data folder.
        params
            Value of each %NAME% placeholder of the deck's files, as text.
        """
        collector = Collector(Library(data_dir), params)
        collector.read_deck(path.resolve())

        events = resolve(collector)
        pruning = prune(collector, events)
        check_pinned_calculators(collector, pruning.kept, pruning.events)

        self._builder = Builder(collector, pruning.kept)
        self.general_nodes = self._builder.build_general_nodes()
        start_date = self.general_nodes.model_definition.start_date

        self.dates = _time_steps(collector.timeline, start_date)
        self._events = _events_by_date(pruning.events, start_date)

        self.nodes = self._builder.build_nodes()

    def read_events(self, date: np.datetime64) -> bool:
        """
        Apply the events queued at a date and refresh the dependent nodes.

        Parameters
        ----------
        date
            A date from ``dates``; a date with no queued events only refreshes
            the dependencies.

        Returns
        -------
        bool
            Whether the events applied at least one statement.
        """
        events = self._events.get(date, [])
        self._builder.apply_events(events)

        return any(block.body for block, _ in events)


def _time_steps(
    timeline: list[np.datetime64 | None], start_date: np.datetime64
) -> DateArray:
    """Build the dates the simulation steps through: the start date and every Date."""
    dated = {date for date in timeline if date is not None}

    before_start = sorted(date for date in dated if date < start_date)
    if before_start:
        listed = ""
        for date in before_start:
            listed += f"\t- Date '{date}' is before start date '{start_date}'\n"

        raise DeckError(
            f"Inconsistent timeline detected:\n{listed}All defined dates must be "
            "later than the start date."
        )

    return np.array(sorted({start_date, *dated}), dtype="datetime64[D]")


def _events_by_date(
    events: list[BoundEvent], start_date: np.datetime64
) -> dict[np.datetime64, list[BoundEvent]]:
    """Key the events by date; on the start date the Start blocks come first."""
    queue: defaultdict[np.datetime64, list[BoundEvent]] = defaultdict(list)

    # two passes instead of a sort: insertion order keeps read order within
    # each pass, and the first pass puts every Start block ahead of a block
    # dated on the start date
    for block, keys in events:
        if block.date is None:
            queue[start_date].append((block, keys))

    for block, keys in events:
        if block.date is not None:
            queue[block.date].append((block, keys))

    return dict(queue)
