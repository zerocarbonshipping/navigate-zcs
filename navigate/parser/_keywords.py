# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import navigate.core.id_ as id_
from navigate.bunker import BunkerLogistics, BunkerOptions
from navigate.calculator import Curve, Forecast, Surface, Timetable, Variable
from navigate.core.enum_ import SimulationSectionID
from navigate.core.misc import SECTION_BOTH, SECTION_DEFINE, SECTION_EVENTS
from navigate.fuel import Emission, Feedstock, Fuel, Plant, Process, Producer, Region, Source, Transport
from navigate.model_definition import ModelDefinition
from navigate.output import Plot, Report
from navigate.policy import Levy, Regulation
from navigate.route import Port, Route
from navigate.vessel import Converter, PowerSystem, Tank, Technology, Vessel
from navigate.vessel.fleet import Fleet

NODE_CLASS = {id_.CONVERTER:            Converter,
              id_.CURVE:                Curve,
              id_.EMISSION:             Emission,
              id_.FEEDSTOCK:            Feedstock,
              id_.FLEET:                Fleet,
              id_.FORECAST:             Forecast,
              id_.FUEL:                 Fuel,
              id_.LEVY:                 Levy,
              id_.PLANT:                Plant,
              id_.PLOT:                 Plot,
              id_.PORT:                 Port,
              id_.POWER_SYSTEM:         PowerSystem,
              id_.PROCESS:              Process,
              id_.PRODUCER:             Producer,
              id_.REGION:               Region,
              id_.REGULATION:           Regulation,
              id_.REPORT:               Report,
              id_.ROUTE:                Route,
              id_.SOURCE:               Source,
              id_.SURFACE:              Surface,
              id_.TANK:                 Tank,
              id_.TECHNOLOGY:           Technology,
              id_.TIMETABLE:            Timetable,
              id_.TRANSPORT:            Transport,
              id_.VARIABLE:             Variable,
              id_.VESSEL:               Vessel}

GENERAL_NODE_CLASS = {id_.BUNKER_LOGISTICS: BunkerLogistics,
                      id_.BUNKER_OPTIONS:   BunkerOptions,
                      id_.MODEL_DEFINITION: ModelDefinition}

NODE_GROUP = {id_.CONVERTER:            'converters',
              id_.CURVE:                'curves',
              id_.EMISSION:             'emissions',
              id_.FEEDSTOCK:            'feedstocks',
              id_.FLEET:                'fleets',
              id_.FORECAST:             'forecasts',
              id_.FUEL:                 'fuels',
              id_.LEVY:                 'levies',
              id_.PLANT:                'plants',
              id_.PLOT:                 'plots',
              id_.PORT:                 'ports',
              id_.POWER_SYSTEM:         'power_systems',
              id_.PROCESS:              'processes',
              id_.PRODUCER:             'producers',
              id_.REGION:               'regions',
              id_.REGULATION:           'regulations',
              id_.REPORT:               'reports',
              id_.ROUTE:                'routes',
              id_.SOURCE:               'sources',
              id_.SURFACE:              'surfaces',
              id_.TANK:                 'tanks',
              id_.TECHNOLOGY:           'technologies',
              id_.TIMETABLE:            'timetables',
              id_.TRANSPORT:            'transports',
              id_.VARIABLE:             'variables',
              id_.VESSEL:               'vessels'}

GENERAL_NODE_GROUP = {id_.BUNKER_LOGISTICS: 'bunker_logistics',
                      id_.BUNKER_OPTIONS:   'bunker_options',
                      id_.MODEL_DEFINITION: 'model_definition'}

NODE_ALLOW_COPY = {id_.CONVERTER:           True,
                   id_.CURVE:               True,
                   id_.EMISSION:            True,
                   id_.FEEDSTOCK:           True,
                   id_.FLEET:               True,
                   id_.FORECAST:            True,
                   id_.FUEL:                True,
                   id_.LEVY:                True,
                   id_.PLANT:               True,
                   id_.PLOT:                True,
                   id_.PORT:                True,
                   id_.POWER_SYSTEM:        True,
                   id_.PROCESS:             True,
                   id_.PRODUCER:            True,
                   id_.REGION:              True,
                   id_.REGULATION:          True,
                   id_.REPORT:              True,
                   id_.ROUTE:               True,
                   id_.SOURCE:              True,
                   id_.SURFACE:             True,
                   id_.TANK:                True,
                   id_.TECHNOLOGY:          True,
                   id_.TIMETABLE:           True,
                   id_.TRANSPORT:           True,
                   id_.VARIABLE:            True,
                   id_.VESSEL:              True}


KEYWORD_SECTIONS = {id_.CONVERTER:          SECTION_BOTH,
                    id_.CURVE:              SECTION_BOTH,
                    id_.EMISSION:           SECTION_DEFINE,
                    id_.FEEDSTOCK:          SECTION_DEFINE,
                    id_.FLEET:              SECTION_BOTH,
                    id_.FORECAST:           SECTION_BOTH,
                    id_.FUEL:               SECTION_DEFINE,
                    id_.LEVY:               SECTION_BOTH,
                    id_.PLANT:              SECTION_BOTH,
                    id_.PLOT:               SECTION_DEFINE,
                    id_.PORT:               SECTION_BOTH,
                    id_.POWER_SYSTEM:       SECTION_BOTH,
                    id_.PROCESS:            SECTION_BOTH,
                    id_.PRODUCER:           SECTION_BOTH,
                    id_.REGION:             SECTION_BOTH,
                    id_.REGULATION:         SECTION_BOTH,
                    id_.REPORT:             SECTION_DEFINE,
                    id_.ROUTE:              SECTION_BOTH,
                    id_.SOURCE:             SECTION_DEFINE,
                    id_.SURFACE:            SECTION_BOTH,
                    id_.TANK:               SECTION_BOTH,
                    id_.TECHNOLOGY:         SECTION_BOTH,
                    id_.TIMETABLE:          SECTION_BOTH,
                    id_.TRANSPORT:          SECTION_BOTH,
                    id_.VARIABLE:           SECTION_BOTH,
                    id_.VESSEL:             SECTION_BOTH,
                    # general nodes ----------------
                    id_.BUNKER_LOGISTICS:   SECTION_DEFINE,
                    id_.BUNKER_OPTIONS:     SECTION_DEFINE,
                    id_.MODEL_DEFINITION:   SECTION_DEFINE,
                    # miscellaneous ----------------
                    id_.START:              SECTION_EVENTS,
                    id_.DATE:               SECTION_EVENTS,
                    id_.END:                SECTION_EVENTS}

SECTION_NAME = {SimulationSectionID.DEFINE: 'DEFINE',
                SimulationSectionID.EVENTS: 'EVENTS'}


# methods --------------------------------------------------------------------------------------------------------------
def define_new_node(node_type, node_name):
    return NODE_CLASS[node_type](node_name)


def define_new_general_node(type_):
    return GENERAL_NODE_CLASS[type_]()
