# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The keyword values a deck can name, and the classifiers internal to the model."""

from __future__ import annotations

from enum import Enum, auto


# external enums -----------------------------------------------------------------------
class SimulationSectionID(Enum):
    """The section of a deck a declaration is read in."""

    DEFINE = auto()
    EVENTS = auto()


class FuelTypeID(Enum):
    """The molecule a fuel is based on, shared by every pathway producing it."""

    AMMONIA = auto()
    ELECTRICITY = auto()
    ETHANOL = auto()
    HYDROGEN = auto()
    LPG = auto()
    METHANE = auto()
    METHANOL = auto()
    OIL = auto()


class SourceDependencyID(Enum):
    """The dependency of an energy source on the electricity grid of its region."""

    STANDALONE = auto()
    CONNECTED = auto()


class EnergyDemandTypeID(Enum):
    """The kind of vessel energy demand a technology targets."""

    PROPULSION = auto()
    ELECTRICAL = auto()
    HEAT = auto()


# iteration order feeds LP variable/constraint creation order, which must be
# deterministic across runs
EnergyDemandTypePortID = (EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT)


class RouteTypeID(Enum):
    """How a vessel moves between the ports of a route."""

    ROUND_TRIP = auto()
    REGIONAL_TRIP = auto()


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
    SUBSIDY = auto()  # subsidy below, no penalty below
    BOTH = auto()  # penalty above, subsidy below


class SpeedAlignmentID(Enum):
    """How the optimal speeds of the vessel types in a fleet are aligned."""

    INDIVIDUAL = auto()  # keep each vessel type's own optimal speed
    MINIMUM = auto()  # use minimum optimal speed across vessels
    MAXIMUM = auto()  # use maximum optimal speed across vessels
    AVERAGE = auto()  # use weighted arithmetic mean of optimal speeds


class ReportReduceID(Enum):
    """Which elements of a report property's tuple keys are reduced over."""

    NONE = auto()
    FIRST = auto()
    SECOND = auto()
    BOTH = auto()


class FileFormatID(Enum):
    """The file format a report is exported in."""

    XLSX = auto()
    CSV = auto()


class SolverBackendID(Enum):
    """The solver backend the bunkering linear program is solved with."""

    AUTOMATIC = auto()
    GUROBI = auto()
    HIGHS = auto()


class SolverMethodID(Enum):
    """The solution method the solver backend applies to the linear program."""

    # Integer values are Gurobi Method IDs (also mapped in solver_highs.py for HiGHS)
    AUTOMATIC = -1
    DETERMINISTIC = 4
    NON_DETERMINISTIC = 3


# internal enums -----------------------------------------------------------------------
class BunkerScopeID(Enum):
    """Whether bunkering is solved for the existing fleet or the expected one."""

    EXPECTED = auto()
    EXISTING = auto()


class UtilityID(Enum):
    """How a metric is turned into the dimensionless utility of a discrete choice."""

    LOWER_LOG_RATIO = (
        auto()
    )  # lower-is-better, log-ratio to the minimum (e.g. LCOT, LCoF)
    HIGHER_LOG_RATIO = (
        auto()
    )  # higher-is-better, log-ratio to the maximum (e.g. expected demand)
    SIGNED_REFERENCE = (
        auto()
    )  # signed metric scaled by a reference value (e.g. NPV / ship CAPEX)
