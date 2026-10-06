# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""GWP weighting and unit conversion in the port profile's derived emission getters."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from navigate.core.enum_ import FuelTypeID
from navigate.core.profiles.port_profile import PortProfile

# hand math for the fixture below: bunker WTT at step 0 is 2 ton CO2 and 0.1 ton
# CH4 for lsfo (GWP 1 and 25), at step 1 0.4 ton CH4 for lng
LSFO_EQUIVALENT_STEP_0 = 2.0 + 0.1 * 25.0
LNG_EQUIVALENT_STEP_1 = 0.4 * 25.0
LSFO_LHV = 40.0  # GJ/ton
LNG_LHV = 50.0  # GJ/ton


def _fuel(lower_heating_value):
    fuel = MagicMock()
    fuel.fuel_type = FuelTypeID.OIL
    fuel.liquid_market = False
    fuel.lower_heating_value.get.return_value = lower_heating_value
    return fuel


def _emission(global_warming_potential):
    emission = MagicMock()
    emission.global_warming_potential.get.return_value = global_warming_potential
    return emission


@pytest.fixture
def profile():
    port_profile = PortProfile()
    port_profile.initialize(
        timeline=np.array([0.0, 1.0]),
        emissions={"co2": _emission(1.0), "ch4": _emission(25.0)},
        fuels={"lsfo": _fuel(LSFO_LHV), "lng": _fuel(LNG_LHV)},
        emissions_lifetime=100.0,
    )
    port_profile.set_bunker_wtt(0, "lsfo", "co2", 2.0)
    port_profile.set_bunker_wtt(0, "lsfo", "ch4", 0.1)
    port_profile.set_bunker_wtt(1, "lng", "ch4", 0.4)
    return port_profile


@pytest.fixture
def profile_without_emissions():
    # a deck with no Emission node initializes every profile with emissions={},
    # leaving every dict keyed by emission empty (#237)
    port_profile = PortProfile()
    port_profile.initialize(
        timeline=np.array([0.0, 1.0, 2.0]),
        emissions={},
        fuels={"lsfo": _fuel(LSFO_LHV), "lng": _fuel(LNG_LHV)},
        emissions_lifetime=100.0,
    )
    return port_profile


class TestBunkerIntensityTotalEquivalentWtt:
    def test_weights_by_gwp_and_divides_the_per_fuel_total_by_lhv_in_g_per_mj(
        self, profile
    ):
        intensity = profile.get_bunker_intensity_total_equivalent_wtt()

        # each emission is weighted by its GWP before the per-fuel sum (the
        # *_EQUIVALENT_* constants); ton -> g is 1e6 and GJ -> MJ is 1e3, so
        # the intensity is 1e3 times the ton-per-GJ ratio
        np.testing.assert_allclose(
            intensity["lsfo"], [LSFO_EQUIVALENT_STEP_0 / LSFO_LHV * 1e3, 0.0]
        )
        np.testing.assert_allclose(
            intensity["lng"], [0.0, LNG_EQUIVALENT_STEP_1 / LNG_LHV * 1e3]
        )


def test_no_emissions_gives_a_zero_intensity_timeline_per_fuel(
    profile_without_emissions,
):
    # a deck with no Emission node reports zero per fuel, not a bare scalar (#237)
    intensity = profile_without_emissions.get_bunker_intensity_total_equivalent_wtt()

    assert intensity.keys() == {"lsfo", "lng"}

    # assert_array_equal broadcasts a scalar, so the shape is checked apart
    for fuel_intensity in intensity.values():
        assert fuel_intensity.shape == (3,)
        np.testing.assert_array_equal(fuel_intensity, 0.0)
