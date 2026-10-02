# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
plot_regulation_unit_trading must not mutate the profile arrays it plots.

The getters it reads (get_surplus_units, get_flexibility_units,
get_remedial_units) return references into the regulation profile's own
storage, so scaling the plotted values for the y-axis unit has to produce new
arrays rather than divide those references in place -- otherwise a second
Plot node rendering the same regulation rescales an already-rescaled array
(issue #394).
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from navigate.core.enum_ import RegulationSchemeID
from navigate.output.plots._style import initialize_matplotlib
from navigate.output.plots.regulation_unit_trading import plot_regulation_unit_trading

initialize_matplotlib()


def _regulation_profile(surplus, flexibility, remedial):
    return SimpleNamespace(
        get_surplus_units=lambda: surplus,
        get_flexibility_units=lambda: flexibility,
        get_remedial_units=lambda: remedial,
        get_non_compliance_units=lambda: flexibility + remedial,
    )


def test_plot_leaves_profile_arrays_unchanged(tmp_path):
    dateline = np.array(
        ["2030-01-01", "2031-01-01", "2032-01-01"], dtype="datetime64[D]"
    )
    surplus_units = np.array([1.0e6, 2.0e6, 3.0e6])
    flexibility_units = np.array([4.0e6, 5.0e6, 6.0e6])
    remedial_units = np.array([7.0e6, 8.0e6, 9.0e6])

    surplus_before = surplus_units.copy()
    flexibility_before = flexibility_units.copy()
    remedial_before = remedial_units.copy()

    profile = _regulation_profile(surplus_units, flexibility_units, remedial_units)
    regulation = SimpleNamespace(scheme=RegulationSchemeID.FLEXIBLE, profile=profile)
    manager = SimpleNamespace(
        dateline=dateline, nodes=SimpleNamespace(regulations={"ets": regulation})
    )

    plot_regulation_unit_trading(manager, str(tmp_path))

    np.testing.assert_array_equal(surplus_units, surplus_before)
    np.testing.assert_array_equal(flexibility_units, flexibility_before)
    np.testing.assert_array_equal(remedial_units, remedial_before)
    assert (tmp_path / "regulation_unit_trading_ets.png").exists()


def test_plot_skips_a_non_flexible_regulation(tmp_path):
    dateline = np.array(["2030-01-01", "2031-01-01"], dtype="datetime64[D]")
    profile = _regulation_profile(
        np.array([1.0, 2.0]), np.array([1.0, 2.0]), np.array([1.0, 2.0])
    )
    regulation = SimpleNamespace(scheme=RegulationSchemeID.INDIVIDUAL, profile=profile)
    manager = SimpleNamespace(
        dateline=dateline, nodes=SimpleNamespace(regulations={"eexi": regulation})
    )

    plot_regulation_unit_trading(manager, str(tmp_path))

    assert not (tmp_path / "regulation_unit_trading_eexi.png").exists()
