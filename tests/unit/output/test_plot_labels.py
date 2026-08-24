# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Guardrail tests for the shared fuel label/colour/order tables.

The plot modules key off :data:`FUEL_TYPE_LABEL` / :data:`FUEL_TYPE_COLOR` (per
fuel type) and :data:`FUEL_LABEL` / :data:`FUEL_COLOR` (per individual fuel), and
iterate the ordering tuples :data:`FUEL_TYPE_ORDER` / :data:`FUEL_ORDER`. These
tests make sure the tables stay in sync -- e.g. a name in an ordering must have a
label and a colour, else it silently drops out of (or crashes) a stacked plot.
"""
from navigate.output.plots._labels import (
    FUEL_COLOR,
    FUEL_LABEL,
    FUEL_ORDER,
    FUEL_TYPE_COLOR,
    FUEL_TYPE_LABEL,
    FUEL_TYPE_ORDER,
)


def test_label_and_colour_tables_cover_the_same_fuel_types():
    assert set(FUEL_TYPE_LABEL) == set(FUEL_TYPE_COLOR)


def test_type_ordering_covers_every_labelled_fuel_type():
    assert set(FUEL_TYPE_ORDER) == set(FUEL_TYPE_LABEL)


def test_fuel_ordering_is_labelled_and_coloured():
    assert set(FUEL_ORDER) <= set(FUEL_LABEL)
    assert set(FUEL_ORDER) <= set(FUEL_COLOR)


def test_orderings_have_no_duplicates():
    assert len(FUEL_TYPE_ORDER) == len(set(FUEL_TYPE_ORDER))
    assert len(FUEL_ORDER) == len(set(FUEL_ORDER))
