# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests :class:`navigate.output.plot_data.PlotData`."""

from __future__ import annotations

import gzip
import pickle

import pytest

from navigate.exceptions import PlotDataError
from navigate.output.plot_data import PlotData


def test_load_rejects_pickle_that_is_not_plot_data(tmp_path):
    path = tmp_path / "plot_data.pkl"
    with gzip.open(path, "wb") as f:
        pickle.dump({}, f)

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)
