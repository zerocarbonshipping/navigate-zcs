# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""The regulation results computed after the run from the written ones."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from navigate.core.results import RegulationResults


def complete_regulation_results(results: RegulationResults) -> None:
    """
    Write the regulation results that total the written ones.

    Parameters
    ----------
    results
        Regulation results, written for the whole run.
    """
    results.non_compliance_units = results.flexibility_units + results.remedial_units
