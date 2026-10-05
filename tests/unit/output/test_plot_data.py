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


def test_load_rejects_pickle_referencing_a_missing_module(tmp_path):
    path = tmp_path / "plot_data.pkl"
    # Hand-built protocol-0 pickle: GLOBAL opcode naming a module that does
    # not exist, as if written by a Navigate version whose classes have
    # since moved or been renamed.
    data = b"cno_such_module\nThing\n."
    with gzip.open(path, "wb") as f:
        f.write(data)

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)


def test_load_rejects_gzip_file_that_is_not_a_pickle(tmp_path):
    path = tmp_path / "plot_data.pkl"
    with gzip.open(path, "wb") as f:
        f.write(b"not a pickle at all, just some arbitrary bytes")

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)


def test_load_rejects_truncated_pickle(tmp_path):
    path = tmp_path / "plot_data.pkl"
    data = pickle.dumps({"a": 1, "b": [1, 2, 3] * 1000})
    with gzip.open(path, "wb") as f:
        f.write(data[: len(data) // 2])

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)


def test_load_rejects_truncated_gzip_file(tmp_path):
    path = tmp_path / "plot_data.pkl"
    with gzip.open(path, "wb") as f:
        pickle.dump({"a": 1, "b": [1, 2, 3] * 1000}, f)

    full = path.read_bytes()
    path.write_bytes(full[: len(full) // 2])

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)
