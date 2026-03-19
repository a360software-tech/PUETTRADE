from pydantic import BaseModel


class PortfolioProviderPosition(BaseModel):
    epic: str
    side: str
    size: float
    entry_price: float | None = None
    provider: str
    execution_mode: str
    deal_id: str | None = None
    deal_reference: str | None = None


class PortfolioDiscrepancy(BaseModel):
    type: str
    epic: str
    detail: str
    local_position_id: str | None = None
    provider_deal_id: str | None = None


class PortfolioReconciliationReport(BaseModel):
    provider: str
    execution_mode: str
    local_open_positions: int
    provider_open_positions: int
    matched_positions: int
    discrepancies: list[PortfolioDiscrepancy]
