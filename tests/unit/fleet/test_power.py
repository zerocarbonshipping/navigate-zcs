# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for converter power-capacity verification and vessel load-function checks.

The power-capacity check asserts, per leg and per port, that the energy a
converter delivers cannot exceed its power capacity times the time spent on
the step. Port demands must fit the onboard converter alone: shore power gives
no allowance.

The load-function checks decide, from a vessel's propulsion, electrical, and
heat loads, its technical speed limits and whether its loads are convex.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Expression, Scalar
from navigate.core.enum_ import (
    BunkerScopeID,
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
)
from navigate.core.expectations.vessel_expectation import VesselExpectation
from navigate.core.nodes.curve import Curve
from navigate.core.table_data import TableData
from navigate.core.unit import MWD_TO_GJ
from navigate.exceptions import PowerCapacityError
from navigate.fleet.power import (
    calculate_technical_speed_limits,
    loads_are_convex,
    verify_power_capacity,
)
from navigate.simulation import SimulationManager
from navigate.util import TOLERANCE

PROPULSION = EnergyDemandTypeID.PROPULSION
ELECTRICAL = EnergyDemandTypeID.ELECTRICAL
HEAT = EnergyDemandTypeID.HEAT

IDX = 3


class _StubConverter:
    def __init__(self, name: str, power_capacity: float) -> None:
        self.name = name
        self.power_capacity = Scalar(power_capacity)

    def __repr__(self) -> str:
        return f'Converter("{self.name}")'


class _StubExpectation:
    def __init__(
        self, energies_sea: dict, times_sea: list, energies_port: dict, times_port: list
    ) -> None:
        self._energies_sea = energies_sea
        self._times_sea = times_sea
        self._energies_port = energies_port
        self._times_port = times_port

    def get_time_sea(self, idx: int) -> list:
        assert idx == IDX
        return self._times_sea

    def get_time_port(self, idx: int) -> list:
        assert idx == IDX
        return self._times_port

    def get_energy_sea(self, idx: int) -> dict:
        assert idx == IDX
        return self._energies_sea

    def get_energy_port(self, idx: int) -> dict:
        assert idx == IDX
        return self._energies_port


class _StubVessel:
    def __init__(
        self,
        capacities: dict,
        energies_sea: dict,
        times_sea: list,
        energies_port: dict,
        times_port: list,
        name: str = "boat",
    ) -> None:
        self.name = name
        converters = {
            d: _StubConverter(f"{name}_{d.name.lower()}", capacity)
            for d, capacity in capacities.items()
        }
        self.power_system = SimpleNamespace(
            get_converter_by_energy_type=lambda demand_type: converters[demand_type]
        )
        self.expectation = _StubExpectation(
            energies_sea, times_sea, energies_port, times_port
        )

    def __repr__(self) -> str:
        return f'Vessel("{self.name}")'


def _make_vessel(**overrides) -> _StubVessel:
    """Build a one-leg, one-port vessel, 10 MW converters at half load everywhere."""
    half_load = 5.0 * 10.0 * MWD_TO_GJ

    defaults = {
        "capacities": {PROPULSION: 10.0, ELECTRICAL: 10.0, HEAT: 10.0},
        "energies_sea": {
            PROPULSION: [half_load],
            ELECTRICAL: [half_load],
            HEAT: [half_load],
        },
        "times_sea": [10.0],
        "energies_port": {ELECTRICAL: [half_load], HEAT: [half_load]},
        "times_port": [10.0],
    }
    defaults.update(overrides)
    return _StubVessel(**defaults)


_LIMIT = 10.0 * 10.0 * MWD_TO_GJ  # 10 MW converter over a 10-day leg


class TestVerifyPowerCapacity:
    @pytest.mark.parametrize(
        ("energy", "time", "error"),
        [
            # a load equal to the installed power is feasible, not a violation
            pytest.param(_LIMIT, 10.0, None, id="exactly_at_capacity"),
            pytest.param(
                _LIMIT * (1.0 + TOLERANCE / 2.0),
                10.0,
                None,
                id="just_inside_tolerance_band",
            ),
            pytest.param(
                _LIMIT * (1.0 + 2.0 * TOLERANCE),
                10.0,
                "propulsion demand on leg 0",
                id="just_outside_tolerance_band",
            ),
            # a leg with no time and no energy demands no power
            pytest.param(0.0, 0.0, None, id="zero_time_zero_energy"),
            # energy over no time is an unbounded power demand
            pytest.param(100.0, 0.0, "inf MW", id="zero_time_with_energy"),
        ],
    )
    def test_capacity_tolerance_boundary(self, energy, time, error):
        vessel = _make_vessel(
            energies_sea={PROPULSION: [energy], ELECTRICAL: [0.0], HEAT: [0.0]},
            times_sea=[time],
        )

        if error is None:
            verify_power_capacity(vessel, IDX)
        else:
            with pytest.raises(PowerCapacityError, match=error):
                verify_power_capacity(vessel, IDX)

    def test_sea_overload_errors_naming_converter_and_leg(self):
        overload = 12.0 * 10.0 * MWD_TO_GJ
        vessel = _make_vessel(
            energies_sea={
                PROPULSION: [0.0, overload],
                ELECTRICAL: [0.0, 0.0],
                HEAT: [0.0, 0.0],
            },
            times_sea=[10.0, 10.0],
        )

        with pytest.raises(PowerCapacityError) as excinfo:
            verify_power_capacity(vessel, IDX)

        message = str(excinfo.value)
        assert "propulsion demand on leg 1" in message
        assert "boat_propulsion" in message
        assert "12.00 MW" in message
        assert "10.00 MW" in message

    def test_port_overload_errors(self):
        """Port demand must fit onboard converter; shore power gives no allowance."""
        vessel = _make_vessel(energies_port={ELECTRICAL: [0.0], HEAT: [1.1 * _LIMIT]})

        with pytest.raises(PowerCapacityError, match="heat demand on port 0"):
            verify_power_capacity(vessel, IDX)

    def test_multiple_violations_reported_in_one_error(self):
        overload = 12.0 * 10.0 * MWD_TO_GJ
        vessel = _make_vessel(
            energies_sea={PROPULSION: [overload], ELECTRICAL: [0.0], HEAT: [overload]}
        )

        with pytest.raises(PowerCapacityError) as excinfo:
            verify_power_capacity(vessel, IDX)

        message = str(excinfo.value)
        assert "propulsion demand on leg 0" in message
        assert "heat demand on leg 0" in message


class TestExpectationHorizonBroadcast:
    """
    Pins the horizon-broadcast contract that expected-scope power gating relies on.

    The expected-scope gating in SimulationManager._verify_power_capacity checks demands
    only at the current index; that is valid because a vessel-expectation write at idx
    broadcasts over the whole remaining horizon, so every future expected-bunkering
    build reads the same demands and times.
    """

    LENGTH = 6
    WRITE_IDX = 2

    @pytest.fixture
    def expectation(self):
        expectation = VesselExpectation()
        expectation._initialize_expectation(self.LENGTH)
        expectation._time_sea = expectation._default_list_array(1)
        expectation._time_port = expectation._default_list_array(1)
        expectation._energy_sea = expectation._default_dict_list_array(
            EnergyDemandTypeID, 1
        )
        expectation._energy_port = expectation._default_dict_list_array(
            EnergyDemandTypePortID, 1
        )
        return expectation

    def test_writes_broadcast_over_the_remaining_horizon(self, expectation):
        expectation.set_time_sea(self.WRITE_IDX, [3.0])
        expectation.set_time_port(self.WRITE_IDX, [4.0])
        expectation.set_energy_sea(
            self.WRITE_IDX, {d: [100.0] for d in EnergyDemandTypeID}
        )
        expectation.set_energy_port(
            self.WRITE_IDX, {d: [50.0] for d in EnergyDemandTypePortID}
        )

        for idx in range(self.WRITE_IDX, self.LENGTH):
            assert expectation.get_time_sea(idx) == [3.0]
            assert expectation.get_time_port(idx) == [4.0]
            assert expectation.get_energy_sea(idx=idx) == {
                d: [100.0] for d in EnergyDemandTypeID
            }
            assert expectation.get_energy_port(idx=idx) == {
                d: [50.0] for d in EnergyDemandTypePortID
            }


class TestSimulationGating:
    """The driver only verifies vessels whose multiplier admits them into LP scope."""

    @staticmethod
    def _make_manager(vessel, existing_multiplier, expected_multipliers):
        expectation = SimpleNamespace(
            get_existing_multipliers=lambda v, idx: existing_multiplier,
            get_expected_multipliers=lambda v, idx: np.asarray(expected_multipliers)[
                idx
            ],
        )
        fleet = SimpleNamespace(vessels=[vessel], expectation=expectation)
        return SimpleNamespace(nodes=SimpleNamespace(fleets={"fleet": fleet}), _idx=IDX)

    @staticmethod
    def _make_overloaded_vessel():
        return _make_vessel(
            energies_sea={
                PROPULSION: [12.0 * 10.0 * MWD_TO_GJ],
                ELECTRICAL: [0.0],
                HEAT: [0.0],
            }
        )

    @pytest.mark.parametrize(
        ("expected_multipliers", "expected_raises"),
        [
            # out of scope in both: the overloaded vessel is skipped
            pytest.param([0.0] * (IDX + 3), False, id="zero_multiplier_skipped"),
            # only the expected scope admits the vessel, and only it errors
            pytest.param(
                [0.0] * IDX + [1.0, 1.0, 1.0], True, id="scope_selects_own_multiplier"
            ),
            # expected bunkering builds one LP per future step, so a vessel entering
            # only at a later forecast step is still verified
            pytest.param(
                [0.0] * (IDX + 2) + [1.0], True, id="expected_spans_remaining_horizon"
            ),
        ],
    )
    def test_gating(self, expected_multipliers, expected_raises):
        manager = self._make_manager(
            self._make_overloaded_vessel(),
            existing_multiplier=0.0,
            expected_multipliers=expected_multipliers,
        )

        SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXISTING)

        if expected_raises:
            with pytest.raises(PowerCapacityError):
                SimulationManager._verify_power_capacity(
                    manager, BunkerScopeID.EXPECTED
                )
        else:
            SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXPECTED)


def _curve(rows: list[list[float]]) -> Curve:
    curve = Curve("load")
    curve.set_table(TableData(rows=rows))
    curve.build_table()
    return curve


# propulsion power against speed: slopes 0.6 then 1.0 MW/kn, so strictly increasing
# and convex
_CONVEX_ROWS = [[10.0, 2.0], [15.0, 5.0], [20.0, 10.0]]

# slopes 1.2 then 0.4 MW/kn: concave
_CONCAVE_ROWS = [[10.0, 2.0], [15.0, 8.0], [20.0, 10.0]]


class TestCalculateTechnicalSpeedLimits:
    """The speed limits are the reverse lookup of the converter power on the load."""

    def test_curveless_propulsion_load_gives_no_technical_limit(self):
        route = SimpleNamespace(get_number_of_legs=lambda: 3)
        vessel = SimpleNamespace(propulsion_load=Expression("1 + 2"), route=route)

        speed_min, speed_max = calculate_technical_speed_limits(vessel)

        np.testing.assert_array_equal(speed_min, np.full(3, -np.inf))
        np.testing.assert_array_equal(speed_max, np.full(3, np.inf))

    @pytest.mark.parametrize(
        ("capacity", "minimum_load", "expected_min", "expected_max"),
        [
            # 8 MW capacity at 50 % minimum load: 4 MW lies two thirds of the way up
            # the 2-5 MW segment (10 + 10/3 kn), 8 MW three fifths up the 5-10 MW
            # segment (15 + 3 kn)
            (8.0, 0.5, 10.0 + 10.0 / 3.0, 18.0),
            # no minimum load: the curve's first speed; 12 MW exceeds the load's
            # largest power, so the curve's last speed
            (12.0, None, 10.0, 20.0),
        ],
    )
    def test_curve_load_reverse_lookup(
        self, capacity, minimum_load, expected_min, expected_max
    ):
        converter = SimpleNamespace(
            power_capacity=Scalar(capacity),
            minimum_load=None if minimum_load is None else Scalar(minimum_load),
        )
        vessel = SimpleNamespace(
            propulsion_load=_curve(_CONVEX_ROWS),
            power_system=SimpleNamespace(propulsion=converter),
            route=SimpleNamespace(get_number_of_legs=lambda: 2),
        )

        speed_min, speed_max = calculate_technical_speed_limits(vessel)

        np.testing.assert_allclose(speed_min, [expected_min] * 2)
        np.testing.assert_allclose(speed_max, [expected_max] * 2)


class TestLoadsAreConvex:
    @pytest.mark.parametrize(
        ("propulsion_load", "expected"),
        [
            # an expression's shape is unknown, so it is treated as non-convex
            pytest.param(Expression("1 + 2"), False, id="expression"),
            pytest.param(Scalar(1.0), True, id="scalar"),
            pytest.param(_curve(_CONVEX_ROWS), True, id="convex_curve"),
            pytest.param(_curve(_CONCAVE_ROWS), False, id="concave_curve"),
        ],
    )
    def test_loads_are_convex(self, propulsion_load, expected):
        vessel = SimpleNamespace(
            propulsion_load=propulsion_load,
            electrical_load_at_sea=Scalar(1.0),
            heat_load_at_sea=Scalar(1.0),
        )

        assert loads_are_convex(vessel) is expected
