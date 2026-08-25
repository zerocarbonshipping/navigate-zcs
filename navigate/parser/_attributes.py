# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import navigate.core.id_ as id_
from navigate.exceptions import AttributeAssignmentError
from navigate.parser._keywords import SECTION_BOTH, SECTION_DEFINE, SECTION_NAME

# high-level class attributes to multiple nodes ------------------------------------------------------------------------
_CALCULATOR_ATTRIBUTES = {'Addition':   SECTION_BOTH,
                          'Multiplier': SECTION_BOTH,
                          'LowerBound': SECTION_BOTH,
                          'UpperBound': SECTION_BOTH}

_TABLE_ATTRIBUTES = {'Interpolate': SECTION_DEFINE,
                     'Extrapolate': SECTION_DEFINE}

_TABLE1D_ATTRIBUTES = {'Below': SECTION_DEFINE,
                       'Above': SECTION_DEFINE}

_TABLE2D_ATTRIBUTES = {'Outside': SECTION_DEFINE}

_MACHINERY_ATTRIBUTES = {'CAPEX':       SECTION_BOTH,
                         'OPEX':        SECTION_BOTH,
                         'Lifetime':    SECTION_BOTH,
                         'Replacement': SECTION_BOTH}

_POLICY_ATTRIBUTES = {'Active':                     SECTION_BOTH,
                      'Scheme':                     SECTION_DEFINE,
                      'Jurisdiction':               SECTION_DEFINE,
                      'Emissions':                  SECTION_DEFINE,
                      'Fuels':                      SECTION_DEFINE,
                      'Scope':                      SECTION_DEFINE,
                      'EmissionsLifetime':          SECTION_DEFINE,
                      'IncludeSlip':                SECTION_BOTH}

# nodes ----------------------------------------------------------------------------------------------------------------
_CONVERTER_ATTRIBUTES = {**_MACHINERY_ATTRIBUTES,
                         'PowerCapacity':    SECTION_DEFINE,
                         'MinimumLoad':      SECTION_DEFINE,
                         'MainFuelTypes':    SECTION_DEFINE,
                         'PilotFuelTypes':   SECTION_DEFINE,
                         'MinimumPilotFuel': SECTION_BOTH,
                         'Efficiency':       SECTION_BOTH}

_CURVE_ATTRIBUTES = {'Table': SECTION_BOTH,
                     **_CALCULATOR_ATTRIBUTES,
                     **_TABLE_ATTRIBUTES,
                     **_TABLE1D_ATTRIBUTES}

_EMISSION_ATTRIBUTES = {'GlobalWarmingPotential': SECTION_DEFINE,
                        'FuelType':               SECTION_DEFINE}

_FEEDSTOCK_ATTRIBUTES = {}

_FLEET_ATTRIBUTES = {'Vessels':                            SECTION_DEFINE,
                     'InitialVessels':                     SECTION_DEFINE,
                     'TradeGrowth':                        SECTION_DEFINE,
                     'InitialSplit':                       SECTION_DEFINE,
                     'InitialAgeDistribution':             SECTION_DEFINE,
                     'Orderbooks':                         SECTION_DEFINE,
                     'Technologies':                       SECTION_DEFINE,
                     'TechnologyCostOfCapital':            SECTION_BOTH,
                     'TechnologyHorizon':                  SECTION_BOTH,
                     'SpeedHorizon':                       SECTION_BOTH,
                     'FixedScrapRate':                     SECTION_BOTH,
                     'AllowSecondaryScrapping':            SECTION_BOTH,
                     'Inertia':                            SECTION_BOTH,
                     'Memory':                             SECTION_BOTH,
                     'InterFuelSensitivity':               SECTION_BOTH,
                     'IntraFuelSensitivity':               SECTION_BOTH,
                     'AllowSpeedManagement':               SECTION_BOTH,
                     'MaximumSpeedChange':                 SECTION_BOTH,
                     'SpeedAlignment':                     SECTION_BOTH,
                     'AssumeReferenceSpeedOptimal':        SECTION_BOTH,
                     'TechnologySensitivity':              SECTION_BOTH,
                     'RetrofitFrequency':                  SECTION_BOTH,
                     'FuelConversionSensitivity':          SECTION_BOTH,
                     'FuelConversionMinimumAge':           SECTION_BOTH,
                     'AllowTechnologyApproximation':       SECTION_BOTH}

_FORECAST_ATTRIBUTES = {'Table': SECTION_BOTH,
                        **_CALCULATOR_ATTRIBUTES,
                        **_TABLE_ATTRIBUTES,
                        **_TABLE1D_ATTRIBUTES}

_FUEL_ATTRIBUTES = {'FuelType':          SECTION_DEFINE,
                    'LowerHeatingValue': SECTION_DEFINE,
                    'MassDensity':       SECTION_DEFINE}

_LEVY_ATTRIBUTES = {**_POLICY_ATTRIBUTES,
                    'Level':          SECTION_BOTH,
                    'LowerThreshold': SECTION_BOTH,
                    'UpperThreshold': SECTION_BOTH}

_PLANT_ATTRIBUTES = {'Fuel':            SECTION_DEFINE,
                     'Process':         SECTION_DEFINE,
                     'Source':          SECTION_DEFINE,
                     'Region':          SECTION_DEFINE,
                     'CostOfCapital':   SECTION_BOTH,
                     'Capacity':        SECTION_BOTH,
                     'Uptime':          SECTION_BOTH,
                     'Lifetime':        SECTION_BOTH,
                     'LeadTime':        SECTION_BOTH}

_PLOT_ATTRIBUTES = {'Directory': SECTION_DEFINE}

_PORT_ATTRIBUTES = {'ShorePowerCost':            SECTION_BOTH,
                    'ShorePowerConnectionShare': SECTION_BOTH}

_POWER_SYSTEM_ATTRIBUTES = {**_MACHINERY_ATTRIBUTES,
                            'Propulsion':          SECTION_DEFINE,
                            'Electrical':          SECTION_DEFINE,
                            'Heat':                SECTION_DEFINE}

_PROCESS_ATTRIBUTES = {'Feeds':       SECTION_DEFINE,
                       'Conversions': SECTION_BOTH}

_PRODUCER_ATTRIBUTES = {'Plants':                   SECTION_DEFINE,
                        'InitialCapacity':          SECTION_DEFINE,
                        'InitialAgeDistribution':   SECTION_DEFINE,
                        'Inertia':                  SECTION_BOTH,
                        'MinimumOfftakeDuration':   SECTION_BOTH,
                        'FuelDemandSensitivity':    SECTION_BOTH,
                        'FuelCostSensitivity':      SECTION_BOTH,
                        'MaximumDevelopment':       SECTION_BOTH,
                        'MaximumRampUp':            SECTION_BOTH,
                        'JumpStartFraction':        SECTION_BOTH}

_REGION_ATTRIBUTES = {}

_REGULATION_ATTRIBUTES = {**_POLICY_ATTRIBUTES,
                          'Measure':                    SECTION_DEFINE,
                          'IntraFraction':              SECTION_BOTH,
                          'InterFraction':              SECTION_BOTH,
                          'ExtraFraction':              SECTION_BOTH,
                          'RemedialCost':               SECTION_BOTH,
                          'FlexibilityHorizon':         SECTION_BOTH,
                          'AllowThresholdAdjustment':   SECTION_BOTH}

_REPORT_ATTRIBUTES = {'Directory': SECTION_DEFINE,
                      'FileFormat': SECTION_DEFINE}

_ROUTE_ATTRIBUTES = {'RouteType':               SECTION_DEFINE,
                     'Ports':                   SECTION_DEFINE,
                     'TimeAtSea':               SECTION_BOTH,
                     'PortDurations':           SECTION_BOTH,
                     'PortCalls':               SECTION_BOTH,
                     'Distances':               SECTION_DEFINE,
                     'ConditionDistribution':   SECTION_BOTH,
                     'Speeds':                  SECTION_BOTH,
                     'CapacityUtilizations':    SECTION_BOTH}

_SOURCE_ATTRIBUTES = {'Dependency': SECTION_DEFINE}

_SURFACE_ATTRIBUTES = {'Table': SECTION_BOTH,
                       **_CALCULATOR_ATTRIBUTES,
                       **_TABLE_ATTRIBUTES,
                       **_TABLE2D_ATTRIBUTES}

_TANK_ATTRIBUTES = {**_MACHINERY_ATTRIBUTES,
                    'FuelTypes': SECTION_DEFINE,
                    'Size': SECTION_DEFINE}

_TECHNOLOGY_ATTRIBUTES = {**_MACHINERY_ATTRIBUTES,
                          'ShorePowerCapacity':    SECTION_BOTH}


_TIMETABLE_ATTRIBUTES = {'Table': SECTION_BOTH,
                         **_CALCULATOR_ATTRIBUTES,
                         **_TABLE_ATTRIBUTES,
                         **_TABLE2D_ATTRIBUTES}

_TRANSPORT_ATTRIBUTES = {}

_VARIABLE_ATTRIBUTES = {**_CALCULATOR_ATTRIBUTES,
                        'Value': SECTION_BOTH}

_VESSEL_ATTRIBUTES = {'PropulsionLoad':         SECTION_DEFINE,
                      'ElectricalLoadAtSea':    SECTION_DEFINE,
                      'ElectricalLoadInPort':   SECTION_DEFINE,
                      'HeatLoadAtSea':          SECTION_DEFINE,
                      'HeatLoadInPort':         SECTION_DEFINE,
                      'FuelType':               SECTION_DEFINE,
                      'PowerSystem':            SECTION_DEFINE,
                      'Tanks':                  SECTION_DEFINE,
                      'Route':                  SECTION_DEFINE,
                      'NominalCapacity':        SECTION_DEFINE,
                      'Lifetime':               SECTION_BOTH,
                      'LeadTime':               SECTION_BOTH,
                      'CAPEX':                  SECTION_BOTH,
                      'OPEX':                   SECTION_BOTH,
                      'CostOfCapital':          SECTION_BOTH}

# general nodes --------------------------------------------------------------------------------------------------------
_MODEL_DEFINITION_ATTRIBUTES = {'StartDate':         SECTION_DEFINE,
                                'EmissionsLifetime': SECTION_DEFINE}

_BUNKER_LOGISTICS_ATTRIBUTES = {'LiquidMarketFuels': SECTION_DEFINE}

_BUNKER_OPTIONS_ATTRIBUTES = {'Solver':                        SECTION_DEFINE,
                              'SolverMethod':                 SECTION_DEFINE,
                              'SolutionTolerance':            SECTION_DEFINE,
                              'Threads':                      SECTION_DEFINE,
                              'FairShareMaximumIterations':   SECTION_DEFINE,
                              'FairShareTolerance':           SECTION_DEFINE}

# assemble dicts -------------------------------------------------------------------------------------------------------
NODE_ATTRIBUTE_SECTIONS = {id_.CONVERTER:           _CONVERTER_ATTRIBUTES,
                           id_.CURVE:               _CURVE_ATTRIBUTES,
                           id_.EMISSION:            _EMISSION_ATTRIBUTES,
                           id_.FEEDSTOCK:           _FEEDSTOCK_ATTRIBUTES,
                           id_.FLEET:               _FLEET_ATTRIBUTES,
                           id_.FORECAST:            _FORECAST_ATTRIBUTES,
                           id_.FUEL:                _FUEL_ATTRIBUTES,
                           id_.LEVY:                _LEVY_ATTRIBUTES,
                           id_.PLANT:               _PLANT_ATTRIBUTES,
                           id_.PLOT:                _PLOT_ATTRIBUTES,
                           id_.PORT:                _PORT_ATTRIBUTES,
                           id_.POWER_SYSTEM:        _POWER_SYSTEM_ATTRIBUTES,
                           id_.PROCESS:             _PROCESS_ATTRIBUTES,
                           id_.PRODUCER:            _PRODUCER_ATTRIBUTES,
                           id_.REGION:              _REGION_ATTRIBUTES,
                           id_.REGULATION:          _REGULATION_ATTRIBUTES,
                           id_.REPORT:              _REPORT_ATTRIBUTES,
                           id_.ROUTE:               _ROUTE_ATTRIBUTES,
                           id_.SOURCE:              _SOURCE_ATTRIBUTES,
                           id_.SURFACE:             _SURFACE_ATTRIBUTES,
                           id_.TANK:                _TANK_ATTRIBUTES,
                           id_.TECHNOLOGY:          _TECHNOLOGY_ATTRIBUTES,
                           id_.TIMETABLE:           _TIMETABLE_ATTRIBUTES,
                           id_.TRANSPORT:           _TRANSPORT_ATTRIBUTES,
                           id_.VARIABLE:            _VARIABLE_ATTRIBUTES,
                           id_.VESSEL:              _VESSEL_ATTRIBUTES}

GENERAL_NODE_ATTRIBUTE_SECTIONS = {id_.MODEL_DEFINITION: _MODEL_DEFINITION_ATTRIBUTES,
                                   id_.BUNKER_LOGISTICS: _BUNKER_LOGISTICS_ATTRIBUTES,
                                   id_.BUNKER_OPTIONS:   _BUNKER_OPTIONS_ATTRIBUTES}


# methods --------------------------------------------------------------------------------------------------------------
def check_node_attribute_is_allowed(node_type, attribute_name, section):
    """

    Parameters
    ----------
    node_type : str
        The node type.
    attribute_name : str
        The name of the attribute.
    section : Enum
        The section (DEFINE or EVENTS) at which the attribute is read.

    Returns
    -------
    bool
        Whether the attribute is allowed.
    """

    allowed_attributes = NODE_ATTRIBUTE_SECTIONS[node_type]

    if attribute_name in allowed_attributes:

        allowed_sections = allowed_attributes[attribute_name]

        if section in allowed_sections:

            return True

        else:

            raise AttributeAssignmentError("Nodes of type '{}' does not allow setting"
                                           " attribute '{}' in '{}'"
                                           .format(node_type, attribute_name, SECTION_NAME[section]))

    else:

        raise AttributeAssignmentError("Nodes of type '{}' has no attribute '{}'".format(node_type, attribute_name))


def check_general_node_attribute_is_allowed(type_, attribute_name, section):
    """

    Parameters
    ----------
    type_ : str
        The general node type.
    attribute_name : str
        The name of the attribute.
    section : Enum
        The section (DEFINE or EVENTS) at which the attribute is read.

    Returns
    -------
    bool
        Whether the attribute is allowed.
    """

    allowed_attributes = GENERAL_NODE_ATTRIBUTE_SECTIONS[type_]

    if attribute_name in allowed_attributes:

        allowed_sections = allowed_attributes[attribute_name]

        if section in allowed_sections:

            return True

        else:

            raise AttributeAssignmentError("'{}' does not allow setting attribute '{}' in '{}'"
                                           .format(type_, attribute_name, SECTION_NAME[section]))

    else:

        raise AttributeAssignmentError("'{}' has no attribute '{}'".format(type_, attribute_name))
