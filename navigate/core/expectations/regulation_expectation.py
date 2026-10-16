# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Regulation node, read by the bunkering LP and policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.expectations._policy_expectation import _PolicyExpectation
from navigate.core.initial_values import EMPTY_FLOAT, EMPTY_NAN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class RegulationExpectation(_PolicyExpectation):
    """Coefficients, thresholds, costs, fractions, measures, allowances, LP results."""

    def __init__(self) -> None:
        super().__init__()

        # keyed by (vessel_name, converter_name, fuel_name), in ton emission/ton fuel
        self._emission_coefficient: dict[tuple[str, str, str], FloatArray] = {}
        self._spend_coefficient: dict[tuple[str, str, str], FloatArray] = {}

        # in ton emission/GJ, the emission coefficient keyed by port_name and the
        # spend coefficient by (vessel_name, port_name)
        self._shore_power_emission_coefficient: dict[str, FloatArray] = {}
        self._shore_power_spend_coefficient: dict[tuple[str, str], FloatArray] = {}

        self._flexibility_cost: FloatArray = EMPTY_FLOAT
        self._belief_flexibility_cost: FloatArray = EMPTY_NAN
        self._vessel_net_flexibility_units: dict[str, FloatArray] = {}
        self._remedial_cost: FloatArray = EMPTY_FLOAT

        self._port_fraction: dict[str, FloatArray] = {}
        # keyed by (departure port_name, arrival port_name)
        self._leg_fraction: dict[tuple[str, str], FloatArray] = {}

        # vessel thresholds in the regulation's unit, kg emission/GJ under INTENSITY
        self._vessel_threshold: dict[str, FloatArray] = {}
        self._vessel_capacity: dict[str, FloatArray] = {}
        self._vessel_measure: dict[str, FloatArray] = {}

        # threshold times measure, in tons emission; zero under INTENSITY, whose
        # threshold enters the spend coefficients instead
        self._vessel_allowance: dict[str, FloatArray] = {}

        # the results of the bunkering LP of each time step: the regulated emissions,
        # in tons, and energy, in GJ, of each policed vessel, and under FLEXIBLE the
        # pooled remedial units and the shadow price of the pooled threshold
        self._vessel_emissions: dict[str, FloatArray] = {}
        self._vessel_energy: dict[str, FloatArray] = {}
        self._pooled_remedial_units: FloatArray = EMPTY_FLOAT
        self._pooled_shadow_price: FloatArray = EMPTY_FLOAT

        # the thresholds adjusted to the compliance achievable, written by the
        # bunkering, which adjusts them; NaN where it adjusted none
        self._adjusted_vessel_threshold: dict[str, FloatArray] = {}
        self._adjusted_shared_threshold: FloatArray = EMPTY_NAN

    def initialize(
        self,
        length: int,
        emission_names: Iterable[str],
        routes: dict[str, Route],
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

        port_names = [port.name for route in routes.values() for port in route.ports]
        legs = [leg for route in routes.values() for leg in route.get_leg_keys()]

        vessel_ports: list[tuple[str, str]] = []
        for vessel_name, vessel in vessels.items():
            vessel_ports.extend((vessel_name, port.name) for port in vessel.route.ports)

        self._shore_power_emission_coefficient = self._default_dict_array(port_names)
        self._shore_power_spend_coefficient = self._default_dict_array(vessel_ports)

        self._port_fraction = self._default_dict_array(port_names)
        self._leg_fraction = self._default_dict_array(legs)

        self._vessel_threshold = self._default_dict_array(vessels)
        self._vessel_capacity = self._default_dict_array(vessels)
        self._vessel_measure = self._default_dict_array(vessels)
        self._vessel_allowance = self._default_dict_array(vessels)

        self._vessel_emissions = self._default_dict_array(vessels)
        self._vessel_energy = self._default_dict_array(vessels)
        self._pooled_remedial_units = self._default_array()
        self._pooled_shadow_price = self._default_array()

        self._adjusted_vessel_threshold = self._default_dict_array(
            vessels, default=np.nan
        )
        self._adjusted_shared_threshold = self._default_array(default=np.nan)

    def reset_expected_bunkering(self) -> None:
        self._flexibility_cost[:] = 0.0

        for units in self._vessel_net_flexibility_units.values():
            units[:] = 0.0

    def set_emission_coefficient(
        self, idx: int, key: tuple[str, str, str], coefficient: FloatLike
    ) -> None:
        self._emission_coefficient.setdefault(key, self._default_array())
        self._emission_coefficient[key][idx:] = coefficient

    def set_spend_coefficient(
        self, idx: int, key: tuple[str, str, str], coefficient: FloatLike
    ) -> None:
        self._spend_coefficient.setdefault(key, self._default_array())
        self._spend_coefficient[key][idx:] = coefficient

    def set_shore_power_emission_coefficient(
        self, idx: int, port_name: str, coefficient: FloatLike
    ) -> None:
        self._shore_power_emission_coefficient[port_name][idx:] = coefficient

    def set_shore_power_spend_coefficient(
        self, idx: int, key: tuple[str, str], coefficient: FloatLike
    ) -> None:
        self._shore_power_spend_coefficient[key][idx:] = coefficient

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

    def set_vessel_threshold(
        self, idx: int, vessel_name: str, threshold: FloatLike
    ) -> None:
        self._vessel_threshold[vessel_name][idx:] = threshold

    def set_vessel_capacity(
        self, idx: int, vessel_name: str, capacity: FloatLike
    ) -> None:
        self._vessel_capacity[vessel_name][idx:] = capacity

    def set_vessel_measure(
        self, idx: int, vessel_name: str, measure: FloatLike
    ) -> None:
        self._vessel_measure[vessel_name][idx:] = measure

    def set_vessel_allowance(
        self, idx: int, vessel_name: str, allowance: FloatLike
    ) -> None:
        self._vessel_allowance[vessel_name][idx:] = allowance

    def set_vessel_emissions(
        self, idx: int, vessel_name: str, emissions: float
    ) -> None:
        self._vessel_emissions[vessel_name][idx] = emissions

    def set_vessel_energy(self, idx: int, vessel_name: str, energy: float) -> None:
        self._vessel_energy[vessel_name][idx] = energy

    def set_pooled_remedial_units(self, idx: int, units: float) -> None:
        self._pooled_remedial_units[idx] = units

    def set_pooled_shadow_price(self, idx: int, price: float) -> None:
        self._pooled_shadow_price[idx] = price

    def set_adjusted_vessel_threshold(
        self, idx: int, vessel_name: str, threshold: float
    ) -> None:
        self._adjusted_vessel_threshold[vessel_name][idx] = threshold

    def set_adjusted_shared_threshold(self, idx: int, threshold: float) -> None:
        self._adjusted_shared_threshold[idx] = threshold

    @overload
    def get_emission_coefficient(
        self, key: tuple[str, str, str], idx: int
    ) -> float: ...

    @overload
    def get_emission_coefficient(
        self, key: tuple[str, str, str], idx: slice
    ) -> FloatLike: ...

    def get_emission_coefficient(
        self, key: tuple[str, str, str], idx: int | slice
    ) -> FloatLike:

        if key in self._emission_coefficient:
            return self._emission_coefficient[key][idx]

        return 0.0

    def get_spend_coefficient(self, key: tuple[str, str, str], idx: int) -> float:
        coefficient: float = self._spend_coefficient[key][idx]
        return coefficient

    @overload
    def get_shore_power_emission_coefficient(
        self, port_name: str, idx: int
    ) -> float: ...

    @overload
    def get_shore_power_emission_coefficient(
        self, port_name: str, idx: slice
    ) -> FloatArray: ...

    def get_shore_power_emission_coefficient(
        self, port_name: str, idx: int | slice
    ) -> FloatLike:
        return self._shore_power_emission_coefficient[port_name][idx]

    def get_shore_power_spend_coefficient(
        self, key: tuple[str, str], idx: int
    ) -> float:
        coefficient: float = self._shore_power_spend_coefficient[key][idx]
        return coefficient

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

    @overload
    def get_vessel_threshold(self, vessel_name: str, idx: int) -> float: ...

    @overload
    def get_vessel_threshold(self, vessel_name: str, idx: slice) -> FloatArray: ...

    def get_vessel_threshold(self, vessel_name: str, idx: int | slice) -> FloatLike:
        return self._vessel_threshold[vessel_name][idx]

    def get_vessel_capacity(self, vessel_name: str, idx: slice) -> FloatArray:
        return self._vessel_capacity[vessel_name][idx]

    @overload
    def get_vessel_measure(self, vessel_name: str, idx: int) -> float: ...

    @overload
    def get_vessel_measure(self, vessel_name: str, idx: slice) -> FloatArray: ...

    def get_vessel_measure(self, vessel_name: str, idx: int | slice) -> FloatLike:
        return self._vessel_measure[vessel_name][idx]

    def get_vessel_allowance(self, vessel_name: str, idx: int) -> float:
        allowance: float = self._vessel_allowance[vessel_name][idx]
        return allowance

    def get_vessel_emissions(self, vessel_name: str, idx: int) -> float:
        emissions: float = self._vessel_emissions[vessel_name][idx]
        return emissions

    def get_vessel_energy(self, vessel_name: str, idx: int) -> float:
        energy: float = self._vessel_energy[vessel_name][idx]
        return energy

    def get_pooled_remedial_units(self, idx: int) -> float:
        units: float = self._pooled_remedial_units[idx]
        return units

    def get_pooled_shadow_price(self, idx: int) -> float:
        price: float = self._pooled_shadow_price[idx]
        return price

    def get_adjusted_vessel_threshold(self, vessel_name: str, idx: int) -> float:
        threshold: float = self._adjusted_vessel_threshold[vessel_name][idx]
        return threshold

    def get_adjusted_shared_threshold(self, idx: int) -> float:
        threshold: float = self._adjusted_shared_threshold[idx]
        return threshold
