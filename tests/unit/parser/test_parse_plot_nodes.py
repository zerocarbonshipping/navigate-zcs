# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for Parser.parse_plot_nodes and the replot error handling (used by --replot)."""
import pytest

import navigate.output.plot_data as plot_data_module
from navigate.output import replot as replot_module
from navigate.parser.parser import Parser

PLOT_INC = '''
Plot "custom" {
    Directory = "./plots_custom/"

    add_plot("global_emission_absolute")
    add_plot("fleet_evolution")
}
'''

MULTI_PLOT_INC = '''
Plot "a" {
    Directory = "./a/"
    add_plot("global_emission_absolute")
}

Plot "b" {
    Directory = "./b/"
    add_plot("fleet_evolution")
    add_plot("fleet_speed")
}
'''


def _write_inc(tmp_path, content, name="plots.inc"):
    path = tmp_path / name
    path.write_text(content, encoding="utf8")
    return path


class TestParsePlotNodes:

    def test_directory_and_selected_plots(self, tmp_path):
        """Directory assignment and add_plot commands are both materialized."""
        nodes = Parser.parse_plot_nodes(_write_inc(tmp_path, PLOT_INC))

        assert set(nodes) == {"custom"}
        node = nodes["custom"]
        assert node.directory == "./plots_custom/"
        assert node.selected_plots == {"global_emission_absolute", "fleet_evolution"}

    def test_multiple_plot_nodes(self, tmp_path):
        nodes = Parser.parse_plot_nodes(_write_inc(tmp_path, MULTI_PLOT_INC))

        assert set(nodes) == {"a", "b"}
        assert nodes["a"].selected_plots == {"global_emission_absolute"}
        assert nodes["b"].selected_plots == {"fleet_evolution", "fleet_speed"}

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Parser.parse_plot_nodes(tmp_path / "does_not_exist.inc")


class TestReplotErrors:

    def test_raises_when_no_configs_and_no_include(self, monkeypatch):
        """A pkl with no stored plot configs and no include file is a clear error, not AttributeError."""
        class _Stub:
            plot_configs = []
            deck_directory = "."

        monkeypatch.setattr(plot_data_module.PlotData, "load", classmethod(lambda cls, path: _Stub()))

        with pytest.raises(ValueError, match="no plot configurations"):
            replot_module.replot("dummy.pkl")

    def test_include_without_plot_nodes_raises(self, tmp_path, monkeypatch):
        """An include file supplied but containing no Plot nodes raises an include-specific error."""
        empty_inc = _write_inc(tmp_path, "# no plot nodes here\n", name="empty.inc")

        class _Stub:
            # non-empty on purpose: the include must take precedence over stored configs
            plot_configs = [{"name": "stored", "directory": "./p/", "selected_plots": set()}]
            deck_directory = str(tmp_path)

        monkeypatch.setattr(plot_data_module.PlotData, "load", classmethod(lambda cls, path: _Stub()))

        with pytest.raises(ValueError, match="No Plot nodes were found"):
            replot_module.replot("dummy.pkl", plot_inc=empty_inc)
