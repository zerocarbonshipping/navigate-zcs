# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import inspect
from collections.abc import Iterable
from enum import Enum
from itertools import product

from navigate.core.assign import expand_id_wildcard
from navigate.core.enum_ import EnergyDemandTypeID, FuelTypeID
from navigate.core.node_type import (
    CONVERTER,
    CURVE,
    EMISSION,
    FEEDSTOCK,
    FLEET,
    FORECAST,
    FUEL,
    LEVY,
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
from navigate.exceptions import CommandError
from navigate.parser._keywords import SECTION_BOTH, SECTION_DEFINE, SECTION_NAME
from navigate.util import name_contains_wildcards

# Per-command wildcard domains. Tuple indices correspond to the method's
# string arguments (excluding self). ``None`` means the argument is a
# node name — wildcards are passed through for downstream matching.
# Commands not listed here have no enum arguments.
_WILDCARD_DOMAINS: dict[str, tuple[type[Enum], ...]] = {
    'set_slip_fraction':          (FuelTypeID,),
    'set_consumption_ttw':        (FuelTypeID,),
    'set_operational_saving_sea': (EnergyDemandTypeID,),
    'set_operational_saving_port': (EnergyDemandTypeID,),
    'set_energy_saving':          (EnergyDemandTypeID,),
    'set_external_power':         (EnergyDemandTypeID,),
    'set_power_transfer':         (EnergyDemandTypeID, EnergyDemandTypeID),
}

# high-level class commands to multiple nodes --------------------------------------------------------------------------
_POLICY_COMMANDS = {'set_include_vessel':           SECTION_BOTH,
                    'set_global_warming_potential': SECTION_BOTH,
                    'set_fuel_wtt':                 SECTION_BOTH,
                    'set_fuel_ttw':                 SECTION_BOTH}

# nodes ----------------------------------------------------------------------------------------------------------------
_ALTERNATIVE_POWER_COMMANDS = {}

_CONVERTER_COMMANDS = {'set_slip_fraction':   SECTION_BOTH,
                       'set_consumption_ttw': SECTION_BOTH}

_CURVE_COMMANDS = {}
_EFFICIENCY_COMMANDS = {}
_EMISSION_COMMANDS = {}

_FEEDSTOCK_COMMANDS = {}

_FLEET_COMMANDS = {'set_fuel_conversion_cost':      SECTION_BOTH,
                   'set_fuel_conversion_limit':     SECTION_BOTH,
                   'set_allow_vessel':              SECTION_BOTH,
                   'set_newbuild_available':        SECTION_BOTH,
                   'set_conversion_available':      SECTION_BOTH,
                   'set_operational_saving_sea':    SECTION_BOTH,
                   'set_operational_saving_port':   SECTION_BOTH,
                   'set_initial_technology_share':  SECTION_DEFINE,
                   'set_newbuild_technology_limit': SECTION_BOTH,
                   'set_retrofit_technology_limit': SECTION_BOTH,
                   'set_newbuild_limit':            SECTION_BOTH}

_FORECAST_COMMANDS = {}
_FUEL_COMMANDS = {'set_ttw': SECTION_DEFINE}

_LEVY_COMMANDS = {**_POLICY_COMMANDS}

_PLANT_COMMANDS = {'set_feed_transport':   SECTION_BOTH,
                   'set_feed_distance':    SECTION_BOTH,
                   'set_fuel_transport':   SECTION_BOTH,
                   'set_fuel_distance':    SECTION_BOTH}

_PLOT_COMMANDS = {'add_plot': SECTION_DEFINE}

_PORT_COMMANDS = {'set_bunkering_allowed':           SECTION_BOTH,
                  'set_bunkering_cost':              SECTION_BOTH,
                  'set_bunkering_limit':             SECTION_BOTH,
                  'set_bunkering_inertia':           SECTION_BOTH,
                  'set_handling_cost':               SECTION_BOTH,
                  'set_bunker_price_overwrite':      SECTION_BOTH,
                  'set_bunker_wtt_overwrite':        SECTION_BOTH,
                  'set_shore_power_emission_factor': SECTION_BOTH}

_POWER_SYSTEM_COMMANDS = {}
_PROCESS_COMMANDS = {}

_PRODUCER_COMMANDS = {'set_existing_pipeline':   SECTION_DEFINE,
                      'set_allow_plant':         SECTION_BOTH,
                      'set_feed_constraint':     SECTION_BOTH,
                      'set_export_distribution': SECTION_BOTH}

_REGION_COMMANDS = {'set_process_capex':                SECTION_BOTH,
                    'set_process_opex':                 SECTION_BOTH,
                    'set_process_energy':               SECTION_BOTH,
                    'set_process_lifetime':             SECTION_BOTH,
                    'set_process_replacement':          SECTION_BOTH,
                    'set_process_wtt':                  SECTION_BOTH,
                    'set_source_capex':                 SECTION_BOTH,
                    'set_source_opex':                  SECTION_BOTH,
                    'set_source_wtt':                   SECTION_BOTH,
                    'set_feedstock_cost':               SECTION_BOTH,
                    'set_feedstock_wtt':                SECTION_BOTH,
                    'set_transport_cost':               SECTION_BOTH,
                    'set_transport_wtt':                SECTION_BOTH}

_REGULATION_COMMANDS = {**_POLICY_COMMANDS,
                        'set_vessel_threshold': SECTION_BOTH,
                        'set_vessel_capacity':  SECTION_BOTH}

_REPORT_COMMANDS = {'add_property':            SECTION_DEFINE,
                    'add_fleet_property':      SECTION_DEFINE,
                    'add_levy_property':       SECTION_DEFINE,
                    'add_plant_property':      SECTION_DEFINE,
                    'add_port_property':       SECTION_DEFINE,
                    'add_producer_property':   SECTION_DEFINE,
                    'add_regulation_property': SECTION_DEFINE,
                    'add_vessel_property':     SECTION_DEFINE}

_ROUTE_COMMANDS = {'set_voyage_distribution':    SECTION_BOTH}

_SOURCE_COMMANDS = {}
_SURFACE_COMMANDS = {}
_TANK_COMMANDS = {}

_TECHNOLOGY_COMMANDS = {'set_energy_saving': SECTION_BOTH,
                        'set_external_power': SECTION_BOTH,
                        'set_power_transfer': SECTION_BOTH}

_TIMETABLE_COMMANDS = {}
_TRANSPORT_COMMANDS = {}
_VARIABLE_COMMANDS = {}
_VESSEL_COMMANDS = {}

# assemble dicts -------------------------------------------------------------------------------------------------------
NODE_COMMAND_SECTIONS = {CONVERTER:             _CONVERTER_COMMANDS,
                         CURVE:                 _CURVE_COMMANDS,
                         EMISSION:              _EMISSION_COMMANDS,
                         FEEDSTOCK:             _FEEDSTOCK_COMMANDS,
                         FLEET:                 _FLEET_COMMANDS,
                         FORECAST:              _FORECAST_COMMANDS,
                         FUEL:                  _FUEL_COMMANDS,
                         LEVY:                  _LEVY_COMMANDS,
                         PLANT:                 _PLANT_COMMANDS,
                         PLOT:                  _PLOT_COMMANDS,
                         PORT:                  _PORT_COMMANDS,
                         POWER_SYSTEM:          _POWER_SYSTEM_COMMANDS,
                         PROCESS:               _PROCESS_COMMANDS,
                         PRODUCER:              _PRODUCER_COMMANDS,
                         REGION:                _REGION_COMMANDS,
                         REGULATION:            _REGULATION_COMMANDS,
                         REPORT:                _REPORT_COMMANDS,
                         ROUTE:                 _ROUTE_COMMANDS,
                         SOURCE:                _SOURCE_COMMANDS,
                         SURFACE:               _SURFACE_COMMANDS,
                         TANK:                  _TANK_COMMANDS,
                         TECHNOLOGY:            _TECHNOLOGY_COMMANDS,
                         TIMETABLE:             _TIMETABLE_COMMANDS,
                         TRANSPORT:             _TRANSPORT_COMMANDS,
                         VARIABLE:              _VARIABLE_COMMANDS,
                         VESSEL:                _VESSEL_COMMANDS}


# classes --------------------------------------------------------------------------------------------------------------
class CommandReference:
    """A deferred command invocation stored on a node.

    Parameters
    ----------
    command : str
        Method name to call on the node.
    inputs : list
        Positional arguments for the method.
    source : SourceLocation
        Source location of the command in the include file.
    deck_line : int
        Line in the .nav file of the enclosing INCLUDE directive.
    """

    def __init__(self, command, inputs, source, deck_line=0):
        self.command = command
        self.inputs = inputs
        self._source = source
        self._deck_line = deck_line

    def execute(self, node):
        method = getattr(node, self.command)
        self._check_command(node, method)

        expanded = _expand_inputs(self.command, self.inputs)
        for combo in expanded:
            method(*combo)

    @property
    def source(self):
        return self._source

    @property
    def deck_line(self):
        return self._deck_line

    def _check_command(self, node, method):
        # extract a list of parameters
        method_inputs = inspect.signature(method).parameters

        # find the args and kwargs
        args = [method_inputs[p].name for p in method_inputs
                if method_inputs[p].default is inspect.Parameter.empty]

        kwargs = [method_inputs[p].name for p in method_inputs
                  if method_inputs[p].default is not inspect.Parameter.empty]

        n_args = len(args)
        n_kwargs = len(kwargs)

        # check that the number of provided inputs
        # corresponding to the required inputs,
        # otherwise throw and error.
        n_given = len(self.inputs)

        if n_given < n_args:

            # join inputs
            input_names = ""
            for input_ in args[:-1]:
                input_names += "'{}', ".format(input_)

            # remove last comma and space if only two inputs
            input_names = input_names[:-2] + ' ' if len(args) < 3 else input_names

            # add the last input name
            input_names += "and '{}'".format(args[-1])

            raise CommandError("{}: Command '{}' requires {} inputs, {}, but only {} {} given"
                               .format(node,
                                       self.command,
                                       n_args,
                                       input_names,
                                       n_given,
                                       'was' if n_given == 1 else 'were'))

        elif n_given > (n_args + n_kwargs):

            all_inputs = args + kwargs

            # join inputs
            input_names = ""
            for input_ in all_inputs[:-1]:
                input_names += "'{}', ".format(input_)

            # remove last comma and space if only two inputs
            input_names = input_names[:-2] + ' ' if len(all_inputs) < 3 else input_names

            # add the last input name
            input_names += "and '{}'".format(all_inputs[-1])

            raise CommandError("{}: Command '{}' takes up to {} inputs, {}, but {} {} given"
                               .format(node,
                                       self.command,
                                       n_args + n_kwargs,
                                       input_names,
                                       n_given,
                                       'was' if n_given == 1 else 'were'))


def _expand_inputs(command: str, inputs: list) -> Iterable[tuple]:
    """Expand wildcard arguments against their registered enum domains.

    Yields argument tuples — one per combination when wildcards match
    multiple enum members, or a single tuple when no expansion applies.
    """

    domains = _WILDCARD_DOMAINS.get(command)

    if not domains:
        return (tuple(inputs),)

    arg_options = []
    for i, inp in enumerate(inputs):
        enum_cls = domains[i] if i < len(domains) else None
        if enum_cls and isinstance(inp, str) and name_contains_wildcards(inp):
            arg_options.append(
                [m.name for m in expand_id_wildcard(inp, enum_cls)]
            )
        else:
            arg_options.append([inp])

    return product(*arg_options)


# methods --------------------------------------------------------------------------------------------------------------
def check_node_command_is_allowed(node_type, command_name, section):
    """

    Parameters
    ----------
    node_type : str
        The node type.
    command_name : str
        The name of the command.
    section : Enum
        The section (DEFINE or EVENTS) at which the command is used.

    Returns
    -------
    bool
        Whether the command is allowed.
    """

    allowed_commands = NODE_COMMAND_SECTIONS[node_type]

    if command_name in allowed_commands:

        allowed_sections = allowed_commands[command_name]

        if section in allowed_sections:

            return True

        else:

            raise CommandError("Nodes of type '{}' does not allow use of command '{}' in '{}'"
                               .format(node_type, command_name, SECTION_NAME[section]))

    else:

        raise CommandError("Nodes of type '{}' has no command '{}'".format(node_type, command_name))
