# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect per-node report properties gathered by the Report node.

navigate.output.report_writer consumes them, keying the model-wide profile by
GLOBAL_PROFILE_KEY.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.enum_ import ReportAccumulationID
from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from navigate.core.enum_ import ReportReduceID

# the key the model-wide profile is reported under, beside the node names
GLOBAL_PROFILE_KEY = "global"


class NodeReport:
    """The report properties requested for one node, in the order they were added."""

    def __init__(self) -> None:
        self.attributes: list[str] = []
        self.results: list[str] = []
        self.reductions: list[ReportReduceID] = []
        self.accumulations: list[ReportAccumulationID] = []

    def add_property(
        self,
        attribute: str,
        reduction: ReportReduceID,
        accumulation: ReportAccumulationID,
    ) -> None:
        """
        Record a report property, ignoring one already recorded for this node.

        A cumulative property is recorded under its attribute token prefixed with
        ``Cumulative``, so a node can report a property both per date and
        accumulated.

        Parameters
        ----------
        attribute
            Deck-facing attribute token naming the property to report.
        reduction
            Reduction to apply to the tuple keys of the property.
        accumulation
            Whether the property is reported per date or accumulated over time.
        """
        label = attribute
        if accumulation is ReportAccumulationID.CUMULATIVE:
            label = f"Cumulative{attribute}"

        if label not in self.attributes:
            self.attributes.append(label)
            self.results.append(attribute_to_instance_name(attribute))
            self.reductions.append(reduction)
            self.accumulations.append(accumulation)
