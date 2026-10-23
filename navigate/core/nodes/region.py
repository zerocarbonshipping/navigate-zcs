# SPDX-FileCopyrightText: 2026 Fonden Mærsk Mc-Kinney Møller Center for Zero Carbon Shipping
# SPDX-License-Identifier: Apache-2.0

"""Define the Region node, the production costs and emissions of a world region."""

from __future__ import annotations

from typing import TYPE_CHECKING

from navigate.core import (
    Scalar,
    as_scalar,
    assign_value,
    deck_command,
    write_matching_key_pairs,
    write_matching_keys,
)
from navigate.core.node import Node
from navigate.core.node_type import FORECAST, REGION, TIMETABLE, VARIABLE

if TYPE_CHECKING:
    from navigate.core.nodes.emission import Emission
    from navigate.core.nodes.feedstock import Feedstock
    from navigate.core.nodes.process import Process
    from navigate.core.nodes.source import Source
    from navigate.core.nodes.transport import Transport
    from navigate.core.types_ import (
        ForecastArgument,
        ForecastInput,
        TimetableArgument,
        TimetableInput,
    )


class Region(Node):
    """A fuel-producing region: its process, source, feedstock and transport inputs."""

    type = REGION

    def __init__(self, name: str) -> None:
        super().__init__(name)

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
    @deck_command()
    def set_process_capex(self, process_name: str, value: TimetableArgument) -> None:
        """Set the CAPEX of a production process."""
        write_matching_keys(
            process_name,
            assign_value(
                as_scalar(value), type_=(FORECAST, TIMETABLE, VARIABLE), lower=0.0
            ),
            self.process_capex,
        )

    @deck_command()
    def set_process_opex(self, process_name: str, value: TimetableArgument) -> None:
        """Set the OPEX of a production process."""
        write_matching_keys(
            process_name,
            assign_value(as_scalar(value), type_=(FORECAST, TIMETABLE, VARIABLE)),
            self.process_opex,
        )

    @deck_command()
    def set_process_energy(self, process_name: str, value: ForecastArgument) -> None:
        """Set the energy demand of a production process."""
        write_matching_keys(
            process_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.process_energy,
        )

    @deck_command()
    def set_process_lifetime(self, process_name: str, value: ForecastArgument) -> None:
        """Set the lifetime of a production process."""
        write_matching_keys(
            process_name,
            assign_value(
                as_scalar(value),
                type_=(FORECAST, VARIABLE),
                lower=0.0,
                inclusive_lower=False,
            ),
            self.process_lifetime,
        )

    @deck_command()
    def set_process_replacement(
        self, process_name: str, value: ForecastArgument
    ) -> None:
        """Set the fraction of CAPEX repaid at the end of a process's lifetime."""
        write_matching_keys(
            process_name,
            assign_value(
                as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0, upper=1.0
            ),
            self.process_replacement,
        )

    @deck_command()
    def set_process_wtt(
        self, process_name: str, emission_name: str, value: ForecastArgument
    ) -> None:
        """Set the WTT emissions of a production process for an emission."""
        write_matching_key_pairs(
            (process_name, emission_name),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.process_wtt,
        )

    @deck_command()
    def set_source_capex(self, source_name: str, value: ForecastArgument) -> None:
        """Set the CAPEX of a source."""
        write_matching_keys(
            source_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.source_capex,
        )

    @deck_command()
    def set_source_opex(self, source_name: str, value: ForecastArgument) -> None:
        """Set the OPEX of a source."""
        write_matching_keys(
            source_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.source_opex,
        )

    @deck_command()
    def set_source_wtt(
        self, source_name: str, emission_name: str, value: ForecastArgument
    ) -> None:
        """Set the WTT emissions of a source for an emission."""
        write_matching_key_pairs(
            (source_name, emission_name),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.source_wtt,
        )

    @deck_command()
    def set_feedstock_cost(self, feedstock_name: str, value: ForecastArgument) -> None:
        """Set the cost of a feedstock."""
        write_matching_keys(
            feedstock_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.feedstock_cost,
        )

    @deck_command()
    def set_feedstock_wtt(
        self, feedstock_name: str, emission_name: str, value: ForecastArgument
    ) -> None:
        """Set the WTT emissions of a feedstock for an emission."""
        write_matching_key_pairs(
            (feedstock_name, emission_name),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.feedstock_wtt,
        )

    @deck_command()
    def set_transport_cost(self, transport_name: str, value: ForecastArgument) -> None:
        """Set the cost of a transport."""
        write_matching_keys(
            transport_name,
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE), lower=0.0),
            self.transport_cost,
        )

    @deck_command()
    def set_transport_wtt(
        self, transport_name: str, emission_name: str, value: ForecastArgument
    ) -> None:
        """Set the WTT emissions of a transport for an emission."""
        write_matching_key_pairs(
            (transport_name, emission_name),
            assign_value(as_scalar(value), type_=(FORECAST, VARIABLE)),
            self.transport_wtt,
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
        # a None lifetime lasts the plant's life, so no replacement cycle is attached
        for process_name in processes:
            self.process_capex.setdefault(process_name, Scalar(0.0))
            self.process_opex.setdefault(process_name, Scalar(0.0))
            self.process_energy.setdefault(process_name, Scalar(0.0))
            self.process_lifetime.setdefault(process_name, None)
            self.process_replacement.setdefault(process_name, Scalar(0.0))

            for emission_name in emissions:
                key = (process_name, emission_name)
                self.process_wtt.setdefault(key, Scalar(0.0))

        for source_name in sources:
            self.source_capex.setdefault(source_name, Scalar(0.0))
            self.source_opex.setdefault(source_name, Scalar(0.0))

            for emission_name in emissions:
                key = (source_name, emission_name)
                self.source_wtt.setdefault(key, Scalar(0.0))

        for feedstock_name in feedstocks:
            self.feedstock_cost.setdefault(feedstock_name, Scalar(0.0))

            for emission_name in emissions:
                key = (feedstock_name, emission_name)
                self.feedstock_wtt.setdefault(key, Scalar(0.0))

        for transport_name in transports:
            self.transport_cost.setdefault(transport_name, Scalar(0.0))

            for emission_name in emissions:
                key = (transport_name, emission_name)
                self.transport_wtt.setdefault(key, Scalar(0.0))
