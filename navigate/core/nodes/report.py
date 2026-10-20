# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Collect which node properties to export at the end of a simulation.

navigate.output.report_writer.write_report writes the Excel/CSV files from the
SimulationResults of a finished run. The Report node is not assigned on any other node.
A property token must name a result of the profile class of the nodes the command
reports on; each command checks its token as it runs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import SECTION_DEFINE, assign_id, deck_attribute, deck_command
from navigate.core.enum_ import FileFormatID, ReportAccumulationID, ReportReduceID
from navigate.core.node import Node
from navigate.core.node_report import GLOBAL_PROFILE_KEY, NodeReport
from navigate.core.node_type import REPORT
from navigate.core.profiles import (
    FleetProfile,
    GlobalProfile,
    LevyProfile,
    PlantProfile,
    PortProfile,
    ProducerProfile,
    RegulationProfile,
    VesselProfile,
    result_names,
)
from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from navigate.core.profiles._base_profile import _BaseProfile

# the profile class whose results each Report command reports
PROFILE_CLASSES: dict[str, type[_BaseProfile]] = {
    "add_property": GlobalProfile,
    "add_fleet_property": FleetProfile,
    "add_levy_property": LevyProfile,
    "add_plant_property": PlantProfile,
    "add_port_property": PortProfile,
    "add_producer_property": ProducerProfile,
    "add_regulation_property": RegulationProfile,
    "add_vessel_property": VesselProfile,
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
        If the command's profile class has no result the token names.
    """
    if attribute_to_instance_name(token) not in result_names(PROFILE_CLASSES[command]):
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
        """Set the directory for where to export the report."""
        self.directory = directory

    @deck_attribute(SECTION_DEFINE)
    def set_file_format(self, file_format: str) -> None:
        """Set the file format for report export."""
        self.file_format = assign_id(file_format, FileFormatID)

    # external methods (DSL commands) --------------------------------------------------
    @deck_command(SECTION_DEFINE)
    def add_property(
        self,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a global property to export."""
        self._add_property(
            "add_property",
            GLOBAL_PROFILE_KEY,
            self.global_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_fleet_property(
        self,
        fleet_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more fleets to export."""
        self._add_property(
            "add_fleet_property",
            fleet_name,
            self.fleet_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_levy_property(
        self,
        levy_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more levies to export."""
        self._add_property(
            "add_levy_property",
            levy_name,
            self.levy_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_plant_property(
        self,
        plant_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more plants to export."""
        self._add_property(
            "add_plant_property",
            plant_name,
            self.plant_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_port_property(
        self,
        port_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more ports to export."""
        self._add_property(
            "add_port_property",
            port_name,
            self.port_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_producer_property(
        self,
        producer_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more producers to export."""
        self._add_property(
            "add_producer_property",
            producer_name,
            self.producer_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_regulation_property(
        self,
        regulation_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more regulations to export."""
        self._add_property(
            "add_regulation_property",
            regulation_name,
            self.regulation_reports,
            attribute,
            reduce,
            accumulate,
        )

    @deck_command(SECTION_DEFINE)
    def add_vessel_property(
        self,
        vessel_name: str,
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        """Record a property of one or more vessels to export."""
        self._add_property(
            "add_vessel_property",
            vessel_name,
            self.vessel_reports,
            attribute,
            reduce,
            accumulate,
        )

    # internal methods -----------------------------------------------------------------
    @staticmethod
    def _add_property(
        command: str,
        node_name: str,
        assignment_dict: dict[str, NodeReport],
        attribute: str,
        reduce: str | None = None,
        accumulate: str | None = None,
    ) -> None:
        check_report_property(command, attribute)

        internal_reduce = ReportReduceID.NONE
        internal_accumulate = ReportAccumulationID.NONE

        if reduce is not None:
            internal_reduce = assign_id(reduce, ReportReduceID)

        if accumulate is not None:
            internal_accumulate = assign_id(accumulate, ReportAccumulationID)

        if node_name not in assignment_dict:
            assignment_dict[node_name] = NodeReport()

        assignment_dict[node_name].add_property(
            attribute, internal_reduce, internal_accumulate
        )
