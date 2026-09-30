# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""A Report command's property token must name a getter on its own profile class."""

from __future__ import annotations

import pytest

from navigate.parser._report_properties import check_report_property


def test_a_token_the_command_reports_passes():
    check_report_property("add_fleet_property", "CargoMiles")


@pytest.mark.parametrize(
    ("command", "token"),
    [
        ("add_fleet_property", "CargoMils"),
        # BunkerPrice is a port getter, which no vessel profile carries
        ("add_vessel_property", "BunkerPrice"),
    ],
    ids=["unknown_token", "token_of_another_command"],
)
def test_a_token_the_command_does_not_report_is_refused(command, token):
    with pytest.raises(ValueError, match=rf"'{token}'.*{command}"):
        check_report_property(command, token)
