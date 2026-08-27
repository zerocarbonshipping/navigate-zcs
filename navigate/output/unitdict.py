# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.node_type import (
    CONVERTER,
    EMISSION,
    FEEDSTOCK,
    FLEET,
    FUEL,
    LEVY,
    PLANT,
    PORT,
    POWER_SYSTEM,
    PROCESS,
    PRODUCER,
    REGION,
    REGULATION,
    REPORT,
    ROUTE,
    SOURCE,
    TANK,
    TECHNOLOGY,
    TRANSPORT,
    VESSEL,
)

_CONVERTER_UNITS = {
    'CAPEX':                            'USD/MW',
    'OPEX':                             'USD/MW/year',
    'Lifetime':                         'years',
    'Replacement':                      'fraction',
    'PowerCapacity':                    'MW',
    'MinimumLoad':                      'fraction',
    'MainFuelTypes':                    None,
    'PilotFuelTypes':                   None,
    'MinimumPilotFuel':                 'GJ/GJ',
    'Efficiency':                       'GJ/GJ',
    'set_slip_fraction':                'ton fuel slip/ton fuel in',
    'set_consumption_ttw':              'ton emission/ton fuel'
}

_EMISSION_UNITS = {
    'GlobalWarmingPotential':           'ton CO2eq/ton emission'
}

_FEEDSTOCK_UNITS = {}

_FLEET_UNITS = {
    'Vessels':                           None,
    'InitialVessels':                   'number of vessels',
    'TradeGrowth':                      'fraction/year',
    'InitialSplit':                      'fraction',
    'InitialAgeDistribution':            None,
    'Orderbooks':                        'number of vessels',
    'Technologies':                      None,
    'FixedScrapRate':                    'fraction/year',
    'AllowSecondaryScrapping':           None,
    'Inertia':                           'fraction/year',
    'Memory':                            None,
    'InterFuelSensitivity':              None,
    'IntraFuelSensitivity':              None,
    'AllowSpeedManagement':              None,
    'MaximumSpeedChange':                'knots/year',
    'SpeedAlignment':                    None,
    'AssumeReferenceSpeedOptimal':       None,
    'SpeedHorizon':                      'years',
    'RetrofitFrequency':                 'years',
    'TechnologySensitivity':             None,
    'TechnologyCostOfCapital':           'fraction',
    'TechnologyHorizon':                 'years',
    'AllowTechnologyApproximation':      None,
    'FuelConversionSensitivity':         None,
    'FuelConversionMinimumAge':          'years',
    'set_fuel_conversion_cost':          'USD',
    'set_allow_vessel':                  None,
    'set_newbuild_available':            None,
    'set_conversion_available':          None,
    'set_newbuild_limit':                'fraction/year',
    'set_newbuild_technology_limit':     'fraction/year',
    'set_retrofit_technology_limit':     'fraction/year',
    'set_fuel_conversion_limit':         'fraction/year'
}


_FUEL_UNITS = {
    'FuelType':                          None,
    'LowerHeatingValue':                'GJ/ton',
    'MassDensity':                      'ton/m3',
    'set_ttw':                          'ton emission/ton fuel'
}

_LEVY_UNITS = {
    'Active':                           None,
    'Scheme':                           None,
    'Jurisdiction':                     None,
    'Emissions':                        None,
    'Fuels':                            None,
    'Scope':                            None,
    'EmissionsLifetime':               'years',
    'IncludeSlip':                      None,
    'Level':                            'USD/ton emission',
    'Threshold':                        'kg emission/GJ',
    'set_global_warming_potential':     'ton CO2eq/ton emission',
    'set_fuel_wtt':                     'ton emission/ton fuel',
    'set_fuel_ttw':                     'ton emission/ton fuel'
}

_PLANT_UNITS = {
    'Fuel':                             None,
    'Process':                          None,
    'Source':                           None,
    'Region':                           None,
    'CostOfCapital':                    'fraction/year',
    'Capacity':                         'tons/day',
    'Uptime':                           'fraction',
    'Lifetime':                         'years',
    'LeadTime':                         'years',
    'set_feed_transport':               None,
    'set_feed_distance':                None
}

_PORT_UNITS = {
    'Fee':                              'USD',
    'ShorePowerCost':                   'USD/MWh',
    'ShorePowerConnectionShare':        'fraction',
    'set_bunkering_allowed':            None,
    'set_bunkering_cost':               'USD/ton',
    'set_bunkering_limit':              'tons/year',
    'set_bunkering_inertia':            'fraction',
    'set_bunker_price_overwrite':       'USD/ton',
    'set_bunker_wtt_overwrite':         'ton emission/ton fuel',
    'set_shore_power_emission_factor':  'ton emission/MWh'
}


_POWER_SYSTEM_UNITS = {
    'CAPEX':                            'USD',
    'OPEX':                             'USD/year',
    'Lifetime':                         'years',
    'Replacement':                      'fraction',
    'Setup':                            None,
    'Propulsion':                       None,
    'Electrical':                       None,
    'Heat':                             None,
    'Combined':                         None
}

_PROCESS_UNITS = {
    'Feeds':                            None,
    'Conversions':                      'ton feedstock/ton output'
}

_PRODUCER_UNITS = {
    'Plants':                           None,
    'InitialCapacity':                  'tons/day',
    'InitialAgeDistribution':           None,
    'Inertia':                          'fraction/year',
    'MinimumOfftakeDuration':           'years',
    'FuelDemandSensitivity':            None,
    'FuelCostSensitivity':              None,
    'MaximumDevelopment':               'plants/year',
    'MaximumRampUp':                    'plants per year',
    'JumpStartFraction':                'fraction',
    'set_existing_pipeline':            'tons/day/year',
    'set_allow_plant':                  None,
    'set_feed_constraint':              'tons/year'
}

_REGION_UNITS = {
    'set_process_capex':                'USD/ton',
    'set_process_opex':                 'USD/ton/year',
    'set_process_energy':               'MWh/ton',
    'set_process_wtt':                  'ton emission/ton fuel',
    'set_source_capex':                 'USD/MWh',
    'set_source_opex':                  'USD/MWh/year',
    'set_source_wtt':                   'ton emission/MWh',
    'set_feedstock_cost':               'USD/ton',
    'set_feedstock_wtt':                'ton emission/ton',
    'set_transport_cost':               'USD/ton-nautical miles',
    'set_transport_wtt':                'ton emission/ton-nautical miles'
}

_REGULATION_UNITS = {
    'Active':                           None,
    'Scheme':                           None,
    'Jurisdiction':                     None,
    'Emissions':                        None,
    'Fuels':                            None,
    'Scope':                            None,
    'EmissionsLifetime':                'years',
    'IncludeSlip':                      None,
    'Measure':                          None,   # dependent on value of measure
    'IntraFraction':                    'fraction',
    'InterFraction':                    'fraction',
    'ExtraFraction':                    'fraction',
    'RemedialCost':                     'USD/ton emission',
    'SharedThreshold':                  None,   # dependent on the value of measure
    'AdjustedVesselThreshold':          None,   # dependent on the value of measure
    'AdjustedSharedThreshold':          None,   # dependent on the value of measure
    'set_global_warming_potential':     'ton CO2eq/ton emission',
    'set_include_vessel':               None,
    'set_fuel_wtt':                     'ton emission/ton fuel',
    'set_fuel_ttw':                     'ton emission/ton fuel',
    'set_vessel_threshold':             None,   # dependent on the value of measure
    'set_vessel_capacity':              None
}

_REPORT_UNITS = {
    'Directory':                        None
}

_ROUTE_UNITS = {
    'RouteType':                        None,
    'Ports':                            None,
    'TimeAtSea':                        'fraction out of total time',
    'PortDurations':                    'days',
    'PortCalls':                        'calls/year',
    'Distances':                        'nautical miles',
    'ConditionDistribution':            'fraction of time spent on the various legs of the trip',
    'Speeds':                           'knots',
    'CapacityUtilizations':             'fraction of cargo capacity',
    'set_voyage_distribution':          'fraction'
}

_SOURCE_UNITS = {
    'Dependency':                       None
}

_TANK_UNITS = {
    'CAPEX':                            'USD/m3',
    'OPEX':                             'USD/m3/year',
    'Lifetime':                         'years',
    'Replacement':                      'fraction',
    'FuelTypes':                        None,
    'Size':                             'm3'
}

_TECHNOLOGY_UNITS = {
    'CAPEX':                            'USD',
    'OPEX':                             'USD/year',
    'Lifetime':                         'years',
    'Replacement':                      'fraction',
    'ShorePowerCapacity':               'MW',
    'set_energy_saving':                'fraction',
    'set_external_power':               'MW',
    'set_power_transfer':               'MW'
}

_TRANSPORT_UNITS = {}


_VESSEL_UNITS = {
    'PropulsionLoad':              'x: knots, y: fraction, z: MW',
    'ElectricalLoadAtSea':         'x: knots, y: fraction, z: MW',
    'ElectricalLoadInPort':        'MW',
    'HeatLoadAtSea':               'x: knots, y: fraction, z: MW',
    'HeatLoadInPort':              'MW',
    'FuelType':                         None,
    'PowerSystem':                      None,
    'Tanks':                            None,
    'Route':                            None,
    'NominalCapacity':                  None,   # dependent on vessel type
    'Lifetime':                         'years',
    'CAPEX':                            'USD',
    'OPEX':                             'USD/year',
    'CostOfCapital':                    'fraction/year'
}

# general nodes --------------------------------------------------------------------------------------------------------
_MODEL_DEFINITION_UNITS = {
    'StartDate':                        None,
    'EmissionsLifetime':                None
}

_BUNKER_LOGISTICS_UNITS = {
    'LiquidMarketFuels':                None,
    'set_distance':                     'nautical miles',
    'set_transport_cost':               'USD/ton/nautical mile',
    'set_transport_wtt':                'ton emission/ton-nautical miles'
}

_BUNKER_OPTIONS_UNITS = {
    'SolutionTolerance':                None,
    'Threads':                          None,
    'FairShareMaximumIterations':       None,
    'FairShareTolerance':               None,
    'FlexibilityMaximumIterations':     None,
    'FlexibilityToleranceX':            None,
    'FlexibilityToleranceY':            None
}

unitdict = {
    CONVERTER:           _CONVERTER_UNITS,
    EMISSION:            _EMISSION_UNITS,
    FEEDSTOCK:           _FEEDSTOCK_UNITS,
    FLEET:               _FLEET_UNITS,
    FUEL:                _FUEL_UNITS,
    LEVY:                _LEVY_UNITS,
    PLANT:               _PLANT_UNITS,
    PORT:                _PORT_UNITS,
    POWER_SYSTEM:        _POWER_SYSTEM_UNITS,
    PROCESS:             _PROCESS_UNITS,
    PRODUCER:            _PRODUCER_UNITS,
    REGION:              _REGION_UNITS,
    REGULATION:          _REGULATION_UNITS,
    REPORT:              _REPORT_UNITS,
    ROUTE:               _ROUTE_UNITS,
    SOURCE:              _SOURCE_UNITS,
    TANK:                _TANK_UNITS,
    TECHNOLOGY:          _TECHNOLOGY_UNITS,
    TRANSPORT:           _TRANSPORT_UNITS,
    VESSEL:              _VESSEL_UNITS
}
