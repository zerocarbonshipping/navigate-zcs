# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
The Report node collects which node properties to export at the end of a simulation and delegates
the actual Excel/CSV writing to the report writer. The Report node is not assigned on any other
node; it is driven by the simulation manager.
"""

import os

import openpyxl as xl

from navigate.core import assign_id
from navigate.core.enum_ import FileFormatID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_type import REPORT
from navigate.output.report_writer import (
    NodeReport,
    export_properties_csv,
    export_properties_xlsx,
    write_csv_report,
    write_xlsx_report,
)


class Report(Node):
    def __init__(self, name):
        super().__init__(name, REPORT)

        # external properties
        self._directory = None  # str, either relative to deck directory or absolute path
        self._file_format = FileFormatID.XLSX  # Default format for backward compatibility

        # reports
        self._manager_reports = {}
        self._fleet_reports = {}
        self._levy_reports = {}
        self._plant_reports = {}
        self._port_reports = {}
        self._producer_reports = {}
        self._regulation_reports = {}
        self._vessel_reports = {}

        # static properties
        self._wb = None
        self._csv_data = None

    # external attributes set through the input deck -------------------------------------------------------------------
    def set_directory(self, directory):
        """
        Set the directory for where to export the report. Can be either a relative or absolute path.
        The directory will be created automatically if it doesn't exist.

        Examples
        --------
        - "./plots"

        Parameters
        ----------
        directory : str
            Relative or absolute path.
        """
        self._directory = directory

    def set_file_format(self, file_format):
        """
        Set the file format for report export.

        Parameters
        ----------
        file_format : str or FileFormatID
            Format for export ('XLSX' or 'CSV').
        """
        if isinstance(file_format, str):
            self._file_format = assign_id(file_format, FileFormatID)
        else:
            self._file_format = file_format

    # external commands called in the input deck -----------------------------------------------------------------------
    def add_property(self, attribute, reduce=None):
        self._add_property('global', self._manager_reports, attribute, reduce=reduce)

    def add_fleet_property(self, fleet_name, attribute, reduce=None):
        self._add_property(fleet_name, self._fleet_reports, attribute, reduce=reduce)

    def add_levy_property(self, levy_name, attribute, reduce=None):
        self._add_property(levy_name, self._levy_reports, attribute, reduce=reduce)

    def add_plant_property(self, plant_name, attribute, reduce=None):
        self._add_property(plant_name, self._plant_reports, attribute, reduce=reduce)

    def add_port_property(self, port_name, attribute, reduce=None):
        self._add_property(port_name, self._port_reports, attribute, reduce=reduce)

    def add_producer_property(self, producer_name, attribute, reduce=None):
        self._add_property(producer_name, self._producer_reports, attribute, reduce=reduce)

    def add_regulation_property(self, regulation_name, attribute, reduce=None):
        self._add_property(regulation_name, self._regulation_reports, attribute, reduce=reduce)

    def add_vessel_property(self, vessel_name, attribute, reduce=None):
        self._add_property(vessel_name, self._vessel_reports, attribute, reduce=reduce)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):
        pass

    def start_export(self):
        if self._file_format == FileFormatID.XLSX:
            self._wb = xl.Workbook()
        else:  # CSV
            self._csv_data = {}

    def end_export(self, deck_directory, deck_name, dateline):
        if self._directory is not None:
            directory = os.path.join(deck_directory, self._directory)
        else:
            directory = deck_directory

        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        if self._file_format == FileFormatID.XLSX:
            write_xlsx_report(self._wb, directory, deck_name, self.name, dateline)
        else:
            write_csv_report(self._csv_data, directory, deck_name, self.name, dateline)

    def export_manager(self, manager):
        if self._manager_reports:
            self._export_sheet('Global', {manager.name: manager}, self._manager_reports)

    def export_fleets(self, fleets):
        if self._fleet_reports:
            self._export_sheet('Fleets', fleets, self._fleet_reports)

    def export_levies(self, levies):
        if self._levy_reports:
            self._export_sheet('Levies', levies, self._levy_reports)

    def export_plants(self, plants):
        if self._plant_reports:
            self._export_sheet('Plants', plants, self._plant_reports)

    def export_ports(self, ports):
        if self._port_reports:
            self._export_sheet('Ports', ports, self._port_reports)

    def export_producers(self, producers):
        if self._producer_reports:
            self._export_sheet('Producers', producers, self._producer_reports)

    def export_regulations(self, regulations):
        if self._regulation_reports:
            self._export_sheet('Regulations', regulations, self._regulation_reports)

    def export_vessels(self, vessels):
        if self._vessel_reports:
            self._export_sheet('Vessels', vessels, self._vessel_reports)

    def _export_sheet(self, title, nodes, extraction_dict):
        if self._file_format == FileFormatID.XLSX:
            ws = self._wb.create_sheet(title=title)
            export_properties_xlsx(ws, nodes, extraction_dict, self.name)
        else:
            export_properties_csv(title, nodes, extraction_dict, self.name, self._csv_data)

    @staticmethod
    def _add_property(node_name, assignment_dict, attribute, reduce=None):

        internal_reduce = ReportReduceID.NONE

        if reduce is not None:
            internal_reduce = assign_id(reduce, ReportReduceID)

        if node_name not in assignment_dict:
            assignment_dict[node_name] = NodeReport()

        assignment_dict[node_name].add_property(attribute, internal_reduce)
