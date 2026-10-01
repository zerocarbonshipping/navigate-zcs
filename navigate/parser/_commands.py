# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The deck commands of each node type, the sections allowing each, and their queue."""

from __future__ import annotations

import inspect
from itertools import product
from typing import TYPE_CHECKING

from navigate.core.assign import expand_id_wildcard
from navigate.core.enum_ import (
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
    FuelTypeID,
)
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
from navigate.core.nodes.report import Report
from navigate.exceptions import CommandError
from navigate.parser._keywords import SECTION_BOTH, SECTION_DEFINE, SECTION_NAME
from navigate.parser._report_properties import check_report_command
from navigate.util import name_contains_wildcards

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from enum import Enum

    from navigate.core.enum_ import SimulationSectionID
    from navigate.core.node import Node
    from navigate.parser._keywords import AllowedSections
    from navigate.parser._lark_parser import MaterializedValue, SourceLocation

# per-command wildcard domains. tuple indices correspond to the method's
# string arguments (excluding self), and an argument beyond the end of the
# tuple is a node name, whose wildcards are matched downstream. a domain
# holds the members the command accepts for that argument: the enum class
# where the target attribute holds every member, a tuple of members where
# it holds a subset. commands not listed here have no enum arguments.
_WILDCARD_DOMAINS: dict[str, tuple[type[Enum] | tuple[Enum, ...], ...]] = {
    "set_slip_fraction": (FuelTypeID,),
    "set_consumption_ttw": (FuelTypeID,),
    "set_operational_saving_sea": (EnergyDemandTypeID,),
    "set_operational_saving_port": (EnergyDemandTypePortID,),
    "set_energy_saving": (EnergyDemandTypeID,),
    "set_external_power": (EnergyDemandTypeID,),
    "set_power_transfer": (EnergyDemandTypeID, EnergyDemandTypeID),
}

# high-level class commands to multiple nodes ------------------------------------------
_POLICY_COMMANDS: dict[str, AllowedSections] = {
    "set_include_vessel": SECTION_BOTH,
    "set_global_warming_potential": SECTION_BOTH,
    "set_fuel_wtt": SECTION_BOTH,
    "set_fuel_ttw": SECTION_BOTH,
}

# nodes --------------------------------------------------------------------------------
_CONVERTER_COMMANDS: dict[str, AllowedSections] = {
    "set_slip_fraction": SECTION_BOTH,
    "set_consumption_ttw": SECTION_BOTH,
}

_CURVE_COMMANDS: dict[str, AllowedSections] = {}
_EMISSION_COMMANDS: dict[str, AllowedSections] = {}

_FEEDSTOCK_COMMANDS: dict[str, AllowedSections] = {}

_FLEET_COMMANDS: dict[str, AllowedSections] = {
    "set_fuel_conversion_cost": SECTION_BOTH,
    "set_fuel_conversion_limit": SECTION_BOTH,
    "set_allow_vessel": SECTION_BOTH,
    "set_newbuild_available": SECTION_BOTH,
    "set_conversion_available": SECTION_BOTH,
    "set_operational_saving_sea": SECTION_BOTH,
    "set_operational_saving_port": SECTION_BOTH,
    "set_initial_technology_share": SECTION_DEFINE,
    "set_newbuild_technology_limit": SECTION_BOTH,
    "set_retrofit_technology_limit": SECTION_BOTH,
    "set_newbuild_limit": SECTION_BOTH,
}

_FORECAST_COMMANDS: dict[str, AllowedSections] = {}
_FUEL_COMMANDS: dict[str, AllowedSections] = {"set_ttw": SECTION_DEFINE}

_LEVY_COMMANDS: dict[str, AllowedSections] = {**_POLICY_COMMANDS}

_PLANT_COMMANDS: dict[str, AllowedSections] = {
    "set_feed_transport": SECTION_BOTH,
    "set_feed_distance": SECTION_BOTH,
    "set_fuel_transport": SECTION_BOTH,
    "set_fuel_distance": SECTION_BOTH,
}

_PLOT_COMMANDS: dict[str, AllowedSections] = {"add_plot": SECTION_DEFINE}

_PORT_COMMANDS: dict[str, AllowedSections] = {
    "set_bunkering_allowed": SECTION_BOTH,
    "set_bunkering_limit": SECTION_BOTH,
    "set_bunkering_inertia": SECTION_BOTH,
    "set_handling_cost": SECTION_BOTH,
    "set_bunker_price_overwrite": SECTION_BOTH,
    "set_bunker_wtt_overwrite": SECTION_BOTH,
    "set_shore_power_emission_factor": SECTION_BOTH,
}

_POWER_SYSTEM_COMMANDS: dict[str, AllowedSections] = {}
_PROCESS_COMMANDS: dict[str, AllowedSections] = {}

_PRODUCER_COMMANDS: dict[str, AllowedSections] = {
    "set_existing_pipeline": SECTION_DEFINE,
    "set_allow_plant": SECTION_BOTH,
    "set_feed_constraint": SECTION_BOTH,
    "set_export_distribution": SECTION_BOTH,
}

_REGION_COMMANDS: dict[str, AllowedSections] = {
    "set_process_capex": SECTION_BOTH,
    "set_process_opex": SECTION_BOTH,
    "set_process_energy": SECTION_BOTH,
    "set_process_lifetime": SECTION_BOTH,
    "set_process_replacement": SECTION_BOTH,
    "set_process_wtt": SECTION_BOTH,
    "set_source_capex": SECTION_BOTH,
    "set_source_opex": SECTION_BOTH,
    "set_source_wtt": SECTION_BOTH,
    "set_feedstock_cost": SECTION_BOTH,
    "set_feedstock_wtt": SECTION_BOTH,
    "set_transport_cost": SECTION_BOTH,
    "set_transport_wtt": SECTION_BOTH,
}

_REGULATION_COMMANDS: dict[str, AllowedSections] = {
    **_POLICY_COMMANDS,
    "set_vessel_threshold": SECTION_BOTH,
    "set_vessel_capacity": SECTION_BOTH,
}

_REPORT_COMMANDS: dict[str, AllowedSections] = {
    "add_property": SECTION_DEFINE,
    "add_fleet_property": SECTION_DEFINE,
    "add_levy_property": SECTION_DEFINE,
    "add_plant_property": SECTION_DEFINE,
    "add_port_property": SECTION_DEFINE,
    "add_producer_property": SECTION_DEFINE,
    "add_regulation_property": SECTION_DEFINE,
    "add_vessel_property": SECTION_DEFINE,
}

_ROUTE_COMMANDS: dict[str, AllowedSections] = {"set_voyage_distribution": SECTION_BOTH}

_SOURCE_COMMANDS: dict[str, AllowedSections] = {}
_SURFACE_COMMANDS: dict[str, AllowedSections] = {}
_TANK_COMMANDS: dict[str, AllowedSections] = {}

_TECHNOLOGY_COMMANDS: dict[str, AllowedSections] = {
    "set_energy_saving": SECTION_BOTH,
    "set_external_power": SECTION_BOTH,
    "set_power_transfer": SECTION_BOTH,
}

_TIMETABLE_COMMANDS: dict[str, AllowedSections] = {}
_TRANSPORT_COMMANDS: dict[str, AllowedSections] = {}
_VARIABLE_COMMANDS: dict[str, AllowedSections] = {}
_VESSEL_COMMANDS: dict[str, AllowedSections] = {}

# assemble dicts -----------------------------------------------------------------------
NODE_COMMAND_SECTIONS: dict[str, dict[str, AllowedSections]] = {
    CONVERTER: _CONVERTER_COMMANDS,
    CURVE: _CURVE_COMMANDS,
    EMISSION: _EMISSION_COMMANDS,
    FEEDSTOCK: _FEEDSTOCK_COMMANDS,
    FLEET: _FLEET_COMMANDS,
    FORECAST: _FORECAST_COMMANDS,
    FUEL: _FUEL_COMMANDS,
    LEVY: _LEVY_COMMANDS,
    PLANT: _PLANT_COMMANDS,
    PLOT: _PLOT_COMMANDS,
    PORT: _PORT_COMMANDS,
    POWER_SYSTEM: _POWER_SYSTEM_COMMANDS,
    PROCESS: _PROCESS_COMMANDS,
    PRODUCER: _PRODUCER_COMMANDS,
    REGION: _REGION_COMMANDS,
    REGULATION: _REGULATION_COMMANDS,
    REPORT: _REPORT_COMMANDS,
    ROUTE: _ROUTE_COMMANDS,
    SOURCE: _SOURCE_COMMANDS,
    SURFACE: _SURFACE_COMMANDS,
    TANK: _TANK_COMMANDS,
    TECHNOLOGY: _TECHNOLOGY_COMMANDS,
    TIMETABLE: _TIMETABLE_COMMANDS,
    TRANSPORT: _TRANSPORT_COMMANDS,
    VARIABLE: _VARIABLE_COMMANDS,
    VESSEL: _VESSEL_COMMANDS,
}


# classes ------------------------------------------------------------------------------
class CommandReference:
    """
    A deferred command invocation the parser queues for a node.

    Parameters
    ----------
    command
        Method name to call on the node.
    inputs
        Positional arguments for the method, every node reference a node.
    source
        Source location of the command in the include file.
    deck_line
        Line in the .nav file of the enclosing INCLUDE directive.
    """

    def __init__(
        self,
        command: str,
        inputs: list[MaterializedValue],
        source: SourceLocation,
        deck_line: int = 0,
    ) -> None:
        self.command: str = command
        self.inputs: list[MaterializedValue] = inputs
        self._source: SourceLocation = source
        self._deck_line: int = deck_line

    def execute(self, node: Node) -> None:
        """
        Run the command on a node, once per combination its wildcards expand to.

        Parameters
        ----------
        node
            The node the command is queued on.
        """
        method: Callable[..., None] = getattr(node, self.command)
        self._check_command(node, method)

        if isinstance(node, Report):
            check_report_command(self.command, method, self.inputs)

        expanded = _expand_inputs(self.command, self.inputs)
        for combo in expanded:
            method(*combo)

    @property
    def source(self) -> SourceLocation:
        """
        The location of the command in its include file.

        Returns
        -------
        SourceLocation
            The include-file location.
        """
        return self._source

    @property
    def deck_line(self) -> int:
        """
        The deck line of the INCLUDE directive the command was read under.

        Returns
        -------
        int
            The line in the .nav file.
        """
        return self._deck_line

    def _check_command(self, node: Node, method: Callable[..., None]) -> None:
        parameters = inspect.signature(method).parameters.values()

        args = [
            parameter.name
            for parameter in parameters
            if parameter.default is inspect.Parameter.empty
        ]
        kwargs = [
            parameter.name
            for parameter in parameters
            if parameter.default is not inspect.Parameter.empty
        ]

        n_args = len(args)
        n_kwargs = len(kwargs)
        n_given = len(self.inputs)

        if n_given < n_args:
            input_names = ""
            for input_ in args[:-1]:
                input_names += f"'{input_}', "

            # two names are joined by "and" alone, without a comma
            input_names = input_names[:-2] + " " if len(args) < 3 else input_names
            input_names += f"and '{args[-1]}'"

            raise CommandError(
                "{}: Command '{}' requires {} inputs, {}, but only {} {} given".format(
                    node,
                    self.command,
                    n_args,
                    input_names,
                    n_given,
                    "was" if n_given == 1 else "were",
                )
            )

        if n_given > (n_args + n_kwargs):
            all_inputs = args + kwargs

            input_names = ""
            for input_ in all_inputs[:-1]:
                input_names += f"'{input_}', "

            # two names are joined by "and" alone, without a comma
            input_names = input_names[:-2] + " " if len(all_inputs) < 3 else input_names
            input_names += f"and '{all_inputs[-1]}'"

            raise CommandError(
                "{}: Command '{}' takes up to {} inputs, {}, but {} {} given".format(
                    node,
                    self.command,
                    n_args + n_kwargs,
                    input_names,
                    n_given,
                    "was" if n_given == 1 else "were",
                )
            )


def _expand_inputs(
    command: str, inputs: list[MaterializedValue]
) -> Iterable[tuple[MaterializedValue, ...]]:
    """
    Expand wildcard arguments against their registered enum domains.

    Yields argument tuples — one per combination when wildcards match
    multiple enum members, or a single tuple when no expansion applies.
    """
    domains = _WILDCARD_DOMAINS.get(command)

    if not domains:
        return (tuple(inputs),)

    argument_options: list[list[MaterializedValue]] = []
    for index, argument in enumerate(inputs):
        domain = domains[index] if index < len(domains) else None
        if domain and isinstance(argument, str) and name_contains_wildcards(argument):
            argument_options.append(
                [member.name for member in expand_id_wildcard(argument, domain)]
            )
        else:
            argument_options.append([argument])

    return product(*argument_options)


# methods ------------------------------------------------------------------------------
def check_node_command_is_allowed(
    node_type: str, command_name: str, section: SimulationSectionID
) -> None:
    """
    Raise if a node type may not use a command in a section.

    Parameters
    ----------
    node_type
        The node type.
    command_name
        The name of the command.
    section
        The section (DEFINE or EVENTS) at which the command is used.
    """
    allowed_commands = NODE_COMMAND_SECTIONS[node_type]

    if command_name not in allowed_commands:
        raise CommandError(
            f"Nodes of type '{node_type}' has no command '{command_name}'"
        )

    if section not in allowed_commands[command_name]:
        raise CommandError(
            f"Nodes of type '{node_type}' does not allow use of command "
            f"'{command_name}' in '{SECTION_NAME[section]}'"
        )
