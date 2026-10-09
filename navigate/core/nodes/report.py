# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which node properties to export at the end of a simulation.

navigate.output.report_writer.write_report writes the Excel/CSV files from the
SimulationResults of a finished run. The Report node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core import assign_id
from navigate.core.enum_ import FileFormatID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_report import GLOBAL_PROFILE_KEY, NodeReport
from navigate.core.node_type import REPORT


class Report(Node):
    """Hold the node properties to export and the file format to export them in."""

    def __init__(self, name: str) -> None:
        super().__init__(name, REPORT)

        # external variables -----------------------------------------------------------
        self.directory: str | None = None
        self.file_format: FileFormatID = FileFormatID.XLSX

        # internal variables -----------------------------------------------------------
        self.global_reports: dict[str, NodeReport] = {}
        self.fleet_reports: dict[str, NodeReport] = {}
        self.levy_reports: dict[str, NodeReport] = {}
        self.plant_reports: dict[str, NodeReport] = {}
        self.port_reports: dict[str, NodeReport] = {}
        self.producer_reports: dict[str, NodeReport] = {}
        self.regulation_reports: dict[str, NodeReport] = {}
        self.vessel_reports: dict[str, NodeReport] = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_directory(self, directory: str) -> None:
        """Set the directory for where to export the report."""
        self.directory = directory

    def set_file_format(self, file_format: str) -> None:
        """Set the file format for report export."""
        self.file_format = assign_id(file_format, FileFormatID)

    # external methods (DSL commands) --------------------------------------------------
    def add_property(self, attribute: str, reduce: str | None = None) -> None:
        """Record a global property to export."""
        self._add_property(
            GLOBAL_PROFILE_KEY, self.global_reports, attribute, reduce=reduce
        )

    def add_fleet_property(
        self, fleet_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more fleets to export."""
        self._add_property(fleet_name, self.fleet_reports, attribute, reduce=reduce)

    def add_levy_property(
        self, levy_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more levies to export."""
        self._add_property(levy_name, self.levy_reports, attribute, reduce=reduce)

    def add_plant_property(
        self, plant_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more plants to export."""
        self._add_property(plant_name, self.plant_reports, attribute, reduce=reduce)

    def add_port_property(
        self, port_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more ports to export."""
        self._add_property(port_name, self.port_reports, attribute, reduce=reduce)

    def add_producer_property(
        self, producer_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more producers to export."""
        self._add_property(
            producer_name, self.producer_reports, attribute, reduce=reduce
        )

    def add_regulation_property(
        self, regulation_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more regulations to export."""
        self._add_property(
            regulation_name, self.regulation_reports, attribute, reduce=reduce
        )

    def add_vessel_property(
        self, vessel_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """Record a property of one or more vessels to export."""
        self._add_property(vessel_name, self.vessel_reports, attribute, reduce=reduce)

    # internal methods -----------------------------------------------------------------
    @staticmethod
    def _add_property(
        node_name: str,
        assignment_dict: dict[str, NodeReport],
        attribute: str,
        reduce: str | None = None,
    ) -> None:
        internal_reduce = ReportReduceID.NONE

        if reduce is not None:
            internal_reduce = assign_id(reduce, ReportReduceID)

        if node_name not in assignment_dict:
            assignment_dict[node_name] = NodeReport()

        assignment_dict[node_name].add_property(attribute, internal_reduce)
