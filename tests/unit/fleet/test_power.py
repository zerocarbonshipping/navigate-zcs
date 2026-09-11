# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the converter power-capacity verification.

The check asserts, per leg and per port, that the energy a converter delivers
cannot exceed its power capacity times the time spent on the step. Port demands
must fit the onboard converter alone: shore power gives no allowance.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from navigate.core import Scalar
from navigate.core.enum_ import (
    BunkerScopeID,
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
)
from navigate.core.expectations.vessel_expectation import VesselExpectation
from navigate.core.unit import MWD_TO_GJ
from navigate.exceptions import PowerCapacityError
from navigate.fleet.power import verify_power_capacity
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

    def get_energy_sea(self, energy_type_id=None, idx=None) -> dict:
        assert idx == IDX
        return self._energies_sea

    def get_energy_port(self, energy_type_id=None, idx=None) -> dict:
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
    """A one-leg, one-port vessel with 10 MW converters at half load everywhere."""
    half_load = 5.0 * 10.0 * MWD_TO_GJ

    defaults = dict(
        capacities={PROPULSION: 10.0, ELECTRICAL: 10.0, HEAT: 10.0},
        energies_sea={
            PROPULSION: [half_load],
            ELECTRICAL: [half_load],
            HEAT: [half_load],
        },
        times_sea=[10.0],
        energies_port={ELECTRICAL: [half_load], HEAT: [half_load]},
        times_port=[10.0],
    )
    defaults.update(overrides)
    return _StubVessel(**defaults)


class TestVerifyPowerCapacity:
    @pytest.mark.parametrize(
        "load_factor, raises",
        [
            # a load equal to the installed power is feasible, not a violation
            pytest.param(1.0, False, id="exactly_at_capacity"),
            pytest.param(1.0 + TOLERANCE / 2.0, False, id="just_inside_tolerance_band"),
            pytest.param(1.0 + 2.0 * TOLERANCE, True, id="just_outside_tolerance_band"),
        ],
    )
    def test_capacity_tolerance_boundary(self, load_factor, raises):
        limit = 10.0 * 10.0 * MWD_TO_GJ
        vessel = _make_vessel(
            energies_sea={
                PROPULSION: [limit * load_factor],
                ELECTRICAL: [0.0],
                HEAT: [0.0],
            }
        )

        if raises:
            with pytest.raises(PowerCapacityError):
                verify_power_capacity(vessel, IDX)
        else:
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

    @pytest.mark.parametrize(
        "demand_type, message",
        [
            pytest.param(HEAT, "heat demand on port 0", id="heat"),
            pytest.param(ELECTRICAL, "electrical demand on port 0", id="electrical"),
        ],
    )
    def test_port_overload_errors_by_demand_type(self, demand_type, message):
        """Port demand must fit onboard converter; shore power gives no allowance."""
        energies_port = {ELECTRICAL: [0.0], HEAT: [0.0]}
        energies_port[demand_type] = [11.0 * 10.0 * MWD_TO_GJ]
        vessel = _make_vessel(energies_port=energies_port)

        with pytest.raises(PowerCapacityError, match=message):
            verify_power_capacity(vessel, IDX)

    def test_zero_time_zero_energy_passes(self):
        vessel = _make_vessel(
            energies_sea={PROPULSION: [0.0], ELECTRICAL: [0.0], HEAT: [0.0]},
            times_sea=[0.0],
        )
        verify_power_capacity(vessel, IDX)

    def test_zero_time_with_energy_errors(self):
        vessel = _make_vessel(
            energies_sea={PROPULSION: [100.0], ELECTRICAL: [0.0], HEAT: [0.0]},
            times_sea=[0.0],
        )

        with pytest.raises(PowerCapacityError, match="inf MW"):
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
    The expected-scope gating in SimulationManager._verify_power_capacity checks demands
    only at the current index; that is valid because a vessel-expectation write at idx
    broadcasts over the whole remaining horizon, so every future expected-bunkering
    build reads the same demands and times. This pins that contract.
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

    def test_zero_multiplier_vessel_is_skipped(self):
        manager = self._make_manager(
            self._make_overloaded_vessel(),
            existing_multiplier=0.0,
            expected_multipliers=[0.0] * (IDX + 3),
        )

        SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXISTING)
        SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXPECTED)

    def test_scope_selects_its_own_multiplier(self):
        manager = self._make_manager(
            self._make_overloaded_vessel(),
            existing_multiplier=0.0,
            expected_multipliers=[0.0] * IDX + [1.0, 1.0, 1.0],
        )

        SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXISTING)

        with pytest.raises(PowerCapacityError):
            SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXPECTED)

    def test_expected_gating_covers_the_remaining_horizon(self):
        """
        A vessel entering only at a later forecast step is still verified: expected
        bunkering builds one LP per future step, so the gate spans the horizon.
        """
        manager = self._make_manager(
            self._make_overloaded_vessel(),
            existing_multiplier=0.0,
            expected_multipliers=[0.0] * (IDX + 2) + [1.0],
        )

        SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXISTING)

        with pytest.raises(PowerCapacityError):
            SimulationManager._verify_power_capacity(manager, BunkerScopeID.EXPECTED)
