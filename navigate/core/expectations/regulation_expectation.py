# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The expectation of a Regulation node, read by the bunkering LP and policy layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, overload

import numpy as np

from navigate.core.expectations._policy_expectation import _PolicyExpectation

if TYPE_CHECKING:
    from collections.abc import Collection

    from navigate.core.nodes.route import Route
    from navigate.core.nodes.vessel import Vessel
    from navigate.util.types_ import FloatArray, FloatLike, Index


class RegulationExpectation(_PolicyExpectation[tuple[str, str, str, str]]):
    """The inputs a regulation gives the bunkering LP and the results it gets back."""

    def __init__(self) -> None:
        super().__init__()

        # keyed by (vessel_name, converter_name, fuel_name), in ton emission/ton fuel;
        # once threshold adjustment has run, a bunkering LP's own step holds the
        # adjusted spend coefficients
        self._emission_coefficient: dict[tuple[str, str, str], FloatArray] = {}
        self._spend_coefficient: dict[tuple[str, str, str], FloatArray] = {}

        # in ton emission/GJ, the emission coefficient keyed by port_name and the
        # spend coefficient by (vessel_name, port_name), adjusted at a bunkering LP's
        # own step as the fuel spend coefficients are
        self._shore_power_emission_coefficient: dict[str, FloatArray]
        self._shore_power_spend_coefficient: dict[tuple[str, str], FloatArray]

        self._flexibility_cost: FloatArray
        self._belief_flexibility_cost: FloatArray
        self._vessel_net_flexibility_units: dict[str, FloatArray]
        self._remedial_cost: FloatArray

        # fractions keyed by port_name and by (departure, arrival) port_name
        self._port_fraction: dict[str, FloatArray]
        self._leg_fraction: dict[tuple[str, str], FloatArray]

        # per vessel; threshold in the regulation's unit, kg emission/GJ under INTENSITY
        self._vessel_threshold: dict[str, FloatArray]
        self._vessel_capacity: dict[str, FloatArray]
        self._vessel_measure: dict[str, FloatArray]

        # threshold times measure, in tons emission; zero under INTENSITY, whose
        # threshold enters the spend coefficients instead; once threshold adjustment
        # has run, a bunkering LP's own step holds the adjusted allowances
        self._vessel_allowance: dict[str, FloatArray]

        # the results of the bunkering LP of each time step: per policed vessel the
        # regulated emissions, in tons, the energy, in GJ, and under INDIVIDUAL the
        # remedial units; under FLEXIBLE the pooled remedial units and the shadow
        # price of the pooled threshold
        self._vessel_emissions: dict[str, FloatArray]
        self._vessel_energy: dict[str, FloatArray]
        self._vessel_remedial_units: dict[str, FloatArray]
        self._pooled_remedial_units: FloatArray
        self._pooled_shadow_price: FloatArray

        # the thresholds adjusted to the compliance achievable, written by the
        # threshold adjustment after the first solve of each bunkering LP; a compliant
        # vessel of an adjustable regulation holds its original threshold. NaN where
        # the regulation allows no adjustment, and in the shared slot under INDIVIDUAL
        # or of a compliant FLEXIBLE regulation
        self._adjusted_vessel_threshold: dict[str, FloatArray]
        self._adjusted_shared_threshold: FloatArray

    def initialize(
        self,
        length: int,
        emission_names: Collection[str],
        routes: dict[str, Route],
        vessels: dict[str, Vessel],
    ) -> None:
        self._initialize_expectation(length)
        self._initialize_policy_expectation(emission_names)

        port_names = [port.name for route in routes.values() for port in route.ports]
        legs = [leg for route in routes.values() for leg in route.get_leg_keys()]

        vessel_ports: list[tuple[str, str]] = []
        for vessel_name, vessel in vessels.items():
            vessel_ports.extend((vessel_name, port.name) for port in vessel.route.ports)

        self._shore_power_emission_coefficient = self._default_dict_array(port_names)
        self._shore_power_spend_coefficient = self._default_dict_array(vessel_ports)

        # the belief is NaN until its first update: the flexibility cost is a shadow
        # price, legitimately zero wherever the constraint does not bind
        self._flexibility_cost = self._default_array()
        self._belief_flexibility_cost = self._default_array(default=np.nan)
        self._vessel_net_flexibility_units = self._default_dict_array(vessels)
        self._remedial_cost = self._default_array()

        self._port_fraction = self._default_dict_array(port_names)
        self._leg_fraction = self._default_dict_array(legs)

        self._vessel_threshold = self._default_dict_array(vessels)
        self._vessel_capacity = self._default_dict_array(vessels)
        self._vessel_measure = self._default_dict_array(vessels)
        self._vessel_allowance = self._default_dict_array(vessels)

        self._vessel_emissions = self._default_dict_array(vessels)
        self._vessel_energy = self._default_dict_array(vessels)
        self._vessel_remedial_units = self._default_dict_array(vessels)
        self._pooled_remedial_units = self._default_array()
        self._pooled_shadow_price = self._default_array()

        self._adjusted_vessel_threshold = self._default_dict_array(
            vessels, default=np.nan
        )
        self._adjusted_shared_threshold = self._default_array(default=np.nan)

    def reset_expected_bunkering(self) -> None:
        self._flexibility_cost = self._default_array()
        self._reset_dict_array(self._vessel_net_flexibility_units)

    def set_emission_coefficient(
        self, key: tuple[str, str, str], idx: int, coefficient: FloatLike
    ) -> None:
        self._emission_coefficient.setdefault(key, self._default_array())
        self._emission_coefficient[key][idx:] = coefficient

    def set_spend_coefficient(
        self, key: tuple[str, str, str], idx: int | slice, coefficient: FloatLike
    ) -> None:
        self._spend_coefficient.setdefault(key, self._default_array())
        self._spend_coefficient[key][idx] = coefficient

    def set_shore_power_emission_coefficient(
        self, port_name: str, idx: int, coefficient: FloatLike
    ) -> None:
        self._shore_power_emission_coefficient[port_name][idx:] = coefficient

    def set_shore_power_spend_coefficient(
        self, key: tuple[str, str], idx: int | slice, coefficient: FloatLike
    ) -> None:
        self._shore_power_spend_coefficient[key][idx] = coefficient

    def set_flexibility_cost(self, idx: int, cost: float) -> None:
        self._flexibility_cost[idx] = cost

    def set_vessel_net_flexibility_units(
        self, vessel_name: str, idx: int, units: float
    ) -> None:
        self._vessel_net_flexibility_units[vessel_name][idx] = units

    def set_remedial_cost(self, idx: int, cost: FloatArray) -> None:
        self._remedial_cost[idx:] = cost

    def set_port_fraction(self, port_name: str, idx: int, fraction: FloatLike) -> None:
        self._port_fraction[port_name][idx:] = fraction

    def set_leg_fraction(
        self, leg: tuple[str, str], idx: int, fraction: FloatArray
    ) -> None:
        self._leg_fraction[leg][idx:] = fraction

    def set_vessel_threshold(
        self, vessel_name: str, idx: int, threshold: FloatLike
    ) -> None:
        self._vessel_threshold[vessel_name][idx:] = threshold

    def set_vessel_capacity(
        self, vessel_name: str, idx: int, capacity: FloatArray
    ) -> None:
        self._vessel_capacity[vessel_name][idx:] = capacity

    def set_vessel_measure(
        self, vessel_name: str, idx: int, measure: FloatLike
    ) -> None:
        self._vessel_measure[vessel_name][idx:] = measure

    def set_vessel_allowance(
        self, vessel_name: str, idx: int | slice, allowance: FloatLike
    ) -> None:
        self._vessel_allowance[vessel_name][idx] = allowance

    def set_vessel_emissions(
        self, vessel_name: str, idx: int, emissions: float
    ) -> None:
        self._vessel_emissions[vessel_name][idx] = emissions

    def set_vessel_energy(self, vessel_name: str, idx: int, energy: float) -> None:
        self._vessel_energy[vessel_name][idx] = energy

    def set_vessel_remedial_units(
        self, vessel_name: str, idx: int, units: float
    ) -> None:
        self._vessel_remedial_units[vessel_name][idx] = units

    def set_pooled_remedial_units(self, idx: int, units: float) -> None:
        self._pooled_remedial_units[idx] = units

    def set_pooled_shadow_price(self, idx: int, price: float) -> None:
        self._pooled_shadow_price[idx] = price

    def set_adjusted_vessel_threshold(
        self, vessel_name: str, idx: int, threshold: float
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
        self, key: tuple[str, str, str], idx: Index
    ) -> FloatLike:
        if key not in self._emission_coefficient:
            return 0.0

        return self._emission_coefficient[key][idx]

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
        self, port_name: str, idx: Index
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

    @overload
    def get_leg_fraction(self, leg: tuple[str, str], idx: int) -> float: ...

    @overload
    def get_leg_fraction(self, leg: tuple[str, str], idx: slice) -> FloatArray: ...

    def get_leg_fraction(self, leg: tuple[str, str], idx: Index) -> FloatLike:
        return self._leg_fraction[leg][idx]

    @overload
    def get_vessel_threshold(self, vessel_name: str, idx: int) -> float: ...

    @overload
    def get_vessel_threshold(self, vessel_name: str, idx: slice) -> FloatArray: ...

    def get_vessel_threshold(self, vessel_name: str, idx: Index) -> FloatLike:
        return self._vessel_threshold[vessel_name][idx]

    def get_vessel_capacity(self, vessel_name: str, idx: slice) -> FloatArray:
        return self._vessel_capacity[vessel_name][idx]

    @overload
    def get_vessel_measure(self, vessel_name: str, idx: int) -> float: ...

    @overload
    def get_vessel_measure(self, vessel_name: str, idx: slice) -> FloatArray: ...

    def get_vessel_measure(self, vessel_name: str, idx: Index) -> FloatLike:
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

    def get_vessel_remedial_units(self, vessel_name: str, idx: int) -> float:
        units: float = self._vessel_remedial_units[vessel_name][idx]
        return units

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
