# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
An expectation getter that indexes its storage by key raises KeyError.

Each of those storages is prepopulated at initialization over the same global
collection its callers iterate, so no run asks for an absent key, and a getter
that answered one with a value would carry the mistake into the arithmetic
consuming it, far from where the key was asked for. A storage that instead
fills within the step it is read in, such as the per-converter spend, carries
no such guarantee and is read through a membership test.
"""

from __future__ import annotations

import pytest

from navigate.core.expectations.plant_expectation import PlantExpectation
from navigate.core.expectations.vessel_expectation import VesselExpectation

LENGTH = 3

# only the keys of these collections reach the storages
EMISSIONS = {"carbon_dioxide": None}
FEEDSTOCKS = {"biomass": None}
PORTS = {"port_a": None}
PROCESSES = {"electrolysis": None}
FUELS = {"ammonia": None}
EMPTY: dict[str, None] = {}

# a key must fail alike on a storage a run would build and on an empty one
POPULATIONS = {
    "populated": (EMISSIONS, FEEDSTOCKS, PORTS, PROCESSES, FUELS),
    "empty": (EMPTY, EMPTY, EMPTY, EMPTY, EMPTY),
}

UNKNOWN = "no_such_name"


class _Port:
    def __init__(self, name):
        self.name = name


class _Route:
    def __init__(self, port_names):
        self.ports = [_Port(name) for name in port_names]

    def get_number_of_legs(self):
        return len(self.ports)

    def get_number_of_regional_legs(self):
        return len(self.ports)

    def get_number_of_ports(self):
        return len(self.ports)


@pytest.fixture(params=POPULATIONS.values(), ids=POPULATIONS)
def expectations(request):
    emissions, feedstocks, ports, processes, fuels = request.param

    plant = PlantExpectation()
    plant.initialize(LENGTH, emissions, feedstocks, ports, processes)

    vessel = VesselExpectation()
    vessel.initialize(LENGTH, _Route(ports), fuels)

    return {"plant": plant, "vessel": vessel}


# every getter on the two classes that indexes its storage by key, once per key
CASES = [
    ("plant", "get_feed_mass", (UNKNOWN,)),
    ("plant", "get_levelized_delivery_cost", (UNKNOWN,)),
    ("plant", "get_production_wtt", (UNKNOWN,)),
    ("plant", "get_expected_production_wtt", (UNKNOWN,)),
    ("plant", "get_delivery_wtt", (UNKNOWN, "carbon_dioxide")),
    ("plant", "get_delivery_wtt", ("port_a", UNKNOWN)),
    ("vessel", "get_bunker_mass_expected", (UNKNOWN, "ammonia")),
    ("vessel", "get_bunker_mass_expected", ("port_a", UNKNOWN)),
    ("vessel", "get_bunker_mass_existing", (UNKNOWN, "ammonia")),
    ("vessel", "get_bunker_mass_existing", ("port_a", UNKNOWN)),
    ("vessel", "get_fair_share_fuel_existing", (UNKNOWN, "ammonia")),
    ("vessel", "get_fair_share_fuel_existing", ("port_a", UNKNOWN)),
    ("vessel", "get_fair_share_fuel_expected", (UNKNOWN, "ammonia")),
    ("vessel", "get_fair_share_fuel_expected", ("port_a", UNKNOWN)),
]


@pytest.mark.parametrize(
    ("node", "getter", "keys"),
    CASES,
    ids=[f"{node}.{getter}{keys}" for node, getter, keys in CASES],
)
def test_unknown_key_raises(expectations, node, getter, keys):
    with pytest.raises(KeyError):
        getattr(expectations[node], getter)(*keys)
