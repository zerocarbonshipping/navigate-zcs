# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect per-node report properties gathered by the Report node.

navigate.output.report_writer consumes them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.util import attribute_to_setter

if TYPE_CHECKING:
    from navigate.core.enum_ import ReportReduceID


class NodeReport:
    """The report properties requested for one node, in the order they were added."""

    def __init__(self) -> None:
        self.attributes: list[str] = []
        self.getters: list[str] = []
        self.reductions: list[ReportReduceID] = []

    def add_property(self, attribute: str, reduction: ReportReduceID) -> None:
        """
        Record a report property, ignoring one already recorded for this node.

        Parameters
        ----------
        attribute
            Deck-facing attribute token naming the property to report.
        reduction
            Reduction to apply to the tuple keys of the property.
        """
        if attribute not in self.attributes:
            self.attributes.append(attribute)
            self.getters.append(attribute_to_setter(attribute, method="get"))
            self.reductions.append(reduction)
