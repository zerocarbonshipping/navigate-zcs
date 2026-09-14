# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""
Regression-suite pytest configuration: the baseline regeneration flag.

pytest registers options only from initial conftests, so `--regen-baselines`
exists only when tests/regression/ is on the command line — the sanctioned
path is `make regen-regression`. Bare `pytest` runs are unaffected: the
fixture falls back to False when the option was never registered.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--regen-baselines",
        action="store_true",
        default=False,
        help=(
            "Regenerate the committed golden baselines instead of comparing "
            "against them. Activation guards still run and gate the copy. "
            "Use `make regen-regression`."
        ),
    )


@pytest.fixture(scope="session")
def regen_baselines_flag(request):
    """Whether this run regenerates baselines instead of comparing."""
    return request.config.getoption("--regen-baselines", default=False)
