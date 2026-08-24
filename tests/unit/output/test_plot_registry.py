# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail tests for the plot registry (single source of truth).

:data:`navigate.output.plots._registry.PLOTS` is the ordered catalogue of
every plot rendered by ``render_plots``. These tests enforce the invariants
that let that catalogue be the single source of truth:

  * every registered plot is a callable named ``plot_<label>``;
  * labels are unique and ``PLOT_LABELS`` is derived from them;
  * every public ``plot_*`` function in the package is either registered or in
    the known-disabled set -- so a new plot file cannot silently go unregistered.
"""
import importlib
import pkgutil

import navigate.output.plots as plots_pkg
from navigate.output.plots._registry import PLOT_LABELS, PLOTS, plot_label

# Public plot functions that intentionally exist but are NOT rendered.
# Mirrors the disabled catalogue documented in _registry.py (currently none).
KNOWN_DISABLED = set()


def _discover_public_plot_functions():
    """Map name -> function for every public ``plot_*`` defined in the package."""
    found = {}
    for info in pkgutil.iter_modules(plots_pkg.__path__):
        if info.name.startswith('_'):
            continue
        mod = importlib.import_module(f'{plots_pkg.__name__}.{info.name}')
        for name in dir(mod):
            if not name.startswith('plot_'):
                continue
            obj = getattr(mod, name)
            if callable(obj) and getattr(obj, '__module__', None) == mod.__name__:
                found[name] = obj
    return found


def test_registered_plots_follow_naming_invariant():
    for func in PLOTS:
        assert callable(func), func
        assert func.__name__.startswith('plot_'), func.__name__
        assert plot_label(func) == func.__name__[len('plot_'):]


def test_labels_are_unique_and_derived():
    labels = [plot_label(f) for f in PLOTS]
    assert len(labels) == len(set(labels)), 'duplicate plot labels in PLOTS'
    assert PLOT_LABELS == set(labels)


def test_every_public_plot_is_registered_or_disabled():
    discovered = set(_discover_public_plot_functions())
    registered = {f.__name__ for f in PLOTS}

    unaccounted = discovered - registered - KNOWN_DISABLED
    assert not unaccounted, (
        'public plot functions neither registered in PLOTS nor listed as '
        f'disabled: {sorted(unaccounted)}')

    stale = KNOWN_DISABLED - discovered
    assert not stale, f'KNOWN_DISABLED names no longer exist: {sorted(stale)}'
