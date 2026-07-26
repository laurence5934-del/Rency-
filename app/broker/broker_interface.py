from __future__ import annotations

from abc import ABC, abstractmethod

from .broker_models import (
    BrokerCapabilities,
    BrokerEnvironment,
    BrokerHealthSnapshot,
    BrokerOrderRequest,
    BrokerOrderResult,
)


class BrokerInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def environment(self) -> BrokerEnvironment:
        raise NotImplementedError

    @property
    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> BrokerHealthSnapshot:
        raise NotImplementedError

    @abstractmethod
    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError
