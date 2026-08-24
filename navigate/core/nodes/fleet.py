# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

import logging

import numpy as np
from numpy.typing import NDArray

from navigate.core import (
    NodeReference,
    Scalar,
    as_list,
    as_scalar,
    as_scalar_list,
    assign_fraction_list,
    assign_id,
    assign_list,
    assign_value,
    command_assignment_to_boolean_dict,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.enum_ import (
    EnergyDemandTypeID,
    EnergyDemandTypePortID,
    ExtrapolateID,
    SpeedAlignmentID,
)
from navigate.core.expectations import FleetExpectation
from navigate.core.id_ import CURVE, FLEET, FORECAST, TECHNOLOGY, VARIABLE, VESSEL
from navigate.core.increment import Increment
from navigate.core.misc import BOOL_ID
from navigate.core.nodes._asset_manager import _AssetManager
from navigate.core.nodes.curve import Curve
from navigate.core.nodes.emission import Emission
from navigate.core.nodes.forecast import Forecast
from navigate.core.nodes.fuel import Fuel
from navigate.core.nodes.technology import Technology
from navigate.core.nodes.variable import Variable
from navigate.core.nodes.vessel import Vessel
from navigate.core.profiles import FleetProfile
from navigate.exceptions import no_value_assigned_error
from navigate.fleet.evolution import calculate_evolution_expectation
from navigate.fleet.package import Package, preprocess_packages
from navigate.fleet.technology import (
    build_technology_packages,
    define_initial_technology,
    transfer_technology_charter_rate,
    transfer_technology_uptake,
    update_residual_energy_demand,
)
from navigate.fleet.utils import (
    calculate_projected_multipliers,
    define_initial_split,
    define_initial_trade,
    extract_cargo_miles,
)
from navigate.util import is_non_strictly_increasing

logger = logging.getLogger(__name__)

# Type helpers
type ScalarLike = Scalar | Forecast | Variable | None
type InputScalarLike = Scalar | Forecast | Variable


class Fleet(_AssetManager):

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._type = FLEET

        self.trade_growth: ScalarLike = None                        # Trade-growth of the fleet
        self.fixed_scrap_rate: ScalarLike = None                    # Fixed scrap rate to replace age based
        self.allow_secondary_scrapping: bool = True                 # Whether to allow secondary scrapping
        self.intra_fuel_sensitivity: ScalarLike = None              # Odds ratio for within-fuel tech choice (LCOT)
        self.inter_fuel_sensitivity: ScalarLike = None              # Odds ratio for fuel-type choice (LCOT)
        self.fuel_conversion_sensitivity: ScalarLike = None         # Odds ratio for fuel conversion (NPV)
        self.memory: ScalarLike = None                              # Weight of historic uptake distributions used
        self.initial_vessels: Scalar | Variable | None = None       # Initial number of vessels
        self.allow_speed_management: bool = False                   # Whether to perform speed management
        self.maximum_speed_change: ScalarLike = None                # Maximum change in speed per year, knots/year
        self.speed_alignment: SpeedAlignmentID = SpeedAlignmentID.INDIVIDUAL  # How to align speed across vessels
        self.assume_reference_speed_optimal: bool = False           # Whether to anchor speed changes to reference
        self.retrofit_frequency: ScalarLike = None                  # Frequency at which retrofit can be done
        self.technology_sensitivity: ScalarLike = None              # Odds ratio for technology packages (NPV)
        self.technology_cost_of_capital: ScalarLike = None          # Cost of capital for technology
        self.technology_horizon: ScalarLike = None                  # Belief horizon for tech decisions, years
        self.speed_horizon: ScalarLike = None                       # Belief horizon for speed management, years
        self.fuel_conversion_minimum_age: Scalar | None = None      # Minimum age of fuel conversions
        self.allow_technology_approximation: bool = True            # Whether to allow technology approximation
        self.projected_multipliers: NDArray[np.float64] | None = None       # Naive projection of future multipliers
        self.fuel_conversion_expenses: NDArray[np.float64] | None = None    # Rolling costs of previous fuel conversions
        self.initial_split: list[float] = []                        # Fraction of vessel type at start
        self.initial_technology_share: dict[tuple[str, str], Curve | None] = {}  # (vessel, tech) -> Curve
        self.orderbooks: list[Forecast] = []                        # Cumulative vessels by date
        self.technologies: list[Technology] = []                    # Energy efficiency technologies
        self.operational_saving_sea: dict[EnergyDemandTypeID, InputScalarLike] = {d: Scalar(0) for d in EnergyDemandTypeID}
        self.operational_saving_port: dict[EnergyDemandTypeID, InputScalarLike] = {d: Scalar(0) for d in EnergyDemandTypePortID}
        self.fuel_conversion_cost: dict[tuple[str, str], float | Forecast] = {}     # Fuel conversion costs
        self.fuel_conversion_limit: dict[tuple[str, str], InputScalarLike] = {}     # Per-pair conversion cap
        self.newbuild_limit: dict[str, InputScalarLike] = {}        # Per-vessel newbuild share cap
        self.newbuild_technology_limit: dict[str, InputScalarLike] = {}             # Per-tech newbuild install cap
        self.retrofit_technology_limit: dict[str, InputScalarLike] = {}             # Per-tech retrofit cap
        self.allow_vessel: dict[str, bool] = {}                     # Whether a vessel is allowed
        self.newbuild_available: dict[str, bool] = {}               # Whether newbuild is available
        self.conversion_available: dict[str, bool] = {}             # Whether conversion is available
        self.trade: NDArray[np.float64] = np.ndarray(0)             # Trade by the fleet, cargo-miles
        self.newbuild_package_uptake: list[NDArray[np.float64]] = []                # EE uptake on newbuilds
        self.orders_delivered: NDArray[np.float64] = np.empty(0)    # Orders delivered per vessel type
        self.orders_postponed: NDArray[np.float64] = np.empty(0)    # Orders postponed per vessel type
        self.technology_packages: list[Package] = []                # Packages based on technology input
        self.package_to_technology_map: dict[int, int] = {}         # Package index -> technology index

    # parser compatibility — attribute_to_setter("Vessels") resolves to "_vessels"
    vessels = property(lambda self: self.assets, lambda self, v: setattr(self, 'assets', v))

    # external attributes set through the input deck -------------------------------------------------------------------

    def set_vessels(self, vessels: list[NodeReference]):
        """
        Set the list of vessel types that exists for the fleet.

        The list of vessel types can be though of as a discretization of the fuel types and technologies of the fleet.

        Examples
        --------
        - Vessel("name")
        - [Vessel("name1"), Vessel("name2")]

        Parameters
        ----------
        vessels
            The list of vessel types that exists for the fleet.
        """

        self.assets = assign_list(as_list(vessels), unique=True, scalar=False, type_=VESSEL)

    def set_memory(self, memory: float | NodeReference):
        """
        Set the exponential decay of the memory of the fleet used in the expected uptake decision of newbuild vessels.

        A high memory means that the expected uptake of newbuild vessels is more stable.

        Examples
        --------
        - 0.66
        - Forecast("name")

        Parameters
        ----------
        memory
            The newbuild vessel distribution memory.
        """

        self.memory = assign_value(as_scalar(memory), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_fixed_scrap_rate(self, fixed_scrap_rate: float | NodeReference):
        """
        Set the fixed scrap rate of the fleet in fraction/year.

        If the fixed scrap rate is set it overwrites the age-based scrapping functionality resulting in vessels
        potentially being scrapped prior to their technical lifetime.

        Examples
        --------
        - 0.1
        - Forecast("name")

        Parameters
        ----------
        fixed_scrap_rate
            The fixed scrap rate of the fleet in fraction/year.
        """

        self.fixed_scrap_rate = assign_value(as_scalar(fixed_scrap_rate), type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_allow_secondary_scrapping(self, allow_secondary_scrapping: str):
        """
        Set the flag for whether secondary scrapping is allowed.

        Secondary scrapping occurs if a drop in trade is not offset by the amount of scrapped vessels.
        If secondary scrapping is not allowed the actual capacity of the fleet may be higher than the projected trade.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        allow_secondary_scrapping
            Whether secondary scrapping is allowed or not.
        """

        self.allow_secondary_scrapping = assign_id(allow_secondary_scrapping, BOOL_ID)

    def set_trade_growth(self, trade_growth: float | NodeReference):
        """
        Set trade-growth of the fleet, fraction/year.

        Examples
        --------
        - 0.05
        - Forecast("name")

        Parameters
        ----------
        trade_growth
            The trade-growth of the fleet in fraction/year.
        """

        self.trade_growth = assign_value(as_scalar(trade_growth), type_=(FORECAST, VARIABLE))

    def set_initial_vessels(self, initial_vessels: float):
        """
        Set the initial amount of vessels in the fleet.

        A minimum of one vessel is necessary to compound the trade-growth.

        Examples
        --------
        - 150

        Parameters
        ----------
        initial_vessels
            Initial number of vessels in the fleet.
        """

        self.initial_vessels = assign_value(as_scalar(initial_vessels), type_=VARIABLE,
                                            lower=0, inclusive_lower=False)

    def set_initial_split(self, initial_split: list[float]):
        """
        Set the initial distribution of vessel types in the fleet.

        The list must have the same length as the list of vessels.
        The list must sum to unity. If not, the list is normalized by equal fractions.

        Examples
        --------
        - [0.3, 0.7]

        Parameters
        ----------
        initial_split
            Initial distribution of vessel types.
        """

        self.initial_split, normalized = assign_fraction_list(initial_split)

        if normalized:
            logger.info("{}: 'InitialSplit' is normalized to 1 by equal fractions.".format(self))

    def set_technologies(self, technologies: list[NodeReference]):
        """
        Set the list of energy efficiency technologies that can be installed on vessels.

        The list can contain any technologies that improve vessel performance through reduced energy consumption,
        alternative power sources, or emissions reductions.

        Examples
        --------
        - Technology("name")
        - [Technology("name1"), Technology("name2")]

        Parameters
        ----------
        technologies
            The list of technologies that can be installed on vessels.
        """

        self.technologies = assign_list(as_list(technologies), unique=True, scalar=False, type_=TECHNOLOGY)

    def set_initial_technology_share(self, vessel_name: str, technology_name: str, uptake_curve):
        """
        Set the initial technology uptake as a function of vessel age.

        The Curve x-axis is vessel age, y-axis is uptake fraction [0, 1].
        Supports wildcards for vessel_name and technology_name.

        Examples
        --------
        - "*oil*", "hull_painting*", Curve("uptake_hull_painting")
        - "vessel_name", "technology_name", Curve("uptake_curve")

        Parameters
        ----------
        vessel_name
            Name of vessel type (supports wildcards).
        technology_name
            Name of technology (supports wildcards).
        uptake_curve
            Curve with age on x-axis and uptake fraction on y-axis.
        """

        command_assignment_to_tuple_dict(
            (vessel_name, technology_name), uptake_curve,
            self.initial_technology_share, scalar=False, type_=CURVE, lower=0., upper=1.
        )

    def set_intra_fuel_sensitivity(self, intra_fuel_sensitivity: float | NodeReference):
        """
        Set the sensitivity of the within-fuel technology choice to levelized cost of transport (LCOT).

        The value is an odds ratio: a technology variant whose LCOT is 10% higher receives this many
        times the odds of an otherwise identical variant. For example 0.5 means a 10% higher LCOT
        halves the odds, and 1 means no preference. LCOT is lower-is-better, so use a value below 1.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        intra_fuel_sensitivity
            Odds ratio for a 10% higher LCOT in the within-fuel-type choice.
        """

        self.intra_fuel_sensitivity = assign_value(
            as_scalar(intra_fuel_sensitivity), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_inter_fuel_sensitivity(self, inter_fuel_sensitivity: float | NodeReference):
        """
        Set the sensitivity of the fuel-type choice to levelized cost of transport (LCOT).

        The value is an odds ratio: a fuel whose LCOT is 10% higher receives this many times the odds
        of an otherwise identical fuel. For example 0.5 means a 10% higher LCOT halves the odds, and
        1 means no preference. LCOT is lower-is-better, so use a value below 1.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        inter_fuel_sensitivity
            Odds ratio for a 10% higher LCOT in the between-fuel-type choice.
        """

        self.inter_fuel_sensitivity = assign_value(
            as_scalar(inter_fuel_sensitivity), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_technology_sensitivity(self, technology_sensitivity: float | NodeReference):
        """
        Set the sensitivity of the energy-saving technology package choice to its NPV.

        The value is an odds ratio: a package whose NPV advantage equals 5% of the ship CAPEX receives
        this many times the odds of an otherwise identical package. For example 2 means such an
        advantage doubles the odds, and 1 means no preference. NPV is higher-is-better, so use a value
        above 1.

        Examples
        --------
        - 2
        - Forecast("name")

        Parameters
        ----------
        technology_sensitivity
            Odds ratio for an NPV advantage equal to 5% of ship CAPEX.
        """

        self.technology_sensitivity = assign_value(
            as_scalar(technology_sensitivity), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_technology_cost_of_capital(self, cost_of_capital: float | NodeReference):
        """
        Set the cost of capital used for evaluating technology investments.

        The cost of capital represents the discount rate used to evaluate the net present value of technology
        investments and retrofits. It reflects the opportunity cost of capital and the risk associated with
        technology adoption.

        Examples
        --------
        - 0.08
        - Forecast("name")

        Parameters
        ----------
        cost_of_capital
            The cost of capital for technology investments as a fraction (e.g., 0.08 for 8%).
        """

        self.technology_cost_of_capital = assign_value(as_scalar(cost_of_capital), type_=(FORECAST, VARIABLE), lower=0.)

    def set_technology_horizon(self, technology_horizon: float | NodeReference):
        """
        Set the decision horizon, in years, used to smooth the energy-scarcity belief that feeds technology
        investment decisions.

        A longer horizon makes the belief respond more slowly to LP-dual updates, matching the longer
        amortization timescale of technology decisions.

        Examples
        --------
        - 3.0
        - Forecast("name")

        Parameters
        ----------
        technology_horizon
            Decision horizon for technology beliefs, in years.
        """

        self.technology_horizon = assign_value(as_scalar(technology_horizon), type_=(FORECAST, VARIABLE), lower=0.)

    def set_speed_horizon(self, speed_horizon: float | NodeReference):
        """
        Set the decision horizon, in years, used to smooth the energy-scarcity belief that feeds speed management.

        A shorter horizon makes the belief more reactive, suited to an operational decision that should
        respond quickly to real tightness.

        Examples
        --------
        - 1.0
        - Forecast("name")

        Parameters
        ----------
        speed_horizon
            Decision horizon for speed beliefs, in years.
        """

        self.speed_horizon = assign_value(as_scalar(speed_horizon), type_=(FORECAST, VARIABLE), lower=0.)

    def set_retrofit_frequency(self, retrofit_frequency: float | NodeReference):
        """
        Set the retrofit frequency, namely the intervals at which a vessel can retrofit technology or perform a
        fuel conversion.

        Examples
        --------
        - 5
        - Forecast("name")

        Parameters
        ----------
        retrofit_frequency
            The retrofit frequency.
        """

        self.retrofit_frequency = assign_value(as_scalar(retrofit_frequency), type_=(FORECAST, VARIABLE), lower=0.)

    def set_orderbooks(self, orderbooks: list[float | NodeReference]):
        """
        Set the list of orderbooks used for determining the newbuild uptake from orderbooks.

        The list must have the same length as the list of vessels.
        If the orderbook is a forecast it must be non-strictly increasing.

        Examples
        --------
        - [Forecast("name"), 0]

        Parameters
        ----------
        orderbooks
            List of orderbooks.
        """

        self.orderbooks = assign_list(as_scalar_list(orderbooks), type_=(FORECAST, VARIABLE), lower=0.)

    def set_allow_speed_management(self, allow_speed_management: str):
        """
        Set the flag for whether speed management is allowed.

        Speed management dynamically optimizes the speed profile of each vessel type based on a cost optimal approach
        between adding newbuilds to the model versus the change in fuel expenses.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        allow_speed_management
            Whether speed management is allowed or not.
        """

        self.allow_speed_management = assign_id(allow_speed_management, BOOL_ID)

    def set_maximum_speed_change(self, maximum_speed_change):
        """
        Set the maximum speed change permissible per year during dynamic speed management.

        Examples
        --------
        - 0.5
        - Forecast("name")

        Parameters
        ----------
        maximum_speed_change
            The maximum speed change permissible.
        """

        self.maximum_speed_change = assign_value(as_scalar(maximum_speed_change), type_=(FORECAST, VARIABLE), lower=0.)

    def set_speed_alignment(self, speed_alignment: str):
        """
        Set the method used to align speed across vessel types within the fleet.

        Speed alignment determines how the individually optimized speeds are reconciled across vessel types.
        By default, each vessel type retains its own optimal speed (INDIVIDUAL).

        Examples
        --------
        - INDIVIDUAL
        - MINIMUM
        - MAXIMUM
        - AVERAGE

        Parameters
        ----------
        speed_alignment
            The speed alignment method.
        """

        self.speed_alignment = assign_id(speed_alignment, SpeedAlignmentID)

    def set_assume_reference_speed_optimal(self, assume_reference_speed_optimal: str):
        """
        Set the flag for whether the reference speed is assumed to be the current market optimum.

        When enabled, the route reference speed is treated as the market optimum (accounting for effects not modelled)
        and speed changes only occur relative to shifts in the modelled optimal speed. This prevents the model from
        adjusting speed away from the reference due to unmodelled market effects.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        assume_reference_speed_optimal
            Whether to assume the reference speed is the current market optimum.
        """

        self.assume_reference_speed_optimal = assign_id(assume_reference_speed_optimal, BOOL_ID)

    def set_fuel_conversion_sensitivity(self, fuel_conversion_sensitivity: float | NodeReference):
        """
        Set the sensitivity of the fuel-conversion choice to its NPV.

        The value is an odds ratio: a conversion whose NPV advantage equals 5% of the ship CAPEX
        receives this many times the odds of an otherwise identical conversion (the do-nothing option
        has an NPV of zero). For example 2 means such an advantage doubles the odds, and 1 means no
        preference. NPV is higher-is-better, so use a value above 1.

        Examples
        --------
        - 2
        - Forecast("name")

        Parameters
        ----------
        fuel_conversion_sensitivity
            Odds ratio for an NPV advantage equal to 5% of ship CAPEX.
        """

        self.fuel_conversion_sensitivity = assign_value(
            as_scalar(fuel_conversion_sensitivity), type_=(FORECAST, VARIABLE), lower=0., inclusive_lower=False)

    def set_fuel_conversion_minimum_age(self, fuel_conversion_minimum_age: float | NodeReference):
        """
        Set the minimum age at which a vessel can perform a fuel conversion, in years.

        Examples
        --------
        - 5
        - Forecast("name")

        Parameters
        ----------
        fuel_conversion_minimum_age
            Minimum age a which a vessel can perform a fuel conversion.
        """

        self.fuel_conversion_minimum_age = assign_value(as_scalar(fuel_conversion_minimum_age),
                                                        type_=(FORECAST, VARIABLE), lower=0.)

    def set_newbuild_limit(self, vessel_name: str, limit: float | NodeReference):
        """
        Set the maximum share of a single timestep's newbuild cargo-miles delivered by the given vessel type.

        The limit is enforced across the orderbook, inertia, and modelled-uptake newbuild sources, so the
        cumulative share across the three sources cannot exceed the configured value.

        Examples
        --------
        - "vessel_oil", 0.4
        - "*ammonia*", Forecast("name")

        Parameters
        ----------
        vessel_name
            Name of the vessel (wildcards supported).
        limit
            Maximum share in [0, 1].
        """

        command_assignment_to_dict(vessel_name, limit, self.newbuild_limit, type_=(FORECAST, VARIABLE),
                                   lower=0., upper=1.)

    def set_newbuild_technology_limit(self, technology_name: str, limit: float | NodeReference):
        """
        Set the maximum fraction of the existing fleet that can install the technology on newbuilds in one year.

        Cap is enforced as ``installs_A_per_year <= limit * y``, where ``y`` is the pre-newbuild total
        multipliers of the fleet. Independent from the retrofit cap.

        Examples
        --------
        - "scrubber", 0.05
        - "ammonia_kit", Forecast("name")

        Parameters
        ----------
        technology_name
            Name of the technology (wildcards supported).
        limit
            Maximum yearly install share in [0, 1].
        """

        command_assignment_to_dict(technology_name, limit, self.newbuild_technology_limit,
                                   type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_retrofit_technology_limit(self, technology_name: str, limit: float | NodeReference):
        """
        Set the maximum fraction of the existing fleet that can retrofit to the technology in one year.

        Cap is enforced as ``retrofits_A_per_year <= limit * y``, where ``y`` is the pre-newbuild total
        multipliers of the fleet. Independent from the newbuild cap.

        Examples
        --------
        - "scrubber", 0.03
        - "ammonia_kit", Forecast("name")

        Parameters
        ----------
        technology_name
            Name of the technology (wildcards supported).
        limit
            Maximum yearly retrofit share in [0, 1].
        """

        command_assignment_to_dict(technology_name, limit, self.retrofit_technology_limit,
                                   type_=(FORECAST, VARIABLE), lower=0., upper=1.)

    def set_allow_technology_approximation(self, allow_technology_approximation: str):
        """
        Set the flag for whether the fleet should approximate technology uptake based on an average impact on technology
        uptake on other fleets which model it bottom-up.

        If there is no fleet which models the technology bottom-up, then the technology uptake is set to zero.

        Examples
        --------
        - TRUE
        - FALSE

        Parameters
        ----------
        allow_technology_approximation
            Whether to allow technology approximation.
        """

        self.allow_technology_approximation = assign_id(allow_technology_approximation, BOOL_ID)

    def set_operational_saving_sea(self, energy_type: str, saving):
        """
        Set the fraction of energy saved at sea through operational measures (e.g., JIT arrival, weather routing).

        These represent zero-cost energy reductions that are not modeled through technology business cases.

        Examples
        --------
        - PROPULSION, 0.1
        - ELECTRICAL, Forecast("name")

        Parameters
        ----------
        energy_type
            Energy demand type (PROPULSION, ELECTRICAL, HEAT).
        saving
            Fraction of energy saved.
        """

        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(id_, saving, self.operational_saving_sea, type_=(FORECAST, VARIABLE),
                                   lower=0., upper=1.)

    def set_operational_saving_port(self, energy_type: str, saving):
        """
        Set the fraction of energy saved in port through operational measures.

        These represent zero-cost energy reductions that are not modeled through technology business cases.

        Examples
        --------
        - ELECTRICAL, 0.1
        - HEAT, Forecast("name")

        Parameters
        ----------
        energy_type
            Energy demand type (ELECTRICAL, HEAT).
        saving
            Fraction of energy saved.
        """

        id_ = assign_id(energy_type, EnergyDemandTypeID)
        command_assignment_to_dict(id_, saving, self.operational_saving_port, type_=(FORECAST, VARIABLE),
                                   lower=0., upper=1.)

    def get_operational_saving_sea(self, energy_type: EnergyDemandTypeID) -> float:
        return self.operational_saving_sea[energy_type].get()

    def get_operational_saving_port(self, energy_type: EnergyDemandTypeID) -> float:
        return self.operational_saving_port[energy_type].get()

    def transfer_operational_saving_to_vessels(self) -> None:
        saving_sea = {d: self.get_operational_saving_sea(d) for d in EnergyDemandTypeID}
        saving_port = {d: self.get_operational_saving_port(d) for d in EnergyDemandTypePortID}
        for vessel in self.assets:
            vessel.expectation.set_operational_saving_fraction_sea(saving_sea)
            vessel.expectation.set_operational_saving_fraction_port(saving_port)

    # external commands called in the input deck -----------------------------------------------------------------------
    def set_fuel_conversion_cost(self, vessel_name_from: str, vessel_name_to: str, fuel_conversion_cost: float):
        """
        Set the cost of performing a fuel conversion of a vessel from one type to another, in USD.

        Examples
        --------
        - "vessel_name_from", "vessel_name_to", 10e6
        - "vessel_name_from", "vessel_name_to", Forecast("name")

        Parameters
        ----------
        vessel_name_from
            Name of vessel type being converted from.
        vessel_name_to
            Name of vessel type being converted to.
        fuel_conversion_cost
            Cost of performing a fuel conversion from vessel type 'vessel_name_from' to 'vessel_name_to'.
        """

        command_assignment_to_tuple_dict((vessel_name_from, vessel_name_to), fuel_conversion_cost,
                                         self.fuel_conversion_cost, type_=(FORECAST, VARIABLE), lower=0.)

    def set_fuel_conversion_limit(self, vessel_name_from: str, vessel_name_to: str,
                                  fuel_conversion_limit: float | NodeReference):
        """
        Set the per-pair cap on fuel conversions, as a fraction of the total fleet allowed to convert
        from `vessel_name_from` to `vessel_name_to` per year.

        With 100 vessels and `set_fuel_conversion_limit("x", "y", 0.05)`, at most 5 vessels per year convert
        from x to y. Default is 1.0 (effectively unlimited).

        Examples
        --------
        - "vessel_name_from", "vessel_name_to", 0.05
        - "vessel_name_from", "vessel_name_to", Forecast("name")

        Parameters
        ----------
        vessel_name_from
            Name of vessel type being converted from.
        vessel_name_to
            Name of vessel type being converted to.
        fuel_conversion_limit
            Fraction in [0, 1] of the total fleet allowed to convert on this (from, to) pair per year.
        """

        command_assignment_to_tuple_dict((vessel_name_from, vessel_name_to), fuel_conversion_limit,
                                         self.fuel_conversion_limit, type_=(FORECAST, VARIABLE),
                                         lower=0., upper=1.)

    def set_allow_vessel(self, vessel_name: str, allow_vessel: str):
        """
        Set a boolean flag for a given vessel from the list of vessels whether it is allowed or not.

        If allow vessel is set to FALSE the vessel can neither enter the fleet as a newbuild nor be fuel converted to.
        Any existing vessels in the fleet however are unaffected.
        This flag supersedes both 'set_newbuild_available' and 'set_conversion_available'.

        Examples
        --------
        - "vessel_name", TRUE
        - "vessel_name", FALSE

        Parameters
        ----------
        vessel_name
            Name of vessel in the list of vessels.
        allow_vessel
            Whether the vessel is allowed or not.
        """

        command_assignment_to_boolean_dict(vessel_name, allow_vessel, self.allow_vessel, allow_empty=True)

    def set_newbuild_available(self, vessel_name: str, newbuild_available: str):
        """
        Set a boolean flag for a given vessel from the list of vessels whether it is allowed as a newbuild.

        If allow vessel is set to FALSE the vessel cannot enter the fleet as a newbuild.

        Examples
        --------
        - "vessel_name", TRUE
        - "vessel_name", FALSE

        Parameters
        ----------
        vessel_name
            Name of vessel in the list of vessels.
        newbuild_available
            Whether the vessel is allowed or not.
        """

        command_assignment_to_boolean_dict(vessel_name, newbuild_available, self.newbuild_available, allow_empty=True)

    def set_conversion_available(self, vessel_name: str, conversion_available: str):
        """
        Set a boolean flag for a given vessel from the list of vessels whether it is allowed to be converted to.

        If allow vessel is set to FALSE it is not possible to perform fuel conversions to vessels of that type.

        Examples
        --------
        - "vessel_name", TRUE
        - "vessel_name", FALSE

        Parameters
        ----------
        vessel_name
            Name of vessel in the list of vessels.
        conversion_available
            Whether the vessel is allowed or not.
        """

        command_assignment_to_boolean_dict(vessel_name, conversion_available, self.conversion_available, allow_empty=True)

    # internal methods -------------------------------------------------------------------------------------------------
    def initialize(self):

        if not self.assets:
            no_value_assigned_error(self, 'Vessels')

        if not self.initial_vessels:
            no_value_assigned_error(self, 'InitialVessels')

        if self.inter_fuel_sensitivity is None:
            no_value_assigned_error(self, 'InterFuelSensitivity')

        if self.intra_fuel_sensitivity is None:
            no_value_assigned_error(self, 'IntraFuelSensitivity')

        if self.technologies:
            if self.technology_sensitivity is None:
                no_value_assigned_error(self, 'TechnologySensitivity')

        if self.fuel_conversion_sensitivity is None:
            self.fuel_conversion_sensitivity = Scalar(2)

        if self.trade_growth is None:
            self.trade_growth = Scalar(0)

        if self.retrofit_frequency is None:
            self.retrofit_frequency = Scalar(5)

        if self.inertia is None:
            self.inertia = Scalar(0)

        if self.memory is None:
            self.memory = Scalar(0.5)

        if self.technology_horizon is None:
            self.technology_horizon = Scalar(3)

        if self.speed_horizon is None:
            self.speed_horizon = Scalar(1)

        if self.fuel_conversion_minimum_age is None:
            self.fuel_conversion_minimum_age = Scalar(0)

        for (name_from, name_to), cost in self.fuel_conversion_cost.items():
            if cost is None:
                continue
            self.fuel_conversion_limit.setdefault((name_from, name_to), Scalar(1.))

        if self.initial_split and (len(self.assets) != len(self.initial_split)):
            raise ValueError("{}: The length of Vessel ({}) and InitialSplit ({}) must correspond."
                             .format(self, len(self.assets), len(self.initial_split)))

        if self._initial_age_distribution and (len(self.assets) != len(self._initial_age_distribution)):
            raise ValueError("{}: The length of Vessel ({}) and InitialAgeDistribution ({}) must correspond."
                             .format(self, len(self.assets), len(self._initial_age_distribution)))

        # check that orderbooks satisfy various requirements
        if self.orderbooks:
            # check length between orderbooks and vessels correspond
            if len(self.assets) != len(self.orderbooks):
                raise ValueError("{}: The length of Vessel ({}) and Orderbooks ({}) must correspond."
                                 .format(self, len(self.assets), len(self.orderbooks)))

            for orderbook in self.orderbooks:

                if isinstance(orderbook, Forecast):

                    # check that orderbooks are cumulative
                    if not is_non_strictly_increasing(orderbook.get_y()):
                        raise ValueError("{}: Orderbook ({}) is not non-strictly increasing.".format(self, orderbook))

                    # print a warning if the forecast allows extrapolation
                    if orderbook.get_extrapolate() == ExtrapolateID.LINEAR:
                        logger.warning("{}: Orderbook ({}) allows extrapolation and"
                                       " may therefore continue past the last date.".format(self, orderbook))

        if self.allow_speed_management:

            if self.maximum_speed_change is None:
                self.maximum_speed_change = Scalar(np.inf)

    def initialize_dependencies(self):
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.
        """

        for vessel in self.assets:
            name = vessel.get_name()
            self.fuel_conversion_cost.setdefault((name, name), None)
            # placeholder self-pair so command_assignment_to_tuple_dict can validate cross-pair keys;
            # real (from, to) defaults are filled post-commands in `initialize`
            self.fuel_conversion_limit.setdefault((name, name), Scalar(1.))
            self.allow_vessel.setdefault(name, True)
            self.newbuild_available.setdefault(name, True)
            self.conversion_available.setdefault(name, True)
            self.newbuild_limit.setdefault(name, Scalar(1.))

            for tech in self.technologies:
                self.initial_technology_share.setdefault((name, tech.get_name()), None)

        for tech in self.technologies:
            self.newbuild_technology_limit.setdefault(tech.get_name(), Scalar(1.))
            self.retrofit_technology_limit.setdefault(tech.get_name(), Scalar(1.))

    def initialize_expectation(self, length: int, fuels: dict[str, Fuel]) -> None:

        vessel_names = [vessel.get_name() for vessel in self.assets]

        self.expectation = FleetExpectation()
        self.expectation.initialize(length, vessel_names, fuels)

    def initialize_profile(self, timeline: np.ndarray,
                           fuels: dict[str, Fuel],
                           emissions: dict[str, Emission],
                           emissions_lifetime: float,
                           regulation_names: list[str] = (),
                           levy_names: list[str] = ()) -> None:

        vessel_names = [vessel.get_name() for vessel in self.assets]
        technology_names = [technology.get_name() for technology in self.technologies]

        self.profile = FleetProfile()
        self.profile.initialize(timeline, vessel_names, technology_names, fuels, emissions, emissions_lifetime,
                                regulation_names, levy_names)

    def initialize_existing_fleet(self, timeline: np.ndarray):
        """
        Initialize the existing fleet. This means discretizing the existing fleet in time, by splitting the initial
        number of vessels into individual increments with varying age.

        Parameters
        ----------
        timeline
            Simulation time-line.
        """

        for vessel in self.assets:
            vessel.set_fleet_assignment(self.name)

        idx = 0
        nv = len(self.assets)

        # build the technology packages and their cost flows; the cost flows
        # must exist before the initial technology uptake is seeded, since the
        # seeding levelizes them into the carried technology charter rate
        self._build_technology_packages()
        preprocess_packages(self.technology_packages, self.assets, timeline[idx])

        # existing fleet
        define_initial_split(self)
        self._define_initial_age()
        self._define_initial_multipliers()
        self._define_initial_technology()
        define_initial_trade(self, timeline)

        # order book
        self.orders_delivered = np.zeros((nv,))
        self.orders_postponed = np.zeros((nv,))

        # initialize baseline for partial age-based scrapping
        for incs in self.increments:
            if incs:
                incs[0].baseline = incs[0].multiplier

        # calculate a naive projection of multipliers
        # which is used to calculate fair-share emissions
        # for fleet level and global regulations
        multipliers = sum(self.get_multiplier(v) for v in range(nv))
        self.projected_multipliers = calculate_projected_multipliers(multipliers, self.trade)

        # calculate the initial effect from technology
        update_residual_energy_demand(self, idx)

        # calculate the initial fleet evolution expectation
        self.expectation.set_uptakes(idx, self.current_uptake)
        calculate_evolution_expectation(self, idx, timeline)

        # initialize technology effect
        self._transfer_multipliers_to_profile(idx)
        transfer_technology_uptake(self, idx)
        transfer_technology_charter_rate(self, idx)

        # set dynamic properties
        self.fuel_conversion_expenses = np.zeros_like(timeline)

    # -- _AssetManager abstract interface -----------------------------------------------------------

    def _get_initial_multiplier(self, index: int) -> float:
        return self.initial_split[index] * self.initial_vessels.get()

    def _adjust_lifetime_for_age(self, lifetime: float) -> float:
        if self.fixed_scrap_rate is not None:
            scrap_rate = self.fixed_scrap_rate.get()
            if scrap_rate > 0.:
                lifetime = min(lifetime, 1. / scrap_rate)
        return lifetime

    def _build_technology_packages(self):
        self.technology_packages, self.package_to_technology_map = build_technology_packages(self.technologies)

    def _define_initial_technology(self):
        define_initial_technology(self)

    def _transfer_multipliers_to_profile(self, idx: int) -> None:
        """
        Transfer the current multiplier state to the profile for output.

        Parameters
        ----------
        idx
            Current time-step index.
        """

        for v, vessel in enumerate(self.assets):
            self.profile.set_existing_vessels(idx, vessel.get_name(), self.get_multiplier(v))

    def get_cargo_miles(self, idx: int) -> float:
        multipliers = [self.get_multiplier(v) for v in range(len(self.assets))]
        cargo_miles = extract_cargo_miles(self.assets, idx)

        return np.dot(multipliers, cargo_miles)

    def get_multiplier_increments(self) -> list[list[Increment]]:
        return self.increments

    def get_vessels(self) -> list[Vessel]:
        return self.assets

    def can_retrofit(self) -> bool:
        return bool(self.technologies)

    def can_fuel_convert(self) -> bool:
        return (any(value is not None for value in self.fuel_conversion_cost.values())
                and (self.fuel_conversion_sensitivity is not None))

    def get_fuel_conversion_cost_pairs(self) -> list[tuple[str, str]]:
        return [pair for pair, cost in self.fuel_conversion_cost.items() if cost is not None]
