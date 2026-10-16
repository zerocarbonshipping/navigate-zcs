# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Technology packages, their uptake, and the operational savings beneath them.

A fleet installs its technologies as packages, whose savings on one energy
demand compound: each technology saves its fraction of what the others leave,
whatever their order. An operational saving scales the raw demand before any
technology acts, so a technology saves its fraction of what the operational
saving leaves. With the initial share at 1, the first step shows a package's
saving exactly, before any newbuild without it enters the fleet.

Uptake on newbuilds is a decision on the package's business case: it must fall
as the technology's CAPEX rises, and rise on a vessel whose fuel gets dearer,
since each GJ saved is then worth more. Only the direction is asserted, on the
decided steps.
"""

from __future__ import annotations

import numpy as np
import pytest

from navigate.core.enum_ import EnergyDemandID

FLEET = "container_15000_teu"
METHANE_VESSEL = "container_15000_teu_ice_methane"
TECHNOLOGY = "combination_technology"

PROPULSION = EnergyDemandID.PROPULSION
ELECTRICAL = EnergyDemandID.ELECTRICAL

# Propulsion savings of the two technologies in technology_package.inc, and the
# saving of each package. Together, each saves its fraction of what the other
# leaves: 1 - (1 - 0.1) * (1 - 0.2) = 0.28, not 0.1 + 0.2.
SAVING_A = 0.1
SAVING_B = 0.2
PACKAGES = {
    ("a",): 0.1,
    ("b",): 0.2,
    ("a", "b"): 0.28,
    ("b", "a"): 0.28,
}

# Operational savings per demand in operational_saving.inc. Under package b,
# propulsion keeps (1 - 0.1) * (1 - 0.2) = 0.72 of its raw energy.
OPERATIONAL_SAVING = {
    "sea_propulsion": 0.1,
    "sea_electrical": 0.2,
    "port_electrical": 0.15,
}
PROPULSION_KEPT_UNDER_B = 0.72

# each saving above, by where and on which demand it acts
OPERATIONAL_DEMANDS = (
    ("sea_propulsion", "sea", PROPULSION),
    ("sea_electrical", "sea", ELECTRICAL),
    ("port_electrical", "port", ELECTRICAL),
)

# USD, on the same 5% propulsion saving: the dearer CAPEX costs ten times more
CHEAP_CAPEX = 1e6
DEAR_CAPEX = 1e7

# USD/ton, as in test_fuel_price_response.py
DEARER_LNG_PRICE = 480

# the same products of savings, taken in a different order
SAVING_RTOL = 1e-9

pytestmark = pytest.mark.slow


def _package_layer(technologies):
    listed = ", ".join(
        f'Technology("combination_technology_{t}")' for t in technologies
    )
    return (
        "technology_package.inc",
        {"saving_a": SAVING_A, "saving_b": SAVING_B, "technologies": listed},
    )


def _operational_layer():
    return ("operational_saving.inc", OPERATIONAL_SAVING)


def _uptake_layer(capex):
    return ("technology_uptake.inc", {"capex": capex})


def _vessels(results):
    return results.nodes.fleets[FLEET].vessels


def _newbuild_uptake(results, vessel):
    uptake = results.nodes.fleets[FLEET].profile.get_newbuild_technology_uptake()
    return uptake[(vessel, TECHNOLOGY)][1:]


@pytest.mark.parametrize(("technologies", "saving"), list(PACKAGES.items()))
def test_a_package_compounds_the_savings_of_its_technologies(
    run_combination, technologies, saving
):
    results = run_combination(_package_layer(technologies))

    for vessel in _vessels(results):
        energy = vessel.profile.get_energy_sea()
        operational = vessel.profile.get_operational_energy_sea()

        kept = energy[PROPULSION][0] / operational[PROPULSION][0]
        assert 1.0 - kept == pytest.approx(saving, rel=SAVING_RTOL), vessel.name

        # a propulsion saving leaves the electrical demand alone
        assert energy[ELECTRICAL][0] == operational[ELECTRICAL][0], vessel.name


def test_an_operational_saving_scales_only_its_own_demand(run_combination):
    results = run_combination(_operational_layer())

    for vessel in _vessels(results):
        profile = vessel.profile
        raw = {
            "sea": profile.get_raw_energy_sea(),
            "port": profile.get_raw_energy_port(),
        }
        operational = {
            "sea": profile.get_operational_energy_sea(),
            "port": profile.get_operational_energy_port(),
        }

        for name, where, demand in OPERATIONAL_DEMANDS:
            assert np.all(raw[where][demand] > 0.0), f"{vessel.name} has no {name}"

            kept = operational[where][demand] / raw[where][demand]
            np.testing.assert_allclose(
                kept,
                1.0 - OPERATIONAL_SAVING[name],
                rtol=SAVING_RTOL,
                err_msg=f"{vessel.name} {name}",
            )


def test_a_technology_saves_on_what_the_operational_saving_leaves(run_combination):
    results = run_combination(_operational_layer(), _package_layer(("b",)))

    for vessel in _vessels(results):
        energy = vessel.profile.get_energy_sea()[PROPULSION][0]
        raw = vessel.profile.get_raw_energy_sea()[PROPULSION][0]

        assert energy / raw == pytest.approx(
            PROPULSION_KEPT_UNDER_B, rel=SAVING_RTOL
        ), vessel.name


def test_newbuild_uptake_falls_as_the_capex_rises(run_combination):
    cheap = run_combination(_uptake_layer(CHEAP_CAPEX))
    dear = run_combination(_uptake_layer(DEAR_CAPEX))

    for vessel in _vessels(cheap):
        cheap_uptake = _newbuild_uptake(cheap, vessel.name)
        dear_uptake = _newbuild_uptake(dear, vessel.name)

        assert np.all(cheap_uptake > 0.0), f"{vessel.name} installs nothing"
        assert np.all(dear_uptake < cheap_uptake), vessel.name


def test_newbuild_uptake_rises_on_the_vessel_whose_fuel_gets_dearer(run_combination):
    base = run_combination(_uptake_layer(CHEAP_CAPEX))
    dearer = run_combination(
        _uptake_layer(CHEAP_CAPEX),
        ("lng_price.inc", {"lng_price": DEARER_LNG_PRICE}),
    )

    base_uptake = _newbuild_uptake(base, METHANE_VESSEL)
    dearer_uptake = _newbuild_uptake(dearer, METHANE_VESSEL)

    assert np.all(dearer_uptake > base_uptake)
