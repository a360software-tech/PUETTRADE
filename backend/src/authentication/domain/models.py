from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UserSession:
    account_id: str
    client_id: str
    lightstreamer_endpoint: str
    access_token: str
    refresh_token: str
    expires_at: datetime
    is_demo: bool = False


@dataclass(slots=True)
class StreamingTokens:
    cst: str
    x_security_token: str
    account_id: str
