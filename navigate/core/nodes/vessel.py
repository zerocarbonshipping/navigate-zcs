# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Vessel node, one vessel type with its loads, machinery and route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    SECTION_DEFINE,
    Scalar,
    as_scalar,
    assign_id,
    assign_reference,
    assign_reference_list,
    assign_value,
    deck_attribute,
)
from navigate.core.enum_ import EnergyDemandID, FuelTypeID
from navigate.core.expectations import VesselExpectation
from navigate.core.node import Node
from navigate.core.node_type import (
    CONVERTER,
    CURVE,
    FORECAST,
    ROUTE,
    SURFACE,
    TANK,
    VARIABLE,
    VESSEL,
)
from navigate.core.results import VesselResults
from navigate.util import is_unique

if TYPE_CHECKING:
    from collections.abc import Sequence

    from navigate.core.nodes.converter import Converter
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.fuel import Fuel
    from navigate.core.nodes.route import Route
    from navigate.core.nodes.tank import Tank
    from navigate.core.results import ResultsContext
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        ScalarArgument,
        ScalarInput,
        SurfaceArgument,
        SurfaceInput,
    )


class Vessel(Node):
    """A vessel type: its power demand, machinery, route, capacity and base cost."""

    type = VESSEL

    def __init__(self, name: str) -> None:
        super().__init__(name)

        # external variables -----------------------------------------------------------
        # power demand
        self.propulsion_load: SurfaceInput = Scalar(0.0)
        self.electrical_load_at_sea: SurfaceInput = Scalar(0.0)
        self.electrical_load_in_port: ScalarInput = Scalar(0.0)
        self.heat_load_at_sea: SurfaceInput = Scalar(0.0)
        self.heat_load_in_port: ScalarInput = Scalar(0.0)

        # machinery
        self.fuel_type: FuelTypeID | None = None
        self.propulsion_converter: Converter
        self.electrical_converter: Converter
        self.heat_converter: Converter
        self.tanks: list[Tank]

        # voyage
        self.route: Route
        self.nominal_capacity: ScalarInput

        # base cost
        self.lifetime: ForecastInput = Scalar(25.0)
        self.lead_time: ForecastInput = Scalar(0.0)
        self.capex: ForecastInput = Scalar(0.0)
        self.opex: ForecastInput = Scalar(0.0)
        self.cost_of_capital: ForecastInput = Scalar(0.0)

        # internal variables -----------------------------------------------------------
        self.expectation: VesselExpectation = VesselExpectation()
        self.results: VesselResults = VesselResults()

        # set by fleet initialization
        self.primary_fuel_type: FuelTypeID
        self.fleet_assignment: str

        # node maps
        self.usable_fuels: dict[str, Fuel]
        self.fuels_per_converter: dict[str, dict[str, Fuel]]
        self.converters_per_fuel: dict[str, dict[str, Converter]]

    # external methods (DSL attributes) ------------------------------------------------
    @deck_attribute(SECTION_DEFINE)
    def set_propulsion_load(self, value: SurfaceArgument) -> None:
        """Set the propulsion load of the vessel."""
        self.propulsion_load = assign_value(
            as_scalar(value), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_electrical_load_at_sea(self, value: SurfaceArgument) -> None:
        """Set the electrical load of the vessel at sea."""
        self.electrical_load_at_sea = assign_value(
            as_scalar(value), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_electrical_load_in_port(self, value: ScalarArgument) -> None:
        """Set the electrical load of the vessel in port."""
        self.electrical_load_in_port = assign_value(
            as_scalar(value), type_=VARIABLE, lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_heat_load_at_sea(self, value: SurfaceArgument) -> None:
        """Set the heat load of the vessel at sea."""
        self.heat_load_at_sea = assign_value(
            as_scalar(value), type_=(CURVE, SURFACE, VARIABLE), lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_heat_load_in_port(self, value: ScalarArgument) -> None:
        """Set the heat load of the vessel in port."""
        self.heat_load_in_port = assign_value(
            as_scalar(value), type_=VARIABLE, lower=0.0
        )

    @deck_attribute(SECTION_DEFINE)
    def set_fuel_type(self, value: str) -> None:
        """Set the primary fuel type of the vessel."""
        self.fuel_type = assign_id(value, FuelTypeID)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_propulsion_converter(self, value: Converter) -> None:
        """Set the converter used to satisfy the propulsion demand."""
        self.propulsion_converter = assign_reference(value, CONVERTER)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_electrical_converter(self, value: Converter) -> None:
        """Set the converter used to satisfy the electrical demand."""
        self.electrical_converter = assign_reference(value, CONVERTER)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_heat_converter(self, value: Converter) -> None:
        """Set the converter used to satisfy the heat demand."""
        self.heat_converter = assign_reference(value, CONVERTER)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_tanks(self, value: Tank | list[Tank]) -> None:
        """Set the tanks used for onboard fuel storage."""
        self.tanks = assign_reference_list(value, TANK, min_length=1, unique=True)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_route(self, value: Route) -> None:
        """Set the route the vessel sails on."""
        self.route = assign_reference(value, ROUTE)

    @deck_attribute(SECTION_DEFINE, required=True)
    def set_nominal_capacity(self, value: ScalarArgument) -> None:
        """Set the nominal cargo carrying capacity of the vessel."""
        self.nominal_capacity = assign_value(
            as_scalar(value), type_=VARIABLE, lower=0.0, inclusive_lower=False
        )

    @deck_attribute()
    def set_lifetime(self, value: ForecastArgument) -> None:
        """Set the lifetime of the vessel."""
        self.lifetime = assign_value(
            as_scalar(value),
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            inclusive_lower=False,
        )

    @deck_attribute()
    def set_lead_time(self, value: ForecastArgument) -> None:
        """Set the lead time of the vessel."""
        self.lead_time = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_capex(self, value: ForecastArgument) -> None:
        """Set the base CAPEX of building the vessel."""
        self.capex = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_opex(self, value: ForecastArgument) -> None:
        """Set the base OPEX of maintaining the vessel."""
        self.opex = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    @deck_attribute()
    def set_cost_of_capital(self, value: ForecastArgument) -> None:
        """Set the cost of capital of the vessel."""
        self.cost_of_capital = assign_value(
            as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0
        )

    # internal methods -----------------------------------------------------------------
    def check_consistency(self) -> None:
        # downstream code sums over the converters (installed power, cost, fuel demand);
        # a shared one would double-count
        names = [converter.name for converter in self.get_converters()]
        if not is_unique(names):
            raise ValueError(
                f"{self}: 'PropulsionConverter', 'ElectricalConverter' and"
                f" 'HeatConverter' must be three distinct converters, got {names}."
            )

    def initialize_expectation(
        self, length: int, fuels: dict[str, Fuel], emissions: dict[str, Emission]
    ) -> None:
        self.expectation.initialize(
            length,
            self.route,
            fuels,
            self.usable_fuels,
            self.fuels_per_converter,
            emissions,
        )

    def initialize_results(
        self,
        context: ResultsContext,
        regulation_names: Sequence[str],
        levy_names: Sequence[str],
    ) -> None:
        self.results.initialize(context, regulation_names, levy_names)

    def get_converters(self) -> tuple[Converter, Converter, Converter]:
        return self.propulsion_converter, self.electrical_converter, self.heat_converter

    def get_converter(self, demand_type: EnergyDemandID) -> Converter:
        match demand_type:
            case EnergyDemandID.PROPULSION:
                return self.propulsion_converter

            case EnergyDemandID.ELECTRICAL:
                return self.electrical_converter

            case EnergyDemandID.HEAT:
                return self.heat_converter
