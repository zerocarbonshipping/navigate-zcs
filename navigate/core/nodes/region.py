# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Region node, the production costs and emissions of a world region."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    command_assignment_to_dict,
    command_assignment_to_tuple_dict,
)
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, REGION, TIMETABLE, VARIABLE

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.input_kinds import ForecastInput, TimetableInput
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.source import Source
    from navigate.core.nodes.transport import Transport


class Region(Node):
    """A fuel-producing region: its process, source, feedstock and transport inputs."""

    def __init__(self, name: str) -> None:
        super().__init__(name, REGION)

        # external variables -----------------------------------------------------------
        # process
        self.process_capex: dict[str, TimetableInput] = {}
        self.process_opex: dict[str, TimetableInput] = {}
        self.process_energy: dict[str, ForecastInput] = {}
        self.process_lifetime: dict[str, ForecastInput | None] = {}
        self.process_replacement: dict[str, ForecastInput] = {}
        self.process_wtt: dict[tuple[str, str], ForecastInput] = {}

        # source
        self.source_capex: dict[str, ForecastInput] = {}
        self.source_opex: dict[str, ForecastInput] = {}
        self.source_wtt: dict[tuple[str, str], ForecastInput] = {}

        # feedstock
        self.feedstock_cost: dict[str, ForecastInput] = {}
        self.feedstock_wtt: dict[tuple[str, str], ForecastInput] = {}

        # transport
        self.transport_cost: dict[str, ForecastInput] = {}
        self.transport_wtt: dict[tuple[str, str], ForecastInput] = {}

    # external methods (DSL commands) --------------------------------------------------
    def set_process_capex(
        self, process_name: str, value: float | TimetableInput
    ) -> None:
        """
        Set the CAPEX associated with a production process in USD/ton.

        Examples
        --------
        - "process_name", 500
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        value
            The CAPEX cost of the process in USD/ton.
        """
        command_assignment_to_dict(
            process_name,
            as_scalar(value),
            self.process_capex,
            type_=(FORECAST, TIMETABLE, VARIABLE),
            lower=0.0,
        )

    def set_process_opex(
        self, process_name: str, value: float | TimetableInput
    ) -> None:
        """
        Set the OPEX associated with a production process in USD/ton/year.

        Notice that OPEX allows negative values so that revenue from byproducts can be
        subtracted from the costs, resulting in potentially negative OPEX.

        Examples
        --------
        - "process_name", 50
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        value
            The OPEX cost of the process in USD/ton/year.
        """
        command_assignment_to_dict(
            process_name,
            as_scalar(value),
            self.process_opex,
            type_=(FORECAST, TIMETABLE, VARIABLE),
        )

    def set_process_energy(
        self, process_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the energy demand required to run a production process in MWh/ton.

        Examples
        --------
        - "process_name", 3.7
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        value
            The energy demand of the process in MWh/ton.
        """
        command_assignment_to_dict(
            process_name,
            as_scalar(value),
            self.process_energy,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_process_lifetime(
        self, process_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the lifetime of a production process in years.

        Examples
        --------
        - "process_name", 25
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        value
            The lifetime of the process in years.
        """
        command_assignment_to_dict(
            process_name,
            as_scalar(value),
            self.process_lifetime,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_process_replacement(
        self, process_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the replacement fraction of CAPEX repaid at the end of a process's lifetime.

        Examples
        --------
        - "process_name", 0.5
        - "process_name", Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        value
            The replacement fraction of the CAPEX repaid at EoL (end of lifetime).
        """
        command_assignment_to_dict(
            process_name,
            as_scalar(value),
            self.process_replacement,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
            upper=1.0,
        )

    def set_process_wtt(
        self, process_name: str, emission_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the WTT emissions from a production process, ton emission/ton fuel.

        Examples
        --------
        - "process_name", "emission_name",  0.5
        - "process_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        process_name
            The name of a process.
        emission_name
            The name of an emission.
        value
            The amount of emissions emitted during the production in ton emissions/ton
            fuel.
        """
        command_assignment_to_tuple_dict(
            (process_name, emission_name),
            as_scalar(value),
            self.process_wtt,
            type_=(FORECAST, VARIABLE),
        )

    def set_source_capex(self, source_name: str, value: float | ForecastInput) -> None:
        """
        Set the CAPEX associated with a source in USD/MWh.

        Examples
        --------
        - "source_name", 50
        - "source_name", Forecast("name")

        Parameters
        ----------
        source_name
            The name of a source.
        value
            The CAPEX cost of the source in USD/MWh.
        """
        command_assignment_to_dict(
            source_name,
            as_scalar(value),
            self.source_capex,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_source_opex(self, source_name: str, value: float | ForecastInput) -> None:
        """
        Set the OPEX associated with a source in USD/MWh/year.

        Examples
        --------
        - "source_name", 50
        - "source_name", Forecast("name")

        Parameters
        ----------
        source_name
            The name of a source.
        value
            The OPEX cost of the source in USD/MWh/year.
        """
        command_assignment_to_dict(
            source_name,
            as_scalar(value),
            self.source_opex,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_source_wtt(
        self, source_name: str, emission_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the WTT emissions of an emission type from using a source, ton emission/MWh.

        Examples
        --------
        - "source_name", "emission_name",  0.5
        - "source_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        source_name
            The name of a source.
        emission_name
            The name of an emission.
        value
            The amount of emissions emitted by using a source in ton emission/MWh.
        """
        command_assignment_to_tuple_dict(
            (source_name, emission_name),
            as_scalar(value),
            self.source_wtt,
            type_=(FORECAST, VARIABLE),
        )

    def set_feedstock_cost(
        self, feedstock_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the cost of a feedstock in USD/ton.

        Examples
        --------
        - "feedstock_name", 150
        - "feedstock_name", Forecast("name")

        Parameters
        ----------
        feedstock_name
            The name of a feedstock.
        value
            The cost of a feedstock in USD/ton.
        """
        command_assignment_to_dict(
            feedstock_name,
            as_scalar(value),
            self.feedstock_cost,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_feedstock_wtt(
        self, feedstock_name: str, emission_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the WTT emissions from a feedstock, ton emission/ton feedstock.

        Examples
        --------
        - "feedstock_name", "emission_name",  0.5
        - "feedstock_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        feedstock_name
            The name of a feedstock.
        emission_name
            The name of an emission.
        value
            The amount of emissions emitted by using a feedstock in ton emission/ton
            feedstock.
        """
        command_assignment_to_tuple_dict(
            (feedstock_name, emission_name),
            as_scalar(value),
            self.feedstock_wtt,
            type_=(FORECAST, VARIABLE),
        )

    def set_transport_cost(
        self, transport_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the cost associated with a transport in USD/ton-nautical mile.

        Examples
        --------
        - "transport_name", 45
        - "transport_name", Forecast("name")

        Parameters
        ----------
        transport_name
            The name of a transport.
        value
            The cost of the transport in USD/ton-nautical mile.
        """
        command_assignment_to_dict(
            transport_name,
            as_scalar(value),
            self.transport_cost,
            type_=(FORECAST, VARIABLE),
            lower=0.0,
        )

    def set_transport_wtt(
        self, transport_name: str, emission_name: str, value: float | ForecastInput
    ) -> None:
        """
        Set the WTT emissions from a transport, ton emission/ton-nautical mile.

        Examples
        --------
        - "transport_name", "emission_name",  0.5
        - "transport_name", "emission_name",  Forecast("name")

        Parameters
        ----------
        transport_name
            The name of a transport.
        emission_name
            The name of an emission.
        value
            The amount of emissions emitted by using a transport in ton
            emission/ton-nautical mile.
        """
        command_assignment_to_tuple_dict(
            (transport_name, emission_name),
            as_scalar(value),
            self.transport_wtt,
            type_=(FORECAST, VARIABLE),
        )

    # internal methods -----------------------------------------------------------------
    def initialize_dependencies(
        self,
        emissions: dict[str, Emission],
        feedstocks: dict[str, Feedstock],
        processes: dict[str, Process],
        sources: dict[str, Source],
        transports: dict[str, Transport],
    ) -> None:
        """
        Initialize dependent dictionaries to allow wildcarding during command calls.

        Parameters
        ----------
        emissions
            All emissions in the simulation.
        feedstocks
            All feedstocks in the simulation.
        processes
            All processes in the simulation.
        sources
            All sources in the simulation.
        transports
            All transports in the simulation.
        """
        for process_name in processes:
            self.process_capex.setdefault(process_name, Scalar(0.0))
            self.process_opex.setdefault(process_name, Scalar(0.0))
            self.process_energy.setdefault(process_name, Scalar(0.0))
            # stays None when unset: Component.initialize_process_component branches on
            # it
            self.process_lifetime.setdefault(process_name, None)
            self.process_replacement.setdefault(process_name, Scalar(0.0))

            for emission_name in emissions:
                self.process_wtt.setdefault((process_name, emission_name), Scalar(0.0))

        for feedstock_name in feedstocks:
            self.feedstock_cost.setdefault(feedstock_name, Scalar(0.0))

            for emission_name in emissions:
                self.feedstock_wtt.setdefault(
                    (feedstock_name, emission_name), Scalar(0.0)
                )

        for source_name in sources:
            self.source_capex.setdefault(source_name, Scalar(0.0))
            self.source_opex.setdefault(source_name, Scalar(0.0))

            for emission_name in emissions:
                self.source_wtt.setdefault((source_name, emission_name), Scalar(0.0))

        for transport_name in transports:
            self.transport_cost.setdefault(transport_name, Scalar(0.0))

            for emission_name in emissions:
                self.transport_wtt.setdefault(
                    (transport_name, emission_name), Scalar(0.0)
                )
