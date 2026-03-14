from dataclasses import dataclass


@dataclass(slots=True)
class LightstreamerCredentials:
    account_id: str
    cst: str
    x_security_token: str
    endpoint: str


class LightstreamerGateway:
    def __init__(self) -> None:
        self.connected = False

    async def connect(self, credentials: LightstreamerCredentials) -> None:
        _ = credentials
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
