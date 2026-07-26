from __future__ import annotations

from ..broker_models import BrokerEnvironment
from ..simulated.simulated_broker import SimulatedBroker


class PaperBroker(SimulatedBroker):
    @property
    def name(self) -> str:
        return "PAPER"

    @property
    def environment(self) -> BrokerEnvironment:
        return BrokerEnvironment.PAPER
