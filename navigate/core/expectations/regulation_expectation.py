# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Regulation node, read by the bunkering LP and policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.port import Port
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class RegulationExpectation(_PolicyExpectation):
    """Emission coefficients, costs, fractions and vessel measures of a regulation."""

    def __init__(self) -> None:
        super().__init__()

        # keyed by (vessel_name, converter_name, fuel_name)
        self._coefficient: dict[tuple[str, str, str], FloatArray] = {}

        self._flexibility_cost: FloatArray = EMPTY_FLOAT
        self._belief_flexibility_cost: FloatArray = EMPTY_NAN
        self._vessel_net_flexibility_units: dict[str, FloatArray] = {}
        self._remedial_cost: FloatArray = EMPTY_FLOAT

        self._port_fraction: dict[str, FloatArray] = {}
        # keyed by (departure port_name, arrival port_name)
        self._leg_fraction: dict[tuple[str, str], FloatArray] = {}

        self._vessel_capacity: dict[str, FloatArray] = {}
        self._vessel_measure: dict[str, FloatArray] = {}

    def initialize(
        self,
        length: int,
        emission_names: Iterable[str],
        ports: dict[str, Port],
        vessels: dict[str, Vessel],
    ) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        self._flexibility_cost = self._default_array()
        # NaN until the first belief update: the flexibility cost is a shadow
        # price, legitimately zero wherever the constraint does not bind
        self._belief_flexibility_cost = self._default_array(default=np.nan)
        self._vessel_net_flexibility_units = self._default_dict_array(vessels)
        self._remedial_cost = self._default_array()

        self._port_fraction = self._default_dict_array(ports)
        self._leg_fraction = self._default_tuple_dict_array(ports, ports)

        self._vessel_capacity = self._default_dict_array(vessels)
        self._vessel_measure = self._default_dict_array(vessels)

    def reset_expected_bunkering(self) -> None:
        self._flexibility_cost[:] = 0.0

        for units in self._vessel_net_flexibility_units.values():
            units[:] = 0.0

    def set_coefficient(
        self, idx: int, key: tuple[str, str, str], coefficient: FloatLike
    ) -> None:
        self._coefficient.setdefault(key, self._default_array())
        self._coefficient[key][idx:] = coefficient

    def set_flexibility_cost(self, idx: int, cost: float) -> None:
        self._flexibility_cost[idx] = cost

    def set_vessel_net_flexibility_units(
        self, idx: int, vessel_name: str, units: float
    ) -> None:
        self._vessel_net_flexibility_units[vessel_name][idx] = units

    def set_remedial_cost(self, idx: int, cost: FloatLike) -> None:
        self._remedial_cost[idx:] = cost

    def set_port_fraction(self, idx: int, port_name: str, fraction: FloatLike) -> None:
        self._port_fraction[port_name][idx:] = fraction

    def set_leg_fraction(
        self, idx: int, leg: tuple[str, str], fraction: FloatLike
    ) -> None:
        self._leg_fraction[leg][idx:] = fraction

    def set_vessel_capacity(
        self, idx: int, vessel_name: str, capacity: FloatLike
    ) -> None:
        self._vessel_capacity[vessel_name][idx:] = capacity

    def set_vessel_measure(
        self, idx: int, vessel_name: str, measure: FloatLike
    ) -> None:
        self._vessel_measure[vessel_name][idx:] = measure

    def get_coefficient(self, key: tuple[str, str, str], idx: int) -> float:

        if key in self._coefficient:
            coefficient: float = self._coefficient[key][idx]
            return coefficient

        return 0.0

    def get_flexibility_cost(self) -> FloatArray:
        return self._flexibility_cost

    def get_belief_flexibility_cost(self) -> FloatArray:
        return self._belief_flexibility_cost

    def get_vessel_net_flexibility_units(self, vessel_name: str) -> FloatArray:
        return self._vessel_net_flexibility_units[vessel_name]

    def get_remedial_cost(self, idx: int) -> float:
        cost: float = self._remedial_cost[idx]
        return cost

    def get_port_fraction(self, port_name: str, idx: int) -> float:
        fraction: float = self._port_fraction[port_name][idx]
        return fraction

    def get_leg_fraction(self, leg: tuple[str, str], idx: Index) -> FloatLike:
        return self._leg_fraction[leg][idx]

    def get_vessel_capacity(self, vessel_name: str, idx: slice) -> FloatArray:
        return self._vessel_capacity[vessel_name][idx]

    def get_vessel_measure(self, vessel_name: str, idx: int) -> float:
        measure: float = self._vessel_measure[vessel_name][idx]
        return measure
