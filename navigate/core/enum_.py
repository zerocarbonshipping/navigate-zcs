# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The keyword values a deck can name, and the classifiers internal to the model."""

from __future__ import annotations

from enum import Enum, auto


# external enums -----------------------------------------------------------------------
class SimulationSectionID(Enum):
    """The section of a deck a declaration is read in."""

    DEFINE = auto()  # deck section where nodes are defined
    EVENTS = auto()  # deck section where the timeline and attribute changes are read


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


class EnergyDemandTypeID(Enum):
    """The kind of vessel energy demand a technology targets."""

    PROPULSION = auto()  # propulsive energy demand
    ELECTRICAL = auto()  # electrical energy demand
    HEAT = auto()  # heat energy demand


# iteration order feeds LP variable/constraint creation order, which must be
# deterministic across runs
EnergyDemandTypePortID = (EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT)


class RouteTypeID(Enum):
    """How a vessel moves between the ports of a route."""

    ROUND_TRIP = auto()  # explicit ordered ports with a start/end, per-leg inputs
    REGIONAL_TRIP = auto()  # no explicit ports; time split across speed/cargo bins


class Interpolate1DID(Enum):
    """The interpolation method of a curve or a forecast."""

    LINEAR = auto()  # interpolate linearly
    PREVIOUS = auto()  # interpolate to the previous down in the table
    NEXT = auto()  # interpolate to the next up in the table
    NEAREST = auto()  # interpolate to nearest (round down at half integer)
    NEAREST_UP = auto()  # interpolate to nearest (round up at half integer)


class Interpolate2DID(Enum):
    """The interpolation method of a surface or a timetable."""

    LINEAR = auto()  # interpolate linearly
    NEAREST = auto()  # interpolate to nearest-neighbour


class ExtrapolateID(Enum):
    """The extrapolation method beyond the ends of a curve or a forecast."""

    FALSE = auto()  # extrapolation not allowed
    FLAT = auto()  # extrapolate flat (either assigned or table values)
    LINEAR = auto()  # extrapolate linearly


class PolicyScopeID(Enum):
    """The part of the fuel life cycle whose emissions a policy covers."""

    WTT = auto()  # well-to-tank
    TTW = auto()  # tank-to-wake
    WTW = auto()  # well-to-wake


class RegulationSchemeID(Enum):
    """Whether vessels may trade compliance with a regulation between them."""

    INDIVIDUAL = auto()  # penalized above, no remuneration below
    FLEXIBLE = auto()  # trading scheme, remunerated below


class RegulationMeasureID(Enum):
    """The quantity a regulation measures emissions in."""

    ABSOLUTE = auto()  # tons of emissions
    INTENSITY = auto()  # kg emissions per GJ
    TRANSPORT = auto()  # gram emissions per cargo-mile
    TRANSPORT_NOMINAL = auto()  # gram emissions per cargo-mile (nominal)


class LevySchemeID(Enum):
    """Whether a levy penalizes emissions, subsidizes avoiding them, or both."""

    PENALTY = auto()  # penalized above, no remuneration below
    SUBSIDY = auto()  # subsidy below, no penalty above
    BOTH = auto()  # penalty above, subsidy below


class SpeedAlignmentID(Enum):
    """How the optimal speeds of the vessel types in a fleet are aligned."""

    INDIVIDUAL = auto()  # keep each vessel type's own optimal speed
    MINIMUM = auto()  # use minimum optimal speed across vessels
    MAXIMUM = auto()  # use maximum optimal speed across vessels
    AVERAGE = auto()  # use weighted arithmetic mean of optimal speeds


class ReportReduceID(Enum):
    """Which elements of a report property's tuple keys are reduced over."""

    NONE = auto()  # no reduction
    FIRST = auto()  # reduce over the first tuple element
    SECOND = auto()  # reduce over the second tuple element
    BOTH = auto()  # reduce over both tuple elements


class FileFormatID(Enum):
    """The file format a report is exported in."""

    XLSX = auto()  # single Excel workbook, one sheet per report table
    CSV = auto()  # one CSV file per report table


class SolverBackendID(Enum):
    """The solver backend the bunkering linear program is solved with."""

    AUTOMATIC = auto()  # use Gurobi if available, else HiGHS
    GUROBI = auto()  # prefer Gurobi, falling back to HiGHS if unavailable
    HIGHS = auto()  # always use HiGHS


class SolverMethodID(Enum):
    """The solution method the solver backend applies to the linear program."""

    # integer values are Gurobi Method IDs; the HiGHS backend does not read them
    AUTOMATIC = -1  # let the solver choose the method automatically
    DETERMINISTIC = 4  # request the deterministic concurrent method
    NON_DETERMINISTIC = 3  # request the concurrent method


# internal enums -----------------------------------------------------------------------
class BunkerScopeID(Enum):
    """Whether bunkering is solved for the existing fleet or the expected one."""

    EXPECTED = auto()  # forward-looking pass that informs investment decisions
    EXISTING = auto()  # final pass solved for the fleet as it currently stands


class UtilityID(Enum):
    """How a metric is turned into the dimensionless utility of a discrete choice."""

    LOWER_LOG_RATIO = auto()  # lower-is-better, log-ratio to the minimum
    HIGHER_LOG_RATIO = auto()  # higher-is-better, log-ratio to the maximum
    SIGNED_REFERENCE = auto()  # signed metric scaled by a reference value
