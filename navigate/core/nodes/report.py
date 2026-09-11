# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The Report node collects which node properties to export at the end of a simulation; the
actual Excel/CSV writing is done by navigate.output.report_writer.write_report, driven
by the simulation manager. The Report node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core import assign_id
from navigate.core.enum_ import FileFormatID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_report import NodeReport
from navigate.core.node_type import REPORT


class Report(Node):
    def __init__(self, name):
        super().__init__(name, REPORT)

        # external variables -----------------------------------------------------------
        self.directory = None  # str, either relative to deck directory or absolute path
        self.file_format = FileFormatID.XLSX

        # internal variables -----------------------------------------------------------
        self.manager_reports = {}
        self.fleet_reports = {}
        self.levy_reports = {}
        self.plant_reports = {}
        self.port_reports = {}
        self.producer_reports = {}
        self.regulation_reports = {}
        self.vessel_reports = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_directory(self, directory):
        """
        Set the directory for where to export the report. Can be either a relative or
        absolute path. The directory will be created automatically if it doesn't exist.

        Examples
        --------
        - "./plots"

        Parameters
        ----------
        directory : str
            Relative or absolute path.
        """
        self.directory = directory

    def set_file_format(self, file_format):
        """
        Set the file format for report export.

        Parameters
        ----------
        file_format : str or FileFormatID
            Format for export ('XLSX' or 'CSV').
        """
        if isinstance(file_format, str):
            self.file_format = assign_id(file_format, FileFormatID)
        else:
            self.file_format = file_format

    # external methods (DSL commands) --------------------------------------------------
    def add_property(self, attribute, reduce=None):
        self._add_property("global", self.manager_reports, attribute, reduce=reduce)

    def add_fleet_property(self, fleet_name, attribute, reduce=None):
        self._add_property(fleet_name, self.fleet_reports, attribute, reduce=reduce)

    def add_levy_property(self, levy_name, attribute, reduce=None):
        self._add_property(levy_name, self.levy_reports, attribute, reduce=reduce)

    def add_plant_property(self, plant_name, attribute, reduce=None):
        self._add_property(plant_name, self.plant_reports, attribute, reduce=reduce)

    def add_port_property(self, port_name, attribute, reduce=None):
        self._add_property(port_name, self.port_reports, attribute, reduce=reduce)

    def add_producer_property(self, producer_name, attribute, reduce=None):
        self._add_property(
            producer_name, self.producer_reports, attribute, reduce=reduce
        )

    def add_regulation_property(self, regulation_name, attribute, reduce=None):
        self._add_property(
            regulation_name, self.regulation_reports, attribute, reduce=reduce
        )

    def add_vessel_property(self, vessel_name, attribute, reduce=None):
        self._add_property(vessel_name, self.vessel_reports, attribute, reduce=reduce)

    # internal methods -----------------------------------------------------------------
    @staticmethod
    def _add_property(node_name, assignment_dict, attribute, reduce=None):

        internal_reduce = ReportReduceID.NONE

        if reduce is not None:
            internal_reduce = assign_id(reduce, ReportReduceID)

        if node_name not in assignment_dict:
            assignment_dict[node_name] = NodeReport()

        assignment_dict[node_name].add_property(attribute, internal_reduce)
