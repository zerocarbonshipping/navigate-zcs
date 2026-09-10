# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The per-node collection of report properties gathered by the Report node and consumed by
navigate.output.report_writer.
"""

from navigate.core.enum_ import ReportReduceID
from navigate.util import attribute_to_setter


class NodeReport:
    def __init__(self) -> None:

        self.attributes: list[str] = []
        self.getters: list[str] = []
        self.reduce: list[ReportReduceID] = []

    def add_property(self, attribute: str, reduce: ReportReduceID) -> None:
        if attribute not in self.attributes:
            self.attributes.append(attribute)
            self.getters.append(attribute_to_setter(attribute, method='get'))
            self.reduce.append(reduce)
