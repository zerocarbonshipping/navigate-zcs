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


_TYPE_CHECKS = {
    'is_converter': CONVERTER,
    'is_curve': CURVE,
    'is_emission': EMISSION,
    'is_feedstock': FEEDSTOCK,
    'is_fleet': FLEET,
    'is_forecast': FORECAST,
    'is_fuel': FUEL,
    'is_levy': LEVY,
    'is_plot': PLOT,
    'is_port': PORT,
    'is_power_system': POWER_SYSTEM,
    'is_process': PROCESS,
    'is_regulation': REGULATION,
    'is_report': REPORT,
    'is_route': ROUTE,
    'is_surface': SURFACE,
    'is_tank': TANK,
    'is_timetable': TIMETABLE,
    'is_variable': VARIABLE,
    'is_vessel': VESSEL,
}

_CALCULATOR_TYPES = (CURVE, FORECAST, SURFACE, TIMETABLE, VARIABLE)


class TypeCheckMixin:
    """Provides is_*() type-checking methods for classes with a type attribute."""

    def is_type(self, type_):
        return self.type == type_

    def is_calculator(self):
        return self.type in _CALCULATOR_TYPES


def _make_checker(type_id):
    def checker(self):
        return self.type == type_id
    return checker


for _name, _type_id in _TYPE_CHECKS.items():
    setattr(TypeCheckMixin, _name, _make_checker(_type_id))
