# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which node properties to export at the end of a simulation.

navigate.output.report_writer.write_report writes the Excel/CSV files from the
SimulationResults of a finished run. No other node refers to the Report node.
A property token must name a result of the results class of the nodes the command
reports on; each command checks its token as it runs.
"""

from __future__ import annotations

from navigate.core import SECTION_DEFINE, assign_id, deck_attribute, deck_command
from navigate.core.enum_ import FileFormatID, ReportAccumulationID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_report import GLOBAL_RESULTS_KEY, NodeReport
from navigate.core.node_type import REPORT
from navigate.core.results import (
    BaseResults,
    FleetResults,
    GlobalResults,
    LevyResults,
    PlantResults,
    PortResults,
    ProducerResults,
    RegulationResults,
    VesselResults,
    result_names,
)
from navigate.util import attribute_to_instance_name

# the results class each Report command reports from
RESULTS_CLASSES: dict[str, type[BaseResults]] = {
    "add_property": GlobalResults,
    "add_fleet_property": FleetResults,
    "add_levy_property": LevyResults,
    "add_plant_property": PlantResults,
    "add_port_property": PortResults,
    "add_producer_property": ProducerResults,
    "add_regulation_property": RegulationResults,
    "add_vessel_property": VesselResults,
}


def check_report_property(command: str, token: str) -> None:
    """
    Check that a Report command reports the property a token names.

    Parameters
    ----------
    command
        Name of the Report command, e.g. ``add_fleet_property``.
    token
        The property token as a deck writes it, e.g. ``CargoMiles``.

    Raises
    ------
    ValueError
        If the command's results class has no result the token names.
    """
    if attribute_to_instance_name(token) not in result_names(RESULTS_CLASSES[command]):
        raise ValueError(
            f"does not report the property '{token}'; the properties {command}"
            " reports are listed in the 'Report Node Properties' appendix on the"
            " Report page of the reference manual"
        )


class Report(Node):
    """Hold the node properties to export and the file format to export them in."""

    type = REPORT

    def __init__(self, name: str) -> None:
        super().__init__(name)

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
    @deck_attribute(SECTION_DEFINE)
    def set_directory(self, directory: str) -> None:
        """Set the directory to export the report to."""
        self.directory = directory

    @deck_attribute(SECTION_DEFINE)
    def set_file_format(self, file_format: str) -> None:
        """Set the file format to export the report in."""
        self.file_format = assign_id(file_format, FileFormatID)

    # external methods (DSL commands) --------------------------------------------------
    @deck_command(SECTION_DEFINE)
    def add_property(
        self,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a global property to export."""
        self._add_property(
            "add_property",
            self.global_reports,
            GLOBAL_RESULTS_KEY,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_fleet_property(
        self,
        fleet_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more fleets to export."""
        self._add_property(
            "add_fleet_property",
            self.fleet_reports,
            fleet_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_levy_property(
        self,
        levy_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more levies to export."""
        self._add_property(
            "add_levy_property",
            self.levy_reports,
            levy_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_plant_property(
        self,
        plant_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more plants to export."""
        self._add_property(
            "add_plant_property",
            self.plant_reports,
            plant_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_port_property(
        self,
        port_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more ports to export."""
        self._add_property(
            "add_port_property",
            self.port_reports,
            port_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_producer_property(
        self,
        producer_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more producers to export."""
        self._add_property(
            "add_producer_property",
            self.producer_reports,
            producer_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_regulation_property(
        self,
        regulation_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more regulations to export."""
        self._add_property(
            "add_regulation_property",
            self.regulation_reports,
            regulation_name,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_vessel_property(
        self,
        vessel_name: str,
        attribute: str,
        reduce: str = "NONE",
        accumulate: str = "NONE",
    ) -> None:
        """Record a property of one or more vessels to export."""
        self._add_property(
            "add_vessel_property",
            self.vessel_reports,
            vessel_name,
            attribute,
            reduce,
            accumulate,
        )

    # internal methods -----------------------------------------------------------------
    @staticmethod
    def _add_property(
        command: str,
        reports: dict[str, NodeReport],
        node_name: str,
        attribute: str,
        reduce: str,
        accumulate: str,
    ) -> None:
        check_report_property(command, attribute)

        reduction = assign_id(reduce, ReportReduceID)
        accumulation = assign_id(accumulate, ReportAccumulationID)

        report = reports.setdefault(node_name, NodeReport())
        report.add_property(attribute, reduction, accumulation)
