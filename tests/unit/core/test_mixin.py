# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the TypeCheckMixin type predicates."""
import pytest

from navigate.core._mixin import TypeCheckMixin
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
from navigate.parser._keywords import NODE_CLASS

TYPE_PREDICATES = {
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

CALCULATOR_TYPES = (CURVE, FORECAST, SURFACE, TIMETABLE, VARIABLE)


class TestTypePredicates:

    @pytest.mark.parametrize('method, type_', TYPE_PREDICATES.items())
    def test_true_for_own_type(self, method: str, type_: str):
        assert getattr(TypeCheckMixin(type_), method)()

    @pytest.mark.parametrize('method, type_', TYPE_PREDICATES.items())
    def test_false_for_every_other_type(self, method: str, type_: str):
        for other in TYPE_PREDICATES.values():
            if other != type_:
                assert not getattr(TypeCheckMixin(other), method)()

    def test_is_type(self):
        assert TypeCheckMixin(FUEL).is_type(FUEL)
        assert not TypeCheckMixin(FUEL).is_type(VESSEL)

    @pytest.mark.parametrize('type_', TYPE_PREDICATES.values())
    def test_is_calculator(self, type_: str):
        assert TypeCheckMixin(type_).is_calculator() == (type_ in CALCULATOR_TYPES)


class TestNodeTypeAttribute:

    @pytest.mark.parametrize('type_, cls', NODE_CLASS.items())
    def test_every_node_class_carries_its_type(self, type_: str, cls: type):
        node = cls("n")
        assert node.type == type_
        assert node.is_type(type_)
