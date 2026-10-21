# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Timings, which books the computational time of each time step to its phases.

navigate.simulation measures its time steps and the methods it decorates with timed;
the global results hold what is booked.
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Concatenate, Protocol

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable, Iterator

    from navigate.util.types_ import FloatArray


class Timings[K]:
    """
    Book the computational time of each time step to the phase that spends it.

    A measurement is exclusive: one nested inside another pauses it, so each second
    is booked to the innermost phase and the phases of a step sum to its wall time.

    Parameters
    ----------
    seconds
        Seconds spent per phase and time step, added to in place.
    """

    def __init__(self, seconds: dict[K, FloatArray]) -> None:
        self._seconds: dict[K, FloatArray] = seconds
        self._idx: int

        # the seconds spent in the measurements nested in each open one
        self._nested: list[float] = []

    @contextmanager
    def step(self, idx: int, phase: K) -> Iterator[None]:
        """
        Measure a time step, booking what no nested measurement claims to a phase.

        Parameters
        ----------
        idx
            Index of the time step.
        phase
            Phase the time of the step outside nested measurements is booked to.
        """
        self._idx = idx

        with self.measure(phase):
            yield

    @contextmanager
    def measure(self, phase: K) -> Iterator[None]:
        """
        Book the time spent inside, less that of nested measurements, to a phase.

        Parameters
        ----------
        phase
            Phase the time is booked to.
        """
        self._nested.append(0.0)
        start = time.perf_counter()

        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            nested = self._nested.pop()
            self._seconds[phase][self._idx] += elapsed - nested

            if self._nested:
                self._nested[-1] += elapsed


# a type parameter bound cannot name another type parameter, so the owner's phase
# key is left open and a phase of the wrong kind fails as a missing key
class _Timed(Protocol):
    timings: Timings[Any]


type _Method[T, **P, R] = Callable[Concatenate[T, P], R]


def timed[T: _Timed, **P, R](
    phase: Hashable,
) -> Callable[[_Method[T, P, R]], _Method[T, P, R]]:
    """
    Decorate a method to book the time spent in it to a phase.

    The time is measured on the timings of the method's first argument, so a plain
    function taking an object with timings is decorated alike.

    Parameters
    ----------
    phase
        Phase the time is booked to.
    """

    def decorate(method: _Method[T, P, R]) -> _Method[T, P, R]:
        @functools.wraps(method)
        def measured(owner: T, *args: P.args, **kwargs: P.kwargs) -> R:
            with owner.timings.measure(phase):
                return method(owner, *args, **kwargs)

        return measured

    return decorate
