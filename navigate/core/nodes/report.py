# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which node properties to export at the end of a simulation.

The actual Excel/CSV writing is done by navigate.output.report_writer.write_report,
driven by the simulation manager. The Report node is not assigned on any other node.
"""

from __future__ import annotations

from navigate.core import assign_id
from navigate.core.enum_ import FileFormatID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_report import NodeReport
from navigate.core.node_type import REPORT


class Report(Node):
    """Hold the node properties to export and the file format to export them in."""

    def __init__(self, name: str) -> None:
        super().__init__(name, REPORT)

        # external variables -----------------------------------------------------------
        self.directory: str | None = None
        self.file_format: FileFormatID = FileFormatID.XLSX

        # internal variables -----------------------------------------------------------
        self.manager_reports: dict[str, NodeReport] = {}
        self.fleet_reports: dict[str, NodeReport] = {}
        self.levy_reports: dict[str, NodeReport] = {}
        self.plant_reports: dict[str, NodeReport] = {}
        self.port_reports: dict[str, NodeReport] = {}
        self.producer_reports: dict[str, NodeReport] = {}
        self.regulation_reports: dict[str, NodeReport] = {}
        self.vessel_reports: dict[str, NodeReport] = {}

    # external methods (DSL attributes) ------------------------------------------------
    def set_directory(self, directory: str) -> None:
        """
        Set the directory for where to export the report.

        Can be either a relative or absolute path. The directory will be created
        automatically if it doesn't exist.

        Examples
        --------
        - "./plots"

        Parameters
        ----------
        directory
            Relative or absolute path.
        """
        self.directory = directory

    def set_file_format(self, file_format: str) -> None:
        """
        Set the file format for report export.

        Parameters
        ----------
        file_format
            Format for export ('XLSX' or 'CSV').
        """
        self.file_format = assign_id(file_format, FileFormatID)

    # external methods (DSL commands) --------------------------------------------------
    def add_property(self, attribute: str, reduce: str | None = None) -> None:
        """
        Record a global property to export.

        Ignored if the property was already recorded for this report.

        Examples
        --------
        - add_property(ConsumedEnergy)

        Parameters
        ----------
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property("global", self.manager_reports, attribute, reduce=reduce)

    def add_fleet_property(
        self, fleet_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more fleets to export.

        Ignored for a fleet the property was already recorded for.

        Examples
        --------
        - add_fleet_property("*", CargoMiles)

        Parameters
        ----------
        fleet_name
            Name of the fleet the property applies to; a wildcard matches
            several fleets when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(fleet_name, self.fleet_reports, attribute, reduce=reduce)

    def add_levy_property(
        self, levy_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more levies to export.

        Ignored for a levy the property was already recorded for.

        Examples
        --------
        - add_levy_property("*", Collected)

        Parameters
        ----------
        levy_name
            Name of the levy the property applies to; a wildcard matches
            several levies when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(levy_name, self.levy_reports, attribute, reduce=reduce)

    def add_plant_property(
        self, plant_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more plants to export.

        Ignored for a plant the property was already recorded for.

        Examples
        --------
        - add_plant_property("*", InstantaneousCost)

        Parameters
        ----------
        plant_name
            Name of the plant the property applies to; a wildcard matches
            several plants when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(plant_name, self.plant_reports, attribute, reduce=reduce)

    def add_port_property(
        self, port_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more ports to export.

        Ignored for a port the property was already recorded for.

        Examples
        --------
        - add_port_property("*", BunkerPrice)

        Parameters
        ----------
        port_name
            Name of the port the property applies to; a wildcard matches
            several ports when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(port_name, self.port_reports, attribute, reduce=reduce)

    def add_producer_property(
        self, producer_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more producers to export.

        Ignored for a producer the property was already recorded for.

        Examples
        --------
        - add_producer_property("*", Development)

        Parameters
        ----------
        producer_name
            Name of the producer the property applies to; a wildcard matches
            several producers when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(
            producer_name, self.producer_reports, attribute, reduce=reduce
        )

    def add_regulation_property(
        self, regulation_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more regulations to export.

        Ignored for a regulation the property was already recorded for.

        Examples
        --------
        - add_regulation_property("*", RemedialUnits)

        Parameters
        ----------
        regulation_name
            Name of the regulation the property applies to; a wildcard matches
            several regulations when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
        self._add_property(
            regulation_name, self.regulation_reports, attribute, reduce=reduce
        )

    def add_vessel_property(
        self, vessel_name: str, attribute: str, reduce: str | None = None
    ) -> None:
        """
        Record a property of one or more vessels to export.

        Ignored for a vessel the property was already recorded for.

        Examples
        --------
        - add_vessel_property("*", AssetCharterRate)

        Parameters
        ----------
        vessel_name
            Name of the vessel the property applies to; a wildcard matches
            several vessels when the report is written.
        attribute
            Deck-facing attribute token naming the property to export; see the
            reference manual for the properties allowed on this command.
        reduce
            Reduction axis applied to the tuple keys of the property; None
            applies no reduction.
        """
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
