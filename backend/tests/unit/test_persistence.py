import asyncio
from pathlib import Path

from authentication.application.dto import SessionStatusResponse
from engine.application.dto import EngineStartRequest
from engine.application.service import EngineService
from engine.infrastructure.repository import EngineStateRepository
from execution.application.dto import ExecuteSignalRequest
from execution.application.service import ExecutionService
from execution.infrastructure.repository import ExecutionEventRepository
from market_discovery.application.service import MarketDiscoveryService
from portfolio.application.service import PortfolioService
from positions.application.dto import CreatePositionFromSignalRequest
from positions.application.service import PositionsService
from positions.infrastructure.repository import PositionRepository
from risk.application.service import RiskService
from safety.application.service import SafetyService
from shared.config.settings import get_settings
from shared.infrastructure.persistence import DatabasePersistence
from strategy.application.service import get_strategy_service
from strategy.domain.models import SignalSide, StrategySignal


class _AuthStub:
    def get_access_token(self) -> str:
        return ""

    def get_status(self) -> SessionStatusResponse:
        return SessionStatusResponse(authenticated=False)

    async def get_session_tokens(self):
        raise RuntimeError("not used in paper mode")


def test_positions_service_loads_persisted_positions(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "positions.sqlite3")
    repository = PositionRepository(persistence)
    first = PositionsService(get_strategy_service(), repository=repository)

    first.open_from_signal(
        CreatePositionFromSignalRequest(
            epic="CS.D.EURUSD.CFD.IP",
            signal=StrategySignal(
                side=SignalSide.LONG,
                price=1.1010,
                time="2026-03-18T12:00:00",
                reason="EMA_CROSS_UP",
            ),
        )
    )

    second = PositionsService(get_strategy_service(), repository=repository)

    assert len(second.list_positions()) == 1
    assert second.list_positions()[0].epic == "CS.D.EURUSD.CFD.IP"


def test_engine_service_loads_persisted_mode_and_epics(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "engine.sqlite3")
    positions = PositionsService(get_strategy_service(), repository=PositionRepository(persistence))
    auth = _AuthStub()
    execution = ExecutionService(
        get_settings(),
        RiskService(get_strategy_service(), positions),
        SafetyService(
            get_settings(),
            auth,
            PortfolioService(get_settings(), positions, auth),
            MarketDiscoveryService(get_settings(), auth),
        ),
        positions,
        auth,
        repository=ExecutionEventRepository(persistence),
    )
    first = EngineService(execution, repository=EngineStateRepository(persistence))

    first.start(EngineStartRequest(epics=["CS.D.EURUSD.CFD.IP"]))

    second = EngineService(execution, repository=EngineStateRepository(persistence))
    status = second.get_status()

    assert status.mode.value == "RUNNING"
    assert status.active_epics == ["CS.D.EURUSD.CFD.IP"]


def test_execution_service_persists_execution_events(tmp_path: Path) -> None:
    persistence = DatabasePersistence(tmp_path / "execution.sqlite3")
    positions = PositionsService(get_strategy_service(), repository=PositionRepository(persistence))
    risk = RiskService(get_strategy_service(), positions)
    auth = _AuthStub()
    execution = ExecutionService(
        get_settings(),
        risk,
        SafetyService(
            get_settings(),
            auth,
            PortfolioService(get_settings(), positions, auth),
            MarketDiscoveryService(get_settings(), auth),
        ),
        positions,
        auth,
        repository=ExecutionEventRepository(persistence),
    )

    asyncio.run(
        execution.execute_from_signal(
            ExecuteSignalRequest(
                epic="CS.D.EURUSD.CFD.IP",
                signal={
                    "side": "SHORT",
                    "price": 1.1050,
                    "time": "2026-03-18T12:00:00",
                    "momentum": 75.0,
                    "reason": "RSI > 70",
                },
                settings={"account_balance": 10000},
            )
        )
    )

    events = persistence.load_execution_events()

    assert len(events) == 1
    assert events[0]["event_type"] == "open_signal"
    assert events[0]["execution_mode"] == "paper"
