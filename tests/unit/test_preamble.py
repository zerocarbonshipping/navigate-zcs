# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Smoke test that the console banner reports a real package version."""
import re

from navigate.output import print_preamble


def test_banner_shows_real_version(capsys):
    print_preamble()
    out = capsys.readouterr().out
    assert 'Version Debug' not in out
    assert re.search(r'Version \d+\.\d+', out)
