from pydantic import BaseModel


class AccountSnapshot(BaseModel):
    account_id: str
    balance: float
    available_cash: float | None = None
    account_name: str | None = None
    account_type: str | None = None
