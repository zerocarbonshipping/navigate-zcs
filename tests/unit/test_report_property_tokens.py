# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Every profile getter is reachable from a report-property token.

attribute_to_setter keeps only [A-Z][a-z]* runs, so the token a getter is written
as in a deck can read back as a different getter: get_co2_mass would spell as
Co2Mass and read back as get_co_mass, silently resolving to the wrong result or to
nothing. Nothing in the parser guards this, so a digit in a getter name is caught
here instead of by a reader of a report column.
"""

from __future__ import annotations

import pytest

from helpers.report_properties import PROFILE_CLASSES, getter_for, token_for


def _getters_of(profile_class):
    return sorted(name for name in dir(profile_class) if name.startswith("get_"))


PROFILE_GETTERS = sorted(
    {
        name
        for profile_class in PROFILE_CLASSES.values()
        for name in _getters_of(profile_class)
    }
)


def test_every_profile_class_exposes_getters():
    without = sorted(
        profile_class.__name__
        for profile_class in PROFILE_CLASSES.values()
        if not _getters_of(profile_class)
    )

    assert not without, f"no getter found on {without}: the enumeration has rotted"


@pytest.mark.parametrize("getter", PROFILE_GETTERS)
def test_getter_round_trips_through_its_token(getter):
    token = token_for(getter)

    assert getter_for(token) == getter, (
        f"'{getter}' spells as the token '{token}', which reads back as"
        f" '{getter_for(token)}', so no report property can name it"
    )
