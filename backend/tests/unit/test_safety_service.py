import asyncio

from execution.domain.models import ExecutionMode
from positions.application.service import get_positions_service
from safety.application.dto import RegisterTradeRequest, SafetyQuery
from safety.application.service import get_safety_service


def setup_function() -> None:
    get_positions_service().reset()
    get_safety_service().reset()


def test_safety_service_allows_paper_trade_when_system_is_clean() -> None:
    report = asyncio.run(get_safety_service().evaluate(SafetyQuery(epic="CS.D.EURUSD.CFD.IP")))

    assert report.can_open_new_trade is True
    assert report.status.value == "OPERATIONAL"


def test_safety_service_blocks_trade_during_grace_period() -> None:
    service = get_safety_service()
    service.register_trade_execution(RegisterTradeRequest(epic="CS.D.EURUSD.CFD.IP"))

    report = asyncio.run(service.evaluate(SafetyQuery(epic="CS.D.EURUSD.CFD.IP")))

    assert report.can_open_new_trade is False
    assert any(check.name == "grace_period" and not check.passed for check in report.checks)
def test_safety_service_blocks_ig_trade_without_authenticated_session() -> None:
    report = asyncio.run(
        get_safety_service().evaluate(
            SafetyQuery(epic="CS.D.EURUSD.CFD.IP", execution_mode=ExecutionMode.IG)
        )
    )

    assert report.can_open_new_trade is False
    assert any(check.name == "authenticated_session" and not check.passed for check in report.checks)
