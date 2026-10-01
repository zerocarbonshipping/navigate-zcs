# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Each node type's deck attributes, the sections allowing each, the required ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core.node_type import (
    BUNKER_OPTIONS,
    CONVERTER,
    CURVE,
    EMISSION,
    FEEDSTOCK,
    FLEET,
    FORECAST,
    FUEL,
    LEVY,
    MODEL_DEFINITION,
    PLANT,
    PLOT,
    PORT,
    POWER_SYSTEM,
    PROCESS,
    PRODUCER,
    REGION,
    REGULATION,
    REPORT,
    ROUTE,
    SOURCE,
    SURFACE,
    TANK,
    TECHNOLOGY,
    TIMETABLE,
    TRANSPORT,
    VARIABLE,
    VESSEL,
)
from navigate.exceptions import AttributeAssignmentError
from navigate.parser._keywords import SECTION_BOTH, SECTION_DEFINE, SECTION_NAME
from navigate.util import attribute_to_instance_name

if TYPE_CHECKING:
    from navigate.core.enum_ import SimulationSectionID
    from navigate.parser._keywords import AllowedSections

# high-level class attributes to multiple nodes ----------------------------------------
_CALCULATOR_ATTRIBUTES: dict[str, AllowedSections] = {
    "Addition": SECTION_BOTH,
    "Multiplier": SECTION_BOTH,
    "LowerBound": SECTION_BOTH,
    "UpperBound": SECTION_BOTH,
}

_TABLE_ATTRIBUTES: dict[str, AllowedSections] = {
    "Interpolate": SECTION_DEFINE,
    "Extrapolate": SECTION_DEFINE,
}

_TABLE1D_ATTRIBUTES: dict[str, AllowedSections] = {
    "Below": SECTION_DEFINE,
    "Above": SECTION_DEFINE,
}

_TABLE2D_ATTRIBUTES: dict[str, AllowedSections] = {"Outside": SECTION_DEFINE}

_MACHINERY_ATTRIBUTES: dict[str, AllowedSections] = {
    "Capex": SECTION_BOTH,
    "Opex": SECTION_BOTH,
    "Lifetime": SECTION_BOTH,
    "Replacement": SECTION_BOTH,
}

_POLICY_ATTRIBUTES: dict[str, AllowedSections] = {
    "Active": SECTION_BOTH,
    "Scheme": SECTION_DEFINE,
    "Jurisdiction": SECTION_DEFINE,
    "Emissions": SECTION_DEFINE,
    "Fuels": SECTION_DEFINE,
    "Scope": SECTION_DEFINE,
    "EmissionsLifetime": SECTION_DEFINE,
    "IncludeSlip": SECTION_BOTH,
}

# nodes --------------------------------------------------------------------------------
_CONVERTER_ATTRIBUTES: dict[str, AllowedSections] = {
    **_MACHINERY_ATTRIBUTES,
    "PowerCapacity": SECTION_DEFINE,
    "MinimumLoad": SECTION_DEFINE,
    "MainFuelTypes": SECTION_DEFINE,
    "PilotFuelTypes": SECTION_DEFINE,
    "MinimumPilotFuel": SECTION_BOTH,
    "Efficiency": SECTION_BOTH,
}

_CURVE_ATTRIBUTES: dict[str, AllowedSections] = {
    "Table": SECTION_BOTH,
    **_CALCULATOR_ATTRIBUTES,
    **_TABLE_ATTRIBUTES,
    **_TABLE1D_ATTRIBUTES,
}

_EMISSION_ATTRIBUTES: dict[str, AllowedSections] = {
    "GlobalWarmingPotential": SECTION_DEFINE,
    "FuelType": SECTION_DEFINE,
}

_FEEDSTOCK_ATTRIBUTES: dict[str, AllowedSections] = {}

_FLEET_ATTRIBUTES: dict[str, AllowedSections] = {
    "Vessels": SECTION_DEFINE,
    "InitialVessels": SECTION_DEFINE,
    "TradeGrowth": SECTION_DEFINE,
    "InitialSplit": SECTION_DEFINE,
    "InitialAgeDistribution": SECTION_DEFINE,
    "Orderbooks": SECTION_DEFINE,
    "Technologies": SECTION_DEFINE,
    "TechnologyCostOfCapital": SECTION_BOTH,
    "TechnologyHorizon": SECTION_BOTH,
    "SpeedHorizon": SECTION_BOTH,
    "FixedScrapRate": SECTION_BOTH,
    "AllowSecondaryScrapping": SECTION_BOTH,
    "Inertia": SECTION_BOTH,
    "Memory": SECTION_BOTH,
    "InterFuelSensitivity": SECTION_BOTH,
    "IntraFuelSensitivity": SECTION_BOTH,
    "AllowSpeedManagement": SECTION_BOTH,
    "MaximumSpeedChange": SECTION_BOTH,
    "SpeedAlignment": SECTION_BOTH,
    "AssumeReferenceSpeedOptimal": SECTION_BOTH,
    "TechnologySensitivity": SECTION_BOTH,
    "RetrofitFrequency": SECTION_BOTH,
    "FuelConversionSensitivity": SECTION_BOTH,
    "FuelConversionMinimumAge": SECTION_BOTH,
    "AllowTechnologyApproximation": SECTION_BOTH,
}

_FORECAST_ATTRIBUTES: dict[str, AllowedSections] = {
    "Table": SECTION_BOTH,
    **_CALCULATOR_ATTRIBUTES,
    **_TABLE_ATTRIBUTES,
    **_TABLE1D_ATTRIBUTES,
}

_FUEL_ATTRIBUTES: dict[str, AllowedSections] = {
    "FuelType": SECTION_DEFINE,
    "LiquidMarket": SECTION_DEFINE,
    "LowerHeatingValue": SECTION_DEFINE,
    "MassDensity": SECTION_DEFINE,
}

_LEVY_ATTRIBUTES: dict[str, AllowedSections] = {
    **_POLICY_ATTRIBUTES,
    "Level": SECTION_BOTH,
    "LowerThreshold": SECTION_BOTH,
    "UpperThreshold": SECTION_BOTH,
}

_PLANT_ATTRIBUTES: dict[str, AllowedSections] = {
    "Fuel": SECTION_DEFINE,
    "Process": SECTION_DEFINE,
    "Source": SECTION_DEFINE,
    "Region": SECTION_DEFINE,
    "CostOfCapital": SECTION_BOTH,
    "Capacity": SECTION_BOTH,
    "Uptime": SECTION_BOTH,
    "Lifetime": SECTION_BOTH,
    "LeadTime": SECTION_BOTH,
}

_PLOT_ATTRIBUTES: dict[str, AllowedSections] = {"Directory": SECTION_DEFINE}

_PORT_ATTRIBUTES: dict[str, AllowedSections] = {
    "ShorePowerCost": SECTION_BOTH,
    "ShorePowerConnectionShare": SECTION_BOTH,
}

_POWER_SYSTEM_ATTRIBUTES: dict[str, AllowedSections] = {
    **_MACHINERY_ATTRIBUTES,
    "Propulsion": SECTION_DEFINE,
    "Electrical": SECTION_DEFINE,
    "Heat": SECTION_DEFINE,
}

_PROCESS_ATTRIBUTES: dict[str, AllowedSections] = {
    "Feeds": SECTION_DEFINE,
    "Conversions": SECTION_BOTH,
}

_PRODUCER_ATTRIBUTES: dict[str, AllowedSections] = {
    "Plants": SECTION_DEFINE,
    "InitialCapacity": SECTION_DEFINE,
    "InitialAgeDistribution": SECTION_DEFINE,
    "Inertia": SECTION_BOTH,
    "MinimumOfftakeDuration": SECTION_BOTH,
    "FuelDemandSensitivity": SECTION_BOTH,
    "FuelCostSensitivity": SECTION_BOTH,
    "MaximumDevelopment": SECTION_BOTH,
    "MaximumRampUp": SECTION_BOTH,
    "JumpStartFraction": SECTION_BOTH,
}

_REGION_ATTRIBUTES: dict[str, AllowedSections] = {}

_REGULATION_ATTRIBUTES: dict[str, AllowedSections] = {
    **_POLICY_ATTRIBUTES,
    "Measure": SECTION_DEFINE,
    "IntraFraction": SECTION_BOTH,
    "InterFraction": SECTION_BOTH,
    "ExtraFraction": SECTION_BOTH,
    "RemedialCost": SECTION_BOTH,
    "FlexibilityHorizon": SECTION_BOTH,
    "AllowThresholdAdjustment": SECTION_BOTH,
}

_REPORT_ATTRIBUTES: dict[str, AllowedSections] = {
    "Directory": SECTION_DEFINE,
    "FileFormat": SECTION_DEFINE,
}

_ROUTE_ATTRIBUTES: dict[str, AllowedSections] = {
    "RouteType": SECTION_DEFINE,
    "Ports": SECTION_DEFINE,
    "TimeAtSea": SECTION_BOTH,
    "PortDurations": SECTION_BOTH,
    "PortCalls": SECTION_BOTH,
    "Distances": SECTION_DEFINE,
    "ConditionDistribution": SECTION_BOTH,
    "Speeds": SECTION_BOTH,
    "CapacityUtilizations": SECTION_BOTH,
}

_SOURCE_ATTRIBUTES: dict[str, AllowedSections] = {"Dependency": SECTION_DEFINE}

_SURFACE_ATTRIBUTES: dict[str, AllowedSections] = {
    "Table": SECTION_BOTH,
    **_CALCULATOR_ATTRIBUTES,
    **_TABLE_ATTRIBUTES,
    **_TABLE2D_ATTRIBUTES,
}

_TANK_ATTRIBUTES: dict[str, AllowedSections] = {
    **_MACHINERY_ATTRIBUTES,
    "FuelTypes": SECTION_DEFINE,
    "Size": SECTION_DEFINE,
}

_TECHNOLOGY_ATTRIBUTES: dict[str, AllowedSections] = {
    **_MACHINERY_ATTRIBUTES,
    "ShorePowerCapacity": SECTION_BOTH,
}


_TIMETABLE_ATTRIBUTES: dict[str, AllowedSections] = {
    "Table": SECTION_BOTH,
    **_CALCULATOR_ATTRIBUTES,
    **_TABLE_ATTRIBUTES,
    **_TABLE2D_ATTRIBUTES,
}

_TRANSPORT_ATTRIBUTES: dict[str, AllowedSections] = {}

_VARIABLE_ATTRIBUTES: dict[str, AllowedSections] = {
    **_CALCULATOR_ATTRIBUTES,
    "Value": SECTION_BOTH,
}

_VESSEL_ATTRIBUTES: dict[str, AllowedSections] = {
    "PropulsionLoad": SECTION_DEFINE,
    "ElectricalLoadAtSea": SECTION_DEFINE,
    "ElectricalLoadInPort": SECTION_DEFINE,
    "HeatLoadAtSea": SECTION_DEFINE,
    "HeatLoadInPort": SECTION_DEFINE,
    "FuelType": SECTION_DEFINE,
    "PowerSystem": SECTION_DEFINE,
    "Tanks": SECTION_DEFINE,
    "Route": SECTION_DEFINE,
    "NominalCapacity": SECTION_DEFINE,
    "Lifetime": SECTION_BOTH,
    "LeadTime": SECTION_BOTH,
    "Capex": SECTION_BOTH,
    "Opex": SECTION_BOTH,
    "CostOfCapital": SECTION_BOTH,
}

# general nodes ------------------------------------------------------------------------
_MODEL_DEFINITION_ATTRIBUTES: dict[str, AllowedSections] = {
    "StartDate": SECTION_DEFINE,
    "EmissionsLifetime": SECTION_DEFINE,
}

_BUNKER_OPTIONS_ATTRIBUTES: dict[str, AllowedSections] = {
    "Solver": SECTION_DEFINE,
    "SolverMethod": SECTION_DEFINE,
    "SolutionTolerance": SECTION_DEFINE,
    "Threads": SECTION_DEFINE,
    "FairShareMaximumIterations": SECTION_DEFINE,
    "FairShareTolerance": SECTION_DEFINE,
}

# assemble dicts -----------------------------------------------------------------------
NODE_ATTRIBUTE_SECTIONS: dict[str, dict[str, AllowedSections]] = {
    CONVERTER: _CONVERTER_ATTRIBUTES,
    CURVE: _CURVE_ATTRIBUTES,
    EMISSION: _EMISSION_ATTRIBUTES,
    FEEDSTOCK: _FEEDSTOCK_ATTRIBUTES,
    FLEET: _FLEET_ATTRIBUTES,
    FORECAST: _FORECAST_ATTRIBUTES,
    FUEL: _FUEL_ATTRIBUTES,
    LEVY: _LEVY_ATTRIBUTES,
    PLANT: _PLANT_ATTRIBUTES,
    PLOT: _PLOT_ATTRIBUTES,
    PORT: _PORT_ATTRIBUTES,
    POWER_SYSTEM: _POWER_SYSTEM_ATTRIBUTES,
    PROCESS: _PROCESS_ATTRIBUTES,
    PRODUCER: _PRODUCER_ATTRIBUTES,
    REGION: _REGION_ATTRIBUTES,
    REGULATION: _REGULATION_ATTRIBUTES,
    REPORT: _REPORT_ATTRIBUTES,
    ROUTE: _ROUTE_ATTRIBUTES,
    SOURCE: _SOURCE_ATTRIBUTES,
    SURFACE: _SURFACE_ATTRIBUTES,
    TANK: _TANK_ATTRIBUTES,
    TECHNOLOGY: _TECHNOLOGY_ATTRIBUTES,
    TIMETABLE: _TIMETABLE_ATTRIBUTES,
    TRANSPORT: _TRANSPORT_ATTRIBUTES,
    VARIABLE: _VARIABLE_ATTRIBUTES,
    VESSEL: _VESSEL_ATTRIBUTES,
}

GENERAL_NODE_ATTRIBUTE_SECTIONS: dict[str, dict[str, AllowedSections]] = {
    MODEL_DEFINITION: _MODEL_DEFINITION_ATTRIBUTES,
    BUNKER_OPTIONS: _BUNKER_OPTIONS_ATTRIBUTES,
}


# required attributes ------------------------------------------------------------------
# a node must be assigned each of these in DEFINE; the parser checks them before any
# lifecycle hook runs, so the node declares them without a None default
_TABLE_REQUIRED = ("Table",)
_POLICY_REQUIRED = ("Scheme",)

NODE_REQUIRED_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    CONVERTER: ("PowerCapacity", "Efficiency"),
    CURVE: _TABLE_REQUIRED,
    FLEET: ("InitialVessels", "InterFuelSensitivity", "IntraFuelSensitivity"),
    FORECAST: _TABLE_REQUIRED,
    FUEL: ("FuelType", "LowerHeatingValue", "MassDensity"),
    LEVY: _POLICY_REQUIRED,
    PLANT: ("Fuel", "Process", "Region", "Source", "Capacity"),
    POWER_SYSTEM: ("Propulsion", "Electrical", "Heat"),
    PRODUCER: ("FuelDemandSensitivity", "FuelCostSensitivity", "MaximumDevelopment"),
    REGULATION: (*_POLICY_REQUIRED, "Measure"),
    ROUTE: ("RouteType",),
    SOURCE: ("Dependency",),
    SURFACE: _TABLE_REQUIRED,
    TANK: ("FuelTypes", "Size"),
    TIMETABLE: _TABLE_REQUIRED,
    VESSEL: ("PowerSystem", "Route", "NominalCapacity"),
}

GENERAL_NODE_REQUIRED_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    MODEL_DEFINITION: ("StartDate",)
}


# methods ------------------------------------------------------------------------------
def instance_to_dsl_name(node_type: str, attribute_name: str) -> str:
    """
    Look up the DSL attribute that assigns a node instance attribute.

    Parameters
    ----------
    node_type
        The node type.
    attribute_name
        The instance-attribute name.

    Returns
    -------
    str
        The DSL attribute name, or the instance-attribute name itself when no
        DSL attribute assigns it.
    """
    for dsl_name in NODE_ATTRIBUTE_SECTIONS[node_type]:
        if attribute_to_instance_name(dsl_name) == attribute_name:
            return dsl_name

    return attribute_name


def check_node_attribute_is_allowed(
    node_type: str, attribute_name: str, section: SimulationSectionID
) -> None:
    """
    Raise if a node type may not set an attribute in a section.

    Parameters
    ----------
    node_type
        The node type.
    attribute_name
        The name of the attribute.
    section
        The section (DEFINE or EVENTS) at which the attribute is read.
    """
    allowed_attributes = NODE_ATTRIBUTE_SECTIONS[node_type]

    if attribute_name not in allowed_attributes:
        raise AttributeAssignmentError(
            f"Nodes of type '{node_type}' has no attribute '{attribute_name}'"
        )

    if section not in allowed_attributes[attribute_name]:
        raise AttributeAssignmentError(
            f"Nodes of type '{node_type}' does not allow setting"
            f" attribute '{attribute_name}' in '{SECTION_NAME[section]}'"
        )


def check_general_node_attribute_is_allowed(
    type_: str, attribute_name: str, section: SimulationSectionID
) -> None:
    """
    Raise if a general node type may not set an attribute in a section.

    Parameters
    ----------
    type_
        The general node type.
    attribute_name
        The name of the attribute.
    section
        The section (DEFINE or EVENTS) at which the attribute is read.
    """
    allowed_attributes = GENERAL_NODE_ATTRIBUTE_SECTIONS[type_]

    if attribute_name not in allowed_attributes:
        raise AttributeAssignmentError(f"'{type_}' has no attribute '{attribute_name}'")

    if section not in allowed_attributes[attribute_name]:
        raise AttributeAssignmentError(
            f"'{type_}' does not allow setting attribute '{attribute_name}' in "
            f"'{SECTION_NAME[section]}'"
        )
