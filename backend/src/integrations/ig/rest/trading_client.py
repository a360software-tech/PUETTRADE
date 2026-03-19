from collections.abc import Mapping

from integrations.ig.rest.base import IgRestClient
from shared.config.settings import Settings


class IgTradingClient(IgRestClient):
    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    async def open_market_position(
        self,
        *,
        epic: str,
        direction: str,
        size: float,
        auth_headers: Mapping[str, str],
        stop_level: float | None = None,
        limit_level: float | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "currencyCode": "EUR",
            "direction": direction,
            "epic": epic,
            "expiry": "-",
            "forceOpen": True,
            "guaranteedStop": False,
            "orderType": "MARKET",
            "size": size,
        }
        if stop_level is not None:
            payload["stopLevel"] = stop_level
        if limit_level is not None:
            payload["limitLevel"] = limit_level

        return await self.request_json(
            "POST",
            "/positions/otc",
            extra_headers=auth_headers,
            json=payload,
        )

    async def close_position(
        self,
        *,
        deal_id: str,
        direction: str,
        size: float,
        auth_headers: Mapping[str, str],
    ) -> dict[str, object]:
        return await self.request_json(
            "POST",
            "/positions/otc",
            extra_headers={**auth_headers, "_method": "DELETE"},
            json={
                "dealId": deal_id,
                "direction": direction,
                "orderType": "MARKET",
                "size": size,
            },
        )

    async def confirm_deal(self, deal_reference: str, *, auth_headers: Mapping[str, str]) -> dict[str, object]:
        return await self.request_json(
            "GET",
            f"/confirms/{deal_reference}",
            extra_headers=auth_headers,
        )

    async def fetch_open_positions(self, *, auth_headers: Mapping[str, str]) -> dict[str, object]:
        return await self.request_json(
            "GET",
            "/positions",
            extra_headers=auth_headers,
        )
