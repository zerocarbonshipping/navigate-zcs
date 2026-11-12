# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
BaseResults, the result marker, its units, and the functions that read and add results.

BaseResults types any results object in the results writer
(output/results_writer.py).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.results.results_context import ResultsContext
    from navigate.util.types_ import BoolArray, FloatArray, FloatLike

_RESULT = "result"


class Unit(Enum):
    """
    A unit a result can carry; its value is the label the results file gives it.

    A label is plain ASCII without metric prefixes, and a rate is per year. ``t`` is
    the metric ton, of fuel or of one emission gas unweighted; ``tCO2e`` is a ton of
    CO2-equivalent, weighted by the global warming potential, the model's own or a
    policy's for regulation and levy units. A cargo-mile is one unit of cargo carried
    one nautical mile, in the vessel segment's own cargo unit (TEU, CEU, dwt, ...),
    which matches the fleet's trade. ``measure`` stands for the unit of the
    regulation's measure: tCO2e/year for ABSOLUTE, gCO2e/MJ for INTENSITY,
    gCO2e/cargo-mile for TRANSPORT and gCO2e/nominal cargo-mile for
    TRANSPORT_NOMINAL.
    """

    GJ_PER_YEAR = "GJ/year"  # gigajoules per year
    MW = "MW"  # megawatts
    MW_PER_YEAR = "MW/year"  # megawatts per year
    TON_PER_YEAR = "t/year"  # metric tons per year, of fuel or of one emission gas
    TON_PER_TON = "t/t"  # tons of one emission gas per ton of fuel
    TCO2E_PER_YEAR = "tCO2e/year"  # tons of CO2-equivalent per year
    TCO2E_PER_TON = "tCO2e/t"  # tons of CO2-equivalent per ton of fuel
    GCO2E_PER_MJ = "gCO2e/MJ"  # grams of CO2-equivalent per MJ, equal to kg/GJ
    USD = "USD"  # money
    USD_PER_YEAR = "USD/year"  # money per year
    USD_PER_GJ = "USD/GJ"  # money per gigajoule
    USD_PER_TON = "USD/t"  # money per ton of fuel
    USD_PER_TCO2E = "USD/tCO2e"  # money per ton of CO2-equivalent
    USD_PER_CARGO_MILE = "USD/cargo-mile"  # money per cargo-mile
    CARGO_MILES_PER_YEAR = "cargo-miles/year"  # cargo-miles per year
    KNOTS = "knots"  # nautical miles per hour
    VESSELS = "vessels"  # a number of vessels
    VESSELS_PER_YEAR = "vessels/year"  # vessels per year
    PLANTS_PER_YEAR = "plants/year"  # plants per year
    YEARS = "years"  # years
    SECONDS_PER_YEAR = "s/year"  # seconds per year
    DIMENSIONLESS = "-"  # a fraction, share or flag
    MEASURE = "measure"  # the unit of the regulation's measure


class ResultSpec(NamedTuple):
    """How a stored result is written to the results file."""

    unit: Unit
    per_step: bool


def result(unit: Unit, *, per_step: bool = False) -> Any:
    """
    Declare a field that holds a result, written out to the results file.

    A field declared with a plain ``field(init=False)`` is state the simulation
    keeps on the results, and no result.

    Parameters
    ----------
    unit
        Unit of the values in the results file.
    per_step
        Whether the field counts what happened in each time step; the results file
        divides it by the step length to write the per-year rate its unit names.

    Returns
    -------
    Any
        The dataclass field.
    """
    return field(init=False, metadata={_RESULT: ResultSpec(unit, per_step)})


def _result_specs(cls: type[BaseResults]) -> dict[str, ResultSpec]:
    return {f.name: f.metadata[_RESULT] for f in fields(cls) if _RESULT in f.metadata}


def result_units(cls: type[BaseResults]) -> dict[str, str]:
    """
    Map every result of a results class to its unit.

    Parameters
    ----------
    cls
        Results class.

    Returns
    -------
    dict[str, str]
        Unit per result name, inherited results included, as the results file
        labels it.
    """
    return {name: spec.unit.value for name, spec in _result_specs(cls).items()}


def result_names(cls: type[BaseResults]) -> frozenset[str]:
    """
    Name every result of a results class.

    Parameters
    ----------
    cls
        Results class.

    Returns
    -------
    frozenset[str]
        Result names, inherited results included.
    """
    return frozenset(_result_specs(cls))


def per_step_results(cls: type[BaseResults]) -> frozenset[str]:
    """
    Name the results of a results class that count what happened in each step.

    Parameters
    ----------
    cls
        Results class.

    Returns
    -------
    frozenset[str]
        Result names; the results file writes these per year.
    """
    return frozenset(name for name, spec in _result_specs(cls).items() if spec.per_step)


def accumulate(
    target: FloatArray | dict[Any, Any],
    source: FloatArray | dict[Any, Any],
    multiplier: FloatLike = 1.0,
) -> None:
    """
    Add a field of one results object into the same field of another, key by key.

    Parameters
    ----------
    target
        Field added into: a timeline, or a dict of timelines or of such dicts.
    source
        Field added, keyed as the target.
    multiplier
        Multiplier applied to the source; a scalar, or a weight per time step.
    """
    if isinstance(target, dict):
        for key, value in target.items():
            accumulate(value, source[key], multiplier)
    else:
        target[:] += multiplier * source[:]


@dataclass(eq=False, repr=False)
class BaseResults:
    """Storage the simulation writes; post-processing assigns the computed results."""

    context: ResultsContext = field(init=False)

    def _default_array(self, default: float = 0.0) -> FloatArray:
        return np.full(self.context.timeline.shape, default, dtype=np.float64)

    def _default_bool_array(self) -> BoolArray:
        return np.zeros(self.context.timeline.shape, dtype=bool)

    def _default_dict[K](
        self, keys: Iterable[K], default: float = 0.0
    ) -> dict[K, FloatArray]:
        return {key: self._default_array(default) for key in keys}

    def _default_bool_dict[K](self, keys: Iterable[K]) -> dict[K, BoolArray]:
        return {key: self._default_bool_array() for key in keys}

    def _default_tuple_dict[K1, K2](
        self, keys1: Iterable[K1], keys2: Iterable[K2], default: float = 0.0
    ) -> dict[tuple[K1, K2], FloatArray]:
        return self._default_dict(itertools.product(keys1, keys2), default)

    def _default_nested_dict[K1, K2](
        self, keys1: Iterable[K1], keys2: Iterable[K2], default: float = 0.0
    ) -> dict[K1, dict[K2, FloatArray]]:
        return {key: self._default_dict(keys2, default) for key in keys1}
