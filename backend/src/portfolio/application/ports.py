from typing import Protocol

from portfolio.domain.models import PortfolioProviderPosition


class PortfolioPort(Protocol):
    async def list_open_positions(self) -> list[PortfolioProviderPosition]:
        ...
