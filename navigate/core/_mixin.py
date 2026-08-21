# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import navigate.core.id_ as id_


class CommandReferenceMixin:
    """Mixin providing command reference storage and retrieval for Node and _GeneralNode."""

    def __init__(self):
        self._command_references = []

    def add_command_reference(self, command_reference):
        self._command_references.append(command_reference)

    def get_command_references(self):
        return self._command_references

    def clear_command_references(self):
        self._command_references = []


# Map method names to id_ constants
_TYPE_CHECKS = {
    'is_converter': id_.CONVERTER,
    'is_curve': id_.CURVE,
    'is_emission': id_.EMISSION,
    'is_feedstock': id_.FEEDSTOCK,
    'is_fleet': id_.FLEET,
    'is_forecast': id_.FORECAST,
    'is_fuel': id_.FUEL,
    'is_levy': id_.LEVY,
    'is_plot': id_.PLOT,
    'is_port': id_.PORT,
    'is_power_system': id_.POWER_SYSTEM,
    'is_process': id_.PROCESS,
    'is_regulation': id_.REGULATION,
    'is_report': id_.REPORT,
    'is_route': id_.ROUTE,
    'is_surface': id_.SURFACE,
    'is_tank': id_.TANK,
    'is_timetable': id_.TIMETABLE,
    'is_variable': id_.VARIABLE,
    'is_vessel': id_.VESSEL,
}

_CALCULATOR_TYPES = (id_.CURVE, id_.FORECAST, id_.SURFACE, id_.TIMETABLE, id_.VARIABLE)


class TypeCheckMixin:
    """Provides is_*() type-checking methods for classes with a _type attribute."""

    def is_type(self, type_):
        return self._type == type_

    def is_calculator(self):
        return self._type in _CALCULATOR_TYPES


def _make_checker(type_id):
    def checker(self):
        return self._type == type_id
    return checker


for _name, _type_id in _TYPE_CHECKS.items():
    setattr(TypeCheckMixin, _name, _make_checker(_type_id))
