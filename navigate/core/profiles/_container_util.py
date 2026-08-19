# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Utility functions for reducing boilerplate in profile and expectation container classes.

Provides factory functions that generate families of emission getter methods on profile classes,
replacing hundreds of hand-written methods with a few registration calls.
"""
from __future__ import annotations

from collections.abc import Callable

import numpy as np

from navigate.util import add_dicts, extract_from_dict, extract_from_tuple_dict


def _make_method(func: Callable, name: str, qualname: str) -> Callable:
    """Set proper __name__ and __qualname__ on a generated method for debugging."""
    func.__name__ = name
    func.__qualname__ = qualname
    return func


def _attach(cls: type, methods: dict[str, Callable]) -> None:
    """Attach a dict of {method_name: function} to cls with proper naming."""
    for name, method in methods.items():
        setattr(cls, name, _make_method(method, name, f'{cls.__qualname__}.{name}'))


def _make_data_fn(data_attr: str | None = None, source_attrs: list[str] | None = None) -> Callable:
    """Return a closure that fetches emission data from an instance."""
    if source_attrs is not None:
        def get_data(self):
            return add_dicts(*(getattr(self, a) for a in source_attrs))
        return get_data
    else:
        def get_data(self):
            return getattr(self, data_attr)
        return get_data


# ---------------------------------------------------------------------------
# Single-dict getters  (keyed by emission_name)
# Used by PlantProfile
# ---------------------------------------------------------------------------

def register_single_dict_getters(cls: type, source_name: str, gwp_attr: str,
                                 lhv_attr: str, convert_to_intensity: str,
                                 data_attr: str | None = None) -> None:
    """
    Generate GWP-equivalent emission getter methods for single-dict storage (keyed by emission_name).

    Generates 4 methods: get_equivalent_{name}, get_total_equivalent_{name},
    get_intensity_equivalent_{name}, get_intensity_total_equivalent_{name}.

    Parameters
    ----------
    cls : type
        The class to attach methods to.
    source_name : str
        Emission source name used in method names (e.g., "TTW", "investment_WTT").
    gwp_attr : str
        Name of the instance attribute holding GWP dict.
    lhv_attr : str
        Name of the instance attribute holding scalar lower heating value.
    convert_to_intensity : str
        Name of the static/class method for intensity conversion.
    data_attr : str, optional
        Name of instance attribute holding emission data dict.
    """
    _data = _make_data_fn(data_attr)

    def get_raw(self, emission_name=None, idx=np.s_[:]):
        return extract_from_dict(_data(self), emission_name, idx)

    def get_equivalent(self, emission_name=None, idx=np.s_[:]):
        if emission_name is not None:
            return get_raw(self, emission_name, idx) * getattr(self, gwp_attr)[emission_name]
        return {key: get_equivalent(self, key, idx) for key in _data(self)}

    def get_total_equivalent(self, idx=np.s_[:]):
        return self._get_total_method(get_equivalent.__get__(self), idx)

    def get_intensity_equivalent(self, emission_name=None, idx=np.s_[:]):
        converter = getattr(self, convert_to_intensity)
        if emission_name is not None:
            return converter(get_equivalent(self, emission_name, idx), getattr(self, lhv_attr))
        return {key: get_intensity_equivalent(self, key, idx) for key in _data(self)}

    def get_intensity_total_equivalent(self, idx=np.s_[:]):
        return self._get_total_method(get_intensity_equivalent.__get__(self), idx)

    _attach(cls, {
        f'get_equivalent_{source_name}': get_equivalent,
        f'get_total_equivalent_{source_name}': get_total_equivalent,
        f'get_intensity_equivalent_{source_name}': get_intensity_equivalent,
        f'get_intensity_total_equivalent_{source_name}': get_intensity_total_equivalent,
    })


# ---------------------------------------------------------------------------
# FuelConsumer tuple-dict getters  (adds cumulative + _to_intensity variants)
# Used by FuelConsumerProfile
# ---------------------------------------------------------------------------

def register_fuel_consumer_getters(cls: type, source_name: str,
                                   data_attr: str | None = None,
                                   source_attrs: list[str] | None = None,
                                   extra_total: Callable | None = None) -> None:
    """
    Generate the 8-method GWP-equivalent emission getter suite for FuelConsumerProfile.

    Generates: equivalent, total_equivalent, cumulative_equivalent,
    cumulative_total_equivalent, intensity_equivalent, intensity_total_equivalent,
    cumulative_intensity_equivalent, cumulative_intensity_total_equivalent.

    Parameters
    ----------
    cls : type
        The class to attach methods to.
    source_name : str
        Emission source name (e.g., "WTT", "TTW", "WTW").
    data_attr : str, optional
        Name of instance attribute holding emission tuple-dict.
    source_attrs : list[str], optional
        Attribute names to add together for combined sources.
    extra_total : Callable, optional
        ``(self, idx) -> equivalent`` term added to every total variant, for
        emissions with no (fuel, emission) attribution (e.g. shore power).
        The per-key getters are unaffected.
    """
    _data = _make_data_fn(data_attr, source_attrs)

    def get_equivalent(self, fuel_name=None, emission_name=None, idx=np.s_[:]):
        if emission_name is not None:
            return extract_from_tuple_dict(_data(self), key1=fuel_name, key2=emission_name, idx=idx,
                                           transform=lambda x: x * self._GWP[emission_name])
        if (fuel_name is not None) and (emission_name is None):
            return {(fuel_name, en): get_equivalent(self, fuel_name, en, idx)
                    for en in self._get_emissions()}
        return {key: get_equivalent(self, *key, idx) for key in self._get_fuel_emissions()}

    def get_total_equivalent(self, idx=np.s_[:]):
        total = self._get_total_method(get_equivalent.__get__(self), idx)
        if extra_total is not None:
            total = total + extra_total(self, idx)
        return total

    def get_cumulative_equivalent(self, fuel_name=None, emission_name=None):
        return self._to_cumulative_any(get_equivalent(self, fuel_name, emission_name))

    def get_cumulative_total_equivalent(self):
        return self._to_cumulative(get_total_equivalent(self))

    def get_intensity_equivalent(self, fuel_name=None, emission_name=None, idx=np.s_[:]):
        return self._to_intensity(get_equivalent.__get__(self), fuel_name, emission_name, idx)

    def get_intensity_total_equivalent(self, idx=np.s_[:]):
        return self._to_intensity(get_total_equivalent.__get__(self), idx=idx)

    def get_cumulative_intensity_equivalent(self, fuel_name=None, emission_name=None, idx=np.s_[:]):
        return self._to_intensity(get_equivalent.__get__(self), fuel_name, emission_name, idx, cumulative=True)

    def get_cumulative_intensity_total_equivalent(self, idx=np.s_[:]):
        return self._to_intensity(get_total_equivalent.__get__(self), idx=idx, cumulative=True)

    _attach(cls, {
        f'get_equivalent_{source_name}': get_equivalent,
        f'get_total_equivalent_{source_name}': get_total_equivalent,
        f'get_cumulative_equivalent_{source_name}': get_cumulative_equivalent,
        f'get_cumulative_total_equivalent_{source_name}': get_cumulative_total_equivalent,
        f'get_intensity_equivalent_{source_name}': get_intensity_equivalent,
        f'get_intensity_total_equivalent_{source_name}': get_intensity_total_equivalent,
        f'get_cumulative_intensity_equivalent_{source_name}': get_cumulative_intensity_equivalent,
        f'get_cumulative_intensity_total_equivalent_{source_name}': get_cumulative_intensity_total_equivalent,
    })
