# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Tests :class:`navigate.output.plot_data.PlotData`."""

from __future__ import annotations

import gzip
import pickle

import pytest

from navigate.exceptions import PlotDataError
from navigate.output.plot_data import PlotData


def _dict_pickle(path):
    with gzip.open(path, "wb") as f:
        pickle.dump({}, f)


def _missing_module_pickle(path):
    # hand-built protocol-0 pickle: GLOBAL opcode naming a module that does
    # not exist, as if written by a Navigate version whose classes have
    # since moved or been renamed.
    data = b"cno_such_module\nThing\n."
    with gzip.open(path, "wb") as f:
        f.write(data)


def _not_a_pickle(path):
    with gzip.open(path, "wb") as f:
        f.write(b"not a pickle at all, just some arbitrary bytes")


def _unsupported_protocol_pickle(path):
    # protocol byte 0xff: no pickle protocol this high exists.
    with gzip.open(path, "wb") as f:
        f.write(b"\x80\xff")


def _truncated_pickle(path):
    data = pickle.dumps({"a": 1, "b": [1, 2, 3] * 1000})
    with gzip.open(path, "wb") as f:
        f.write(data[: len(data) // 2])


def _truncated_gzip(path):
    with gzip.open(path, "wb") as f:
        pickle.dump({"a": 1, "b": [1, 2, 3] * 1000}, f)

    full = path.read_bytes()
    path.write_bytes(full[: len(full) // 2])


def _corrupt_deflate(path):
    with gzip.open(path, "wb") as f:
        pickle.dump({"a": 1, "b": [1, 2, 3] * 1000}, f)

    # keep the 10-byte gzip header intact and corrupt bytes in the middle of
    # the compressed body, so decompression starts but fails mid-stream.
    full = bytearray(path.read_bytes())
    mid = len(full) // 2
    for i in range(mid, mid + 20):
        full[i] ^= 0xFF
    path.write_bytes(bytes(full))


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(_dict_pickle, id="dict_pickle"),
        pytest.param(_not_a_pickle, id="not_a_pickle"),
        pytest.param(_truncated_pickle, id="truncated_pickle"),
        pytest.param(_truncated_gzip, id="truncated_gzip"),
        pytest.param(_missing_module_pickle, id="missing_module"),
        pytest.param(_unsupported_protocol_pickle, id="unsupported_protocol"),
        pytest.param(_corrupt_deflate, id="corrupt_deflate"),
    ],
)
def test_load_rejects_malformed_plot_data(tmp_path, build):
    path = tmp_path / "plot_data.pkl"
    build(path)

    with pytest.raises(PlotDataError) as excinfo:
        PlotData.load(str(path))

    assert str(path) in str(excinfo.value)
