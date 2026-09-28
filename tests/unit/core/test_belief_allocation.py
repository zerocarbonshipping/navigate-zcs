# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
A belief path is allocated NaN-filled, the never-updated marker it bootstraps from.

The smoothed quantities are shadow prices, legitimately zero wherever their
constraint does not bind, so a zero-filled allocation would make the first
update after a stretch of zeros smooth against a prior that was never observed.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.enum_ import EnergyDemandTypeID, EnergyDemandTypePortID
from navigate.core.expectations.regulation_expectation import RegulationExpectation
from navigate.core.expectations.vessel_expectation import VesselExpectation

LENGTH = 4

# distinct counts, so a sea belief sized by legs or ports instead of regional
# legs, or a port belief sized by legs, fails
N_LEG = 2
N_REGIONAL_LEG = 3
N_PORT = 5


class _Port:
    def __init__(self, name):
        self.name = name


class _Route:
    def __init__(self):
        self.ports = [_Port(f"port_{i}") for i in range(N_PORT)]

    def get_number_of_legs(self):
        return N_LEG

    def get_number_of_regional_legs(self):
        return N_REGIONAL_LEG

    def get_number_of_ports(self):
        return N_PORT


def test_regulation_flexibility_cost_belief_is_all_nan():
    expectation = RegulationExpectation()
    expectation.initialize(LENGTH, ["carbon_dioxide"], {"vessel_a": None})

    belief = expectation.get_belief_flexibility_cost()

    assert belief.shape == (LENGTH,)
    assert np.isnan(belief).all()


@pytest.mark.parametrize(
    ("getter", "keys", "n_legs"),
    [
        ("get_belief_pi_sea_technology", set(EnergyDemandTypeID), N_REGIONAL_LEG),
        ("get_belief_pi_port_technology", set(EnergyDemandTypePortID), N_PORT),
        ("get_belief_pi_sea_speed", set(EnergyDemandTypeID), N_REGIONAL_LEG),
        ("get_belief_pi_port_speed", set(EnergyDemandTypePortID), N_PORT),
    ],
    ids=["pi_sea_technology", "pi_port_technology", "pi_sea_speed", "pi_port_speed"],
)
def test_vessel_scarcity_belief_is_all_nan(getter, keys, n_legs):
    expectation = VesselExpectation()
    expectation.initialize(LENGTH, _Route(), {"ammonia": None})

    belief = getattr(expectation, getter)()

    assert set(belief) == keys
    for key, legs in belief.items():
        assert len(legs) == n_legs, key
        for leg in legs:
            assert leg.shape == (LENGTH,), key
            assert np.isnan(leg).all(), key
