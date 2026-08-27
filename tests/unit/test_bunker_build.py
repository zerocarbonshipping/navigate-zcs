# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for the LP get-or-create build helpers.

The stub model below is the only check on element names: the HiGHS backend
discards the name passed to addVar, so an LP-level comparison cannot see
variable-name drift.
"""
import pytest

import navigate.bunker.solver as gp
import navigate.core.enum_ as enum_
from navigate.bunker._build import add_variable, get_constraint
from navigate.bunker.variables import update_vessel_variables


class _StubModel:
    """Records addVar/addConstr calls; each returns a fresh sentinel object."""

    def __init__(self):
        self.added_variables = []
        self.added_constraints = []

    def addVar(self, vtype, name):
        self.added_variables.append((vtype, name))
        return object()

    def addConstr(self, constr, name):
        self.added_constraints.append((constr, name))
        return object()


class _StubAlgorithm:
    def __init__(self):
        self.model = _StubModel()


def test_add_variable_creates_named_continuous_variable_under_key():
    alg = _StubAlgorithm()
    container = {}

    add_variable(alg, container, ("vessel_a", 2, "ammonia"), "bunker")

    assert alg.model.added_variables == [(gp.GRB.CONTINUOUS, "bunker_vessel_a_2_ammonia")]
    assert list(container) == [("vessel_a", 2, "ammonia")]


def test_add_variable_reuses_existing_variable():
    alg = _StubAlgorithm()
    existing = object()
    container = {("vessel_a", 2, "ammonia"): existing}

    add_variable(alg, container, ("vessel_a", 2, "ammonia"), "bunker")

    assert not alg.model.added_variables
    assert container[("vessel_a", 2, "ammonia")] is existing


def test_add_variable_scalar_key_is_single_name_element():
    alg = _StubAlgorithm()
    container = {}

    add_variable(alg, container, "regulation_a", "remedial_factor_flexibility")

    assert [name for _, name in alg.model.added_variables] == ["remedial_factor_flexibility_regulation_a"]
    assert list(container) == ["regulation_a"]


def test_get_constraint_creates_named_constraint_under_key():
    alg = _StubAlgorithm()
    container = {}

    constraint = get_constraint(alg, container, ("vessel_a", 2, "tank_b"), "<=", "tank_capacity")

    assert [name for _, name in alg.model.added_constraints] == ["tank_capacity_vessel_a_2_tank_b"]
    assert container[("vessel_a", 2, "tank_b")] is constraint


@pytest.mark.skipif(gp.get_active_backend() != "highs", reason="inspects the HiGHS TempConstr")
@pytest.mark.parametrize("sense", ["==", "<=", ">="])
def test_get_constraint_builds_row_with_requested_sense(sense):
    alg = _StubAlgorithm()

    get_constraint(alg, {}, ("vessel_a",), sense, "family")

    (temp_constraint, _), = alg.model.added_constraints
    assert temp_constraint.sense == sense


def test_get_constraint_returns_existing_constraint():
    alg = _StubAlgorithm()
    existing = object()
    container = {("vessel_a", 2, "tank_b"): existing}

    constraint = get_constraint(alg, container, ("vessel_a", 2, "tank_b"), "<=", "tank_capacity")

    assert constraint is existing
    assert not alg.model.added_constraints


def test_get_constraint_rejects_unknown_sense():
    alg = _StubAlgorithm()

    with pytest.raises(ValueError):
        get_constraint(alg, {}, ("vessel_a",), "<", "tank_capacity")


class _StubConverter:
    def __init__(self, name):
        self.name = name

    def get_name(self):
        return self.name


class _StubPowerSystem:
    def __init__(self):
        self.electrical = _StubConverter("electrical_a")
        self.heat = _StubConverter("heat_a")

    def get_converters(self):
        return ()


class _StubPort:
    def is_bunkering_allowed(self, fuel):
        return False


class _StubRoute:
    def __init__(self, number_of_ports):
        self.ports = [_StubPort() for _ in range(number_of_ports)]
        self.route_type = enum_.RouteTypeID.ROUND_TRIP

    def get_leg_indices(self):
        return ()


class _StubVesselExpectation:
    def get_shore_power_capacity(self, idx):
        return 0.


class _StubVessel:
    def __init__(self):
        self.route = _StubRoute(2)
        self.usable_fuels = {"hfo": object()}
        self.power_system = _StubPowerSystem()
        self.expectation = _StubVesselExpectation()

    def get_name(self):
        return "vessel_a"


def test_update_vessel_variables_adds_mass_tank_per_port_and_fuel():
    """No committed test deck assigns a ROUND_TRIP route, so the mass-tank keys
    and names are pinned here rather than by an LP-level comparison."""

    alg = _StubAlgorithm()
    alg.idx = 0
    alg.bunker = {}
    alg.spend_sea = {}
    alg.spend_port = {}
    alg.mass_tank = {}
    alg.shore_power = {}
    alg.fuels_per_converter = {("vessel_a", "electrical_a"): {}, ("vessel_a", "heat_a"): {}}

    update_vessel_variables(alg, _StubVessel())

    assert list(alg.mass_tank) == [("vessel_a", 0, "hfo"), ("vessel_a", 1, "hfo")]
    assert [name for _, name in alg.model.added_variables] == ["mass_tank_vessel_a_0_hfo", "mass_tank_vessel_a_1_hfo"]
    assert not (alg.bunker or alg.spend_sea or alg.spend_port or alg.shore_power)
