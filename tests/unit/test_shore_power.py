# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests the regulation emission factor and spend coefficient of shore power."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from navigate.bunker.coefficients import calculate_regulation_coefficients
from navigate.core import Scalar
from navigate.core.enum_ import RegulationMeasureID


def _shore_power_coefficients(measure, emission_factors, gwp, threshold):
    """Return the shore-power regulation emission factor and spend coefficient."""
    regulation = SimpleNamespace(
        measure=measure,
        emissions=[SimpleNamespace(name=name) for name in emission_factors],
        vessel_threshold={"vessel": Scalar(threshold)},
        vessel_is_policed=lambda vessel_name: True,
        expectation=SimpleNamespace(get_global_warming_potential=gwp.get),
    )
    port = SimpleNamespace(
        expectation=SimpleNamespace(
            get_shore_power_emission_factor=lambda name, idx: emission_factors[name]
        )
    )
    # a vessel without converters, so only the shore-power terms are computed
    vessel = SimpleNamespace(
        name="vessel",
        route=SimpleNamespace(ports=[port]),
        power_system=SimpleNamespace(get_converters=lambda: ()),
    )
    alg = SimpleNamespace(
        idx=0,
        time=0.0,
        active_regulations={"reg": regulation},
        effective_lhv={},
        fuels_per_converter={},
        shore_power={("vessel", 0): None},
        regulation_vessel_threshold={},
        regulation_emission_factor={},
        regulation_spend_coefficient={},
        shore_power_regulation_emission_factor={},
        shore_power_regulation_coefficient={},
    )

    calculate_regulation_coefficients(alg, vessel)

    key = ("vessel", 0, "reg")
    return (
        alg.shore_power_regulation_emission_factor[key],
        alg.shore_power_regulation_coefficient[key],
    )


@pytest.mark.parametrize(
    ("measure", "emission_factors", "gwp", "threshold", "expected"),
    [
        # shore power is bought in GJ, so the 10 g/MJ (kg/GJ) threshold comes
        # off the 0.05 t/GJ factor as 10 / 1000 t/GJ: 0.05 - 0.01
        pytest.param(
            RegulationMeasureID.INTENSITY,
            {"co2": 0.05},
            {"co2": 1.0},
            10.0,
            (0.05, 0.04),
            id="intensity_subtracts_threshold",
        ),
        # co2: 0.05 * 1.0 + ch4: 0.001 * 28.0 = 0.078
        pytest.param(
            RegulationMeasureID.ABSOLUTE,
            {"co2": 0.05, "ch4": 0.001},
            {"co2": 1.0, "ch4": 28.0},
            0.0,
            (0.078, 0.078),
            id="gwp_conversion_applied",
        ),
    ],
)
def test_regulation_coefficient(measure, emission_factors, gwp, threshold, expected):
    result = _shore_power_coefficients(measure, emission_factors, gwp, threshold)

    assert result == pytest.approx(expected)
