from typing import Protocol

from authentication.application.service import AuthService, get_auth_service
from execution.domain.models import ExecutionMode
from integrations.ig.rest.trading_client import IgTradingClient
from portfolio.application.dto import PortfolioPositionsResponse, PortfolioQuery, PortfolioReconciliationResponse
from portfolio.domain.models import PortfolioDiscrepancy, PortfolioProviderPosition, PortfolioReconciliationReport
from positions.application.service import PositionsService, get_positions_service
from positions.domain.models import Position, PositionStatus
from shared.config.settings import Settings, get_settings


class PortfolioProvider(Protocol):
    async def list_open_positions(self) -> list[PortfolioProviderPosition]:
        ...


class PaperPortfolioProvider:
    def __init__(self, positions_service: PositionsService) -> None:
        self._positions_service = positions_service

    async def list_open_positions(self) -> list[PortfolioProviderPosition]:
        open_positions = self._positions_service.list_positions(status=PositionStatus.OPEN)
        return [
            PortfolioProviderPosition(
                epic=position.epic,
                side=position.side,
                size=position.size or 0.0,
                entry_price=position.entry_price,
                provider="paper",
                execution_mode=ExecutionMode.PAPER.value,
                deal_id=position.provider_deal_id,
                deal_reference=position.provider_deal_reference,
            )
            for position in open_positions
            if position.execution_mode == ExecutionMode.PAPER.value
        ]


class IgPortfolioProvider:
    def __init__(self, settings: Settings, auth_service: AuthService) -> None:
        self._client = IgTradingClient(settings)
        self._auth_service = auth_service

    async def list_open_positions(self) -> list[PortfolioProviderPosition]:
        access_token = self._auth_service.get_access_token()
        tokens = await self._auth_service.get_session_tokens()
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "CST": tokens.cst,
            "X-SECURITY-TOKEN": tokens.x_security_token,
            "IG-ACCOUNT-ID": tokens.account_id,
            "Version": "2",
        }
        payload = await self._client.fetch_open_positions(auth_headers=auth_headers)
        raw_positions = payload.get("positions")
        if not isinstance(raw_positions, list):
            return []

        provider_positions: list[PortfolioProviderPosition] = []
        for item in raw_positions:
            if not isinstance(item, dict):
                continue
            position = item.get("position") if isinstance(item.get("position"), dict) else item
            market = item.get("market") if isinstance(item.get("market"), dict) else {}
            epic = str(position.get("epic") or market.get("epic") or "")
            direction = str(position.get("direction") or "")
            side = "LONG" if direction.upper() == "BUY" else "SHORT"
            provider_positions.append(
                PortfolioProviderPosition(
                    epic=epic,
                    side=side,
                    size=_as_float(position.get("size")),
                    entry_price=_as_optional_float(position.get("level")),
                    provider="ig",
                    execution_mode=ExecutionMode.IG.value,
                    deal_id=_as_optional_str(position.get("dealId")),
                    deal_reference=_as_optional_str(position.get("dealReference")),
                )
            )
        return provider_positions


class PortfolioService:
    def __init__(self, settings: Settings, positions_service: PositionsService, auth_service: AuthService) -> None:
        self._settings = settings
        self._positions_service = positions_service
        self._paper_provider = PaperPortfolioProvider(positions_service)
        self._ig_provider = IgPortfolioProvider(settings, auth_service)

    async def get_positions(self, query: PortfolioQuery) -> PortfolioPositionsResponse:
        mode = self._resolve_mode(query.execution_mode)
        local_positions = [
            position
            for position in self._positions_service.list_positions(status=PositionStatus.OPEN)
            if position.execution_mode == mode.value
        ]
        provider_positions = await self._provider_for(mode).list_open_positions()
        return PortfolioPositionsResponse(
            provider=mode.value,
            execution_mode=mode.value,
            local_positions=local_positions,
            provider_positions=provider_positions,
        )

    async def reconcile(self, query: PortfolioQuery) -> PortfolioReconciliationResponse:
        snapshot = await self.get_positions(query)
        local_by_key = {_local_key(position): position for position in snapshot.local_positions}
        provider_by_key = {_provider_key(position): position for position in snapshot.provider_positions}

        discrepancies: list[PortfolioDiscrepancy] = []
        matched_positions = 0

        for key, local in local_by_key.items():
            provider = provider_by_key.get(key)
            if provider is None:
                discrepancies.append(
                    PortfolioDiscrepancy(
                        type="missing_provider_position",
                        epic=local.epic,
                        detail="Local open position does not exist in provider snapshot",
                        local_position_id=local.id,
                        provider_deal_id=local.provider_deal_id,
                    )
                )
                continue
            matched_positions += 1
            if local.size is not None and abs(local.size - provider.size) > 1e-9:
                discrepancies.append(
                    PortfolioDiscrepancy(
                        type="size_mismatch",
                        epic=local.epic,
                        detail=f"Local size {local.size} differs from provider size {provider.size}",
                        local_position_id=local.id,
                        provider_deal_id=provider.deal_id,
                    )
                )

        for key, provider in provider_by_key.items():
            if key in local_by_key:
                continue
            discrepancies.append(
                PortfolioDiscrepancy(
                    type="orphan_provider_position",
                    epic=provider.epic,
                    detail="Provider has an open position that is not tracked locally",
                    local_position_id=None,
                    provider_deal_id=provider.deal_id,
                )
            )

        return PortfolioReconciliationResponse(
            report=PortfolioReconciliationReport(
                provider=snapshot.provider,
                execution_mode=snapshot.execution_mode,
                local_open_positions=len(snapshot.local_positions),
                provider_open_positions=len(snapshot.provider_positions),
                matched_positions=matched_positions,
                discrepancies=discrepancies,
            )
        )

    def _resolve_mode(self, requested: ExecutionMode | None) -> ExecutionMode:
        if requested is not None:
            return requested
        configured = self._settings.execution_mode.lower()
        if configured == ExecutionMode.IG.value:
            return ExecutionMode.IG
        return ExecutionMode.PAPER

    def _provider_for(self, mode: ExecutionMode) -> PortfolioProvider:
        if mode == ExecutionMode.IG:
            return self._ig_provider
        return self._paper_provider


def get_portfolio_service() -> PortfolioService:
    return PortfolioService(get_settings(), get_positions_service(), get_auth_service())


def _local_key(position: Position) -> str:
    return position.provider_deal_id or f"{position.epic}:{position.side}:{position.entry_price}"


def _provider_key(position: PortfolioProviderPosition) -> str:
    return position.deal_id or f"{position.epic}:{position.side}:{position.entry_price}"


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: object) -> float:
    optional = _as_optional_float(value)
    return 0.0 if optional is None else optional
