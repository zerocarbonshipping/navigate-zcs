# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from navigate.core.node_type import (
    CONVERTER,
    CURVE,
    EMISSION,
    FEEDSTOCK,
    FLEET,
    FORECAST,
    FUEL,
    LEVY,
    PLOT,
    PORT,
    POWER_SYSTEM,
    PROCESS,
    REGULATION,
    REPORT,
    ROUTE,
    SURFACE,
    TANK,
    TIMETABLE,
    VARIABLE,
    VESSEL,
)


class CommandReferenceMixin:
    """Mixin providing command reference storage and retrieval for Node and _GeneralNode."""

    def __init__(self):
        self.command_references = []

    def add_command_reference(self, command_reference):
        self.command_references.append(command_reference)

    def clear_command_references(self):
        self.command_references = []


_CALCULATOR_TYPES = (CURVE, FORECAST, SURFACE, TIMETABLE, VARIABLE)


class TypeCheckMixin:
    """Stores the node type and provides the is_*() type-checking methods."""

    def __init__(self, type_: str) -> None:
        self.type = type_

    def is_type(self, type_: str) -> bool:
        return self.type == type_

    def is_calculator(self) -> bool:
        return self.type in _CALCULATOR_TYPES

    def is_converter(self) -> bool:
        return self.type == CONVERTER

    def is_curve(self) -> bool:
        return self.type == CURVE

    def is_emission(self) -> bool:
        return self.type == EMISSION

    def is_feedstock(self) -> bool:
        return self.type == FEEDSTOCK

    def is_fleet(self) -> bool:
        return self.type == FLEET

    def is_forecast(self) -> bool:
        return self.type == FORECAST

    def is_fuel(self) -> bool:
        return self.type == FUEL

    def is_levy(self) -> bool:
        return self.type == LEVY

    def is_plot(self) -> bool:
        return self.type == PLOT

    def is_port(self) -> bool:
        return self.type == PORT

    def is_power_system(self) -> bool:
        return self.type == POWER_SYSTEM

    def is_process(self) -> bool:
        return self.type == PROCESS

    def is_regulation(self) -> bool:
        return self.type == REGULATION

    def is_report(self) -> bool:
        return self.type == REPORT

    def is_route(self) -> bool:
        return self.type == ROUTE

    def is_surface(self) -> bool:
        return self.type == SURFACE

    def is_tank(self) -> bool:
        return self.type == TANK

    def is_timetable(self) -> bool:
        return self.type == TIMETABLE

    def is_variable(self) -> bool:
        return self.type == VARIABLE

    def is_vessel(self) -> bool:
        return self.type == VESSEL
