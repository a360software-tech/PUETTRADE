import asyncio

from execution.application.dto import ExecuteSignalRequest
from execution.application.service import get_execution_service
from portfolio.application.dto import PortfolioQuery
from portfolio.application.service import get_portfolio_service
from positions.application.service import get_positions_service


def setup_function() -> None:
    get_positions_service().reset()


def test_portfolio_service_returns_matching_paper_positions() -> None:
    execution = get_execution_service()
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

    portfolio = get_portfolio_service()
    response = asyncio.run(portfolio.get_positions(PortfolioQuery()))

    assert response.provider == "paper"
    assert len(response.local_positions) == 1
    assert len(response.provider_positions) == 1


def test_portfolio_reconcile_reports_no_discrepancies_for_paper_positions() -> None:
    execution = get_execution_service()
    asyncio.run(
        execution.execute_from_signal(
            ExecuteSignalRequest(
                epic="CS.D.EURUSD.CFD.IP",
                signal={
                    "side": "LONG",
                    "price": 1.1010,
                    "time": "2026-03-18T12:00:00",
                    "momentum": 30.0,
                    "reason": "RSI < 30",
                },
                settings={"account_balance": 10000},
            )
        )
    )

    portfolio = get_portfolio_service()
    response = asyncio.run(portfolio.reconcile(PortfolioQuery()))

    assert response.report.matched_positions == 1
    assert response.report.discrepancies == []
