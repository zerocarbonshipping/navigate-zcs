# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""_BaseProfile, the context every profile is sized by, and the result marker."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable

    from navigate.core.profiles.profile_context import ProfileContext
    from navigate.util.types_ import BoolArray, FloatArray, FloatLike

_RESULT = "result"


class ResultSpec(NamedTuple):
    """How a stored result is written to the results file."""

    unit: str
    per_step: bool


def result(unit: str, *, per_step: bool = False) -> Any:
    """
    Declare a profile field that holds a result: reported, plotted and written out.

    A field declared with a plain ``field(init=False)`` is state the simulation
    keeps on the profile, and no result.

    The unit is the one the results file labels the values with, plain ASCII
    without metric prefixes:

    * rates are per year (``GJ/year``, ``t/year``, ``USD/year``);
    * ``t`` is the metric ton; ``tCO2e`` is a ton of CO2-equivalent, weighted by the
      global warming potential (the model's own, or a policy's for regulation and
      levy units), while a bare ``t`` of emission is one gas unweighted;
    * emission intensities are ``g/MJ`` (equal to kg/GJ);
    * a cargo-mile is one unit of cargo carried one nautical mile, in the vessel
      segment's own cargo unit (TEU, CEU, dwt, ...), which matches the fleet's trade;
    * ``-`` marks a dimensionless fraction, share or flag;
    * ``measure`` marks a value in the unit of the regulation's measure: tCO2e/year
      for ABSOLUTE, gCO2e/MJ for INTENSITY, gCO2e/cargo-mile for TRANSPORT and
      gCO2e/nominal cargo-mile for TRANSPORT_NOMINAL.

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


def _results(cls: type[_BaseProfile]) -> dict[str, ResultSpec]:
    return {f.name: f.metadata[_RESULT] for f in fields(cls) if _RESULT in f.metadata}


def result_units(cls: type[_BaseProfile]) -> dict[str, str]:
    """
    Map every result of a profile class to its unit.

    Parameters
    ----------
    cls
        Profile class.

    Returns
    -------
    dict[str, str]
        Unit per result name, inherited results included, as the results file
        labels it.
    """
    return {name: spec.unit for name, spec in _results(cls).items()}


def result_names(cls: type[_BaseProfile]) -> frozenset[str]:
    """
    Name every result of a profile class.

    Parameters
    ----------
    cls
        Profile class.

    Returns
    -------
    frozenset[str]
        Result names, inherited results included.
    """
    return frozenset(_results(cls))


def per_step_results(cls: type[_BaseProfile]) -> frozenset[str]:
    """
    Name the results of a profile class that count what happened in each step.

    Parameters
    ----------
    cls
        Profile class.

    Returns
    -------
    frozenset[str]
        Result names; the results file writes these per year.
    """
    return frozenset(name for name, spec in _results(cls).items() if spec.per_step)


def accumulate(
    target: FloatArray | dict[Any, Any],
    source: FloatArray | dict[Any, Any],
    multiplier: FloatLike = 1.0,
) -> None:
    """
    Add a field of one profile into the same field of another, key by key.

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
class _BaseProfile:
    """The run's context and the storage allocation every profile shares."""

    context: ProfileContext = field(init=False)

    def _initialize_base(self, context: ProfileContext) -> None:
        self.context = context

    def _default_array(self, default: float | None = None) -> FloatArray:
        if default is None:
            return np.zeros(self.context.timeline.shape)
        return np.full(self.context.timeline.shape, default, dtype=np.float64)

    def _default_bool_array(self, default: bool) -> BoolArray:
        return np.full(self.context.timeline.shape, default, dtype=bool)

    def _default_dict[K](
        self, keys: Iterable[K], default: float | None = None
    ) -> dict[K, FloatArray]:
        return {key: self._default_array(default) for key in keys}

    def _default_bool_dict[K](
        self, keys: Iterable[K], default: bool
    ) -> dict[K, BoolArray]:
        return {key: self._default_bool_array(default) for key in keys}

    def _default_tuple_dict[K1, K2](
        self,
        keys1: Iterable[K1],
        keys2: Iterable[K2],
        default: float | None = None,
    ) -> dict[tuple[K1, K2], FloatArray]:
        return self._default_dict(itertools.product(keys1, keys2), default)

    def _default_nested_dict[K1, K2](
        self,
        keys1: Iterable[K1],
        keys2: Iterable[K2],
        default: float | None = None,
    ) -> dict[K1, dict[K2, FloatArray]]:
        return {key: self._default_dict(keys2, default) for key in keys1}
