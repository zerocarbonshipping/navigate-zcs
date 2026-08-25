# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

from enum import Enum, auto


# external enums -------------------------------------------------------------------------------------------------------
class SimulationSectionID(Enum):
    DEFINE = auto()
    EVENTS = auto()


class FuelTypeID(Enum):
    AMMONIA = auto()
    ELECTRICITY = auto()
    ETHANOL = auto()
    HYDROGEN = auto()
    LPG = auto()
    METHANE = auto()
    METHANOL = auto()
    OIL = auto()


class SourceDependencyID(Enum):
    STANDALONE = auto()
    CONNECTED = auto()


class EnergyDemandTypeID(Enum):
    PROPULSION = auto()
    ELECTRICAL = auto()
    HEAT = auto()


# iteration order feeds LP variable/constraint creation order, which must be deterministic across runs
EnergyDemandTypePortID = (EnergyDemandTypeID.ELECTRICAL, EnergyDemandTypeID.HEAT)


class RouteTypeID(Enum):
    ROUND_TRIP = auto()
    REGIONAL_TRIP = auto()


class Interpolate1DID(Enum):
    LINEAR = auto()         # interpolate linearly
    PREVIOUS = auto()       # interpolate to the previous down in the table
    NEXT = auto()           # interpolate to the next up in the table
    NEAREST = auto()        # interpolate to nearest (round down at half integer)
    NEAREST_UP = auto()     # interpolate to nearest (round up at half integer)


class Interpolate2DID(Enum):
    LINEAR = auto()         # interpolate linearly
    NEAREST = auto()        # interpolate to nearest-neighbour


class ExtrapolateID(Enum):
    FALSE = auto()      # extrapolation not allowed
    FLAT = auto()       # extrapolate flat (either assigned or table values)
    LINEAR = auto()     # extrapolate linearly


class PolicyScopeID(Enum):
    WTT = auto()        # well-to-tank
    TTW = auto()        # tank-to-wake
    WTW = auto()        # well-to-tank


class RegulationSchemeID(Enum):
    INDIVIDUAL = auto()     # penalized above, no remuneration below
    FLEXIBLE = auto()       # trading scheme, remunerated below


class RegulationMeasureID(Enum):
    ABSOLUTE = auto()           # tons of emissions
    INTENSITY = auto()          # kg emissions per GJ
    TRANSPORT = auto()          # gram emissions per cargo-mile
    TRANSPORT_NOMINAL = auto()  # gram emissions per cargo-mile (nominal)


class LevySchemeID(Enum):
    PENALTY = auto()    # penalized above, no remuneration below
    SUBSIDY = auto()    # subsidy below, no penalty below
    BOTH = auto()       # penalty above, subsidy below


class SpeedAlignmentID(Enum):
    INDIVIDUAL = auto()     # no alignment, current behavior
    MINIMUM = auto()        # use minimum optimal speed across vessels
    MAXIMUM = auto()        # use maximum optimal speed across vessels
    AVERAGE = auto()        # use weighted arithmetic mean of optimal speeds


class ReportReduceID(Enum):
    NONE = auto()
    FIRST = auto()
    SECOND = auto()
    BOTH = auto()


class FileFormatID(Enum):
    XLSX = auto()
    CSV = auto()


class SolverBackendID(Enum):
    AUTOMATIC = auto()
    GUROBI = auto()
    HIGHS = auto()


class SolverMethodID(Enum):
    # Integer values are Gurobi Method IDs (also mapped in solver_highs.py for HiGHS)
    AUTOMATIC = -1
    DETERMINISTIC = 4
    NON_DETERMINISTIC = 3


# internal enums -------------------------------------------------------------------------------------------------------
class BunkerScopeID(Enum):
    EXPECTED = auto()
    EXISTING = auto()


class UtilityID(Enum):
    LOWER_LOG_RATIO = auto()    # lower-is-better, log-ratio to the minimum (e.g. LCOT, LCoF)
    HIGHER_LOG_RATIO = auto()   # higher-is-better, log-ratio to the maximum (e.g. expected demand)
    SIGNED_REFERENCE = auto()   # signed metric scaled by a reference value (e.g. NPV / ship CAPEX)
