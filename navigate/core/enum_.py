# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The keyword values a deck can name, and the classifiers internal to the model."""

from __future__ import annotations

from enum import Enum, auto


# external enums -----------------------------------------------------------------------
class SectionID(Enum):
    """The section of a deck a declaration is read in."""

    DEFINE = auto()  # where nodes are defined
    EVENTS = auto()  # where the timeline and attribute changes are read


class FuelTypeID(Enum):
    """The molecule a fuel is based on, shared by every pathway producing it."""

    AMMONIA = auto()  # ammonia-based fuel
    ELECTRICITY = auto()  # not a fuel; represents battery-electric vessels
    ETHANOL = auto()  # ethanol-based fuel
    HYDROGEN = auto()  # hydrogen-based fuel
    LPG = auto()  # liquefied petroleum gas, e.g. butane, propane
    METHANE = auto()  # methane-based fuel, e.g. LNG, bio-methane
    METHANOL = auto()  # methanol-based fuel
    OIL = auto()  # oil- or diesel-based fuel


class SourceDependencyID(Enum):
    """The dependency of an energy source on the electricity grid of its region."""

    STANDALONE = auto()  # not connected to the region's electricity grid
    CONNECTED = auto()  # connected to the region's electricity grid


class EnergyDemandID(Enum):
    """The kind of vessel energy demand a technology targets."""

    PROPULSION = auto()  # energy that propels the vessel
    ELECTRICAL = auto()  # the vessel's electricity demand
    HEAT = auto()  # the vessel's heat demand


# iteration order feeds LP variable/constraint creation order, which must be
# deterministic across runs
PORT_ENERGY_DEMANDS = (EnergyDemandID.ELECTRICAL, EnergyDemandID.HEAT)


class RouteTypeID(Enum):
    """How a vessel moves between the ports of a route."""

    LINER = auto()  # ports called in order, each consecutive pair a leg
    TRAMP = auto()  # ports called in any order, every ordered pair a leg


class Interpolate1DID(Enum):
    """The interpolation method of a curve or a forecast."""

    LINEAR = auto()  # interpolate linearly
    PREVIOUS = auto()  # take the value at the previous point
    NEXT = auto()  # take the value at the next point
    NEAREST = auto()  # take the value at the nearest point, the lower on a tie
    NEAREST_UP = auto()  # take the value at the nearest point, the higher on a tie


class Interpolate2DID(Enum):
    """The interpolation method of a surface or a timetable."""

    LINEAR = auto()  # interpolate linearly
    NEAREST = auto()  # take the value at the nearest point


class ExtrapolateID(Enum):
    """The extrapolation method beyond the ends of a curve or a forecast."""

    FALSE = auto()  # extrapolation not allowed
    FLAT = auto()  # hold the assigned value, or the table's end value, flat
    LINEAR = auto()  # extrapolate linearly


class PolicyScopeID(Enum):
    """The part of the fuel life cycle whose emissions a policy covers."""

    WTT = auto()  # well-to-tank
    TTW = auto()  # tank-to-wake
    WTW = auto()  # well-to-wake


class RegulationSchemeID(Enum):
    """Whether vessels may trade compliance with a regulation between them."""

    INDIVIDUAL = auto()  # penalty above, no remuneration below
    FLEXIBLE = auto()  # trading scheme, remuneration below


class RegulationMeasureID(Enum):
    """The quantity a regulation measures emissions in."""

    ABSOLUTE = auto()  # tons of emissions
    INTENSITY = auto()  # kg of emissions per GJ
    TRANSPORT = auto()  # g of emissions per actual cargo-mile
    TRANSPORT_NOMINAL = auto()  # g of emissions per nominal cargo-mile


class LevySchemeID(Enum):
    """Whether a levy penalizes emissions, subsidizes avoiding them, or both."""

    PENALTY = auto()  # penalty above, no subsidy below
    SUBSIDY = auto()  # subsidy below, no penalty above
    BOTH = auto()  # penalty above, subsidy below


class SpeedAlignmentID(Enum):
    """How the optimal speeds of the vessel types in a fleet are aligned."""

    INDIVIDUAL = auto()  # keep each vessel type's own optimal speed
    MINIMUM = auto()  # use the lowest optimal speed of the vessel types
    MAXIMUM = auto()  # use the highest optimal speed of the vessel types
    AVERAGE = auto()  # use the mean optimal speed, weighted by vessel count


class SolverBackendID(Enum):
    """The solver backend the bunkering linear program is solved with."""

    AUTOMATIC = auto()  # use Gurobi if available, else HiGHS
    GUROBI = auto()  # use Gurobi if available, else warn and use HiGHS
    HIGHS = auto()  # always use HiGHS


class SolverMethodID(Enum):
    """The solution method, applied as Gurobi's Method parameter; HiGHS ignores it."""

    # the values are Gurobi's Method parameter codes
    AUTOMATIC = -1  # let the solver choose the method automatically
    DETERMINISTIC = 4  # request the deterministic concurrent method
    NON_DETERMINISTIC = 3  # request the concurrent method


# internal enums -----------------------------------------------------------------------
class BunkerScopeID(Enum):
    """Whether bunkering is solved for the existing fleet or the expected one."""

    EXPECTED = auto()  # forward-looking pass that informs investment decisions
    EXISTING = auto()  # final pass solved for the fleet as it currently stands


class SolveStatusID(Enum):
    """How the last solve of the bunkering linear program ended."""

    OPTIMAL = auto()  # an optimal solution was found
    INFEASIBLE = auto()  # no point satisfies every constraint
    UNBOUNDED = auto()  # the objective decreases without bound
    INFEASIBLE_OR_UNBOUNDED = auto()  # infeasible or unbounded, not told apart
    OTHER = auto()  # any other outcome, such as a reached limit


class UtilityID(Enum):
    """How a metric is turned into the dimensionless utility of a discrete choice."""

    LOWER_LOG_RATIO = auto()  # lower-is-better, log-ratio to the minimum
    HIGHER_LOG_RATIO = auto()  # higher-is-better, log-ratio to the maximum
    SIGNED_REFERENCE = auto()  # signed metric scaled by a reference value


class TimingID(Enum):
    """The phase of a time step its computational time is booked to."""

    LP_BUILD = auto()  # building and updating the bunkering LPs
    LP_SOLVE = auto()  # solving the bunkering LPs
    LP_TRANSFER = auto()  # transferring the LP solutions to the nodes
    FLEET_EVOLUTION = auto()  # scrapping, fuel conversions and newbuilds
    SPEED_MANAGEMENT = auto()  # speed management of the fleets
    TECHNOLOGY_INSTALLATION = auto()  # technology installation on the fleets
    PLANT_PRODUCTION = auto()  # production properties of the plants
    PRODUCER_EVOLUTION = auto()  # decommissioning, delivery and planning of plants
    POLICY = auto()  # emission coefficients, regulation measures and compliance
    OTHER = auto()  # everything in a time step no other phase claims
