"""Unit tests for the IBKR account-summary adapter.

These tests deliberately avoid a live TWS/IB Gateway connection.
Live connectivity belongs in scripts/manual_tests or integration tests.
"""

from __future__ import annotations

from app.broker import ibkr_official


class FakeIBKRApp:
    def __init__(self) -> None:
        self.accounts = ["DU123456"]
        self.account_summary = [
            {
                "account": "DU123456",
                "tag": "NetLiquidation",
                "value": "100000.00",
                "currency": "USD",
            }
        ]
        self.errors: list[dict] = []
        self.requested = False
        self.cancelled = False
        self.disconnected = False

    def reqAccountSummary(
        self,
        request_id: int,
        group: str,
        tags: str,
    ) -> None:
        self.requested = True
        assert request_id == 9001
        assert group == "All"
        assert "NetLiquidation" in tags

    def cancelAccountSummary(self, request_id: int) -> None:
        assert request_id == 9001
        self.cancelled = True

    def isConnected(self) -> bool:
        return True

    def disconnect(self) -> None:
        self.disconnected = True


def test_get_account_summary_without_live_ibkr(
    monkeypatch,
) -> None:
    fake_app = FakeIBKRApp()

    monkeypatch.setattr(
        ibkr_official,
        "connect_ibkr",
        lambda: fake_app,
    )
    monkeypatch.setattr(
        ibkr_official.time,
        "sleep",
        lambda _seconds: None,
    )

    result = ibkr_official.get_account_summary()

    assert result["connected"] is True
    assert result["accounts"] == ["DU123456"]
    assert result["summary"][0]["tag"] == "NetLiquidation"
    assert fake_app.requested is True
    assert fake_app.cancelled is True
    assert fake_app.disconnected is True


def test_get_account_summary_returns_error_payload(
    monkeypatch,
) -> None:
    fake_app = FakeIBKRApp()

    def raise_request_error(*_args, **_kwargs) -> None:
        raise RuntimeError("simulated account-summary failure")

    fake_app.reqAccountSummary = raise_request_error

    monkeypatch.setattr(
        ibkr_official,
        "connect_ibkr",
        lambda: fake_app,
    )
    monkeypatch.setattr(
        ibkr_official.time,
        "sleep",
        lambda _seconds: None,
    )

    result = ibkr_official.get_account_summary()

    assert result["connected"] is False
    assert result["status"] == "ERROR"
    assert "simulated" in result["message"]
    assert fake_app.disconnected is True
